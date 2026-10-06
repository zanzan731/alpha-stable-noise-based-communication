"""Generate the logarithmic BER charts as animation-friendly vector SVGs.

The data collection and graph selection are intentionally delegated to
``graphs_logaritmic_scale.py`` so that the SVG and PNG scripts always use the
same input data and stopping rules.

SVG drawing order (and Inkscape layer order):

1. axes, grid, labels, title, and legend;
2. every curve's leftmost point;
3. every connector from the first point to the second point;
4. every curve's second point;
5. the following connectors and points, continuing left to right.

Every plotted point and connector is a separate vector object.  Text is also
converted to vector paths, and the exporter rejects an SVG if Matplotlib ever
places a raster ``<image>`` element in it.
"""

import argparse
import os
import re
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

try:
    from . import graphs_logaritmic_scale as original_graphs
except ImportError:
    import graphs_logaritmic_scale as original_graphs


GRAPH_OUTPUT_DIR = os.path.join(
    original_graphs.SIMULATION_ROOT,
    "graphs_logarithmic_svg",
)

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
INKSCAPE_NAMESPACE = "http://www.inkscape.org/namespaces/inkscape"

ET.register_namespace("", SVG_NAMESPACE)
ET.register_namespace("xlink", XLINK_NAMESPACE)
ET.register_namespace("inkscape", INKSCAPE_NAMESPACE)

DATA_GROUP_RE = re.compile(
    r"data_(point_\d{3}|segment_\d{3}_to_\d{3})_curve_\d{3}$"
)


def _shortened_segment(ax, start, end, marker_size_points):
    """Return data coordinates whose ends meet, but do not cross, the dots."""
    start_display = ax.transData.transform(start)
    end_display = ax.transData.transform(end)
    difference = end_display - start_display
    length = np.linalg.norm(difference)

    # Matplotlib marker sizes are diameters in points.  Shortening in display
    # coordinates keeps the visible result correct even with a logarithmic axis.
    radius_pixels = marker_size_points * ax.figure.dpi / 144.0
    if length <= 2.0 * radius_pixels:
        return start, end

    direction = difference / length
    visible_start = start_display + radius_pixels * direction
    visible_end = end_display - radius_pixels * direction
    inverse_transform = ax.transData.inverted()

    return (
        tuple(inverse_transform.transform(visible_start)),
        tuple(inverse_transform.transform(visible_end)),
    )


def _layer_label(phase, layer_number):
    if phase.startswith("point_"):
        point_number = int(phase.removeprefix("point_")) + 1
        if point_number == 1:
            return f"{layer_number:02d} leftmost points"
        return f"{layer_number:02d} points {point_number}"

    match = re.fullmatch(r"segment_(\d{3})_to_(\d{3})", phase)
    if match:
        start = int(match.group(1)) + 1
        end = int(match.group(2)) + 1
        return f"{layer_number:02d} connectors {start} to {end}"

    return f"{layer_number:02d} {phase}"


