#!/usr/bin/env python3
"""Transmit one framed alpha-stable packet with a USRP B210."""

import signal
import sys
import threading
from argparse import ArgumentParser
import numpy as np
from gnuradio import blocks, gr, uhd
from gnuradio.eng_arg import eng_float, intx

import alpha_stable_generator_epy_block_0 as epy_block_0


class alpha_stable_generator(gr.top_block):
    def __init__(
        self,
        L=20,
        alpha_map_str="1.2,1.4,1.6,1.8",
        beta_map_str="-1.0,1.0",
        center_frequency=915000000,
        decoded_file="",
        device_serial="30F4194",
        encoded_file="",
        eos_timeout=3.0,
        gama_map_str="0.5,1.0,1.5,2.0",
        noise_ratio=10,
        payload_scale=0.05,
        samp_rate=64000,
        samples_per_symbol=500,
        source_file="source.bin",
        source_number_of_samples=128,
        subcarrier_frequency=4000,
        tx_gain=35,
    ):
        gr.top_block.__init__(self, "Alpha-stable SDR sender", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        self.L = int(L)
        self.center_frequency = float(center_frequency)
        self.device_serial = str(device_serial)
        self.eos_timeout = float(eos_timeout)
        self.payload_scale = float(payload_scale)
        self.samp_rate = float(samp_rate)
        self.samples_per_symbol = int(samples_per_symbol)
        self.source_file = str(source_file)
        self.source_number_of_samples = int(source_number_of_samples)
        self.subcarrier_frequency = float(subcarrier_frequency)
        self.tx_gain = float(tx_gain)
        self.alpha_map = [float(value) for value in alpha_map_str.split(",")]
        self.beta_map = [float(value) for value in beta_map_str.split(",")]
        self.gama_map = [float(value) for value in gama_map_str.split(",")]

        device_args = f"serial={self.device_serial}" if self.device_serial else ""
        self.uhd_usrp_sink_0 = uhd.usrp_sink(
            device_args,
            uhd.stream_args(cpu_format="fc32", args="", channels=[0]),
            "",
        )
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)
        self.uhd_usrp_sink_0.set_center_freq(self.center_frequency, 0)
        self.uhd_usrp_sink_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_0.set_bandwidth(200000, 0)
        self.uhd_usrp_sink_0.set_gain(self.tx_gain, 0)

        actual_rate = float(self.uhd_usrp_sink_0.get_samp_rate())
        print(
            f"[SDR TX] serial={self.device_serial or 'auto'} "
            f"frequency={self.center_frequency:.0f} Hz rate={actual_rate:.0f} S/s "
            f"gain={self.tx_gain:.1f} dB",
            file=sys.stderr,
            flush=True,
        )
        if abs(actual_rate - self.samp_rate) > 1.0:
            raise RuntimeError(
                f"USRP negotiated {actual_rate} S/s, not {self.samp_rate} S/s. "
                "Use the same supported --samp-rate on sender and receiver."
            )

        self.epy_block_0 = epy_block_0.alpha_encoder(
            alpha_map=self.alpha_map,
            beta_map=self.beta_map,
            gama_map=self.gama_map,
            samples_per_symbol=self.samples_per_symbol,
            encode_alpha=False,
            encode_beta=True,
            encode_gama=False,
            eos_timeout=self.eos_timeout,
            expected_input_bytes=self.source_number_of_samples,
            sync_symbols=32,
            header_repetitions=3,
            payload_scale=self.payload_scale,
            sample_rate=self.samp_rate,
            subcarrier_frequency=self.subcarrier_frequency,
        )

        payload = np.random.randint(
            0, 256, self.source_number_of_samples, dtype=np.uint8
        )
        self.vector_source = blocks.vector_source_b(payload.tolist(), False)
        self.file_sink = blocks.file_sink(gr.sizeof_char, self.source_file, False)
        self.file_sink.set_unbuffered(True)

        self.connect(self.vector_source, self.file_sink)
        self.connect(self.vector_source, self.epy_block_0)
        self.connect(self.epy_block_0, self.uhd_usrp_sink_0)


def argument_parser():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--L", type=intx, default=20)
    parser.add_argument("--alpha-map-str", type=str, default="1.2,1.4,1.6,1.8")
    parser.add_argument("--beta-map-str", type=str, default="-1.0,1.0")
    parser.add_argument("--center-frequency", type=eng_float, default=915000000)
    parser.add_argument("--decoded-file", type=str, default="")
    parser.add_argument("--device-serial", type=str, default="30F4194")
    parser.add_argument("--encoded-file", type=str, default="")
    parser.add_argument("--eos-timeout", type=eng_float, default=3.0)
    parser.add_argument("--gama-map-str", type=str, default="0.5,1.0,1.5,2.0")
    parser.add_argument("--noise-ratio", type=eng_float, default=10)
    parser.add_argument("--payload-scale", type=eng_float, default=0.05)
    parser.add_argument("--samp-rate", type=eng_float, default=64000)
    parser.add_argument("--samples-per-symbol", type=intx, default=500)
    # Keep the C++ file sink path ASCII-only.  On Windows, GNU Radio 3.10 can
    # mis-encode non-ASCII user-directory names such as "žan".
    parser.add_argument("--source-file", type=str, default="source.bin")
    parser.add_argument("--source-number-of-samples", type=intx, default=128)
    parser.add_argument("--subcarrier-frequency", type=eng_float, default=4000)
    parser.add_argument("--tx-gain", type=eng_float, default=35)
    return parser


def main(top_block_cls=alpha_stable_generator, options=None):
    options = argument_parser().parse_args() if options is None else options
    tb = top_block_cls(**vars(options))

    def stop(*_):
        tb.stop()
        tb.wait()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    tb.start()
    tb.flowgraph_started.set()
    tb.wait()


if __name__ == "__main__":
    main()
