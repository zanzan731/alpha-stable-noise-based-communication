"""Shared framed alpha-stable SDR protocol used by sender and receiver.

The synchronization word and header are deterministic BPSK.  Only the payload
uses alpha-stable symbols, so acquisition does not depend on a statistical
estimate and the payload modulation remains unchanged in principle.
"""

import struct
import sys
import time
import zlib

import numpy as np
from gnuradio import gr


SYNC_WORD = 0x1ACFFC1D  # 32-bit CCSDS attached synchronization marker
MIN_SYNC_SYMBOLS = 32
MAGIC = 0xD39A
HEADER_BYTES = 10  # uint16 magic, uint32 payload length, uint32 CRC32
HEADER_BITS = HEADER_BYTES * 8
MAX_SAMPLE_CLOCK_ERROR_PPM = 20.0


def bytes_to_bits(data):
    """Return least-significant-bit-first bits, matching the payload mapping."""
    values = np.frombuffer(bytes(data), dtype=np.uint8)
    return np.unpackbits(values, bitorder="little").astype(np.uint8, copy=False)


def bits_to_bytes(bits):
    bits = np.asarray(bits, dtype=np.uint8)
    if len(bits) % 8:
        raise ValueError("Number of bits must be a multiple of 8")
    return np.packbits(bits, bitorder="little").tobytes()


def sync_pattern(symbols=MIN_SYNC_SYMBOLS):
    """Build a deterministic, non-periodic +/-1 synchronization sequence."""
    symbols = max(MIN_SYNC_SYMBOLS, int(symbols))
    word_bits = np.asarray(
        [(SYNC_WORD >> (31 - index)) & 1 for index in range(32)],
        dtype=np.float32,
    )
    bits = np.resize(word_bits, symbols)
    return np.where(bits > 0, 1.0, -1.0).astype(np.float32)


