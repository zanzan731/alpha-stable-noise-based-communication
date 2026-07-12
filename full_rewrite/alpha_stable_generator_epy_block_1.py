"""
GNU Radio Embedded Python Block: alpha_decoder

Dekodira vzorce alfa-stabilne porazdelitve nazaj v bajte.
"""

import numpy as np
from gnuradio import gr
import sys
import time

class alpha_decoder(gr.basic_block):
    """Dekodira vzorce alfa-stabilne porazdelitve v bajte."""

    def __init__(
        self,
        alpha_map=[1.2, 1.4, 1.6, 1.8],
        beta_map=[-1.0, 1.0],
        gama_map=[1.0],
        samples_per_symbol=500,
        L=10,
        encode_alpha=False,
        encode_beta=True,
        encode_gama=False,
        eos_timeout=3.0,
        expected_input_samples=None,
    ):
        gr.basic_block.__init__(
            self,
            name="alpha_decoder",
            in_sig=[np.float32],
            out_sig=[np.uint8],
        )

        self.alpha_map = list(alpha_map)
        self.beta_map = list(beta_map)
        self.gama_map = list(gama_map)
        self.samples_per_symbol = int(samples_per_symbol)
        self.L = int(L)
        self.encode_alpha = bool(encode_alpha)
        self.encode_beta = bool(encode_beta)
        self.encode_gama = bool(encode_gama)

        self._sample_buffer = np.empty(0, dtype=np.float32)
        self._decoded_bit_buffer = []
        self._eos_reached = False
        self._ever_received_input = False #potrebno da vem kdaj startam stevec oziroma da ne konča predn dobi delo

        # Fallback-only timing state
        self.eos_timeout = float(eos_timeout)
        self._last_input_time = None

        # NEW: deterministic sample-count tracking (this is the real fix)
        self.expected_input_samples = (
            int(expected_input_samples) if expected_input_samples is not None else None
        )
        self._total_samples_seen = 0  # running total of input samples consumed this run

        if self.samples_per_symbol <= 0:
            raise ValueError("samples_per_symbol must be pozitive number")
        if self.L <= 0:
            raise ValueError("L must be pozitive number")
        if self.samples_per_symbol % self.L != 0:
            raise ValueError("samples_per_symbol must be devisible by L")

        if self.encode_alpha and not self.is_power_of_two(len(self.alpha_map)):
            raise ValueError("Size of alpha_map bust be 2^n")
        if self.encode_beta and not self.is_power_of_two(len(self.beta_map)):
            raise ValueError("Size of beta_map bust be 2^n")
        if self.encode_gama and not self.is_power_of_two(len(self.gama_map)):
            raise ValueError("Size of gama_map bust be 2^n")

        self.bits_alpha = self.log2_za_potence2(len(self.alpha_map)) if self.encode_alpha else 0
        self.bits_beta  = self.log2_za_potence2(len(self.beta_map))  if self.encode_beta  else 0
        self.bits_gama  = self.log2_za_potence2(len(self.gama_map))  if self.encode_gama  else 0
        self.bits_per_symbol = self.bits_alpha + self.bits_beta + self.bits_gama

        if self.bits_per_symbol <= 0:
            raise ValueError("At least one encode alpha, beta or gama must be True")

        if self.encode_alpha or self.encode_gama:
            raise ValueError(
                "Dekoder supports only encode_beta=True, encode_alpha=False, encode_gama=False now"
            )

    def forecast(self, noutput_items, ninputs):
        return [0] * int(ninputs)

    @staticmethod
    def is_power_of_two(x):
        return x > 0 and (x & (x - 1)) == 0

    @staticmethod
    def log2_za_potence2(x):
        if x == 0:
            return 0
        if alpha_decoder.is_power_of_two(x):
            vrednost = 0
            while x > 1:
                x >>= 1
                vrednost += 1
            return vrednost
        raise ValueError("Ena od map ni velikosti 2^n")

    #najbližji indeks po naši metodi
    @staticmethod
    def closest_index(value, values):
        arr = np.array(values, dtype=float)
        if arr.size == 1:
            return 0
        return int(np.argmin(np.abs(arr - value)))

    def estimate_beta(self, symbol_samples):
        samples_per_segment = self.samples_per_symbol // self.L
        if samples_per_segment <= 0:
            return 0.0

        symbol_array = np.asarray(symbol_samples, dtype=np.float32)
        segments = symbol_array[: samples_per_segment * self.L].reshape(
            self.L, samples_per_segment
        )

        y_max = np.max(segments, axis=1)
        y_min = np.min(segments, axis=1)

        if y_max.size == 0 or y_min.size == 0:
            return 0.0

        s2_max = float(np.var(y_max, ddof=1)) if len(y_max) > 1 else 0.0
        s2_min = float(np.var(y_min, ddof=1)) if len(y_min) > 1 else 0.0
        s2_max = float(np.nan_to_num(s2_max, nan=0.0, posinf=0.0, neginf=0.0))
        s2_min = float(np.nan_to_num(s2_min, nan=0.0, posinf=0.0, neginf=0.0))

        spread = np.sqrt(max(0.0, s2_max)) + np.sqrt(max(0.0, s2_min)) + 1e-12
        score = (np.sqrt(max(0.0, s2_max)) - np.sqrt(max(0.0, s2_min))) / spread
        return float(np.clip(score, -1.0, 1.0))

    def _append_input_samples(self, input_samples):
        if input_samples.size:
            self._sample_buffer = np.concatenate(
                (self._sample_buffer, input_samples.astype(np.float32, copy=False))
            )

    def _flush_bits_to_output(self, out, out_index):
        available_bytes = len(self._decoded_bit_buffer) // 8
        bytes_to_write = min(len(out) - out_index, available_bytes) #znova da ne prepišemo slučajno out bufferja 

        for byte_index in range(bytes_to_write):
            base = byte_index * 8
            byte_value = 0
            for bit_index in range(8):
                byte_value |= (self._decoded_bit_buffer[base + bit_index] & 0x1) << bit_index
            out[out_index + byte_index] = byte_value

        if bytes_to_write > 0:
            self._decoded_bit_buffer = self._decoded_bit_buffer[bytes_to_write * 8:]

        return bytes_to_write

    def general_work(self, input_items, output_items):
        in_samples = input_items[0]
        out = output_items[0]
        '''
        if not hasattr(self, '_dbg_call'):
            self._dbg_call = 0
        self._dbg_call += 1
        c = self._dbg_call
        '''
        if len(out) == 0:
            return 0

        #print(f"[DEC #{c}] id={id(self)} in={len(in_samples)} out_buf={len(out)} sample_buf={len(self._sample_buffer)} bit_buf={len(self._decoded_bit_buffer)} eos={self._eos_reached} ever={self._ever_received_input} seen={self._total_samples_seen}/{self.expected_input_samples}", file=sys.stderr, flush=True)
        #isto kot v alpha_encoder rabimo nek način da ne končamo prehitro
        if len(in_samples) > 0:
            self._ever_received_input = True
            self._eos_reached = False
            self._last_input_time = time.time()  # fallback bookkeeping only
            self._total_samples_seen += len(in_samples)  # NEW: exact running count
            self._append_input_samples(in_samples)
            self.consume(0, len(in_samples))

            if (
                self.expected_input_samples is not None
                and self._total_samples_seen >= self.expected_input_samples
            ):
                self._eos_reached = True

        elif self._ever_received_input:
            if (time.time() - self._last_input_time) >= self.eos_timeout:
                self._eos_reached = True
        else:
            # Če ni še nič podatkov prišlo
            return 0

        out_index = 0
        beta_mask = (1 << self.bits_beta) - 1 if self.bits_beta > 0 else 0 #safety net bolj kot kaj drugega pomojem ne rabim samo tko za sigurn

        # Vrži vn kar smo že dekodali
        out_index += self._flush_bits_to_output(out, out_index)
        #če stem zapolneš že cel out_index moreš končati saj len(out) ne smemo prekoračiti ka zgubiš podatke ker prepišeš čez buffer
        if out_index == len(out):
            return out_index

        # Dekodiramo novo
        available_symbols = len(self._sample_buffer) // self.samples_per_symbol

        for symbol_index in range(available_symbols):
            symbol_start = symbol_index * self.samples_per_symbol
            symbol_end = symbol_start + self.samples_per_symbol
            symbol_samples = self._sample_buffer[symbol_start:symbol_end]

            estimated_beta = self.estimate_beta(symbol_samples)
            beta_idx = (
                self.closest_index(estimated_beta, self.beta_map) & beta_mask
                if self.bits_beta > 0 #ta if je odveč se strinjam je tle samo zaradi logike če implementiram alpha + je dober dodaten check
                else 0
            )

            for _ in range(self.bits_alpha):
                self._decoded_bit_buffer.append(0)
            for bit_index in range(self.bits_beta):
                self._decoded_bit_buffer.append((beta_idx >> bit_index) & 0x1)
            for _ in range(self.bits_gama):
                self._decoded_bit_buffer.append(0)

        # Zbriši kar smo poslali oziroma sprocesirali
        consumed_samples = available_symbols * self.samples_per_symbol
        self._sample_buffer = self._sample_buffer[consumed_samples:]

        # Izpiši na output sprocesirano
        out_index += self._flush_bits_to_output(out, out_index)

        if out_index > 0:
            return out_index

        if self._eos_reached:
            samples_remain = len(self._sample_buffer) >= self.samples_per_symbol
            #print(f"[DEC #{c}] eos confirmed, samples_remain={samples_remain} bit_buf={len(self._decoded_bit_buffer)}", file=sys.stderr, flush=True)
            bits_remain = len(self._decoded_bit_buffer) >= 8
            if not samples_remain and not bits_remain:
                return gr.WORK_DONE

        return 0