def _organize_svg_layers(svg_path):
    """Wrap Matplotlib objects in ordered, named Inkscape-compatible layers."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    group_tag = f"{{{SVG_NAMESPACE}}}g"
    image_tag = f"{{{SVG_NAMESPACE}}}image"
    path_tag = f"{{{SVG_NAMESPACE}}}path"
    use_tag = f"{{{SVG_NAMESPACE}}}use"

    # Matplotlib represents a space in path-converted text as an empty <path>
    # definition.  Browsers accept it, but the SVG parser used by Manim 0.19
    # raises TypeError when a path has no ``d`` attribute.  Empty glyphs draw
    # nothing, and glyph positions are absolute, so both the definition and its
    # references can safely be removed.
    parent_by_child = {
        child: parent for parent in root.iter() for child in list(parent)
    }
    empty_path_ids = set()
    for element in list(root.iter(path_tag)):
        if element.get("d", "").strip():
            continue
        if element.get("id"):
            empty_path_ids.add(element.get("id"))
        parent = parent_by_child.get(element)
        if parent is not None:
            parent.remove(element)

    if empty_path_ids:
        parent_by_child = {
            child: parent for parent in root.iter() for child in list(parent)
        }
        for element in list(root.iter(use_tag)):
            reference = element.get(f"{{{XLINK_NAMESPACE}}}href") or element.get(
                "href"
            )
            if reference not in {f"#{path_id}" for path_id in empty_path_ids}:
                continue
            parent = parent_by_child.get(element)
            if parent is not None:
                parent.remove(element)

    if any(element.tag == image_tag for element in root.iter()):
        raise RuntimeError(f"Raster image found in vector output: {svg_path}")

    axes_group = next(
        (
            element
            for element in root.iter(group_tag)
            if element.get("id") == "axes_1"
        ),
        None,
    )
    if axes_group is None:
        raise RuntimeError(f"Could not find the axes group in {svg_path}")

    figure_group = next(
        (
            element
            for element in root.iter(group_tag)
            if element.get("id") == "figure_1"
        ),
        None,
    )
    figure_background = None
    if figure_group is not None:
        figure_background = next(
            (
                child
                for child in list(figure_group)
                if child.get("id") == "patch_1"
            ),
            None,
        )
        if figure_background is not None:
            figure_group.remove(figure_background)

    axes_children = []
    phases = {}
    phase_order = []

    for child in list(axes_group):
        group_id = child.get("id", "")
        match = DATA_GROUP_RE.fullmatch(group_id)
        if match is None:
            axes_children.append(child)
            continue

        phase = match.group(1)
        if phase not in phases:
            phases[phase] = []
            phase_order.append(phase)
        phases[phase].append(child)

    for child in list(axes_group):
        axes_group.remove(child)

    axes_layer = ET.SubElement(
        axes_group,
        group_tag,
        {
            "id": "layer_001_axes",
            f"{{{INKSCAPE_NAMESPACE}}}groupmode": "layer",
            f"{{{INKSCAPE_NAMESPACE}}}label": "01 axes, grid, labels, and legend",
        },
    )
    if figure_background is not None:
        axes_layer.append(figure_background)
    for child in axes_children:
        axes_layer.append(child)

    for layer_number, phase in enumerate(phase_order, start=2):
        layer = ET.SubElement(
            axes_group,
            group_tag,
            {
                "id": f"layer_{layer_number:03d}_{phase}",
                f"{{{INKSCAPE_NAMESPACE}}}groupmode": "layer",
                f"{{{INKSCAPE_NAMESPACE}}}label": _layer_label(
                    phase, layer_number
                ),
            },
        )
        for child in phases[phase]:
            layer.append(child)

    tree.write(svg_path, encoding="utf-8", xml_declaration=True)


def save_publication_chart(curves, title, xlabel, ylabel, filename):
    """Save one chart as a fully vector, left-to-right layered SVG."""
    figure, axes = plt.subplots(figsize=(8, 5))
    colors = plt.cm.tab20.colors
    marker_size = 6
    prepared_curves = []
    legend_handles = []

    for curve_index, (label, x_values, y_values) in enumerate(curves):
        x_values = np.asarray(x_values, dtype=float)
        y_values = original_graphs.prepare_log_values(y_values)
        color = colors[curve_index % len(colors)]
        prepared_curves.append((label, x_values, y_values, color))

        # Invisible lines establish the same automatic limits as the PNG script.
        axes.plot(x_values, y_values, visible=False)
        legend_handles.append(
            Line2D(
                [],
                [],
                color=color,
                linewidth=2.2,
                marker="o",
                markersize=marker_size,
                markerfacecolor="white",
                markeredgewidth=1.5,
                label=label,
            )
        )

    axes.set_title(title, fontsize=14)
    axes.set_xlabel(xlabel, fontsize=12)
    axes.set_ylabel(ylabel, fontsize=12)
    axes.set_yscale("log")
    original_graphs.apply_publication_style(axes)

    output_stem = os.path.splitext(os.path.basename(filename))[0]
    legend_location = "lower left" if output_stem == "beta_error" else "upper right"
    if legend_handles:
        axes.legend(handles=legend_handles, loc=legend_location)

    figure.tight_layout()
    figure.canvas.draw()

    max_point_count = max(
        (len(x_values) for _, x_values, _, _ in prepared_curves),
        default=0,
    )

    # All data artists share a z-order.  Matplotlib therefore writes them in
    # insertion order, after every axes/label/legend artist.
    for point_index in range(max_point_count):
        for curve_index, (_, x_values, y_values, color) in enumerate(
            prepared_curves
        ):
            if point_index >= len(x_values):
                continue

            point, = axes.plot(
                [x_values[point_index]],
                [y_values[point_index]],
                linestyle="None",
                marker="o",
                markersize=marker_size,
                markerfacecolor="white",
                markeredgewidth=1.5,
                color=color,
                zorder=10,
            )
            point.set_gid(
                f"data_point_{point_index:03d}_curve_{curve_index:03d}"
            )

        for curve_index, (_, x_values, y_values, color) in enumerate(
            prepared_curves
        ):
            if point_index + 1 >= len(x_values):
                continue

            start = (x_values[point_index], y_values[point_index])
            end = (x_values[point_index + 1], y_values[point_index + 1])
            visible_start, visible_end = _shortened_segment(
                axes, start, end, marker_size
            )
            segment, = axes.plot(
                [visible_start[0], visible_end[0]],
                [visible_start[1], visible_end[1]],
                linestyle="-",
                linewidth=2.2,
                color=color,
                solid_capstyle="butt",
                zorder=10,
            )
            segment.set_gid(
                "data_segment_"
                f"{point_index:03d}_to_{point_index + 1:03d}_"
                f"curve_{curve_index:03d}"
            )

    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)
    svg_filename = f"{output_stem}.svg"
    output_path = os.path.join(GRAPH_OUTPUT_DIR, svg_filename)

    with matplotlib.rc_context(
        {
            "svg.fonttype": "path",
            "svg.hashsalt": "graphs-logarithmic-scale-svg",
        }
    ):
        figure.savefig(
            output_path,
            format="svg",
            bbox_inches="tight",
            metadata={"Date": None},
        )

    plt.close(figure)
    _organize_svg_layers(output_path)


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

    print(f"Vector SVG graphs written to {GRAPH_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
