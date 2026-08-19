# Alpha-stable SDR link

The sender and receiver each contain their complete implementation directly in
their GNU Radio Embedded Python Block:

- `sender/alpha_stable_generator_epy_block_0.py` contains the encoder
- `receiver/alpha_stable_generator_epy_block_1.py` contains the decoder

The same complete source is stored inside each `.grc` block, so opening or
regenerating the flowgraph does not depend on a separate protocol module.

The over-the-air frame is:

1. 32-symbol deterministic synchronization word
2. a deterministic 10-byte header repeated three times (magic, length, CRC-32)
3. one positive deterministic pilot followed by one beta-encoded alpha-stable
   data symbol for every payload bit
4. a short deterministic end guard that is not part of the payload

Both B210s must use the same center frequency, sample rate, and samples per
symbol. The defaults are 915 MHz, 64 kS/s, and 500 samples/symbol.
The sender places the waveform on a 4 kHz complex subcarrier to avoid the
B210's baseband DC notch; receiver carrier recovery removes it automatically.

## Hardware test

Start the receiver first:

```powershell
cd receiver
python alpha_stable_generator.py
```

Then start the sender on the other computer:

```powershell
cd sender
python alpha_stable_generator.py
```

The receiver prints `[SYNC SUCCESS]` after detecting the deterministic
preamble and validating the repeated header. It always writes the demodulated payload to
`decoded.bin`, including when CRC reports `FAIL`, so the two files can be used
to calculate BER. CRC does not correct or discard payload bits. Compare
`sender/source.bin` with `receiver/decoded.bin` after each received packet.

The receiver is a one-packet process. After the decoder has released its final
payload byte, it prints `[DEC OUTPUT COMPLETE]` and returns end-of-stream. GNU
Radio then drains all intermediate buffers through the unbuffered file sink.
Only after the scheduler's `wait()` confirms that draining is complete does the
application close the file and exit automatically.

The pilot before each payload symbol carries no information. It gives the
receiver a local phase/frequency reference for only the following alpha-stable
symbol; the bit is still encoded by alpha-stable beta (`-1` or `+1`) and decoded
with the extrema-based beta estimator. The estimator uses about five samples
per extrema segment and automatically increases the effective number of
segments when `samples_per_symbol` is increased. The receiver parameter `L`
defaults to 20 and is used as a hint only when it gives a statistically safe
segment length; the old fixed value `L=2` is not statistically sufficient and
produces strongly biased bit decisions after TX amplitude limiting. A few
samples are omitted at each data-symbol boundary so
that a small timing error cannot insert deterministic pilot samples into the
alpha-stable estimate. With the defaults, a 128-byte frame
takes about 18.19 seconds and a 256-byte frame takes about 34.19 seconds. The
sender also transmits an eight-symbol guard tail; the receiver ignores it.

The sender's `source_number_of_samples` controls the transmitted payload length.
The receiver reads the actual length from the validated header. If its local
`source_number_of_samples` differs, it prints `[HEADER LENGTH]` and uses the
sender's value instead of rejecting synchronization. Longer frames accumulate
more sample-clock drift between independent B210s, so the receiver measures the
first pilot/data transition and the final data/tail transition over a six-symbol
timing guard before resampling all pilot/data pairs. A tail estimate that would
imply more than 20 ppm of sample-clock error is rejected as a false transition;
the receiver then keeps the measured packet origin and uses the nominal pair
length instead of stretching the entire payload. The CRC line reports
`timing=tracked` or `timing=nominal` to show which timing mode was applied.

The receiver does not wait for an external PPS edge. The current flowgraph does
not use timed UHD commands, so PPS waiting would not synchronize the two B210
sample clocks and could prevent startup when no PPS source is connected.

Run each command from its `sender` or `receiver` directory as shown. The capture
filenames are intentionally relative because GNU Radio 3.10 on Windows can
mis-encode absolute paths containing non-ASCII characters such as `ž`.

The checked-in serial defaults are TX `30F4194` and RX `30F4146`. The sender
serial can be overridden from the command line:

```powershell
python alpha_stable_generator.py --device-serial SERIAL
```

The sender also exposes `--tx-gain` and `--payload-scale`. The receiver serial,
RX gain, and sample rate are currently configured in its GRC UHD Source block;
the checked-in defaults are 40 dB and 64 kS/s. Keep the sample rate and
`samples_per_symbol` identical on both computers.
