# Noise-Based Wireless Communication Using Software-Defined Radio

This repository contains the thesis, reference material, simulation code, SDR implementations, and experimental results for a communication system that encodes information in the statistical parameters of alpha-stable noise.

## Folder overview

| Folder | Contents |
| --- | --- |
| `articles_and_other_pdfs/` | Articles and other PDF material read while preparing the thesis. There is also the antena specifications of my antena that was used. |
| `binary_diff/` | C++ code that compares two binary files bit by bit and reports how many bits differ. The current program processes numbered pairs of source and decoded files and writes a text report. This is used inside automatization.py for writting back a report on BER(bit error rate). |
| `biodiff/` | A graphical binary comparison tool that runs in a terminal or Windows Command Prompt. It lets you inspect two binary files visually. |
| `Conference_latex/` | LaTeX files for the conference paper. **Writing is in progress.** |
| `full_rewrite/` | The main GNU Radio simulation of communication using alpha-stable noise, including automated experiments and plotting scripts. See below for parameters and examples. |
| `itterations_of_codes/` | Earlier versions and experiments. These old implementations are kept temporarily and will be deleted when a more final version is ready. |
| `latex_diplomska/` | Thesis written in LaTeX, with Slovenian and English versions. |
| `matlab_implementation/` | MATLAB implementations and simulations involving alpha-stable distributions, including distribution utilities and communication experiments. |
| `SDR_alpha_stable/` | Alpha-stable transmitter and receiver code for an actual radio link. An over-the-air experiment requires **two SDR devices**, one for transmission and one for reception. |
| `SDR_tests/`, `simulations/`, `simulations_old/` | Test results, measurement outputs, and older experiments. Some test folders contain only `.txt` reports because the complete binary files were not uploaded or kept up to date(since the binary files combined were larger than 100 GBs at the end). |

## Thesis

