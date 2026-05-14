"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__ will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr


class alpha_decoder(gr.basic_block):
    """Decode alpha-stable sample bursts back into bytes."""

    def __init__(self, alpha_map=[1.2, 1.4, 1.6, 1.8], beta_map=[-1.0, -0.3, 0.3, 1.0], gama_map=[0.5, 1.0, 1.5, 2.0], samples_per_symbol=1000, L=10, encode_alpha=True, encode_beta=True, encode_gama=False):
        gr.basic_block.__init__(
            self,
            name='alpha_decoder',
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

        if self.samples_per_symbol <= 0:
            raise ValueError("samples_per_symbol must be positive")
        if self.L <= 0:
            raise ValueError("L must be positive")
        if self.samples_per_symbol % self.L != 0:
            raise ValueError("samples_per_symbol must be divisible by L")
        if not self.is_power_of_two(len(self.beta_map)):
            raise ValueError("beta_map size must be power of 2")

        self.bits_per_beta = self.log2_za_potence2(len(self.beta_map))
        self.symbols_per_byte = 8 // self.bits_per_beta
        if self.symbols_per_byte * self.bits_per_beta != 8:
            raise ValueError("beta_map size must allow whole-byte packing")

        self.expected_chunk = self.samples_per_symbol * self.symbols_per_byte

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
        raise ValueError("One of the maps is not of power 2^n")

    @staticmethod
    def closest_index(value, values):
        arr = np.array(values)
        return int(np.argmin(np.abs(arr - value)))

    def estimate_beta(self, symbol_samples):
        samples_per_realization = self.samples_per_symbol // self.L
        y_max = []
        y_min = []

        for l in range(self.L):
            start = l * samples_per_realization
            end = start + samples_per_realization
            segment = symbol_samples[start:end]
            y_max.append(np.max(segment))
            y_min.append(np.min(segment))
        s2_max = np.var(y_max, ddof=1) if self.L > 1 else 0.0
        s2_min = np.var(y_min, ddof=1) if self.L > 1 else 0.0

        # guard against negative/NaN variances and numerical overflow
        s2_max = float(np.nan_to_num(s2_max, nan=0.0, posinf=np.finfo(float).max, neginf=0.0))
        s2_min = float(np.nan_to_num(s2_min, nan=0.0, posinf=np.finfo(float).max, neginf=0.0))

        alpha = 1.1
        diff = np.sqrt(max(0.0, s2_max)) - np.sqrt(max(0.0, s2_min))
        t = alpha * diff

        # Prevent overflow in exp by clamping the argument range.
        # For large positive t, exp(-t) -> 0 and result -> 1.
        # For large negative t, exp(-t) would overflow; treat result as -1.
        MAX_ARG = 700.0
        if not np.isfinite(t):
            return 0.0
        if t >= MAX_ARG:
            return 1.0
        if t <= -MAX_ARG:
            return -1.0

        val = 1.0 - 2.0 * np.exp(-t)
        return float(np.clip(val, -1.0, 1.0))

    def _append_input_samples(self, input_samples):
        if input_samples.size:
            self._sample_buffer = np.concatenate((self._sample_buffer, input_samples.astype(np.float32, copy=False)))

    def general_work(self, input_items, output_items):
        in_samples = input_items[0]
        out = output_items[0]

        self._append_input_samples(in_samples)

        available_bytes = len(self._sample_buffer) // self.expected_chunk
        bytes_to_process = min(len(out), available_bytes)

        beta_mask = (1 << self.bits_per_beta) - 1

        for byte_index in range(bytes_to_process):
            chunk_start = byte_index * self.expected_chunk
            chunk_end = chunk_start + self.expected_chunk
            byte_samples = self._sample_buffer[chunk_start:chunk_end]
            byte_value = 0

            for symbol_index in range(self.symbols_per_byte):
                symbol_start = symbol_index * self.samples_per_symbol
                symbol_end = symbol_start + self.samples_per_symbol
                symbol_samples = byte_samples[symbol_start:symbol_end]

                probably_beta = self.estimate_beta(symbol_samples)
                beta_idx = self.closest_index(probably_beta, self.beta_map)
                byte_value |= (beta_idx & beta_mask) << (symbol_index * self.bits_per_beta)

            out[byte_index] = byte_value

        consumed_samples = bytes_to_process * self.expected_chunk
        if consumed_samples:
            self._sample_buffer = self._sample_buffer[consumed_samples:]

        if len(in_samples):
            self.consume(0, len(in_samples))

        return bytes_to_process
