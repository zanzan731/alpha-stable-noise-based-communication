import argparse
import os
import re

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SIMULATION_ROOT = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations"
GRAPH_OUTPUT_DIR = os.path.join(SIMULATION_ROOT, "graphs_logarithmic")


FILE_LINE_RE = re.compile(r"File stevilka\s+\d+:\s*(\d+)\s*/\s*(\d+)")

def prepare_log_values(y_values):
    y_arr = np.asarray(y_values, dtype=float)

    # Protect against accidental zeros
    y_arr[y_arr <= 0] = 1e-12

    return y_arr

def read_error_rate(output_path):
    total_errors = 0
    total_bits = 0

    with open(output_path, "r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            match = FILE_LINE_RE.search(line)
            if match:
                total_errors += int(match.group(1))
                total_bits += int(match.group(2))

    if total_bits == 0:
        return None, False

    # BER cannot be shown as zero on a logarithmic axis.
    # If no errors were observed, plot the smallest measurable BER.
    if total_errors == 0:
        return 1.0 / total_bits, True

    return total_errors / total_bits, False


def decode_beta_label(folder_name):
    return folder_name.replace("m", "-").replace("_", ",", 1)


def ensure_output_dir():
    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)
def save_publication_chart(
    curves,
    title,
    xlabel,
    ylabel,
    filename,
):
    fig, ax = plt.subplots(figsize=(8, 5))

    colors = plt.cm.tab20.colors

    for i, (label, x_values, y_values) in enumerate(curves):
        x_arr = np.asarray(x_values, dtype=float)
        y_plot = prepare_log_values(y_values)

        ax.plot(
            x_arr,
            y_plot,
            "-o",
            linewidth=2.2,
            markersize=6,
            markerfacecolor="white",
            markeredgewidth=1.5,
            color=colors[i % len(colors)],
            label=label,
        )

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)

    ax.set_yscale("log")

    apply_publication_style(ax)

    ax.legend(loc="upper right")

    fig.tight_layout()

    fig.savefig(
        os.path.join(GRAPH_OUTPUT_DIR, filename),
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

def apply_publication_style(ax):
    ax.set_axisbelow(True)

    ax.minorticks_on()

    ax.grid(which="major", linestyle="-", linewidth=0.6, alpha=0.35)
    ax.grid(which="minor", linestyle=":", linewidth=0.4, alpha=0.30)

    for spine in ax.spines.values():
        spine.set_linewidth(1.1)

    ax.tick_params(
        which="major",
        direction="in",
        length=6,
        width=1.1,
    )

    ax.tick_params(
        which="minor",
        direction="in",
        length=3,
        width=0.8,
    )


def graph_beta():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_beta")

    if not os.path.isdir(base_dir):
        return

    curves = []

    sample_dirs = sorted(
        [d for d in os.listdir(base_dir) if d.isdigit()],
        key=int
    )

    for sample_dir in sample_dirs:

        results = []

        current_dir = os.path.join(base_dir, sample_dir)

        beta_folders = []
        for folder_name in os.listdir(current_dir):
            label = decode_beta_label(folder_name)

            try:
                beta_min, beta_max = map(float, label.split(","))
            except ValueError:
                continue

            delta_beta = beta_max - beta_min
            beta_folders.append((delta_beta, folder_name))

        for delta_beta, folder_name in sorted(beta_folders):

            output_path = os.path.join(current_dir, folder_name, "output.txt")

            if not os.path.isfile(output_path):
                continue

            error_rate, stop_curve = read_error_rate(output_path)

            if error_rate is None:
                continue

            results.append((delta_beta, error_rate))

            # After first zero-error point, skip all remaining folders for this curve.
            if stop_curve:
                break

        results.sort()

        if results:
            x, y = zip(*results)
            curves.append((f"N={sample_dir}", x, y))

    save_publication_chart(
        curves,
        "BER vs Δβ",
        "Δβ",
        "BER",
        "beta_error.png",
    )

def graph_gama():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_gama")

    if not os.path.isdir(base_dir):
        return

    curves = []

    sample_dirs = sorted(
        [d for d in os.listdir(base_dir) if d.isdigit()],
        key=int
    )

    for sample_dir in sample_dirs:

        results = []

        current_dir = os.path.join(base_dir, sample_dir)

        gamma_folders = []
        for folder_name in os.listdir(current_dir):
            try:
                gamma = float(folder_name.replace("p", "."))
            except ValueError:
                continue

            gamma_folders.append((gamma, folder_name))

        for gamma, folder_name in sorted(gamma_folders):

            output_path = os.path.join(current_dir, folder_name, "output.txt")

            if not os.path.isfile(output_path):
                continue

            error_rate, stop_curve = read_error_rate(output_path)

            if error_rate is None:
                continue

            results.append((gamma, error_rate))

            # After first zero-error point, skip all remaining folders for this curve.
            if stop_curve:
                break

        results.sort()

        if results:

            gamma_values, ber = zip(*results)

            msnr = [10*np.log10(g) for g in gamma_values]

            curves.append((f"N={sample_dir}", msnr, ber))

    save_publication_chart(
        curves,
        "BER vs MSNR",
        "MSNR (dB)",
        "BER",
        "gama_error_log.png",
    )

def graph_sample_size():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_noise")

    if not os.path.isdir(base_dir):
        return

    curves = []

    noise_entries = []
    for noise_dir in os.listdir(base_dir):
        try:
            noise_value = float(noise_dir.replace("noise_", "").replace("p", "."))
        except ValueError:
            continue

        noise_entries.append((noise_value, noise_dir))

    for noise_value, noise_dir in sorted(noise_entries):

        current_dir = os.path.join(base_dir, noise_dir)

        if not os.path.isdir(current_dir):
            continue

        results = []

        sample_dirs = sorted(
            [d for d in os.listdir(current_dir) if d.isdigit()],
            key=int
        )

        for sample_dir in sample_dirs:

            output_path = os.path.join(current_dir, sample_dir, "output.txt")

            if not os.path.isfile(output_path):
                continue

            error_rate, stop_curve = read_error_rate(output_path)

            if error_rate is None:
                continue

            results.append((int(sample_dir), error_rate))

            # After first zero-error point, skip all remaining folders for this curve.
            if stop_curve:
                break

        if results:

            x, y = zip(*results)

            noise = f"{noise_value:g}"

            curves.append((f"Noise={noise}", x, y))

    save_publication_chart(
        curves,
        "BER vs samples per symbol",
        "Samples per symbol (N)",
        "BER",
        "sample_size_error.png",
    )


def graph_l():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_L")

    if not os.path.isdir(base_dir):
        return

    curves = []

    l_dirs = []
    for folder_name in os.listdir(base_dir):
        if not folder_name.startswith("L_"):
            continue

        try:
            l_value = int(folder_name.replace("L_", ""))
        except ValueError:
            continue

        l_dirs.append((l_value, folder_name))

    for l_value, folder_name in sorted(l_dirs):
        results = []
        current_dir = os.path.join(base_dir, folder_name)

        sample_dirs = sorted(
            [d for d in os.listdir(current_dir) if d.isdigit()],
            key=int,
        )

        for sample_dir in sample_dirs:
            output_path = os.path.join(current_dir, sample_dir, "output.txt")

            if not os.path.isfile(output_path):
                continue

            error_rate, stop_curve = read_error_rate(output_path)

            if error_rate is None:
                continue

            results.append((int(sample_dir), error_rate))

            if stop_curve:
                break

        if results:
            x, y = zip(*results)
            curves.append((f"L={l_value}", x, y))

    save_publication_chart(
        curves,
        "BER vs samples per symbol",
        "Samples per symbol (N)",
        "BER",
        "l_error_log.png",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plot",
        choices=[
            "all",
            "beta",
            "gama",
            "sample_size",
            "l",
        ],
        default="all",
        help="Choose which graph family to generate.",
    )
    args = parser.parse_args()

    ensure_output_dir()

    if args.plot in ("all", "beta"):
        graph_beta()

    if args.plot in ("all", "gama"):
        graph_gama()

    if args.plot in ("all", "sample_size"):
        graph_sample_size()

    if args.plot in ("all", "l"):
        graph_l()

    print(f"Graphs written to {GRAPH_OUTPUT_DIR}")

if __name__ == "__main__":
    main()