The Slovenian thesis is available from the [University of Ljubljana Repository](https://repozitorij.uni-lj.si/IzpisGradiva.php?id=187276&lang=slv).

In `latex_diplomska/`:

- `vzorec_dip_Seminar.tex` is the Slovenian LaTeX source.
- `english.tex` and `english.pdf` contain the English version.

**English translation notice:** The English version was translated using AI. I have not read through the entire English document, so it may still contain translation mistakes or inaccuracies.

## Simulation: `full_rewrite/`

The simulation generates random input bytes, encodes them into alpha-stable noise samples, adds Gaussian channel noise, and decodes the received samples back into bytes. It saves the original bytes, encoded samples, and decoded bytes so that decoding errors can be measured.

No SDR hardware is needed for this simulation. Use a Python environment with GNU Radio and its Python bindings. The flowgraph was generated with **GNU Radio 3.10.12.0** and also uses NumPy, PyQt5, and the GNU Radio Qt GUI components. Plotting scripts require Matplotlib.

### Main files

- `alpha_stable_generator.grc`: flowgraph to open and edit in GNU Radio Companion.
- `alpha_stable_generator.py`: runnable simulation.
- `alpha_stable_generator_epy_block_0.py`: custom alpha-stable encoder.
- `alpha_stable_generator_epy_block_1.py`: custom decoder using an extrema-based beta estimator.
- `automatization.py`: repeated experiments and parameter sweeps.
- `graphs.py` and the `graphs_log...` scripts: plots from saved experiment reports.

Keep the embedded block files beside the runnable script. If editing through GNU Radio Companion, update the embedded block source there as well: regenerating a flowgraph can overwrite generated Python files.

### Simulation parameters

| Parameter / command-line option | Meaning and how to experiment |
| --- | --- |
| `beta_map` / `--beta-map-str` | Comma-separated beta values representing symbols. Beta controls asymmetry and lies between -1 and 1. The default `-1.0,1.0` represents two symbols, or one bit per symbol. Try `-0.5,0.5` to make the distributions more similar and observe how this affects decoding. Enabled mapping sizes must be powers of two. |
| `gama_map` / `--gama-map-str` | Scale of the alpha-stable samples. With gamma encoding disabled, only the first value is used. A larger positive value increases sample amplitudes relative to a fixed amount of added channel noise. Default: `1.0`. |
| `samples_per_symbol` / `--samples-per-symbol` | Number of samples per symbol, denoted by N. Increasing N usually improves parameter estimation but increases processing time, output size, and symbol duration. Default: `500`. |
| `L` / `--L` | Number of segments used by the decoder to estimate beta from extrema. Default: `2`. Choose an integer of at least 2 that divides N exactly. Changing L changes the balance between the number of segments and the number of samples in each segment. |
| `noise_ratio` / `--noise-ratio` | Amplitude setting of the added Gaussian noise source, rather than an SNR value in decibels. `0` disables added noise; larger values make decoding more difficult. Script default: `5`. |
| `source_number_of_samples` / `--source-number-of-samples` | Number of randomly generated input **bytes**, despite the name. Default: `128`, corresponding to 1024 input bits. |
| `source_file` / `--source-file` | Output file containing the generated original bytes. This option does not load an existing input file. |
| `encoded_file` / `--encoded-file` | Output file containing encoded float32 samples before channel noise is added. This is a waveform file, not a byte-for-byte copy of the message. |
| `decoded_file` / `--decoded-file` | Output file containing the recovered bytes. Compare this with the source file to measure bit errors. |
| `eos_timeout` / `--eos-timeout` | Fallback inactivity timeout in seconds for end-of-stream handling. Default: `3`. The flowgraph also supplies expected byte and sample counts. |
| `alpha_map` / `--alpha-map-str` | Candidate stability parameters. In the current flowgraph, alpha encoding is disabled and the encoder fixes alpha at `1.1`; changing this option alone does not change that fixed value. |
| `encode_alpha`, `encode_beta`, `encode_gama` | Embedded block settings controlling which parameters carry information. The runnable flowgraph uses `False`, `True`, `False`. The current decoder supports beta encoding only; enabling the other modes requires further implementation. |
| `samp_rate` | Set to `32000` in the simulation script/flowgraph and used for the GUI frequency scale. It is not exposed as a command-line option in this simulation. |

### Run one simulation

From the `Diploma` directory, in an environment where GNU Radio is available:

```powershell
cd full_rewrite
python alpha_stable_generator.py --beta-map-str="-1.0,1.0" --gama-map-str="1.0" --samples-per-symbol 500 --L 2 --noise-ratio 1 --source-number-of-samples 128 --source-file source_1.bin --encoded-file encoded_1.bin --decoded-file decoded_1.bin
```

This example uses relative output paths to avoid the machine-specific defaults in the script. The files are written to the current directory and an existing file with the same name is overwritten. For a new experiment, use a new output directory or different filenames.

Try changing one parameter at a time:

1. Start with `--noise-ratio 0` to observe decoding without added channel noise.
2. Increase noise while keeping the mapping and N fixed.
3. Increase N and compare the number of incorrectly decoded bits.
4. Reduce the separation between beta values, for example to `--beta-map-str="-0.5,0.5"`.
5. Vary gamma or L to study signal scaling and estimator behaviour.

The code can be used to study bit error rate (BER), compare decoder settings, investigate the reliability-versus-sample-count trade-off, and develop alternative estimators. Supporting alpha or gamma modulation end to end requires extending the decoder and checking the flowgraph's sample-count assumptions.

### Automated tests and plots

`automatization.py` contains the experiments used to sweep beta mappings, gamma, noise amplitude, L, and the number of samples per symbol. By default, each configuration is run **100 times**.

Before running it on another computer, change:

- `BINARY_DIFF_EXE` to the location of your compiled binary comparison program.
- The `base_dir` and `output_dir` paths inside the experiment functions to your own results folders.
- `SIMULATION_ROOT` and any other machine-specific paths in the plotting scripts.

The automation starts subprocesses using `python`, so that command must point to an environment with GNU Radio installed. If the comparison executable is missing, its step is skipped and no comparison report is generated for that run.

From `full_rewrite/`, run:

```powershell
python automatization.py --experiment different_beta
python automatization.py --experiment different_gama
python automatization.py --experiment different_noise
python automatization.py --experiment different_L
```

Other options are `--experiment all`, `--experiment graphs`, and `--experiment graphs_logarithmic`. Running without arguments opens an interactive menu, which also includes a small test option. A full sweep creates many binary files and can take substantial time and disk space; reduce `runs` and the parameter lists for a quick trial.

Some checked-in result folders contain only `.txt` reports rather than all original binaries. To rerun the same experiment configurations and regenerate the binaries, use these automated tests after updating the paths. New runs use random data and random noise, so their exact error counts may differ.

## Comparing binary files

### `binary_diff/`

Build `binary_diff/binary_diff/binary_diff.cpp` using a C++ compiler, or use a compatible existing executable. The current program does not accept two filenames as command-line arguments. Instead, run it from the directory containing pairs named:

```text
source_1.bin     decoded_1.bin
source_2.bin     decoded_2.bin
...
```

It compares each pair bit by bit, stops at the first missing pair, and writes `output.txt` in that directory. The report contains each pair's differing-bit count and total compared bits, plus the average number of errors across completed pairs. A length mismatch is reported separately. For a completed equal-length pair:

```text
BER = number of differing bits / total number of compared bits
```

Compare the original and decoded byte files, not the encoded float32 waveform file.

### `biodiff/`

For visual inspection, open a terminal in `biodiff/` and run:

```powershell
.\biodiff.exe source.bin decoded.bin
```

This opens a graphical terminal view of the binary differences. Use it to inspect where files differ; use `binary_diff` for the bit-error counts used in the experiment reports.

## Hardware communication: `SDR_alpha_stable/`

The `sender/` and `receiver/` folders implement transmission and reception of framed alpha-stable noise. The repository also contains `receiver2/` for my testing purposues for what code changes do to the sistem rather then corupting the working receiver and `closed_environment_sim/` for software experiments. The startup instructions below refer to `sender/` and `receiver/`.

For the actual radio link, you need **two SDRs**: one transmitter and one receiver. The code was developed for two USRP B210 devices with suitable antennas. Install GNU Radio with UHD support and the required device drivers on the computers running them.

### Configure your devices

Replace the saved device addresses/serial numbers with those of **your own SDRs**:

- Sender: use `--device-serial YOUR_TX_SERIAL`. The saved default is `30F4194`.
- Receiver: change `serial=30F4146` in the UHD USRP Source block in `receiver/alpha_stable_generator.grc` and regenerate the flowgraph. If running the Python file directly, change the device argument in `receiver/alpha_stable_generator.py`. The receiver currently has no `--device-serial` command-line option.

The transmitter and receiver must agree on the centre frequency, actual sample rate, samples per symbol, and symbol mapping. Configure compatible antenna ports and gains for the connected equipment.

### Main SDR parameters

| Setting | Purpose and current configuration |
| --- | --- |
| Device address / serial | Selects which physical SDR to use. Configure separately for TX and RX as described above. |
| `center_frequency` / `--center-frequency` | Radio carrier frequency in Hz. Default: `915000000` (915 MHz) on both sides. |
| `samp_rate` / sender `--samp-rate` | Complex sample rate. Default: `64000` samples/s. On the receiver, change it in the flowgraph or Python configuration; there is no receiver command-line option for it. |
| `samples_per_symbol` / `--samples-per-symbol` | Samples in each pilot or data symbol. Default: `500`. Larger values increase packet duration and give the decoder more observations. Must match on both sides. |
| `beta_map` / `--beta-map-str` | Two beta values used for the binary data symbols. Default: `-1.0,1.0`. Keep this mapping for the supplied hardware setup; changes require checking decoder decisions as well. |
| Alpha and gamma | The current SDR sample generator uses fixed alpha `1.1` and unit gamma. The map arguments are retained in the interface, but alpha/gamma encoding is disabled. |
| `payload_scale` / sender `--payload-scale` | Scales alpha-stable payload amplitudes before limiting them for transmission. Default: `0.05`. This affects the transmitted sample distribution. |
| `tx_gain` / sender `--tx-gain` | Transmitter hardware gain in dB. Default: `35`. |
| RX gain | Receiver hardware gain in dB. Currently `40`, configured in its UHD Source block. |
| `subcarrier_frequency` / sender `--subcarrier-frequency` | Places the baseband waveform on a complex subcarrier to avoid the radio's DC notch. Default: `4000` Hz. Receiver carrier recovery estimates and removes the offset. |
| `source_number_of_samples` / `--source-number-of-samples` | Sender payload size in **bytes**. Default: `128`. The receiver obtains the actual payload length from the validated packet header. |
| `source_file` / sender `--source-file` | Saves the randomly generated transmitted bytes; default `source.bin`. It does not read an existing file as payload. |
| `decoded_file` / receiver `--decoded-file` | Saves recovered payload bytes; default `decoded.bin`. |
| `eos_timeout` / `--eos-timeout` | Fallback end-of-stream inactivity timeout in seconds. Default: `3`. |
| `L` / receiver `--L` | Hint for the extrema estimator's segment count; the current `receiver/` script defaults to `5`. The decoder may choose a different effective segment count to keep segments suitable for estimation. This differs from the fixed-L simulation. |
| Synchronisation thresholds | Embedded decoder settings controlling correlation/coherence checks for packet detection. Change these in the decoder block if experimenting with synchronisation. |

Some simulation-style arguments remain in the SDR i will delete it some day (probably). For example, `noise_ratio` does not add simulated Gaussian noise to the hardware link, and the sender's `encoded_file` argument does not create a waveform capture in the current script...

### Run a hardware test

Start the receiver first, from its own directory:

```powershell
cd SDR_alpha_stable/receiver
python alpha_stable_generator.py --samples-per-symbol 500 --center-frequency 915000000 --decoded-file decoded.bin
```

Then, on the transmitter computer, start the sender from its own directory:

```powershell
cd SDR_alpha_stable/sender
python alpha_stable_generator.py --device-serial YOUR_TX_SERIAL --samples-per-symbol 500 --center-frequency 915000000 --source-number-of-samples 128 --source-file source.bin
```

You can also change this parameters in GNU Radio Companion and then just run the it by ```python alpha_stable_generator.py``` but be careful to generate it before you run it so you dont run the old version. 

Run these commands from the `Diploma` directory on the respective computers before changing into the indicated folder. Replace `YOUR_TX_SERIAL` and configure the receiver serial before starting. Relative capture filenames are useful on Windows, where paths containing non-ASCII characters can cause problems with GNU Radio file handling.

The transmitter sends a synchronisation sequence, a repeated header, pilot/data pairs, and a guard tail. The receiver reports synchronisation and CRC results, writes the decoded payload even if CRC fails, and exits after one packet. CRC detects errors; it does not correct them. Restart the receiver for another packet.

After reception, bring `sender/source.bin` and `receiver/decoded.bin` onto the same computer and compare them. To use the current `binary_diff` program, place copies named `source_1.bin` and `decoded_1.bin` in a comparison directory and run the executable there.

Additional implementation details are in [`SDR_alpha_stable/README.md`](SDR_alpha_stable/README.md). The code and parameter descriptions above refer to the current implementation; older test results may have been produced with earlier versions or settings.
