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


class alpha_encoder(gr.basic_block):
    """Frame bytes and encode payload bits as skewed alpha-stable symbols."""

    def __init__(
        self,
        alpha_map=(1.2, 1.4, 1.6, 1.8),
        beta_map=(-1.0, 1.0),
        gama_map=(0.5, 1.0, 1.5, 2.0),
        samples_per_symbol=500,
        encode_alpha=False,
        encode_beta=True,
        encode_gama=False,
        eos_timeout=2.0,
        expected_input_bytes=None,
        sync_symbols=MIN_SYNC_SYMBOLS,
        header_repetitions=3,
        tx_amplitude=0.70,
        payload_scale=0.05,
        sample_rate=64000,
        subcarrier_frequency=4000,
        payload_pilot_amplitude=0.70,
        tx_tail_symbols=8,
    ):
        gr.basic_block.__init__(
            self, name="alpha_encoder", in_sig=[np.uint8], out_sig=[np.complex64]
        )

        self.alpha_map = np.asarray(alpha_map, dtype=np.float64)
        self.beta_map = np.asarray(beta_map, dtype=np.float64)
        self.gama_map = np.asarray(gama_map, dtype=np.float64)
        self.samples_per_symbol = int(samples_per_symbol)
        self.encode_alpha = bool(encode_alpha)
        self.encode_beta = bool(encode_beta)
        self.encode_gama = bool(encode_gama)
        self.eos_timeout = float(eos_timeout)
        self.expected_input_bytes = (
            None if expected_input_bytes is None else int(expected_input_bytes)
        )
        self.sync_symbols = max(MIN_SYNC_SYMBOLS, int(sync_symbols))
        self.header_repetitions = int(header_repetitions)
        self.tx_amplitude = float(tx_amplitude)
        self.payload_scale = float(payload_scale)
        self.sample_rate = float(sample_rate)
        self.subcarrier_frequency = float(subcarrier_frequency)
        self.payload_pilot_amplitude = float(payload_pilot_amplitude)
        self.tx_tail_symbols = int(tx_tail_symbols)

        if self.samples_per_symbol <= 0:
            raise ValueError("samples_per_symbol must be positive")
        if len(self.beta_map) != 2 or not self.encode_beta:
            raise ValueError("Hardware protocol requires two beta values")
        if self.encode_alpha or self.encode_gama:
            raise ValueError("Framed hardware protocol currently encodes beta only")
        if self.header_repetitions < 1 or self.header_repetitions % 2 == 0:
            raise ValueError("header_repetitions must be a positive odd number")
        if not (0.0 < self.tx_amplitude <= 0.95):
            raise ValueError("tx_amplitude must be in (0, 0.95]")
        if self.payload_scale <= 0.0:
            raise ValueError("payload_scale must be positive")
        if self.sample_rate <= 0.0:
            raise ValueError("sample_rate must be positive")
        if abs(self.subcarrier_frequency) >= self.sample_rate / 4.0:
            raise ValueError("subcarrier_frequency must be below sample_rate/4")
        if not (0.0 < self.payload_pilot_amplitude <= 0.95):
            raise ValueError("payload_pilot_amplitude must be in (0, 0.95]")
        if self.tx_tail_symbols < 1:
            raise ValueError("tx_tail_symbols must be positive")

        self._input = bytearray()
        self._output_fifo = np.empty(0, dtype=np.complex64)
        self._frame_prepared = False
        self._ever_received_input = False
        self._last_input_time = None

        print(
            "\n[ENC INIT] protocol=PN32+REPEATED_HEADER+PILOTED_ALPHA_STABLE_PAYLOAD",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[ENC INIT] samples_per_symbol={self.samples_per_symbol} "
            f"sync_symbols={self.sync_symbols} "
            f"header_repetitions={self.header_repetitions}",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[ENC INIT] tx_amplitude={self.tx_amplitude:.3f} "
            f"payload_scale={self.payload_scale:.4f} "
            f"subcarrier={self.subcarrier_frequency:.0f} Hz "
            f"payload_pilot={self.payload_pilot_amplitude:.3f} "
            f"tx_tail_symbols={self.tx_tail_symbols}",
            file=sys.stderr,
            flush=True,
        )

    def forecast(self, noutput_items, ninputs):
        if self._frame_prepared or len(self._output_fifo):
            return [0] * int(ninputs)
        return [1] * int(ninputs)

    @staticmethod
    def alpha_stable_batch(beta_values, samples_per_symbol, alpha=1.1, gamma=1.0):
        beta_values = np.asarray(beta_values, dtype=np.float64)
        count = len(beta_values) * int(samples_per_symbol)
        if count == 0:
            return np.empty(0, dtype=np.float32)

        beta = np.repeat(beta_values, int(samples_per_symbol))
        v = np.random.uniform(-np.pi / 2.0, np.pi / 2.0, count)
        w = np.maximum(np.random.exponential(1.0, count), 1e-12)
        constant = beta * np.tan(np.pi * alpha / 2.0)
        shift = np.arctan(constant)
        scale = (1.0 + constant * constant) ** (1.0 / (2.0 * alpha))
        samples = (
            scale
            * np.sin(alpha * v + shift)
            / np.cos(v) ** (1.0 / alpha)
            * (np.cos((1.0 - alpha) * v - shift) / w)
            ** ((1.0 - alpha) / alpha)
        )
        samples = np.nan_to_num(samples * gamma, nan=0.0, posinf=0.0, neginf=0.0)
        return samples.astype(np.float32, copy=False)

    def _deterministic_symbols(self, values):
        values = np.asarray(values, dtype=np.float32) * self.tx_amplitude
        return np.repeat(values, self.samples_per_symbol).astype(np.complex64)

    def build_frame(self, payload):
        """Build one complete contiguous transmit burst."""
        payload = bytes(payload)
        crc = zlib.crc32(payload) & 0xFFFFFFFF

        preamble = self._deterministic_symbols(sync_pattern(self.sync_symbols))

        # The header is deterministic and repeated so that packet length and
        # the diagnostic CRC can be recovered before decoding stochastic data.
        header = struct.pack("<HII", MAGIC, len(payload), crc)
        header_bits = bytes_to_bits(header)
        repeated_header_bits = np.tile(header_bits, self.header_repetitions)
        header_samples = self._deterministic_symbols(
            np.where(repeated_header_bits > 0, 1.0, -1.0)
        )

        payload_bits = bytes_to_bits(payload)
        beta_values = self.beta_map[payload_bits]
        payload_real = self.alpha_stable_batch(
            beta_values, self.samples_per_symbol, alpha=1.1, gamma=1.0
        )
        # UHD expects normalized complex samples.  Explicit limiting prevents
        # undocumented DAC clipping while retaining the skew sign in the tails.
        payload_real = np.clip(
            payload_real * self.payload_scale,
            -self.tx_amplitude,
            self.tx_amplitude,
        )
        alpha_symbols = payload_real.reshape(-1, self.samples_per_symbol)
        # Every information bit is still represented only by the beta of its
        # alpha-stable data symbol.  The preceding deterministic symbol is a
        # local phase/frequency reference and carries no information.
        pilot_symbols = np.full_like(
            alpha_symbols, self.payload_pilot_amplitude, dtype=np.float32
        )
        pairs = np.empty(
            (len(payload_bits), 2, self.samples_per_symbol), dtype=np.complex64
        )
        pairs[:, 0, :] = pilot_symbols
        pairs[:, 1, :] = alpha_symbols
        payload_samples = pairs.reshape(-1)

        # Keep the final data symbols away from UHD's end-of-burst boundary.
        # Without a guard tail, the receiver can observe noise in place of the
        # last part of the payload when the B210 transmit stream shuts down.
        # A positive tone maintains a continuous envelope; it is not decoded.
        tail_samples = np.full(
            self.tx_tail_symbols * self.samples_per_symbol,
            np.complex64(self.payload_pilot_amplitude + 0j),
            dtype=np.complex64,
        )

        frame = np.concatenate(
            (preamble, header_samples, payload_samples, tail_samples)
        )
        if self.subcarrier_frequency:
            index = np.arange(len(frame), dtype=np.float64)
            frame = frame * np.exp(
                1j * 2.0 * np.pi * self.subcarrier_frequency * index / self.sample_rate
            )
            frame = frame.astype(np.complex64, copy=False)
        print(
            f"[ENC FRAME] payload={len(payload)} bytes crc=0x{crc:08X} "
            f"preamble={len(preamble)} header={len(header_samples)} "
            f"payload_samples={len(payload_samples)} tail={len(tail_samples)} "
            f"total={len(frame)}",
            file=sys.stderr,
            flush=True,
        )
        return frame

    def general_work(self, input_items, output_items):
        incoming = input_items[0]
        out = output_items[0]

        if len(incoming):
            self._ever_received_input = True
            self._last_input_time = time.monotonic()
            remaining = None
            if self.expected_input_bytes is not None:
                remaining = max(0, self.expected_input_bytes - len(self._input))
            accepted = len(incoming) if remaining is None else min(len(incoming), remaining)
            if accepted:
                self._input.extend(np.asarray(incoming[:accepted], dtype=np.uint8).tobytes())
            self.consume(0, len(incoming))

        complete = (
            self.expected_input_bytes is not None
            and len(self._input) >= self.expected_input_bytes
        )
        timed_out = (
            self.expected_input_bytes is None
            and self._ever_received_input
            and self._last_input_time is not None
            and time.monotonic() - self._last_input_time >= self.eos_timeout
        )

        # Prepare the entire packet before emitting its first sample.  This
        # removes the preamble-to-payload underflow seen with the USRP sink.
        if not self._frame_prepared and (complete or timed_out):
            self._output_fifo = self.build_frame(self._input)
            self._frame_prepared = True

        if len(self._output_fifo):
            count = min(len(out), len(self._output_fifo))
            out[:count] = self._output_fifo[:count]
            self._output_fifo = self._output_fifo[count:]
            return count

        if self._frame_prepared:
            print("[ENC] WORK_DONE", file=sys.stderr, flush=True)
            return gr.WORK_DONE
        return 0
