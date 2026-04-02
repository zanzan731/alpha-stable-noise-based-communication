"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr


class alpha_encoder(gr.sync_block):
    """Alpha_stable_generator"""
    
    

    #argumenti
    def __init__(self, alpha_map=[1.2, 1.4, 1.6, 1.8], beta_map=[-1.0, -0.3, 0.3, 1.0], gama_map=[0.5, 1.0, 1.5, 2.0], samples_per_symbol=500, encode_alpha=True, encode_beta=True, encode_gama=False):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='alpha_encoder', # will show up in GRC
            in_sig=[np.uint8], #vrsta podatka ka gre in
            out_sig=[np.float32] #vrsta podatka ka gre out
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.alpha_map = alpha_map
        self.beta_map = beta_map
        self.gama_map = gama_map
        self.encode_alpha = encode_alpha
        self.encode_beta = encode_beta
        self.encode_gama = encode_gama
        self.samples_per_symbol = samples_per_symbol
        self.bit_buffer = []
        

    #Chambers-Mallows-Stuck Method (stran 8), alpha naj ni = 1 za 1 mogoce pole
    def alpha_stable(self, size, alpha, beta, gama=1.0): #size=number_of_samples generated, scale je gama (igraj se s temi tremi ce ti rata lahk encodas en byte kar ze ni tko slabo)
        V = np.random.uniform(-np.pi/2, np.pi/2, size)
        W = np.random.exponential(1, size)

        B = np.arctan(beta * np.tan(np.pi * alpha / 2)) / alpha
        S = (1 + (beta**2) * (np.tan(np.pi * alpha / 2)**2))**(1/(2*alpha))

        X = S * (np.sin(alpha * (V + B)) / (np.cos(V))**(1/alpha)) * ((np.cos(V - alpha * (V + B)) / W)**((1-alpha)/alpha))

        return gama * X
    
    @staticmethod
    def is_power_of_two(x):
            #flika vse bitke bo tocn 0
            return x == 0 or (x & (x - 1)) == 0
    
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
        else:
            raise ValueError("One of the maps is not of power 2^n")

    
    def work(self, input_items, output_items):
        data = input_items[0]
        out = output_items[0]

        idx = 0
        
        if self.encode_alpha and not self.is_power_of_two(len(self.alpha_map)):
            raise ValueError("alpha_map size must be power of 2")

        if self.encode_beta and not self.is_power_of_two(len(self.beta_map)):
            raise ValueError("beta_map size must be power of 2")

        if self.encode_gama and not self.is_power_of_two(len(self.gama_map)):
            raise ValueError("gama_map size must be power of 2")
        
        bits_alpha = self.log2_za_potence2(len(self.alpha_map)) if self.encode_alpha else 0
        bits_beta  = self.log2_za_potence2(len(self.beta_map)) if self.encode_beta else 0
        bits_gama  = self.log2_za_potence2(len(self.gama_map)) if self.encode_gama else 0

        #to rabimo da vemo koliko bitov lahko z enim signalom predstavimo
        bits_per_symbol = bits_alpha + bits_beta + bits_gama

        if bits_per_symbol == 0:
            return 0

        #bit buffer ka rabim delat z streemom
        
        for byte in data:
            for i in range(8):
                self.bit_buffer.append((byte >> i) & 1)

        #provimo byte predstavit
        while len(self.bit_buffer) >= bits_per_symbol:
            
            offset = 0

            # defaults če ni mape mogoce pole za popravit
            alpha = 1.1
            beta = 0.0
            gama = 1.0

            def read_bits(n, offset):
                val = 0
                for i in range(n):
                    val |= (self.bit_buffer[offset + i] << i)
                return val
            

            # --- ALPHA ---
            if self.encode_alpha:
                #koliko bitov je v alphi
                alpha_bits = read_bits(bits_alpha, offset)
                alpha = self.alpha_map[alpha_bits]
                offset += bits_alpha

            # --- BETA ---
            if self.encode_beta:
                beta_bits = read_bits(bits_beta, offset)
                beta = self.beta_map[beta_bits]
                offset += bits_beta

            # --- GAMA ---
            if self.encode_gama:
                gama_bits = read_bits(bits_gama, offset)
                gama = self.gama_map[gama_bits]
                offset += bits_gama

            self.bit_buffer = self.bit_buffer[bits_per_symbol:]

            samples = self.alpha_stable(
                self.samples_per_symbol,
                alpha,
                beta,
                gama
            )

            if idx + self.samples_per_symbol > len(out):
                return idx

            out[idx:idx+self.samples_per_symbol] = samples
            idx += self.samples_per_symbol

        return idx