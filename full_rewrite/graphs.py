import argparse
import os
import re

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SIMULATION_ROOT = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations"
GRAPH_OUTPUT_DIR = os.path.join(SIMULATION_ROOT, "graphs")


FILE_LINE_RE = re.compile(r"File stevilka\s+\d+:\s*(\d+)\s*/\s*(\d+)")


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

    return total_errors / total_bits


def decode_beta_label(folder_name):
    return folder_name.replace("m", "-").replace("_", ",", 1)


def ensure_output_dir():
    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)


def save_bar_chart(labels, values, title, xlabel, ylabel, filename, rotation=20):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, values, color="#2f6fed")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=rotation)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(GRAPH_OUTPUT_DIR, filename), dpi=200)
    plt.close(fig)


def save_line_chart(x_values, y_values, title, xlabel, ylabel, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x_values, y_values, marker="o", linewidth=2, color="#2f6fed")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(GRAPH_OUTPUT_DIR, filename), dpi=200)
    plt.close(fig)


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

        results.append((decode_beta_label(folder_name), error_rate))

    if not results:
        print("No beta results found.")
        return

    labels, values = zip(*results)
    save_bar_chart(labels, values, "Average error by beta map", "beta map", "error rate", "beta_error.png")
    best_label, best_value = min(results, key=lambda item: item[1])
    print(f"Best beta map: {best_label} with error rate {best_value:.6f}")


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
    save_line_chart(x_values, y_values, "Error rate vs sample size", "samples per symbol", "error rate", "sample_size_error.png")
    best_sample, best_value = min(results, key=lambda item: item[1])
    print(f"Best sample size: {best_sample} with error rate {best_value:.6f}")


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
    save_line_chart(x_values, y_values, "Error rate vs noise ratio", "noise ratio", "error rate", "noise_ratio_error.png")
    best_noise, best_value = min(results, key=lambda item: item[1])
    print(f"Best noise ratio: {best_noise} with error rate {best_value:.6f}")


def graph_l_ratio():
    base_dir = os.path.join(SIMULATION_ROOT, "BERvsMSNR_different_L_K_ratio")
    results = []

    if not os.path.isdir(base_dir):
        print(f"Skipping L/K graph, missing folder: {base_dir}")
        return

    for folder_name in sorted(os.listdir(base_dir)):
        output_path = os.path.join(base_dir, folder_name, "output.txt")
        if not os.path.isfile(output_path) or not folder_name.startswith("sample_"):
            continue

        match = re.match(r"sample_(\d+)_L_(\d+)", folder_name)
        if not match:
            continue

        sample_size = int(match.group(1))
        l_value = int(match.group(2))
        error_rate = read_error_rate(output_path)
        if error_rate is None:
            continue

        ratio = sample_size / l_value
        results.append((ratio, sample_size, l_value, error_rate))

    if not results:
        print("No L/K results found.")
        return

    results.sort(key=lambda item: item[0])
    ratios = [item[0] for item in results]
    errors = [item[3] for item in results]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(ratios, errors, color="#2f6fed")
    ax.set_title("Error rate vs K/L ratio")
    ax.set_xlabel("K/L ratio (sample size / L)")
    ax.set_ylabel("error rate")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(GRAPH_OUTPUT_DIR, "l_ratio_error.png"), dpi=200)
    plt.close(fig)

    best_ratio, best_sample, best_l, best_value = min(results, key=lambda item: item[3])
    print(f"Best K/L ratio: {best_ratio:.3f} from sample {best_sample} and L {best_l} with error rate {best_value:.6f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plot",
        choices=["all", "beta", "sample_size", "noise_ratio", "l_ratio"],
        default="all",
        help="Choose which graph family to generate.",
    )
    args = parser.parse_args()

    ensure_output_dir()

    if args.plot in ("all", "beta"):
        graph_beta()

    if args.plot in ("all", "sample_size"):
        graph_sample_size()

    if args.plot in ("all", "noise_ratio"):
        graph_noise_ratio()

    if args.plot in ("all", "l_ratio"):
        graph_l_ratio()

    print(f"Graphs written to {GRAPH_OUTPUT_DIR}")


if __name__ == "__main__":
    main()