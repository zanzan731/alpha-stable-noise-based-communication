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
        return None

    # BER cannot be shown as zero on a logarithmic axis.
    # If no errors were observed, plot the smallest measurable BER.
    if total_errors == 0:
        return 1.0 / total_bits

    return total_errors / total_bits


def decode_beta_label(folder_name):
    return folder_name.replace("m", "-").replace("_", ",", 1)


def ensure_output_dir():
    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)

def save_publication_chart(x_values, y_values, title, xlabel, ylabel, filename):
    x_arr = np.asarray(x_values, dtype=float)
    y_plot = prepare_log_values(y_values)

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(
        x_arr,
        y_plot,
        "-o",
        linewidth=2.2,
        markersize=6,
        markerfacecolor="white",
        markeredgewidth=1.5,
    )

    if len(x_arr) >= 2:
        step = np.mean(np.diff(np.sort(x_arr)))
        ax.set_xlim(
            np.min(x_arr) - step * 0.5,
            np.max(x_arr) + step * 0.5,
        )

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)

    ax.set_yscale("log")

    apply_publication_style(ax)

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


def graph_noise_ratio():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_noise_ratio")
    results = []

    if not os.path.isdir(base_dir):
        print(f"Skipping noise-ratio graph, missing folder: {base_dir}")
        return

    for folder_name in sorted(os.listdir(base_dir)):
        output_path = os.path.join(base_dir, folder_name, "output.txt")
        if not os.path.isfile(output_path) or not folder_name.startswith("noise_"):
            continue

        error_rate = read_error_rate(output_path)
        if error_rate is None:
            continue

        noise_value = float(folder_name.replace("noise_", "").replace("p", "."))
        results.append((noise_value, error_rate))

    if not results:
        print("No noise-ratio results found.")
        return

    results.sort(key=lambda item: item[0])
    x_values, y_values = zip(*results)
    save_publication_chart(
        x_values,
        y_values,
        "Error rate vs noise ratio",
        "noise ratio",
        "error rate",
        "noise_ratio_error.png",
    )
    best_noise, best_value = min(results, key=lambda item: item[1])
    print(f"Best noise ratio: {best_noise} with error rate {best_value:.6f}")
def graph_beta():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_beta")
    results = []

    if not os.path.isdir(base_dir):
        print(f"Skipping beta graph, missing folder: {base_dir}")
        return

    for folder_name in sorted(os.listdir(base_dir)):
        output_path = os.path.join(base_dir, folder_name, "output.txt")
        if not os.path.isfile(output_path):
            continue

        error_rate = read_error_rate(output_path)
        if error_rate is None:
            continue

        label = decode_beta_label(folder_name)

        try:
            beta_min, beta_max = map(float, label.split(","))
        except ValueError:
            continue

        delta_beta = beta_max - beta_min

        results.append((delta_beta, error_rate))

    if not results:
        print("No beta results found.")
        return

    results.sort(key=lambda x: x[0])
    x_values, y_values = zip(*results)

    save_publication_chart(
        x_values,
        y_values,
        "BER vs Δβ",
        "β",
        "BER",
        "beta_error.png",
    )

    best_beta, best_value = min(results, key=lambda x: x[1])
    print(f"Best beta: {best_beta} with error rate {best_value:.6f}")

def graph_gama():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_gama")
    results = []

    if not os.path.isdir(base_dir):
        print(f"Skipping gama graph, missing folder: {base_dir}")
        return

    for folder_name in sorted(os.listdir(base_dir)):
        output_path = os.path.join(base_dir, folder_name, "output.txt")
        if not os.path.isfile(output_path):
            continue

        error_rate = read_error_rate(output_path)
        if error_rate is None:
            continue

        try:
            gama_value = float(folder_name.replace("p", ".").replace("m", "-"))
        except ValueError:
            continue

        results.append((gama_value, error_rate))

    if not results:
        print("No gama results found.")
        return

    results.sort(key=lambda item: item[0])
    gamma_values, y_values = zip(*results)
    gamma_reference = 1.0
    x_values = [10.0 * np.log10(gamma / gamma_reference) for gamma in gamma_values if gamma > 0]
    y_values = [y for gamma, y in zip(gamma_values, y_values) if gamma > 0]

    if not x_values:
        print("No positive gama values found for MSNR conversion.")
        return

    save_publication_chart(
        x_values,
        y_values,
        "BER vs MSNR",
        "MSNR (dB)",
        "BER",
        "gama_error_log.png",
    )

    best_gama, best_value = min(results, key=lambda item: item[1])
    print(f"Best gama: {best_gama} with error rate {best_value:.6f}")


def graph_sample_size():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_sample_size")
    results = []

    if not os.path.isdir(base_dir):
        print(f"Skipping sample-size graph, missing folder: {base_dir}")
        return

    for folder_name in sorted(os.listdir(base_dir), key=lambda value: int(value) if value.isdigit() else value):
        output_path = os.path.join(base_dir, folder_name, "output.txt")
        if not os.path.isfile(output_path) or not folder_name.isdigit():
            continue

        error_rate = read_error_rate(output_path)
        if error_rate is None:
            continue

        results.append((int(folder_name), error_rate))

    if not results:
        print("No sample-size results found.")
        return

    x_values, y_values = zip(*results)
    save_publication_chart(x_values, y_values, "Error rate vs sample size", "samples per symbol", "error rate", "sample_size_error.png")
    best_sample, best_value = min(results, key=lambda item: item[1])
    print(f"Best sample size: {best_sample} with error rate {best_value:.6f}")



def graph_sample_size_with_noise():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_sample_size_with_noise")
    results = []

    if not os.path.isdir(base_dir):
        print(f"Skipping sample-size graph, missing folder: {base_dir}")
        return

    for folder_name in sorted(os.listdir(base_dir), key=lambda value: int(value) if value.isdigit() else value):
        output_path = os.path.join(base_dir, folder_name, "output.txt")
        if not os.path.isfile(output_path) or not folder_name.isdigit():
            continue

        error_rate = read_error_rate(output_path)
        if error_rate is None:
            continue

        results.append((int(folder_name), error_rate))

    if not results:
        print("No sample-size results found.")
        return

    x_values, y_values = zip(*results)
    save_publication_chart(x_values, y_values, "Error rate vs sample size", "samples per symbol", "error rate", "sample_size_error_with_noise.png")
    best_sample, best_value = min(results, key=lambda item: item[1])
    print(f"Best sample size: {best_sample} with error rate {best_value:.6f}")




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plot",
        choices=["all", "beta", "gama", "sample_size", "noise_ratio", "l_ratio", "sample_size_with_noise"],
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
    
    if args.plot in ("all", "sample_size_with_noise"):
        graph_sample_size_with_noise()

    if args.plot in ("all", "noise_ratio"):
        graph_noise_ratio()

    print(f"Graphs written to {GRAPH_OUTPUT_DIR}")


if __name__ == "__main__":
    main()