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
    def __init__(self, alpha=1.5, beta=0.0, gama=1.0, samples_per_symbol=500, encode_alpha=True, encode_beta=True, encode_gama=False):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='alpha_encoder', # will show up in GRC
            in_sig=[np.uint8], #vrsta podatka ka gre in
            out_sig=[np.float32] #vrsta podatka ka gre out
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.alpha = alpha
        self.beta = beta
        self.gama = gama
        self.encode_alpha = encode_alpha
        self.encode_beta = encode_beta
        self.encode_gama = encode_gama
        self.samples_per_symbol = samples_per_symbol

    #Chambers-Mallows-Stuck Method (stran 8), alpha naj ni = 1 za 1 mogoce pole
    def alpha_stable(self, size, alpha, beta, gama=1.0): #size=number_of_samples generated, scale je gama (igraj se s temi tremi ce ti rata lahk encodas en byte kar ze ni tko slabo)
        V = np.random.uniform(-np.pi/2, np.pi/2, size)
        W = np.random.exponential(1, size)

        B = np.arctan(beta * np.tan(np.pi * alpha / 2)) / alpha
        S = (1 + (beta**2) * (np.tan(np.pi * alpha / 2)**2))**(1/(2*alpha))

        X = S * (np.sin(alpha * (V + B)) / (np.cos(V))**(1/alpha)) * ((np.cos(V - alpha * (V + B)) / W)**((1-alpha)/alpha))

        return gama * X

    def work(self, input_items, output_items):
        data = input_items[0]
        out = output_items[0]

        idx = 0

        for byte in data:
            b = byte / 255.0  # normalize

            # defaults
            alpha = self.alpha
            beta = self.beta
            gama = self.gama

            # encode parameters if enabled
            if self.encode_alpha:
                alpha = 1.1 + b * 0.9   # 1.1 → 2.0

            if self.encode_beta:
                beta = -1.0 + 2.0 * b   # -1 → 1

            if self.encode_gama:
                gama = 0.1 + 2.0 * b   # 0.1 → 2.1

            samples = self.alpha_stable(self.samples_per_symbol, alpha, beta, gama)

            if idx + self.samples_per_symbol > len(out):
                break
            
            out[idx:idx+self.samples_per_symbol] = samples
            idx += self.samples_per_symbol
            print("Produced:", idx)
        return idx