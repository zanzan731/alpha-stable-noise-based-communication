#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Alpha stable simulation
# GNU Radio version: 3.10.12.0

from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
import alpha_stable_generator_epy_block_1 as epy_block_1  # embedded python block
import threading




class alpha_stable_generator(gr.top_block):

    def __init__(self, L=20, alpha_map_str="1.2,1.4,1.6,1.8", beta_map_str="-1.0,1.0", center_frequency=915000000, decoded_file=r"decoded.bin", encoded_file=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\encoded.bin", eos_timeout=3.0, gama_map_str="0.5,1.0,1.5,2.0", noise_ratio=10, samples_per_symbol=500, source_file=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\source.bin", source_number_of_samples=128):
        gr.top_block.__init__(self, "Alpha stable simulation", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Parameters
        ##################################################
        self.L = L
        self.alpha_map_str = alpha_map_str
        self.beta_map_str = beta_map_str
        self.center_frequency = center_frequency
        self.decoded_file = decoded_file
        self.encoded_file = encoded_file
        self.eos_timeout = eos_timeout
        self.gama_map_str = gama_map_str
        self.noise_ratio = noise_ratio
        self.samples_per_symbol = samples_per_symbol
        self.source_file = source_file
        self.source_number_of_samples = source_number_of_samples

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 64000
        self.gama_map = gama_map = [float(x) for x in gama_map_str.split(",")]
        self.beta_map = beta_map = [float(x) for x in beta_map_str.split(",")]
        self.alpha_map = alpha_map = [float(x) for x in alpha_map_str.split(",")]

        ##################################################
        # Blocks
        ##################################################

        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(("serial=30F4146", '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_time_unknown_pps(uhd.time_spec(0))

        self.uhd_usrp_source_0.set_center_freq(center_frequency, 0)
        self.uhd_usrp_source_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_source_0.set_bandwidth(200000, 0)
        self.uhd_usrp_source_0.set_gain(55, 0)
        self.epy_block_1 = epy_block_1.alpha_decoder(beta_map=beta_map, samples_per_symbol=samples_per_symbol, L=L, sync_symbols=32, sync_threshold=0.75, sync_corr_threshold=None, sync_coherence_threshold=0.08, header_repetitions=3, max_payload_bytes=1000000, debug_symbols=20, expected_output_bytes=source_number_of_samples, timing_guard_symbols=6)
        self.blocks_file_sink_1 = blocks.file_sink(gr.sizeof_char*1, decoded_file, False)
        self.blocks_file_sink_1.set_unbuffered(True)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.epy_block_1, 0), (self.blocks_file_sink_1, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.epy_block_1, 0))


    def get_L(self):
        return self.L

    def set_L(self, L):
        self.L = L
        self.epy_block_1.L = self.L

    def get_alpha_map_str(self):
        return self.alpha_map_str

    def set_alpha_map_str(self, alpha_map_str):
        self.alpha_map_str = alpha_map_str

    def get_beta_map_str(self):
        return self.beta_map_str

    def set_beta_map_str(self, beta_map_str):
        self.beta_map_str = beta_map_str

    def get_center_frequency(self):
        return self.center_frequency

    def set_center_frequency(self, center_frequency):
        self.center_frequency = center_frequency
        self.uhd_usrp_source_0.set_center_freq(self.center_frequency, 0)

    def get_decoded_file(self):
        return self.decoded_file

    def set_decoded_file(self, decoded_file):
        self.decoded_file = decoded_file
        self.blocks_file_sink_1.open(self.decoded_file)

    def get_encoded_file(self):
        return self.encoded_file

    def set_encoded_file(self, encoded_file):
        self.encoded_file = encoded_file

    def get_eos_timeout(self):
        return self.eos_timeout

    def set_eos_timeout(self, eos_timeout):
        self.eos_timeout = eos_timeout

    def get_gama_map_str(self):
        return self.gama_map_str

    def set_gama_map_str(self, gama_map_str):
        self.gama_map_str = gama_map_str

    def get_noise_ratio(self):
        return self.noise_ratio

    def set_noise_ratio(self, noise_ratio):
        self.noise_ratio = noise_ratio

    def get_samples_per_symbol(self):
        return self.samples_per_symbol

    def set_samples_per_symbol(self, samples_per_symbol):
        self.samples_per_symbol = samples_per_symbol
        self.epy_block_1.samples_per_symbol = self.samples_per_symbol

    def get_source_file(self):
        return self.source_file

    def set_source_file(self, source_file):
        self.source_file = source_file

    def get_source_number_of_samples(self):
        return self.source_number_of_samples

    def set_source_number_of_samples(self, source_number_of_samples):
        self.source_number_of_samples = source_number_of_samples
        self.epy_block_1.expected_output_bytes = self.source_number_of_samples

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_gama_map(self):
        return self.gama_map

    def set_gama_map(self, gama_map):
        self.gama_map = gama_map

    def get_beta_map(self):
        return self.beta_map

    def set_beta_map(self, beta_map):
        self.beta_map = beta_map
        self.epy_block_1.beta_map = self.beta_map

    def get_alpha_map(self):
        return self.alpha_map

    def set_alpha_map(self, alpha_map):
        self.alpha_map = alpha_map



def argument_parser():
    parser = ArgumentParser()
    parser.add_argument(
        "--L", dest="L", type=intx, default=20,
        help="Set L [default=%(default)r]")
    parser.add_argument(
        "--alpha-map-str", dest="alpha_map_str", type=str, default="1.2,1.4,1.6,1.8",
        help="Set alpha_map_str [default=%(default)r]")
    parser.add_argument(
        "--beta-map-str", dest="beta_map_str", type=str, default="-1.0,1.0",
        help="Set beta_map_str [default=%(default)r]")
    parser.add_argument(
        "--center-frequency", dest="center_frequency", type=intx, default=915000000,
        help="Set center_frequency [default=%(default)r]")
    parser.add_argument(
        "--decoded-file", dest="decoded_file", type=str, default=r"decoded.bin",
        help="Set decoded_file [default=%(default)r]")
    parser.add_argument(
        "--encoded-file", dest="encoded_file", type=str, default=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\encoded.bin",
        help="Set encoded_file [default=%(default)r]")
    parser.add_argument(
        "--eos-timeout", dest="eos_timeout", type=eng_float, default=eng_notation.num_to_str(float(3.0)),
        help="Set EOS_timeout [default=%(default)r]")
    parser.add_argument(
        "--gama-map-str", dest="gama_map_str", type=str, default="0.5,1.0,1.5,2.0",
        help="Set gama_map_str [default=%(default)r]")
    parser.add_argument(
        "--noise-ratio", dest="noise_ratio", type=eng_float, default=eng_notation.num_to_str(float(10)),
        help="Set noise_ratio [default=%(default)r]")
    parser.add_argument(
        "--samples-per-symbol", dest="samples_per_symbol", type=intx, default=500,
        help="Set samples_per_symbol [default=%(default)r]")
    parser.add_argument(
        "--source-file", dest="source_file", type=str, default=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\source.bin",
        help="Set source_file [default=%(default)r]")
    parser.add_argument(
        "--source-number-of-samples", dest="source_number_of_samples", type=intx, default=128,
        help="Set source_number_of_samples [default=%(default)r]")
    return parser


def main(top_block_cls=alpha_stable_generator, options=None):
    if options is None:
        options = argument_parser().parse_args()
    tb = top_block_cls(L=options.L, alpha_map_str=options.alpha_map_str, beta_map_str=options.beta_map_str, center_frequency=options.center_frequency, decoded_file=options.decoded_file, encoded_file=options.encoded_file, eos_timeout=options.eos_timeout, gama_map_str=options.gama_map_str, noise_ratio=options.noise_ratio, samples_per_symbol=options.samples_per_symbol, source_file=options.source_file, source_number_of_samples=options.source_number_of_samples)

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    tb.wait()


if __name__ == '__main__':
    main()
