"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr


class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, example_param=1.0):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Alpha stable noise source',   # will show up in GRC
            in_sig=None, #za enkrat dejmo sam random signal pole naj bo input in bomo provali prave podatke poslat
            out_sig=[np.complex64]
        )
        
        self.alpha = float(1.6)
        self.scale = float(1.0)
        self.clip = float(3.0)

        self.rng = np.random.default_rng(1234)

    def alpha_stable(self, size):
        alpha = self.alpha

        v = self.rng.uniform(-np.pi/2, np.pi/2, size)
        w = self.rng.exponential(1, size)

        part1 = np.sin(alpha*v)/(np.cos(v))**(1/alpha)
        part2 = (np.cos((1-alpha)*v) / w)**((1-alpha)/alpha)
        return part1 * part2


    def work(self, input_items, output_items):
        N = len(output_items[0])

        noise_i = self.alpha_stable(N)
        noise_q = self.alpha_stable(N)

        complex_noise = noise_i + 1j * noise_q

        complex_noise *= self.scale

        # Clip to prevent USRP saturation
        if self.clip > 0:
            mag = np.abs(complex_noise)
            mask = mag > self.clip
            complex_noise[mask] = self.clip * complex_noise[mask] / mag[mask]

        output_items[0][:] = complex_noise.astype(np.complex64)

        return N

