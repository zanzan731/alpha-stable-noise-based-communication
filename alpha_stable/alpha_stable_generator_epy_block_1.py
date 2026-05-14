"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__ will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr


class alpha_decoder(gr.basic_block):
    """Decode alpha-stable sample bursts into a bit stream."""

    def __init__(self, alpha_map=[1.2, 1.4, 1.6, 1.8], beta_map=[-1.0, -0.3, 0.3, 1.0], gama_map=[0.5, 1.0, 1.5, 2.0], samples_per_symbol=500, L=10, encode_alpha=False, encode_beta=True, encode_gama=False):
        gr.basic_block.__init__(
            self,
            name='alpha_decoder',   # will show up in GRC
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

        if self.samples_per_symbol <= 0:
            raise ValueError("samples_per_symbol must be positive")
        if self.L <= 0:
            raise ValueError("L must be positive")
        if self.samples_per_symbol % self.L != 0:
            raise ValueError("samples_per_symbol must be divisible by L")
        if self.encode_alpha and not self.is_power_of_two(len(self.alpha_map)):
            raise ValueError("alpha_map size must be power of 2")
        if self.encode_beta and not self.is_power_of_two(len(self.beta_map)):
            raise ValueError("beta_map size must be power of 2")
        if self.encode_gama and not self.is_power_of_two(len(self.gama_map)):
            raise ValueError("gama_map size must be power of 2")

        self.bits_alpha = self.log2_za_potence2(len(self.alpha_map)) if self.encode_alpha else 0
        self.bits_beta = self.log2_za_potence2(len(self.beta_map)) if self.encode_beta else 0
        self.bits_gama = self.log2_za_potence2(len(self.gama_map)) if self.encode_gama else 0
        self.bits_per_symbol = self.bits_alpha + self.bits_beta + self.bits_gama

        if self.bits_per_symbol <= 0:
            raise ValueError("At least one of encode_alpha, encode_beta, or encode_gama must be enabled")

        # This decoder currently implements only beta estimation.
        if self.encode_alpha or self.encode_gama:
            raise ValueError("Decoder currently supports only encode_beta=True, encode_alpha=False, encode_gama=False")

        self.expected_chunk = self.samples_per_symbol

    def forecast(self, noutput_items, ninputs):
        """Non-blocking forecast prevents starvation on finite input streams."""
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
        raise ValueError("One of the maps is not of power 2^n")

    @staticmethod
    def closest_index(value, values):
        arr = np.array(values, dtype=float)
        if arr.size == 1:
            return 0
        return int(np.argmin(np.abs(arr - value)))

    def estimate_beta(self, symbol_samples):
        """Vectorized beta estimator from paper."""
        samples_per_realization = self.samples_per_symbol // self.L
        if samples_per_realization <= 0:
            return 0.0

        # Reshape into L segments and compute max/min per segment
        symbol_array = np.asarray(symbol_samples, dtype=np.float32)
        segments = symbol_array[:samples_per_realization * self.L].reshape(self.L, samples_per_realization)
        
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
            self._sample_buffer = np.concatenate((self._sample_buffer, input_samples.astype(np.float32, copy=False)))

    def general_work(self, input_items, output_items):
        in_samples = input_items[0]
        out = output_items[0]

        if len(out) == 0:
            return 0

        if len(in_samples) > 0:
            self._append_input_samples(in_samples)
            self.consume(0, len(in_samples))

        out_index = 0

        # Drain already decoded bytes first. This is important near end-of-stream.
        buffered_bytes = len(self._decoded_bit_buffer) // 8
        bytes_from_buffer = min(len(out), buffered_bytes)
        for byte_index in range(bytes_from_buffer):
            base = byte_index * 8
            byte_value = 0
            for bit_index in range(8):
                byte_value |= (self._decoded_bit_buffer[base + bit_index] & 0x1) << bit_index
            out[out_index] = byte_value
            out_index += 1

        if bytes_from_buffer > 0:
            self._decoded_bit_buffer = self._decoded_bit_buffer[bytes_from_buffer * 8:]

        if out_index == len(out):
            return out_index

        available_symbols = len(self._sample_buffer) // self.expected_chunk
        symbols_to_process = available_symbols

        beta_mask = (1 << self.bits_beta) - 1 if self.bits_beta > 0 else 0

        # First decode all available symbols into a bit buffer.
        for symbol_index in range(symbols_to_process):
            symbol_start = symbol_index * self.expected_chunk
            symbol_end = symbol_start + self.expected_chunk
            symbol_samples = self._sample_buffer[symbol_start:symbol_end]

            probably_beta = self.estimate_beta(symbol_samples)
            beta_idx = self.closest_index(probably_beta, self.beta_map) & beta_mask if self.bits_beta > 0 else 0

            # Emit decoded field bits in encoder order: alpha, beta, gama.
            for bit_index in range(self.bits_alpha):
                self._decoded_bit_buffer.append(0)
            for bit_index in range(self.bits_beta):
                self._decoded_bit_buffer.append((beta_idx >> bit_index) & 0x1)
            for bit_index in range(self.bits_gama):
                self._decoded_bit_buffer.append(0)

        consumed_samples = symbols_to_process * self.expected_chunk
        self._sample_buffer = self._sample_buffer[consumed_samples:]

        # Then pack every 8 decoded bits back into output bytes.
        available_bytes = len(self._decoded_bit_buffer) // 8
        bytes_to_output = min(len(out) - out_index, available_bytes)

        for byte_index in range(bytes_to_output):
            base = byte_index * 8
            byte_value = 0
            for bit_index in range(8):
                byte_value |= (self._decoded_bit_buffer[base + bit_index] & 0x1) << bit_index
            out[out_index] = byte_value
            out_index += 1

        if bytes_to_output > 0:
            self._decoded_bit_buffer = self._decoded_bit_buffer[bytes_to_output * 8:]

        return out_index
