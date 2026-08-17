#!/usr/bin/env python3
"""Closed-environment loopback using the exact hardware link protocol."""

import signal
from argparse import ArgumentParser
import numpy as np
from gnuradio import blocks, gr
from gnuradio.eng_arg import eng_float, intx

import alpha_stable_generator_epy_block_0 as epy_block_0
import alpha_stable_generator_epy_block_1 as epy_block_1


class alpha_stable_generator(gr.top_block):
    def __init__(
        self,
        L=20,
        alpha_map_str="1.2,1.4,1.6,1.8",
        beta_map_str="-1.0,1.0",
        center_frequency=915000000,
        decoded_file="decoded.bin",
        encoded_file="",
        eos_timeout=3.0,
        expected_output_bytes=None,
        gama_map_str="0.5,1.0,1.5,2.0",
        noise_ratio=0,
        payload_scale=0.05,
        samples_per_symbol=500,
        source_file="source.bin",
        source_number_of_samples=128,
    ):
        gr.top_block.__init__(self, "Alpha-stable framed loopback", catch_exceptions=True)
        count = int(source_number_of_samples)
        expected = count if expected_output_bytes is None else int(expected_output_bytes)
        alpha_map = [float(value) for value in alpha_map_str.split(",")]
        beta_map = [float(value) for value in beta_map_str.split(",")]
        gama_map = [float(value) for value in gama_map_str.split(",")]

        payload = np.random.randint(0, 256, count, dtype=np.uint8)
        self.source = blocks.vector_source_b(payload.tolist(), False)
        self.encoder = epy_block_0.alpha_encoder(
            alpha_map=alpha_map,
            beta_map=beta_map,
            gama_map=gama_map,
            samples_per_symbol=samples_per_symbol,
            encode_alpha=False,
            encode_beta=True,
            encode_gama=False,
            eos_timeout=eos_timeout,
            expected_input_bytes=count,
            sync_symbols=32,
            header_repetitions=3,
            payload_scale=payload_scale,
            sample_rate=64000,
            subcarrier_frequency=4000,
        )
        self.decoder = epy_block_1.alpha_decoder(
            beta_map=beta_map,
            samples_per_symbol=samples_per_symbol,
            L=L,
            sync_symbols=32,
            sync_threshold=0.75,
            header_repetitions=3,
            expected_output_bytes=expected,
        )
        self.source_sink = blocks.file_sink(gr.sizeof_char, str(source_file), False)
        self.decoded_sink = blocks.file_sink(gr.sizeof_char, str(decoded_file), False)
        self.source_sink.set_unbuffered(True)
        self.decoded_sink.set_unbuffered(True)

        self.connect(self.source, self.source_sink)
        self.connect(self.source, self.encoder)
        self.connect(self.encoder, self.decoder)
        self.connect(self.decoder, self.decoded_sink)


def argument_parser():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--L", type=intx, default=20)
    parser.add_argument("--alpha-map-str", type=str, default="1.2,1.4,1.6,1.8")
    parser.add_argument("--beta-map-str", type=str, default="-1.0,1.0")
    parser.add_argument("--center-frequency", type=eng_float, default=915000000)
    parser.add_argument("--decoded-file", type=str, default="decoded.bin")
    parser.add_argument("--encoded-file", type=str, default="")
    parser.add_argument("--eos-timeout", type=eng_float, default=3.0)
    parser.add_argument("--expected-output-bytes", type=intx, default=None)
    parser.add_argument("--gama-map-str", type=str, default="0.5,1.0,1.5,2.0")
    parser.add_argument("--noise-ratio", type=eng_float, default=0)
    parser.add_argument("--payload-scale", type=eng_float, default=0.05)
    parser.add_argument("--samples-per-symbol", type=intx, default=500)
    parser.add_argument("--source-file", type=str, default="source.bin")
    parser.add_argument("--source-number-of-samples", type=intx, default=128)
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
    tb.run()


if __name__ == "__main__":
    main()
