import argparse
import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import graphs_logaritmic_scale as original_graphs


MIN_BER = 1e-4
GRAPH_OUTPUT_DIR = os.path.join(
    original_graphs.SIMULATION_ROOT,
    "graphs_logarithmic_cutoff_1e-4",
)


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
        y_plot = original_graphs.prepare_log_values(y_values)

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
    ax.set_ylim(bottom=MIN_BER)

    original_graphs.apply_publication_style(ax)

    legend_location = "lower left" if filename == "beta_error.png" else "upper right"
    ax.legend(loc=legend_location)

    fig.tight_layout()
    fig.savefig(
        os.path.join(GRAPH_OUTPUT_DIR, filename),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plot",
        choices=["all", "beta", "gama", "sample_size", "l"],
        default="all",
        help="Choose which graph family to generate.",
    )
    args = parser.parse_args()

    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)

    original_graphs.GRAPH_OUTPUT_DIR = GRAPH_OUTPUT_DIR
    original_graphs.save_publication_chart = save_publication_chart

    if args.plot in ("all", "beta"):
        original_graphs.graph_beta()
    if args.plot in ("all", "gama"):
        original_graphs.graph_gama()
    if args.plot in ("all", "sample_size"):
        original_graphs.graph_sample_size()
    if args.plot in ("all", "l"):
        original_graphs.graph_l()

    print(f"Graphs written to {GRAPH_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