class alpha_decoder(gr.basic_block):
    """Acquire framed bursts, validate the header, and decode alpha payloads."""

    STATE_SEARCH_SYNC = 0
    STATE_HEADER = 1
    STATE_PAYLOAD = 2

    def __init__(
        self,
        beta_map=(-1.0, 1.0),
        samples_per_symbol=500,
        L=20,
        sync_symbols=MIN_SYNC_SYMBOLS,
        sync_threshold=0.75,
        sync_corr_threshold=None,
        sync_coherence_threshold=0.08,
        header_repetitions=3,
        max_payload_bytes=1000000,
        debug_symbols=20,
        expected_output_bytes=128,
        timing_guard_symbols=6,
    ):
        gr.basic_block.__init__(
            self, name="alpha_decoder", in_sig=[np.complex64], out_sig=[np.uint8]
        )
        self.beta_map = np.asarray(beta_map, dtype=np.float64)
        self.samples_per_symbol = int(samples_per_symbol)
        self.L = int(L)
        self.sync_symbols = max(MIN_SYNC_SYMBOLS, int(sync_symbols))
        self.sync_threshold = float(
            sync_threshold if sync_corr_threshold is None else sync_corr_threshold
        )
        self.sync_coherence_threshold = float(sync_coherence_threshold)
        self.header_repetitions = int(header_repetitions)
        self.max_payload_bytes = int(max_payload_bytes)
        self.debug_symbols = int(debug_symbols)
        self.expected_output_bytes = (
            None if expected_output_bytes is None else int(expected_output_bytes)
        )
        self.timing_guard_symbols = int(timing_guard_symbols)
        self.symbol_edge_guard = max(
            2, min(8, self.samples_per_symbol // 25)
        )
        self.decision_sample_count = (
            self.samples_per_symbol - 2 * self.symbol_edge_guard
        )

        if len(self.beta_map) != 2:
            raise ValueError("beta_map must contain exactly two values")
        if self.samples_per_symbol <= 0 or self.L <= 0:
            raise ValueError("samples_per_symbol and L must be positive")
        if self.decision_sample_count < 4:
            raise ValueError("samples_per_symbol is too small for the timing guard")
        if self.header_repetitions < 1 or self.header_repetitions % 2 == 0:
            raise ValueError("header_repetitions must be a positive odd number")
        if self.expected_output_bytes is not None and self.expected_output_bytes <= 0:
            raise ValueError("expected_output_bytes must be positive or None")
        if self.timing_guard_symbols < 2:
            raise ValueError("timing_guard_symbols must be at least 2")

        self._pattern = sync_pattern(self.sync_symbols).astype(np.complex64)
        self._sample_buffer = np.empty(0, dtype=np.complex64)
        self._output_queue = bytearray()
        self._state = self.STATE_SEARCH_SYNC
        self._cfo = 0.0
        self._channel_phase = 0.0
        self._packet_sample_offset = 0
        self._sync_samples = np.empty(0, dtype=np.complex64)
        self._payload_length = 0
        self._expected_crc = 0

        self._work_call = 0
        self._total_samples_seen = 0
        self._total_output_bytes = 0
        self._sync_count = 0
        self._candidate_count = 0
        self._search_attempts = 0
        self._crc_ok = 0
        self._crc_fail = 0
        # One-packet receiver completion state. packet_decoded means the
        # payload is in the output queue; packet_output_complete is set only
        # after GNU Radio has accepted every decoded byte from that queue.
        self.packet_decoded = False
        self.packet_output_complete = False
        self.completed_payload_bytes = 0

        print(
            "\n[DEC INIT] protocol=PN32+REPEATED_HEADER+PILOTED_ALPHA_STABLE_PAYLOAD",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[DEC INIT] samples_per_symbol={self.samples_per_symbol} "
            f"L_requested={self.L} "
            f"L_effective={self._effective_segment_count(self.decision_sample_count)} "
            f"samples_per_segment={self.decision_sample_count // self._effective_segment_count(self.decision_sample_count)} "
            f"edge_guard={self.symbol_edge_guard} "
            f"sync_symbols={self.sync_symbols} corr_threshold={self.sync_threshold:.2f} "
            f"coherence_threshold={self.sync_coherence_threshold:.2f} "
            f"header_repetitions={self.header_repetitions} "
            f"payload_pilot=BEFORE_EACH_DATA_SYMBOL "
            f"timing_guard={self.timing_guard_symbols}",
            file=sys.stderr,
            flush=True,
        )

    def forecast(self, noutput_items, ninputs):
        return [1] * int(ninputs)

    def append_input(self, data):
        if len(data):
            self._sample_buffer = np.concatenate(
                (self._sample_buffer, np.asarray(data, dtype=np.complex64))
            )

    @staticmethod
    def _estimate_cfo(samples):
        """Estimate radians/sample with BPSK sign removed by squaring."""
        samples = np.asarray(samples, dtype=np.complex64)
        if len(samples) < 2:
            return 0.0
        # Remove the stationary B210 LO/DC component. Squaring then removes
        # the wanted BPSK +/- sign without being confused by bit transitions.
        samples = samples - np.mean(samples)
        squared = samples * samples
        product = np.vdot(squared[:-1], squared[1:])
        if abs(product) < 1e-12:
            return 0.0
        return 0.5 * float(np.angle(product))

    def find_sync(self):
        preamble_length = self.sync_symbols * self.samples_per_symbol
        if len(self._sample_buffer) < preamble_length:
            return None

        # Search the complete rolling buffer.  UHD commonly delivers chunks
        # larger than one symbol, so the burst may begin thousands of samples
        # after the buffer start rather than within the first symbol period.
        # Do not let a large already-buffered stochastic payload dominate the
        # carrier estimate; acquisition only needs the preamble and early
        # deterministic header.
        search_length = min(len(self._sample_buffer), 2 * preamble_length)
        raw_search = self._sample_buffer[:search_length]
        search = raw_search - np.mean(raw_search)
        cfo = self._estimate_cfo(search)
        index = np.arange(search_length, dtype=np.float64)
        corrected = search * np.exp(-1j * cfo * index)
        cumulative = np.concatenate(
            (np.zeros(1, dtype=np.complex128), np.cumsum(corrected, dtype=np.complex128))
        )
        cumulative_power = np.concatenate(
            (
                np.zeros(1, dtype=np.float64),
                np.cumsum(np.abs(search) ** 2, dtype=np.float64),
            )
        )

        max_offset = search_length - preamble_length + 1
        if max_offset <= 0:
            return None

        offsets = np.arange(max_offset, dtype=np.int64)
        symbol_starts = (
            np.arange(self.sync_symbols, dtype=np.int64)[:, None]
            * self.samples_per_symbol
            + offsets[None, :]
        )
        means = (
            cumulative[symbol_starts + self.samples_per_symbol]
            - cumulative[symbol_starts]
        ) / self.samples_per_symbol
        # Remove the known PN signs. Any remaining phase progression between
        # symbol means is residual CFO left by the sample-level estimator.
        despread = np.conjugate(self._pattern)[:, None] * means
        phase_step_values = np.sum(
            np.conjugate(despread[:-1]) * despread[1:], axis=0
        )
        residual_phase_steps = np.angle(phase_step_values)
        symbol_indices = np.arange(self.sync_symbols, dtype=np.float64)[:, None]
        aligned_despread = despread * np.exp(
            -1j * symbol_indices * residual_phase_steps[None, :]
        )
        correlation_values = np.sum(aligned_despread, axis=0)
        means_energy = np.sum(np.abs(means) ** 2, axis=0)
        correlations = np.abs(correlation_values) / (
            np.sqrt(float(self.sync_symbols) * means_energy) + 1e-12
        )
        sample_powers = (
            cumulative_power[offsets + preamble_length] - cumulative_power[offsets]
        ) / preamble_length
        coherences = (means_energy / self.sync_symbols) / (sample_powers + 1e-12)
        metrics = correlations * np.minimum(1.0, coherences)
        offset = int(np.argmax(metrics))
        correlation = float(correlations[offset])
        coherence = float(coherences[offset])
        residual_cfo = float(residual_phase_steps[offset]) / self.samples_per_symbol
        final_cfo = cfo + residual_cfo
        # Re-fit channel phase directly against the raw candidate using the
        # improved CFO and frame-relative indices.
        candidate = raw_search[offset : offset + preamble_length]
        candidate_index = np.arange(preamble_length, dtype=np.float64)
        known_sync = np.repeat(self._pattern, self.samples_per_symbol)
        channel = np.vdot(
            known_sync,
            candidate * np.exp(-1j * final_cfo * candidate_index),
        )
        phase = float(np.angle(channel))
        self._search_attempts += 1
        if (
            self._search_attempts == 1
            or self._search_attempts % 8 == 0
            or correlation >= self.sync_threshold * 0.85
        ):
            print(
                f"[SYNC SEARCH] best_offset={offset} corr={correlation:.4f} "
                f"coherence={coherence:.4f} cfo={final_cfo:+.6e} rad/sample "
                f"residual={residual_cfo:+.2e} "
                f"power={float(sample_powers[offset]):.3e}",
                file=sys.stderr,
                flush=True,
            )
        if correlation < self.sync_threshold or coherence < self.sync_coherence_threshold:
            return None

        self._candidate_count += 1
        print(
            f"[SYNC CANDIDATE] offset={offset} corr={correlation:.4f} "
            f"coherence={coherence:.4f} cfo={final_cfo:+.6e} rad/sample",
            file=sys.stderr,
            flush=True,
        )
        return offset, final_cfo, phase

    def _correct_packet_samples(self, samples, relative_start):
        index = relative_start + np.arange(len(samples), dtype=np.float64)
        return np.asarray(samples) * np.exp(-1j * (self._channel_phase + self._cfo * index))

    def _track_and_correct_carrier(self, samples):
        """Correct a real-valued modulation while following slow LO drift.

        Squaring removes both BPSK signs and the signs of alpha-stable samples.
        A blockwise phase estimate then tracks residual phase instead of
        assuming one perfectly constant CFO throughout a multi-second packet.
        The returned real axis has an unavoidable global +/- ambiguity, which
        the header magic or payload CRC resolves.
        """
        samples = np.asarray(samples, dtype=np.complex64)
        if len(samples) < 2:
            return samples, 0.0
        centered = samples - np.mean(samples)
        coarse_cfo = self._estimate_cfo(centered)
        index = np.arange(len(centered), dtype=np.float64)
        squared_derotated = centered * centered * np.exp(-2j * coarse_cfo * index)

        block_size = max(32, min(100, self.samples_per_symbol // 4))
        block_count = len(centered) // block_size
        if block_count < 2:
            phase = coarse_cfo * index
            return centered * np.exp(-1j * phase), coarse_cfo

        usable = block_count * block_size
        phasors = np.sum(
            squared_derotated[:usable].reshape(block_count, block_size), axis=1
        )
        residual_phase_twice = np.unwrap(np.angle(phasors))
        centers = (
            np.arange(block_count, dtype=np.float64) * block_size
            + (block_size - 1) / 2.0
        )
        interpolated = np.interp(
            index,
            centers,
            residual_phase_twice,
            left=residual_phase_twice[0],
            right=residual_phase_twice[-1],
        )
        carrier_phase = coarse_cfo * index + 0.5 * interpolated
        corrected = centered * np.exp(-1j * carrier_phase)
        return corrected, coarse_cfo

    def _effective_segment_count(self, sample_count):
        """Choose enough extrema segments for a statistically useful estimate.

        L=2 compares only two maxima and two minima and is effectively random.
        Use the configured L only when it produces four to six samples per
        segment; otherwise fall back to about five samples per segment. This
        prevents both the old L=2 failure for long symbols and over-segmentation
        for short symbols. The estimator discards only a final incomplete
        segment when the sample count is not exactly divisible.
        """
        sample_count = int(sample_count)
        if sample_count <= 1:
            return 1
        maximum = max(1, sample_count // 2)
        configured = min(maximum, max(2, self.L))
        configured_length = sample_count // configured
        if 4 <= configured_length <= 6:
            return configured
        return min(maximum, max(2, sample_count // 5))

    def _estimate_beta_legacy(self, symbol_samples):
        segment_count = self._effective_segment_count(len(symbol_samples))
        required = (len(symbol_samples) // segment_count) * segment_count
        if len(symbol_samples) < required:
            return 0.0
        x = np.asarray(symbol_samples[:required]).real.astype(np.float32, copy=False)
        segments = x.reshape(segment_count, required // segment_count)
        maximums = np.max(segments, axis=1)
        minimums = np.min(segments, axis=1)
        max_std = float(np.std(maximums, ddof=1)) if segment_count > 1 else 0.0
        min_std = float(np.std(minimums, ddof=1)) if segment_count > 1 else 0.0
        return float(np.clip((max_std - min_std) / (max_std + min_std + 1e-12), -1.0, 1.0))

    def _estimate_beta_logarithmic(self, symbol_samples):
        segment_count = self._effective_segment_count(len(symbol_samples))
        required = (len(symbol_samples) // segment_count) * segment_count
        if len(symbol_samples) < required:
            return 0.0
        x = np.asarray(symbol_samples[:required]).real.astype(np.float64, copy=False)
        segments = x.reshape(segment_count, required // segment_count)
        maximums = np.max(segments, axis=1)
        minimum_magnitudes = -np.min(segments, axis=1)
        valid = (
            np.isfinite(maximums)
            & np.isfinite(minimum_magnitudes)
            & (maximums > 0.0)
            & (minimum_magnitudes > 0.0)
        )
        if np.count_nonzero(valid) < 2:
            return 0.0
        y_max = np.log(maximums[valid])
        y_min = np.log(minimum_magnitudes[valid])
        mean_max = float(np.mean(y_max))
        mean_min = float(np.mean(y_min))
        std_max = float(np.std(y_max, ddof=1))
        std_min = float(np.std(y_min, ddof=1))
        if (
          not np.all(np.isfinite([mean_max, mean_min, std_max, std_min]))
          or std_max <= 1e-12
            or std_min <= 1e-12
        ):
          return 0.0
        alpha_hat = np.pi / (2.0 * np.sqrt(6.0)) * (
            1.0 / std_max + 1.0 / std_min
        )
        log_tail_ratio = alpha_hat * (mean_max - mean_min)
        beta_hat = np.tanh(0.5 * log_tail_ratio)
        return float(np.clip(beta_hat, -1.0, 1.0))

    def estimate_beta(self, symbol_samples):
        # The legacy estimator is more robust to residual OTA offsets.
        return self._estimate_beta_legacy(symbol_samples)

    def estimate_bit(self, symbol_samples):
        beta = self.estimate_beta(symbol_samples)
        distances = np.abs(self.beta_map - beta)
        return int(np.argmin(distances)), beta

    def _find_variance_transition(
        self,
        magnitudes,
        predicted,
        stable_before,
        search_radius=None,
        stable_after_window=None,
    ):
        """Locate a pilot/data boundary from distance to the pilot level."""
        magnitudes = np.asarray(magnitudes, dtype=np.float64)
        window = max(64, self.samples_per_symbol // 2)
        radius = (
            self.samples_per_symbol // 2
            if search_radius is None
            else max(self.samples_per_symbol // 2, int(search_radius))
        )
        after_window = (
            window if stable_after_window is None else int(stable_after_window)
        )
        first = max(window, int(round(predicted)) - radius)
        last = min(len(magnitudes) - after_window, int(round(predicted)) + radius)
        if last < first:
            return int(np.clip(round(predicted), 0, len(magnitudes)))

        candidates = np.arange(first, last + 1, dtype=np.int64)
        if stable_before:
            reference_slice = magnitudes[
                max(0, int(predicted) - self.samples_per_symbol) :
                max(1, int(predicted) - window)
            ]
        else:
            # The end of the captured timing guard is guaranteed to be inside
            # the deterministic tail even when a long payload accumulates
            # hundreds of samples of clock drift.
            reference_slice = magnitudes[-self.samples_per_symbol :]
        if len(reference_slice) == 0:
            reference_slice = magnitudes[max(0, first - window) : min(len(magnitudes), last + window)]
        pilot_level = float(np.median(reference_slice))
        squared_error = (magnitudes - pilot_level) ** 2
        cumulative_error = np.concatenate(
            (np.zeros(1, dtype=np.float64), np.cumsum(squared_error))
        )
        before_error = (
            cumulative_error[candidates] - cumulative_error[candidates - window]
        ) / window
        after_error = (
            cumulative_error[candidates + after_window] - cumulative_error[candidates]
        ) / after_window
        scores = after_error - before_error if stable_before else before_error - after_error
        # Resolve very flat maxima toward the expected position.
        scores -= 1e-8 * np.abs(candidates - predicted)
        return int(candidates[int(np.argmax(scores))])

    @staticmethod
    def _interpolate_complex(samples, positions):
        positions = np.clip(positions, 0.0, max(0.0, len(samples) - 1.000001))
        lower = np.floor(positions).astype(np.int64)
        fraction = positions - lower
        upper = np.minimum(lower + 1, len(samples) - 1)
        return samples[lower] * (1.0 - fraction) + samples[upper] * fraction

    def reset_packet_state(self):
        self._state = self.STATE_SEARCH_SYNC
        self._cfo = 0.0
        self._channel_phase = 0.0
        self._packet_sample_offset = 0
        self._sync_samples = np.empty(0, dtype=np.complex64)
        self._payload_length = 0
        self._expected_crc = 0

    def _acquire_candidate(self):
        result = self.find_sync()
        if result is None:
            keep = self.sync_symbols * self.samples_per_symbol + self.samples_per_symbol - 1
            if len(self._sample_buffer) > keep:
                self._sample_buffer = self._sample_buffer[-keep:]
            return False

        offset, self._cfo, self._channel_phase = result
        preamble_length = self.sync_symbols * self.samples_per_symbol
        self._sync_samples = self._sample_buffer[offset : offset + preamble_length].copy()
        self._sample_buffer = self._sample_buffer[offset + preamble_length :]
        self._packet_sample_offset = preamble_length
        self._state = self.STATE_HEADER
        return True

    def decode_header(self):
        header_symbols = HEADER_BITS * self.header_repetitions
        needed = header_symbols * self.samples_per_symbol
        if len(self._sample_buffer) < needed:
            return None

        raw = self._sample_buffer[:needed]
        corrected, tracked_cfo = self._track_and_correct_carrier(raw)
        means = corrected.reshape(header_symbols, self.samples_per_symbol).real.mean(axis=1)
        raw_bits = (means > 0.0).astype(np.uint8)

        decoded = None
        header_polarity = 1
        for polarity in (1, -1):
            candidate_bits = raw_bits if polarity > 0 else (1 - raw_bits)
            repetitions = candidate_bits.reshape(self.header_repetitions, HEADER_BITS)
            header_bits = (
                np.sum(repetitions, axis=0) > self.header_repetitions // 2
            ).astype(np.uint8)
            magic, length, expected_crc = struct.unpack(
                "<HII", bits_to_bytes(header_bits)
            )
            if (
                magic == MAGIC
                and 0 < length <= self.max_payload_bytes
            ):
                decoded = (length, expected_crc)
                header_polarity = polarity
                break

        if decoded is None:
            magic, length, _ = struct.unpack(
                "<HII", bits_to_bytes(raw_bits[:HEADER_BITS])
            )
            print(
                f"[SYNC REJECTED] invalid tracked header magic=0x{magic:04X} "
                f"length={length} tracked_cfo={tracked_cfo:+.6e}",
                file=sys.stderr,
                flush=True,
            )
            # Advance into this false candidate instead of repeatedly finding
            # the same preamble-like correlation peak.
            self._sample_buffer = self._sample_buffer[self.samples_per_symbol :]
            self.reset_packet_state()
            return False

        self._payload_length, self._expected_crc = decoded
        if (
            self.expected_output_bytes is not None
            and self.expected_output_bytes != self._payload_length
        ):
            print(
                f"[HEADER LENGTH] sender={self._payload_length} bytes "
                f"receiver_setting={self.expected_output_bytes} bytes; "
                "using sender header length",
                file=sys.stderr,
                flush=True,
            )
        self._sample_buffer = self._sample_buffer[needed:]
        self._packet_sample_offset += needed
        self._state = self.STATE_PAYLOAD
        self._sync_count += 1
        print(
            f"\n[SYNC SUCCESS] valid header received packet={self._sync_count} "
            f"length={self._payload_length} crc=0x{self._expected_crc:08X} "
            f"header_polarity={header_polarity:+d}",
            file=sys.stderr,
            flush=True,
        )
        return True

    def decode_payload(self):
        symbols = self._payload_length * 8
        pair_samples = 2 * self.samples_per_symbol
        payload_nominal = symbols * pair_samples
        capture_needed = (
            payload_nominal
            + self.timing_guard_symbols * self.samples_per_symbol
        )
        if len(self._sample_buffer) < capture_needed:
            return None

        raw = np.asarray(self._sample_buffer[:capture_needed], dtype=np.complex64)
        centered = raw - np.mean(raw)
        magnitudes = np.abs(centered)

        # Pilot -> first data and final data -> tail transitions reveal the
        # accumulated TX/RX sample-clock mismatch over the complete payload.
        first_data_start = self._find_variance_transition(
            magnitudes,
            self.samples_per_symbol,
            stable_before=True,
            search_radius=self.samples_per_symbol,
        )
        estimated_tail_start = float(self._find_variance_transition(
            magnitudes,
            payload_nominal,
            stable_before=False,
            search_radius=(self.timing_guard_symbols - 2)
            * self.samples_per_symbol,
            stable_after_window=2 * self.samples_per_symbol,
        ))

        first_data_start = float(first_data_start)
        origin_error = first_data_start - self.samples_per_symbol
        origin_limit = float(self.symbol_edge_guard)
        if not np.isfinite(origin_error) or abs(origin_error) > origin_limit:
            print(
                f"[TIMING ORIGIN REJECTED] estimate={origin_error:+.1f} samples "
                f"limit={origin_limit:.1f}; using nominal payload origin",
                file=sys.stderr,
                flush=True,
            )
            first_data_start = float(self.samples_per_symbol)

        raw_pair_spacing = (
            estimated_tail_start - first_data_start
        ) / max(0.5, symbols - 0.5)
        estimated_clock_error_ppm = (
            1.0e6 * (raw_pair_spacing / pair_samples - 1.0)
        )
        timing_valid = (
            np.isfinite(estimated_clock_error_ppm)
            and abs(estimated_clock_error_ppm) <= MAX_SAMPLE_CLOCK_ERROR_PPM
        )
        if timing_valid:
            pair_spacing = float(raw_pair_spacing)
            timing_mode = "tracked"
        else:
            raw_drift = estimated_tail_start - payload_nominal
            print(
                f"[TIMING REJECTED] tail_drift={raw_drift:+.1f} samples "
                f"clock_error={estimated_clock_error_ppm:+.1f} ppm "
                f"limit={MAX_SAMPLE_CLOCK_ERROR_PPM:.1f}; "
                "using nominal pair spacing",
                file=sys.stderr,
                flush=True,
            )
            pair_spacing = float(pair_samples)
            timing_mode = "nominal"

        symbol_spacing = 0.5 * pair_spacing
        first_pilot_start = first_data_start - symbol_spacing
        normalized = (
            np.arange(self.samples_per_symbol, dtype=np.float64) + 0.5
        ) / self.samples_per_symbol
        pilot_positions = (
            first_pilot_start
            + np.arange(symbols, dtype=np.float64)[:, None] * pair_spacing
            + normalized[None, :] * symbol_spacing
        )
        data_positions = pilot_positions + symbol_spacing
        pilot_samples = self._interpolate_complex(
            centered, pilot_positions.reshape(-1)
        ).reshape(symbols, self.samples_per_symbol)
        data_samples = self._interpolate_complex(
            centered, data_positions.reshape(-1)
        ).reshape(symbols, self.samples_per_symbol)

        bits = np.empty(symbols, dtype=np.uint8)
        pilot_index = np.arange(self.samples_per_symbol, dtype=np.float64)
        data_index = self.samples_per_symbol + pilot_index
        for symbol_index in range(symbols):
            pilot = pilot_samples[symbol_index]
            data = data_samples[symbol_index]

            # This pilot estimates carrier phase/frequency only for the one
            # alpha-stable information symbol immediately following it.
            product = np.vdot(pilot[:-1], pilot[1:])
            local_cfo = (
                0.0 if abs(product) < 1e-12
                else float(np.angle(product))
            )
            channel = np.mean(
                pilot * np.exp(-1j * local_cfo * pilot_index)
            )
            local_phase = float(np.angle(channel))
            corrected_data = data * np.exp(
                -1j * (local_phase + local_cfo * data_index)
            )
            # A small boundary error otherwise injects deterministic pilot
            # samples into the extrema estimator. Discard only the edge of the
            # alpha-stable symbol; the information remains in the interior.
            decision_samples = corrected_data[
                self.symbol_edge_guard : -self.symbol_edge_guard
            ]
            bit, beta = self.estimate_bit(decision_samples)
            bits[symbol_index] = bit
            if symbol_index < self.debug_symbols:
                print(
                    f"[DEC SYMBOL] index={symbol_index} bit={bit} "
                    f"beta_est={beta:+.5f} local_cfo={local_cfo:+.6e}",
                    file=sys.stderr,
                    flush=True,
                )

        payload = bits_to_bytes(bits)
        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
        payload_polarity = 1
        valid = actual_crc == self._expected_crc
        if not valid:
            inverted_payload = bits_to_bytes(1 - bits)
            inverted_crc = zlib.crc32(inverted_payload) & 0xFFFFFFFF
            if inverted_crc == self._expected_crc:
                payload = inverted_payload
                actual_crc = inverted_crc
                payload_polarity = -1
                valid = True

        self._sample_buffer = self._sample_buffer[capture_needed:]
        applied_tail_start = first_data_start + (symbols - 0.5) * pair_spacing
        timing_drift = float(applied_tail_start - payload_nominal)
        self._output_queue.extend(payload)
        self.packet_decoded = True
        self.completed_payload_bytes = len(payload)
        if valid:
            self._crc_ok += 1
            print(
                f"[DEC CRC] OK payload={len(payload)} bytes "
                f"crc=0x{actual_crc:08X} polarity={payload_polarity:+d} "
                f"timing_pair={pair_spacing:.6f} "
                f"origin={first_pilot_start:+.1f} "
                f"drift={timing_drift:+.1f} samples timing={timing_mode}",
                file=sys.stderr,
                flush=True,
            )
        else:
            self._crc_fail += 1
            print(
                f"[DEC CRC] FAIL expected=0x{self._expected_crc:08X} "
                f"actual=0x{actual_crc:08X}; payload emitted for BER "
                f"timing_pair={pair_spacing:.6f} "
                f"origin={first_pilot_start:+.1f} "
                f"drift={timing_drift:+.1f} samples timing={timing_mode}",
                file=sys.stderr,
                flush=True,
            )
        self.reset_packet_state()
        return valid

    def _process_buffer(self):
        while True:
            if self.packet_decoded:
                return
            if self._state == self.STATE_SEARCH_SYNC:
                if not self._acquire_candidate():
                    return
            if self._state == self.STATE_HEADER:
                if self.decode_header() is None:
                    return
            if self._state == self.STATE_PAYLOAD:
                if self.decode_payload() is None:
                    return

    def general_work(self, input_items, output_items):
        if self.packet_output_complete:
            return gr.WORK_DONE

        self._work_call += 1
        incoming = input_items[0]
        out = output_items[0]
        if len(incoming):
            self._total_samples_seen += len(incoming)
            self.append_input(incoming)
            self.consume(0, len(incoming))

        self._process_buffer()
        if self._output_queue and len(out):
            count = min(len(out), len(self._output_queue))
            out[:count] = np.frombuffer(self._output_queue[:count], dtype=np.uint8)
            del self._output_queue[:count]
            self._total_output_bytes += count
            if self.packet_decoded and not self._output_queue:
                self.packet_output_complete = True
                print(
                    f"[DEC OUTPUT COMPLETE] {self.completed_payload_bytes} bytes "
                    "released to GNU Radio output buffer",
                    file=sys.stderr,
                    flush=True,
                )
            return count
        return 0