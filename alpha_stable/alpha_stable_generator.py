#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Alpha stable simulation
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import analog
from gnuradio import blocks
import numpy
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import alpha_stable_generator_epy_block_0 as epy_block_0  # embedded python block
import alpha_stable_generator_epy_block_1 as epy_block_1  # embedded python block
import threading



class alpha_stable_generator(gr.top_block, Qt.QWidget):

    def __init__(self, L=4, alpha_map_str="1.2,1.4,1.6,1.8", beta_map_str="-1.0,1.0", decoded_file=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\decoded.bin", encoded_file=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\encoded.bin", gama_map_str="0.5,1.0,1.5,2.0", samples_per_symbol=24, source_file=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\source.bin", source_number_of_samples=128):
        gr.top_block.__init__(self, "Alpha stable simulation", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Alpha stable simulation")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "alpha_stable_generator")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Parameters
        ##################################################
        self.L = L
        self.alpha_map_str = alpha_map_str
        self.beta_map_str = beta_map_str
        self.decoded_file = decoded_file
        self.encoded_file = encoded_file
        self.gama_map_str = gama_map_str
        self.samples_per_symbol = samples_per_symbol
        self.source_file = source_file
        self.source_number_of_samples = source_number_of_samples

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 32000
        self.gama_map = gama_map = [float(x) for x in gama_map_str.split(",")]
        self.beta_map = beta_map = [float(x) for x in beta_map_str.split(",")]
        self.alpha_map = alpha_map = [float(x) for x in alpha_map_str.split(",")]

        ##################################################
        # Blocks
        ##################################################

        self.epy_block_1 = epy_block_1.alpha_decoder(alpha_map=alpha_map, beta_map=beta_map, gama_map=gama_map, samples_per_symbol=samples_per_symbol, L=L, encode_alpha=False, encode_beta=True, encode_gama=False)
        self.epy_block_0 = epy_block_0.alpha_encoder(alpha_map=alpha_map, beta_map=beta_map, gama_map=gama_map, samples_per_symbol=samples_per_symbol, encode_alpha=False, encode_beta=True, encode_gama=False)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_char*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_head_1 = blocks.head(gr.sizeof_float*1, (source_number_of_samples*8*samples_per_symbol - 1))
        self.blocks_head_0 = blocks.head(gr.sizeof_char*1, 128)
        self.blocks_file_sink_2 = blocks.file_sink(gr.sizeof_float*1, encoded_file, False)
        self.blocks_file_sink_2.set_unbuffered(False)
        self.blocks_file_sink_1 = blocks.file_sink(gr.sizeof_char*1, decoded_file, False)
        self.blocks_file_sink_1.set_unbuffered(False)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_char*1, source_file, False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_add_xx_0 = blocks.add_vff(1)
        self.analog_random_source_x_0 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 255, source_number_of_samples))), False)
        self.analog_noise_source_x_0 = analog.noise_source_f(analog.GR_GAUSSIAN, 0.2, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_noise_source_x_0, 0), (self.blocks_head_1, 0))
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_head_0, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.epy_block_1, 0))
        self.connect((self.blocks_head_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.blocks_head_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_head_1, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.blocks_throttle2_0, 0), (self.epy_block_0, 0))
        self.connect((self.epy_block_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.epy_block_0, 0), (self.blocks_file_sink_2, 0))
        self.connect((self.epy_block_1, 0), (self.blocks_file_sink_1, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "alpha_stable_generator")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

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

    def get_decoded_file(self):
        return self.decoded_file

    def set_decoded_file(self, decoded_file):
        self.decoded_file = decoded_file
        self.blocks_file_sink_1.open(self.decoded_file)

    def get_encoded_file(self):
        return self.encoded_file

    def set_encoded_file(self, encoded_file):
        self.encoded_file = encoded_file
        self.blocks_file_sink_2.open(self.encoded_file)

    def get_gama_map_str(self):
        return self.gama_map_str

    def set_gama_map_str(self, gama_map_str):
        self.gama_map_str = gama_map_str

    def get_samples_per_symbol(self):
        return self.samples_per_symbol

    def set_samples_per_symbol(self, samples_per_symbol):
        self.samples_per_symbol = samples_per_symbol
        self.blocks_head_1.set_length((self.source_number_of_samples*8*self.samples_per_symbol - 1))
        self.epy_block_0.samples_per_symbol = self.samples_per_symbol
        self.epy_block_1.samples_per_symbol = self.samples_per_symbol

    def get_source_file(self):
        return self.source_file

    def set_source_file(self, source_file):
        self.source_file = source_file
        self.blocks_file_sink_0.open(self.source_file)

    def get_source_number_of_samples(self):
        return self.source_number_of_samples

    def set_source_number_of_samples(self, source_number_of_samples):
        self.source_number_of_samples = source_number_of_samples
        self.blocks_head_1.set_length((self.source_number_of_samples*8*self.samples_per_symbol - 1))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)

    def get_gama_map(self):
        return self.gama_map

    def set_gama_map(self, gama_map):
        self.gama_map = gama_map
        self.epy_block_0.gama_map = self.gama_map
        self.epy_block_1.gama_map = self.gama_map

    def get_beta_map(self):
        return self.beta_map

    def set_beta_map(self, beta_map):
        self.beta_map = beta_map
        self.epy_block_0.beta_map = self.beta_map
        self.epy_block_1.beta_map = self.beta_map

    def get_alpha_map(self):
        return self.alpha_map

    def set_alpha_map(self, alpha_map):
        self.alpha_map = alpha_map
        self.epy_block_0.alpha_map = self.alpha_map
        self.epy_block_1.alpha_map = self.alpha_map



def argument_parser():
    parser = ArgumentParser()
    parser.add_argument(
        "--L", dest="L", type=intx, default=4,
        help="Set L [default=%(default)r]")
    parser.add_argument(
        "--alpha-map-str", dest="alpha_map_str", type=str, default="1.2,1.4,1.6,1.8",
        help="Set alpha_map_str [default=%(default)r]")
    parser.add_argument(
        "--beta-map-str", dest="beta_map_str", type=str, default="-1.0,1.0",
        help="Set beta_map_str [default=%(default)r]")
    parser.add_argument(
        "--decoded-file", dest="decoded_file", type=str, default=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\decoded.bin",
        help="Set decoded_file [default=%(default)r]")
    parser.add_argument(
        "--encoded-file", dest="encoded_file", type=str, default=r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\encoded.bin",
        help="Set encoded_file [default=%(default)r]")
    parser.add_argument(
        "--gama-map-str", dest="gama_map_str", type=str, default="0.5,1.0,1.5,2.0",
        help="Set gama_map_str [default=%(default)r]")
    parser.add_argument(
        "--samples-per-symbol", dest="samples_per_symbol", type=intx, default=24,
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

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(L=options.L, alpha_map_str=options.alpha_map_str, beta_map_str=options.beta_map_str, decoded_file=options.decoded_file, encoded_file=options.encoded_file, gama_map_str=options.gama_map_str, samples_per_symbol=options.samples_per_symbol, source_file=options.source_file, source_number_of_samples=options.source_number_of_samples)

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
