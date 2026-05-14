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
            raise ValueError("beta_map size must allow whole-byte packing") # zaenkrat itak za vse normalne namene več kot to ne mojo dolgi seznami

        self.expected_chunk = self.samples_per_symbol * self.symbols_per_byte
        self.beta_reference_scores = self._build_beta_reference_scores() #lazje za primerjavo
        print("beta_map:", self.beta_map)
        print("beta_reference_scores:", self.beta_reference_scores)

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

    @staticmethod
    def alpha_stable(size, alpha=1.1, beta=0.0, gama=1.0):
        v_values = np.random.uniform(-np.pi / 2, np.pi / 2, size)
        w_values = np.random.exponential(1, size)

        constant = beta * np.tan(np.pi * alpha / 2)
        shift = np.arctan(constant)
        scale = (1 + constant ** 2) ** (1 / (2 * alpha))

        samples = scale * np.sin(alpha * v_values + shift) / (np.cos(v_values)) ** (1 / alpha) * (np.cos((1 - alpha) * v_values - shift) / w_values) ** ((1 - alpha) / alpha)
        return gama * samples

    #to ni napisano ampak lahko pride zelo prov ka gledam te repe mi povejo najvec o scewnees
    def _beta_score(self, symbol_samples):
        samples = np.asarray(symbol_samples, dtype=np.float32)
        if samples.size == 0:
            return 0.0

        #ocena bete na mal drgacen nacin
        sorted_samples = np.sort(samples)
        tail_size = max(1, sorted_samples.size // 10) #vzami najvecje elemente 10% ce bi delil z 20 bi blo 5 ma je blo premalo oziroma 10 kr lepo funkcionira
        low_tail = float(np.mean(sorted_samples[:tail_size])) #vzami min
        high_tail = float(np.mean(sorted_samples[-tail_size:])) #vzami max
        denom = abs(low_tail) + abs(high_tail) + 1e-12 #ce je blizu nule dodaj neki malega da ne dobim Nan


        return float(np.clip((high_tail + low_tail) / denom, -1.0, 1.0)) # vrni in clipi na interval od beta_sample

    #za priblizno rabimo neke score ki mi povejo glede na mapo kaj gledam cez to potem primerjam lazje namesto da preverjam direktno na list
    def _build_beta_reference_scores(self):
        reference_scores = []
        trials = max(16, min(128, self.samples_per_symbol // 4))
        
        for beta in self.beta_map:
            trial_scores = []
            for _ in range(trials):
                reference_symbol = self.alpha_stable(self.samples_per_symbol, alpha=1.1, beta=float(beta), gama=1.0)
                
                # Use paper formula: partition into L segments, compute max/min std
                samples_per_realization = self.samples_per_symbol // self.L
                y_max = []
                y_min = []
                
                for l in range(self.L):
                    start = l * samples_per_realization
                    end = start + samples_per_realization
                    segment = reference_symbol[start:end]
                    y_max.append(np.max(segment))
                    y_min.append(np.min(segment))
                
                s2_max = float(np.var(y_max, ddof=1)) if len(y_max) > 1 else 0.0
                s2_min = float(np.var(y_min, ddof=1)) if len(y_min) > 1 else 0.0
                s2_max = float(np.nan_to_num(s2_max, nan=0.0, posinf=0.0, neginf=0.0))
                s2_min = float(np.nan_to_num(s2_min, nan=0.0, posinf=0.0, neginf=0.0))
                
                spread = np.sqrt(max(0.0, s2_max)) + np.sqrt(max(0.0, s2_min)) + 1e-12
                score = (np.sqrt(max(0.0, s2_max)) - np.sqrt(max(0.0, s2_min))) / spread
                trial_scores.append(float(np.clip(score, -1.0, 1.0)))
            
            reference_scores.append(float(np.mean(trial_scores)))
        
        return np.array(reference_scores, dtype=float)

    def estimate_beta(self, symbol_samples):
        samples_per_realization = self.samples_per_symbol // self.L
        if samples_per_realization <= 0:
            return 0.0

        y_max = []
        y_min = []

        for l in range(self.L):
            start = l * samples_per_realization
            end = start + samples_per_realization
            segment = symbol_samples[start:end]
            if segment.size == 0:
                continue
            y_max.append(np.max(segment))
            y_min.append(np.min(segment))

        if not y_max or not y_min:
            return 0.0

        s2_max = float(np.var(y_max, ddof=1)) if len(y_max) > 1 else 0.0
        s2_min = float(np.var(y_min, ddof=1)) if len(y_min) > 1 else 0.0

        s2_max = float(np.nan_to_num(s2_max, nan=0.0, posinf=0.0, neginf=0.0))
        s2_min = float(np.nan_to_num(s2_min, nan=0.0, posinf=0.0, neginf=0.0))

        spread = np.sqrt(max(0.0, s2_max)) + np.sqrt(max(0.0, s2_min)) + 1e-12
        variance_score = (np.sqrt(max(0.0, s2_max)) - np.sqrt(max(0.0, s2_min))) / spread
        tail_score = self._beta_score(symbol_samples)

        score = 0.35 * variance_score + 0.65 * tail_score
        return float(np.clip(score, -1.0, 1.0))

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
                beta_idx = self.closest_index(probably_beta, self.beta_reference_scores)
                byte_value |= (beta_idx & beta_mask) << (symbol_index * self.bits_per_beta)

            out[byte_index] = byte_value

        consumed_samples = bytes_to_process * self.expected_chunk
        if consumed_samples:
            self._sample_buffer = self._sample_buffer[consumed_samples:]

        if len(in_samples):
            self.consume(0, len(in_samples))

        return bytes_to_process
