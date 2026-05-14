"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__ will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr


class alpha_encoder(gr.basic_block):
    """Encode bytes into alpha-stable sample bursts."""

    def __init__(self, alpha_map=[1.2, 1.4, 1.6, 1.8], beta_map=[-1.0, -0.3, 0.3, 1.0], gama_map=[0.5, 1.0, 1.5, 2.0], samples_per_symbol=500, encode_alpha=True, encode_beta=True, encode_gama=False):
        gr.basic_block.__init__(
            self,
            name='alpha_encoder',
            in_sig=[np.uint8],
            out_sig=[np.float32],
        )

        self.alpha_map = list(alpha_map)
        self.beta_map = list(beta_map)
        self.gama_map = list(gama_map)
        self.encode_alpha = bool(encode_alpha)
        self.encode_beta = bool(encode_beta)
        self.encode_gama = bool(encode_gama)
        self.samples_per_symbol = int(samples_per_symbol)
        self._bit_buffer = []

        if self.samples_per_symbol <= 0:
            raise ValueError("samples_per_symbol must be positive")

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

    @staticmethod
    def is_power_of_two(x):
        return x > 0 and (x & (x - 1)) == 0

    @staticmethod
    def log2_za_potence2(x):
        if x == 0:
            return 0

        if alpha_encoder.is_power_of_two(x):
            vrednost = 0
            while x > 1:
                x >>= 1
                vrednost += 1
            return vrednost
        raise ValueError("One of the maps is not of power 2^n")

    @staticmethod
    def alpha_stable(size, alpha=1.1, beta=0.0, gama=1.0):
        v_values = np.random.uniform(-np.pi / 2, np.pi / 2, size)
        w_values = np.random.exponential(1, size)

        constant = beta * np.tan(np.pi * alpha / 2)
        shift = np.arctan(constant)
        scale = (1 + constant ** 2) ** (1 / (2 * alpha))

        samples = scale * np.sin(alpha * v_values + shift) / (np.cos(v_values)) ** (1 / alpha) * (np.cos((1 - alpha) * v_values - shift) / w_values) ** ((1 - alpha) / alpha)
        return gama * samples

    @staticmethod
    def _read_bits(bit_buffer, start, count):
        value = 0
        for index in range(count):
            value |= (bit_buffer[start + index] << index)
        return value

    def _append_input_bits(self, input_bytes):
        for byte in input_bytes:
            byte_value = int(byte)
            for bit_index in range(8):
                self._bit_buffer.append((byte_value >> bit_index) & 1)

    def _encode_one_symbol(self, bit_offset):
        alpha = 1.1
        beta = 0.0
        gama = 1.0
        offset = bit_offset

        if self.encode_alpha:
            alpha_index = self._read_bits(self._bit_buffer, offset, self.bits_alpha)
            alpha = self.alpha_map[alpha_index]
            offset += self.bits_alpha

        if self.encode_beta:
            beta_index = self._read_bits(self._bit_buffer, offset, self.bits_beta)
            beta = self.beta_map[beta_index]
            offset += self.bits_beta

        if self.encode_gama:
            gama_index = self._read_bits(self._bit_buffer, offset, self.bits_gama)
            gama = self.gama_map[gama_index]

        return alpha, beta, gama

    def general_work(self, input_items, output_items):
        input_bytes = input_items[0]
        output_samples = output_items[0]

        if len(input_bytes):
            self._append_input_bits(input_bytes)

        max_symbols = len(output_samples) // self.samples_per_symbol
        produced_symbols = 0
        bit_offset = 0

        while produced_symbols < max_symbols and len(self._bit_buffer) - bit_offset >= self.bits_per_symbol:
            alpha, beta, gama = self._encode_one_symbol(bit_offset)
            samples = self.alpha_stable(self.samples_per_symbol, alpha=alpha, beta=beta, gama=gama).astype(np.float32)

            start = produced_symbols * self.samples_per_symbol
            end = start + self.samples_per_symbol
            output_samples[start:end] = samples

            produced_symbols += 1
            bit_offset += self.bits_per_symbol

        if bit_offset:
            self._bit_buffer = self._bit_buffer[bit_offset:]

        if len(input_bytes):
            self.consume(0, len(input_bytes))

        return produced_symbols * self.samples_per_symbol
        