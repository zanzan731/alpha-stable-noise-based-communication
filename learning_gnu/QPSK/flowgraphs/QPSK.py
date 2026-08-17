#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: QPSKsender(ExcessBandwidth)
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import sip
import threading



class QPSK(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "QPSKsender(ExcessBandwidth)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("QPSKsender(ExcessBandwidth)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "QPSK")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 32000
        self.rrcDelay = rrcDelay = 1408
        self.constelQPSK = constelQPSK = digital.constellation_rect([-1-1j, -1+1j, 1+1j, 1-1j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.bpsk = bpsk = digital.constellation_bpsk().base()
        self.bpsk.set_npwr(1.0)
        self.bitDelay = bitDelay = 1756

        ##################################################
        # Blocks
        ##################################################

        self.tabi = Qt.QTabWidget()
        self.tabi_widget_0 = Qt.QWidget()
        self.tabi_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabi_widget_0)
        self.tabi_grid_layout_0 = Qt.QGridLayout()
        self.tabi_layout_0.addLayout(self.tabi_grid_layout_0)
        self.tabi.addTab(self.tabi_widget_0, 'Spectrum')
        self.tabi_widget_1 = Qt.QWidget()
        self.tabi_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabi_widget_1)
        self.tabi_grid_layout_1 = Qt.QGridLayout()
        self.tabi_layout_1.addLayout(self.tabi_grid_layout_1)
        self.tabi.addTab(self.tabi_widget_1, 'Time Domain')
        self.top_layout.addWidget(self.tabi)
        self._bitDelay_range = qtgui.Range(0, 3000, 1, 1756, 200)
        self._bitDelay_win = qtgui.RangeWidget(self._bitDelay_range, self.set_bitDelay, "Bit Delay", "counter_slider", float, QtCore.Qt.Horizontal)
        self.tabi_layout_0.addWidget(self._bitDelay_win)
        self._rrcDelay_range = qtgui.Range(0, 3000, 1, 1408, 200)
        self._rrcDelay_win = qtgui.RangeWidget(self._rrcDelay_range, self.set_rrcDelay, "RRC Delay", "counter_slider", float, QtCore.Qt.Horizontal)
        self.tabi_layout_0.addWidget(self._rrcDelay_win)
        self.qtgui_time_sink_x_0 = qtgui.time_sink_f(
            400, #size
            1, #samp_rate
            "Time domain", #name
            3, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0.set_update_time(0.10)
        self.qtgui_time_sink_x_0.set_y_axis(-1, 1)

        self.qtgui_time_sink_x_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0.enable_tags(True)
        self.qtgui_time_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0.enable_grid(False)
        self.qtgui_time_sink_x_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0.enable_stem_plot(False)


        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['dark blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(3):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0.qwidget(), Qt.QWidget)
        self.tabi_layout_1.addWidget(self._qtgui_time_sink_x_0_win)
        self.qtgui_freq_sink_x_0 = qtgui.freq_sink_f(
            2048, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Spectrum", #name
            2,
            None # parent
        )
        self.qtgui_freq_sink_x_0.set_update_time(0.10)
        self.qtgui_freq_sink_x_0.set_y_axis((-140), 10)
        self.qtgui_freq_sink_x_0.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_0.enable_autoscale(False)
        self.qtgui_freq_sink_x_0.enable_grid(False)
        self.qtgui_freq_sink_x_0.set_fft_average(0.05)
        self.qtgui_freq_sink_x_0.enable_axis_labels(True)
        self.qtgui_freq_sink_x_0.enable_control_panel(False)
        self.qtgui_freq_sink_x_0.set_fft_window_normalized(False)


        self.qtgui_freq_sink_x_0.set_plot_pos_half(not True)

        labels = ['Rectangular Bitstream', 'RRC Bitstream', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(2):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_0_win = sip.wrapinstance(self.qtgui_freq_sink_x_0.qwidget(), Qt.QWidget)
        self.tabi_layout_0.addWidget(self._qtgui_freq_sink_x_0_win)
        self.filter_fft_rrc_filter_0 = filter.fft_filter_fff(1, firdes.root_raised_cosine(1, samp_rate, 4000, 0.35, (11*samp_rate)), 1)
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=constelQPSK,
            differential=True,
            samples_per_symbol=8,
            pre_diff_code=True,
            excess_bw=0.35,
            verbose=False,
            log=False,
            truncate=False)
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(8)
        self.blocks_uchar_to_float_0 = blocks.uchar_to_float()
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_char*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_repeat_0 = blocks.repeat(gr.sizeof_char*1, 8)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_ff(2)
        self.blocks_delay_1 = blocks.delay(gr.sizeof_float*1, bitDelay)
        self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, bitDelay)
        self.blocks_complex_to_real_0 = blocks.complex_to_real(1)
        self.blocks_add_const_vxx_0 = blocks.add_const_ff((-0.5))
        self.analog_random_uniform_source_x_0 = analog.random_uniform_source_b(0, 255, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_random_uniform_source_x_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_add_const_vxx_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_complex_to_real_0, 0), (self.blocks_delay_0, 0))
        self.connect((self.blocks_complex_to_real_0, 0), (self.filter_fft_rrc_filter_0, 0))
        self.connect((self.blocks_delay_0, 0), (self.qtgui_freq_sink_x_0, 1))
        self.connect((self.blocks_delay_0, 0), (self.qtgui_time_sink_x_0, 1))
        self.connect((self.blocks_delay_1, 0), (self.blocks_add_const_vxx_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.qtgui_freq_sink_x_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.qtgui_time_sink_x_0, 0))
        self.connect((self.blocks_repeat_0, 0), (self.blocks_uchar_to_float_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.blocks_uchar_to_float_0, 0), (self.blocks_delay_1, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.blocks_repeat_0, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.blocks_complex_to_real_0, 0))
        self.connect((self.filter_fft_rrc_filter_0, 0), (self.qtgui_time_sink_x_0, 2))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "QPSK")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.filter_fft_rrc_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, 4000, 0.35, (11*self.samp_rate)))
        self.qtgui_freq_sink_x_0.set_frequency_range(0, self.samp_rate)

    def get_rrcDelay(self):
        return self.rrcDelay

    def set_rrcDelay(self, rrcDelay):
        self.rrcDelay = rrcDelay

    def get_constelQPSK(self):
        return self.constelQPSK

    def set_constelQPSK(self, constelQPSK):
        self.constelQPSK = constelQPSK

    def get_bpsk(self):
        return self.bpsk

    def set_bpsk(self, bpsk):
        self.bpsk = bpsk

    def get_bitDelay(self):
        return self.bitDelay

    def set_bitDelay(self, bitDelay):
        self.bitDelay = bitDelay
        self.blocks_delay_0.set_dly(int(self.bitDelay))
        self.blocks_delay_1.set_dly(int(self.bitDelay))




def main(top_block_cls=QPSK, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

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
