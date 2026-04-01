"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr


class alpha_decoder(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Decoder for alpha_encoder using samples with corresponding variances"""

    def __init__(self, alpha_map=[1.2, 1.4, 1.6, 1.8], beta_map=[-1.0, -0.3, 0.3, 1.0], gama_map=[0.5, 1.0, 1.5, 2.0], samples_per_symbol=500, L=10, encode_alpha=True, encode_beta=True, encode_gama=False):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='alpha_decoder',   # will show up in GRC
            in_sig=[np.float32],
            out_sig=[np.uint8]
        )
        self.samples_per_symbol = samples_per_symbol
        self.L = L
        self.encode_alpha = encode_alpha
        self.encode_beta = encode_beta
        self.encode_gama = encode_gama
        self.alpha_map = alpha_map
        self.beta_map = beta_map
        self.gama_map = gama_map

        self.bit_buffer = []

    @staticmethod
    def ali_je_deljivo(samples_per_symbol, L):
         return samples_per_symbol % L == 0
            
    @staticmethod
    def closest_index(value, list):
        arr = np.array(list)
        return int(np.argmin(np.abs(arr - value)))
    
    @staticmethod
    def is_power_of_two(x):
            #flika vse bitke bo tocn 0
            return x == 0 or (x & (x - 1)) == 0
    
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
        else:
            raise ValueError("One of the maps is not of power 2^n")

    def work(self, input_items, output_items):
        in_samples = input_items[0]
        out = output_items[0]
        num_symbols = len(in_samples) // self.samples_per_symbol
        if not self.ali_je_deljivo(self.samples_per_symbol, self.L):
            raise ValueError("Samples_per_symbol is not devisible by L")

        samples_per_realization = self.samples_per_symbol // self.L


        for sym in range(num_symbols):
            #print(self.bit_buffer)
            sym_samples = in_samples[sym*self.samples_per_symbol : (sym+1)*self.samples_per_symbol]

            Yl_max = []
            Yl_min = []

            for l in range(self.L):
                #samples kolko jih dat skup in kje zacet in koncat
                start = l*samples_per_realization 
                end = start + samples_per_realization
                segment = sym_samples[start:end] #probably samples_per_symbol mora bit deliv z L

                Yl_max.append(np.max(segment))
                Yl_min.append(np.min(segment))

            #zdej zračuni vse

            Y_max = np.mean(Yl_max)
            Y_min = np.mean(Yl_min)

            s2_max = np.var(Yl_max, ddof=1) #ddof je za uno minus 1 (deliš z L - 1) dokumentacija
            s2_min = np.var(Yl_min, ddof=1)

            #zdej pa iz tega izračunamo parametre
            
            #alpha
            probably_alpha = (np.pi / (2*np.sqrt(6))) * ((1.0 / Y_max) + (1.0 / Y_min))

            #beta
            probably_beta = 1 - (2 / (np.exp(probably_alpha*(np.sqrt(s2_max) - np.sqrt(s2_min)))))

            #gama (to je skaliranje torej provamo z Y_max in Y_min, mogoče pa tudi kako drugače z max od vseh ne povpračje al neki idk)
            probably_gama = (Y_max - Y_min) / 2.0

            #zdej rabim samo še mapirat te vrednosti najbližjim vrednostim v mapi
            if self.encode_alpha:
                alpha_idx = self.closest_index(probably_alpha, self.alpha_map)
                bits_alpha = self.log2_za_potence2(len(self.alpha_map))
                #rabim ohranjat LSB iz encoderja
                self.bit_buffer += [(alpha_idx >> i) & 1 for i in range(bits_alpha)] # bejzi od zadi naprej mozn da je to fljeno da bi mogu MSB ka je areeb neki reku idk
            
            if self.encode_beta:
                beta_idx = self.closest_index(probably_beta, self.beta_map)
                bits_beta = self.log2_za_potence2(len(self.beta_map))
                self.bit_buffer += [(beta_idx >> i) & 1 for i in range(bits_beta)] 

            if self.encode_gama:
                gama_idx = self.closest_index(probably_gama, self.gama_map)
                bits_gama = self.log2_za_potence2(len(self.gama_map))
                self.bit_buffer += [(gama_idx >> i) & 1 for i in range(bits_gama)]

        idx = 0
        #convert bits to bytes
        for i in range(0, len(self.bit_buffer), 8):
            byte_bits = self.bit_buffer[i:i+8]
            if len(byte_bits) < 8:
                break

            val = sum([bit << j for j, bit in enumerate(byte_bits)])

            if idx < len(out):
                out[idx] = val
                idx += 1
        
        self.bit_buffer = self.bit_buffer[idx*8:] #zbriše une ka sm v tem loopu zdej uporabu

        return idx