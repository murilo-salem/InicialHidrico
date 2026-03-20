#!/usr/bin/env python3
"""Generate SVG plots from descriptive-statistics CSV outputs."""

from __future__ import annotations

import csv
import html
import math
from dataclasses import dataclass
from pathlib import Path


GENOTYPE_ORDER = {"BR16": 0, "CD202": 1, "EMB48": 2}
CONDITION_ORDER = {"irrigado": 0, "nao_irrigado": 1}
GENOTYPE_COLORS = {
    "BR16": "#0f766e",
    "CD202": "#c2410c",
    "EMB48": "#2563eb",
}
DATE_COLORS = {
    "2017-02-23": "#0f766e",
    "2017-02-24": "#2563eb",
    "2017-02-25": "#c2410c",
    "2017-02-26": "#a16207",
    "2017-02-27": "#7c3aed",
    "2017-03-02": "#0891b2",
}
CONDITION_STYLES = {
    "irrigado": {"dash": "", "opacity": "0.96"},
    "nao_irrigado": {"dash": "8 6", "opacity": "0.86"},
}


@dataclass(frozen=True)
class SpectralRecord:
    date: str
    genotype: str
    condition: str
    n_samples: int
    values: list[float]


@dataclass(frozen=True)
class CountRecord:
    date: str
    genotype: str
    condition: str
    n_samples: int


class SvgCanvas:
    def __init__(self, width: int, height: int, background: str = "#f7f5ef") -> None:
        self.width = width
        self.height = height
        self.background = background
        self.elements: list[str] = []

    def add(self, element: str) -> None:
        self.elements.append(element)

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: str = "none",
        stroke: str = "none",
        stroke_width: float = 1.0,
        rx: float = 0.0,
        opacity: float | None = None,
    ) -> None:
        attrs = [
            f'x="{x:.2f}"',
            f'y="{y:.2f}"',
            f'width="{width:.2f}"',
            f'height="{height:.2f}"',
            f'fill="{fill}"',
            f'stroke="{stroke}"',
            f'stroke-width="{stroke_width:.2f}"',
        ]
        if rx:
            attrs.append(f'rx="{rx:.2f}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity:.3f}"')
        self.add(f"<rect {' '.join(attrs)}/>")

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        stroke: str = "#111827",
        stroke_width: float = 1.0,
        dash: str = "",
        opacity: float | None = None,
    ) -> None:
        attrs = [
            f'x1="{x1:.2f}"',
            f'y1="{y1:.2f}"',
            f'x2="{x2:.2f}"',
            f'y2="{y2:.2f}"',
            f'stroke="{stroke}"',
            f'stroke-width="{stroke_width:.2f}"',
            'stroke-linecap="round"',
        ]
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity:.3f}"')
        self.add(f"<line {' '.join(attrs)}/>")

    def polyline(
        self,
        points: list[tuple[float, float]],
        *,
        stroke: str,
        stroke_width: float = 1.0,
        dash: str = "",
        opacity: float = 1.0,
    ) -> None:
        point_text = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        attrs = [
            f'points="{point_text}"',
            'fill="none"',
            f'stroke="{stroke}"',
            f'stroke-width="{stroke_width:.2f}"',
            'stroke-linejoin="round"',
            'stroke-linecap="round"',
            f'opacity="{opacity:.3f}"',
        ]
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
        self.add(f"<polyline {' '.join(attrs)}/>")

    def text(
        self,
        x: float,
        y: float,
        text: str,
        *,
        font_size: int = 14,
        fill: str = "#111827",
        anchor: str = "start",
        weight: str = "400",
    ) -> None:
        safe = html.escape(text)
        self.add(
            (
                f'<text x="{x:.2f}" y="{y:.2f}" font-family="Segoe UI, Arial, sans-serif" '
                f'font-size="{font_size}" fill="{fill}" text-anchor="{anchor}" '
                f'font-weight="{weight}">{safe}</text>'
            )
        )

    def save(self, path: Path) -> None:
        svg = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
                f'height="{self.height}" viewBox="0 0 {self.width} {self.height}">'
            ),
            f'<rect x="0" y="0" width="{self.width}" height="{self.height}" fill="{self.background}"/>',
            *self.elements,
            "</svg>",
        ]
        path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def read_spectral_csv(path: Path) -> tuple[list[float], list[SpectralRecord]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        wavelengths = [float(value) for value in header[4:]]
        records: list[SpectralRecord] = []
        for row in reader:
            records.append(
                SpectralRecord(
                    date=row[0],
                    genotype=row[1],
                    condition=row[2],
                    n_samples=int(row[3]),
                    values=[float(value) if value else float("nan") for value in row[4:]],
                )
            )
    return wavelengths, records


def read_count_csv(path: Path) -> list[CountRecord]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            CountRecord(
                date=row["data_coleta"],
                genotype=row["genotipo"],
                condition=row["condicao"],
                n_samples=int(row["n_amostras"]),
            )
            for row in reader
        ]


def sort_records(records: list[SpectralRecord]) -> list[SpectralRecord]:
    return sorted(
        records,
        key=lambda record: (
            record.date,
            GENOTYPE_ORDER[record.genotype],
            CONDITION_ORDER[record.condition],
        ),
    )


def scale(value: float, domain_min: float, domain_max: float, range_min: float, range_max: float) -> float:
    if math.isclose(domain_min, domain_max):
        return (range_min + range_max) / 2.0
    ratio = (value - domain_min) / (domain_max - domain_min)
    return range_min + ratio * (range_max - range_min)


def nice_number(value: float, should_round: bool) -> float:
    if value <= 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    fraction = value / (10 ** exponent)
    if should_round:
        if fraction < 1.5:
            nice_fraction = 1.0
        elif fraction < 3.0:
            nice_fraction = 2.0
        elif fraction < 7.0:
            nice_fraction = 5.0
        else:
            nice_fraction = 10.0
    else:
        if fraction <= 1.0:
            nice_fraction = 1.0
        elif fraction <= 2.0:
            nice_fraction = 2.0
        elif fraction <= 5.0:
            nice_fraction = 5.0
        else:
            nice_fraction = 10.0
    return nice_fraction * (10 ** exponent)


def nice_ticks(min_value: float, max_value: float, tick_count: int = 5) -> list[float]:
    if math.isclose(min_value, max_value):
        min_value -= 1.0
        max_value += 1.0
    value_range = nice_number(max_value - min_value, should_round=False)
    spacing = nice_number(value_range / max(1, tick_count - 1), should_round=True)
    nice_min = math.floor(min_value / spacing) * spacing
    nice_max = math.ceil(max_value / spacing) * spacing
    ticks: list[float] = []
    current = nice_min
    while current <= nice_max + spacing * 0.5:
        ticks.append(round(current, 10))
        current += spacing
    return ticks


def format_tick(value: float) -> str:
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    if abs(value) >= 1:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:.3f}".rstrip("0").rstrip(".")


def wavelength_ticks(wavelengths: list[float], tick_count: int = 6) -> list[float]:
    min_wave = wavelengths[0]
    max_wave = wavelengths[-1]
    step = (max_wave - min_wave) / (tick_count - 1)
    return [round(min_wave + (step * index), 0) for index in range(tick_count)]


def sample_points(
    wavelengths: list[float],
    values: list[float],
    x: float,
    y: float,
    width: float,
    height: float,
    y_min: float,
    y_max: float,
    max_points: int = 900,
) -> list[tuple[float, float]]:
    point_count = len(values)
    step = max(1, math.ceil(point_count / max_points))
    points: list[tuple[float, float]] = []
    for index in range(0, point_count, step):
        if not math.isfinite(values[index]):
            continue
        px = scale(wavelengths[index], wavelengths[0], wavelengths[-1], x, x + width)
        py = scale(values[index], y_min, y_max, y + height, y)
        points.append((px, py))
    if not points:
        return points
    if math.isfinite(values[-1]) and points[-1][0] < x + width - 0.5:
        points.append((x + width, scale(values[-1], y_min, y_max, y + height, y)))
    return points


def finite_series_extrema(records: list[SpectralRecord]) -> tuple[float, float]:
    finite_values = [
        value
        for record in records
        for value in record.values
        if math.isfinite(value)
    ]
    if not finite_values:
        raise ValueError("No finite values available to build the chart.")
    return min(finite_values), max(finite_values)


def draw_metric_legend(
    canvas: SvgCanvas,
    *,
    x: float,
    y: float,
    title: str,
    color_items: list[tuple[str, str]],
    style_items: list[tuple[str, dict[str, str]]],
) -> None:
    canvas.text(x, y, title, font_size=14, fill="#1f2937", weight="700")
    current_y = y + 24
    canvas.text(x, current_y, "Cores", font_size=12, fill="#4b5563", weight="700")
    current_y += 18
    for label, color in color_items:
        canvas.line(x, current_y - 5, x + 24, current_y - 5, stroke=color, stroke_width=3.0)
        canvas.text(x + 34, current_y, label, font_size=12, fill="#374151")
        current_y += 18

    current_y += 6
    canvas.text(x, current_y, "Estilo", font_size=12, fill="#4b5563", weight="700")
    current_y += 18
    for label, style in style_items:
        canvas.line(
            x,
            current_y - 5,
            x + 24,
            current_y - 5,
            stroke="#111827",
            stroke_width=2.6,
            dash=style["dash"],
            opacity=float(style["opacity"]),
        )
        canvas.text(x + 34, current_y, label, font_size=12, fill="#374151")
        current_y += 18


def draw_panel_axes(
    canvas: SvgCanvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    x_ticks: list[float],
    y_ticks: list[float],
    x_domain: tuple[float, float],
    y_domain: tuple[float, float],
    panel_title: str,
) -> None:
    canvas.rect(x, y, width, height, fill="#fffdf8", stroke="#d6d3d1", stroke_width=1.2, rx=14)
    plot_x = x + 58
    plot_y = y + 24
    plot_width = width - 82
    plot_height = height - 70

    canvas.text(x + 18, y + 18, panel_title, font_size=15, fill="#1f2937", weight="700")
    canvas.line(plot_x, plot_y, plot_x, plot_y + plot_height, stroke="#374151", stroke_width=1.2)
    canvas.line(
        plot_x,
        plot_y + plot_height,
        plot_x + plot_width,
        plot_y + plot_height,
        stroke="#374151",
        stroke_width=1.2,
    )

    for tick in y_ticks:
        tick_y = scale(tick, y_domain[0], y_domain[1], plot_y + plot_height, plot_y)
        canvas.line(plot_x, tick_y, plot_x + plot_width, tick_y, stroke="#e7e5e4", stroke_width=1.0)
        canvas.text(plot_x - 10, tick_y + 4, format_tick(tick), font_size=11, fill="#6b7280", anchor="end")

    for tick in x_ticks:
        tick_x = scale(tick, x_domain[0], x_domain[1], plot_x, plot_x + plot_width)
        canvas.line(tick_x, plot_y + plot_height, tick_x, plot_y + plot_height + 6, stroke="#374151", stroke_width=1.0)
        canvas.text(tick_x, plot_y + plot_height + 22, str(int(tick)), font_size=11, fill="#6b7280", anchor="middle")


def draw_line_series_in_panel(
    canvas: SvgCanvas,
    *,
    records: list[SpectralRecord],
    wavelengths: list[float],
    x: float,
    y: float,
    width: float,
    height: float,
    y_min: float,
    y_max: float,
    color_key: str,
    style_key: str,
) -> None:
    plot_x = x + 58
    plot_y = y + 24
    plot_width = width - 82
    plot_height = height - 70

    for record in records:
        color = GENOTYPE_COLORS[record.genotype] if color_key == "genotype" else DATE_COLORS[record.date]
        style = CONDITION_STYLES[record.condition]
        points = sample_points(
            wavelengths,
            record.values,
            plot_x,
            plot_y,
            plot_width,
            plot_height,
            y_min,
            y_max,
        )
        if len(points) < 2:
            continue
        canvas.polyline(
            points,
            stroke=color,
            stroke_width=2.2,
            dash=style["dash"] if style_key == "condition" else "",
            opacity=float(style["opacity"]),
        )


def create_line_chart_by_date(
    wavelengths: list[float],
    records: list[SpectralRecord],
    *,
    metric_label: str,
    y_label: str,
    output_path: Path,
) -> None:
    width = 1680
    height = 1140
    canvas = SvgCanvas(width, height)
    canvas.text(70, 64, f"{metric_label} por data de coleta", font_size=30, fill="#111827", weight="700")
    canvas.text(
        70,
        94,
        "Cada painel mostra 6 curvas: 3 genotipos x 2 condicoes de irrigacao.",
        font_size=16,
        fill="#4b5563",
    )
    canvas.text(70, 118, "Comprimento de onda (nm)", font_size=13, fill="#374151", weight="700")
    canvas.text(36, 620, y_label, font_size=13, fill="#374151", weight="700")

    draw_metric_legend(
        canvas,
        x=1340,
        y=54,
        title="Legenda",
        color_items=[(key, GENOTYPE_COLORS[key]) for key in ["BR16", "CD202", "EMB48"]],
        style_items=[
            ("irrigado", CONDITION_STYLES["irrigado"]),
            ("nao_irrigado", CONDITION_STYLES["nao_irrigado"]),
        ],
    )

    dates = sorted({record.date for record in records})
    columns = 2
    rows = math.ceil(len(dates) / columns)
    panel_width = 720
    panel_height = 290
    start_x = 70
    start_y = 150
    gap_x = 34
    gap_y = 28

    global_min, global_max = finite_series_extrema(records)
    padding = (global_max - global_min) * 0.06 or 1.0
    y_min = global_min - padding
    y_max = global_max + padding
    y_ticks = nice_ticks(y_min, y_max, tick_count=5)
    x_ticks = wavelength_ticks(wavelengths, tick_count=6)

    for index, date in enumerate(dates):
        row_index, col_index = divmod(index, columns)
        panel_x = start_x + col_index * (panel_width + gap_x)
        panel_y = start_y + row_index * (panel_height + gap_y)
        panel_records = sort_records([record for record in records if record.date == date])
        draw_panel_axes(
            canvas,
            x=panel_x,
            y=panel_y,
            width=panel_width,
            height=panel_height,
            x_ticks=x_ticks,
            y_ticks=y_ticks,
            x_domain=(wavelengths[0], wavelengths[-1]),
            y_domain=(y_min, y_max),
            panel_title=date,
        )
        draw_line_series_in_panel(
            canvas,
            records=panel_records,
            wavelengths=wavelengths,
            x=panel_x,
            y=panel_y,
            width=panel_width,
            height=panel_height,
            y_min=y_min,
            y_max=y_max,
            color_key="genotype",
            style_key="condition",
        )

    canvas.save(output_path)


def create_line_chart_by_genotype(
    wavelengths: list[float],
    records: list[SpectralRecord],
    *,
    metric_label: str,
    y_label: str,
    output_path: Path,
) -> None:
    width = 1740
    height = 760
    canvas = SvgCanvas(width, height)
    canvas.text(70, 64, f"{metric_label} por genotipo", font_size=30, fill="#111827", weight="700")
    canvas.text(
        70,
        94,
        "Cada painel mostra 12 curvas: 6 datas x 2 condicoes de irrigacao.",
        font_size=16,
        fill="#4b5563",
    )
    canvas.text(70, 118, "Comprimento de onda (nm)", font_size=13, fill="#374151", weight="700")
    canvas.text(36, 430, y_label, font_size=13, fill="#374151", weight="700")

    draw_metric_legend(
        canvas,
        x=1460,
        y=54,
        title="Legenda",
        color_items=[(date, DATE_COLORS[date]) for date in sorted(DATE_COLORS)],
        style_items=[
            ("irrigado", CONDITION_STYLES["irrigado"]),
            ("nao_irrigado", CONDITION_STYLES["nao_irrigado"]),
        ],
    )

    genotypes = ["BR16", "CD202", "EMB48"]
    panel_width = 430
    panel_height = 460
    start_x = 70
    start_y = 160
    gap_x = 28

    global_min, global_max = finite_series_extrema(records)
    padding = (global_max - global_min) * 0.06 or 1.0
    y_min = global_min - padding
    y_max = global_max + padding
    y_ticks = nice_ticks(y_min, y_max, tick_count=5)
    x_ticks = wavelength_ticks(wavelengths, tick_count=6)

    for index, genotype in enumerate(genotypes):
        panel_x = start_x + index * (panel_width + gap_x)
        panel_y = start_y
        panel_records = sorted(
            [record for record in records if record.genotype == genotype],
            key=lambda record: (record.date, CONDITION_ORDER[record.condition]),
        )
        draw_panel_axes(
            canvas,
            x=panel_x,
            y=panel_y,
            width=panel_width,
            height=panel_height,
            x_ticks=x_ticks,
            y_ticks=y_ticks,
            x_domain=(wavelengths[0], wavelengths[-1]),
            y_domain=(y_min, y_max),
            panel_title=genotype,
        )
        draw_line_series_in_panel(
            canvas,
            records=panel_records,
            wavelengths=wavelengths,
            x=panel_x,
            y=panel_y,
            width=panel_width,
            height=panel_height,
            y_min=y_min,
            y_max=y_max,
            color_key="date",
            style_key="condition",
        )

    canvas.save(output_path)


def create_sample_count_chart(records: list[CountRecord], output_path: Path) -> None:
    width = 1680
    height = 860
    canvas = SvgCanvas(width, height)
    canvas.text(70, 64, "Amostras por grupo", font_size=30, fill="#111827", weight="700")
    canvas.text(
        70,
        94,
        "Barras agrupadas por data; cor representa genotipo e a opacidade diferencia a condicao.",
        font_size=16,
        fill="#4b5563",
    )

    chart_x = 90
    chart_y = 160
    chart_width = 1470
    chart_height = 570
    canvas.rect(chart_x - 20, chart_y - 20, chart_width + 40, chart_height + 60, fill="#fffdf8", stroke="#d6d3d1", stroke_width=1.2, rx=18)
    canvas.text(chart_x, chart_y - 32, "n_amostras", font_size=13, fill="#374151", weight="700")
    canvas.text(chart_x + chart_width - 4, chart_y + chart_height + 48, "data_coleta", font_size=13, fill="#374151", anchor="end", weight="700")

    dates = sorted({record.date for record in records})
    max_count = max(record.n_samples for record in records)
    y_ticks = nice_ticks(0.0, float(max_count), tick_count=6)
    y_min = 0.0
    y_max = max(y_ticks)

    for tick in y_ticks:
        tick_y = scale(tick, y_min, y_max, chart_y + chart_height, chart_y)
        canvas.line(chart_x, tick_y, chart_x + chart_width, tick_y, stroke="#e7e5e4", stroke_width=1.0)
        canvas.text(chart_x - 10, tick_y + 4, format_tick(tick), font_size=11, fill="#6b7280", anchor="end")

    canvas.line(chart_x, chart_y, chart_x, chart_y + chart_height, stroke="#374151", stroke_width=1.2)
    canvas.line(chart_x, chart_y + chart_height, chart_x + chart_width, chart_y + chart_height, stroke="#374151", stroke_width=1.2)

    group_width = chart_width / len(dates)
    inner_padding = 24
    bar_gap = 8
    bar_width = (group_width - (2 * inner_padding) - (5 * bar_gap)) / 6

    ordered_records = sorted(
        records,
        key=lambda record: (
            record.date,
            GENOTYPE_ORDER[record.genotype],
            CONDITION_ORDER[record.condition],
        ),
    )

    for date_index, date in enumerate(dates):
        date_x = chart_x + date_index * group_width
        canvas.text(date_x + group_width / 2, chart_y + chart_height + 24, date, font_size=12, fill="#4b5563", anchor="middle")
        day_records = [record for record in ordered_records if record.date == date]

        for bar_index, record in enumerate(day_records):
            bar_x = date_x + inner_padding + bar_index * (bar_width + bar_gap)
            bar_y = scale(float(record.n_samples), y_min, y_max, chart_y + chart_height, chart_y)
            bar_height = chart_y + chart_height - bar_y
            opacity = 0.92 if record.condition == "irrigado" else 0.48
            canvas.rect(
                bar_x,
                bar_y,
                bar_width,
                bar_height,
                fill=GENOTYPE_COLORS[record.genotype],
                stroke="none",
                rx=4,
                opacity=opacity,
            )
            canvas.text(bar_x + bar_width / 2, bar_y - 6, str(record.n_samples), font_size=10, fill="#374151", anchor="middle")

    legend_x = 1180
    legend_y = 116
    canvas.text(legend_x, legend_y, "Legenda", font_size=14, fill="#1f2937", weight="700")
    current_y = legend_y + 24
    canvas.text(legend_x, current_y, "Genotipo", font_size=12, fill="#4b5563", weight="700")
    current_y += 18
    for genotype in ["BR16", "CD202", "EMB48"]:
        canvas.rect(legend_x, current_y - 12, 24, 12, fill=GENOTYPE_COLORS[genotype], stroke="none", rx=3)
        canvas.text(legend_x + 34, current_y - 2, genotype, font_size=12, fill="#374151")
        current_y += 18

    current_y += 8
    canvas.text(legend_x, current_y, "Condicao", font_size=12, fill="#4b5563", weight="700")
    current_y += 18
    canvas.rect(legend_x, current_y - 12, 24, 12, fill="#111827", stroke="none", rx=3, opacity=0.92)
    canvas.text(legend_x + 34, current_y - 2, "irrigado", font_size=12, fill="#374151")
    current_y += 18
    canvas.rect(legend_x, current_y - 12, 24, 12, fill="#111827", stroke="none", rx=3, opacity=0.48)
    canvas.text(legend_x + 34, current_y - 2, "nao_irrigado", font_size=12, fill="#374151")

    canvas.save(output_path)


def write_index_html(output_dir: Path, files: list[tuple[str, str]]) -> None:
    items = "\n".join(
        (
            f'<section class="card"><h2>{html.escape(title)}</h2>'
            f'<p><a href="{html.escape(file_name)}">{html.escape(file_name)}</a></p>'
            f'<img src="{html.escape(file_name)}" alt="{html.escape(title)}"/></section>'
        )
        for title, file_name in files
    )
    markup = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Graficos dos outputs</title>
  <style>
    :root {{
      --bg: #f3efe6;
      --card: #fffdf8;
      --ink: #111827;
      --muted: #4b5563;
      --line: #d6d3d1;
    }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #f3efe6 0%, #ede7db 100%);
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
    }}
    main {{
      max-width: 1600px;
      margin: 0 auto;
      padding: 32px 28px 48px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 32px;
    }}
    p {{
      color: var(--muted);
      line-height: 1.5;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
      gap: 24px;
      margin-top: 28px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 14px 32px rgba(17, 24, 39, 0.08);
    }}
    .card h2 {{
      margin: 0 0 8px;
      font-size: 20px;
    }}
    .card a {{
      color: #1d4ed8;
      text-decoration: none;
    }}
    .card img {{
      width: 100%;
      height: auto;
      display: block;
      margin-top: 12px;
      border-radius: 14px;
      background: #fff;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Graficos gerados a partir dos outputs</h1>
    <p>As figuras abaixo foram renderizadas em SVG a partir dos CSVs de media, coeficiente de variacao e amostras por grupo.</p>
    <div class="grid">
      {items}
    </div>
  </main>
</body>
</html>
"""
    (output_dir / "index.html").write_text(markup, encoding="utf-8")


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    outputs_dir = base_dir / "outputs"
    plots_dir = outputs_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    mean_wavelengths, mean_records = read_spectral_csv(outputs_dir / "estatistica_descritiva_media.csv")
    cv_wavelengths, cv_records = read_spectral_csv(outputs_dir / "estatistica_descritiva_coeficiente_variacao.csv")
    count_records = read_count_csv(outputs_dir / "amostras_por_grupo.csv")

    create_line_chart_by_date(
        mean_wavelengths,
        mean_records,
        metric_label="Media espectral",
        y_label="Media",
        output_path=plots_dir / "media_por_data.svg",
    )
    create_line_chart_by_genotype(
        mean_wavelengths,
        mean_records,
        metric_label="Media espectral",
        y_label="Media",
        output_path=plots_dir / "media_por_genotipo.svg",
    )
    create_line_chart_by_date(
        cv_wavelengths,
        cv_records,
        metric_label="Coeficiente de variacao",
        y_label="CV (%)",
        output_path=plots_dir / "coef_var_por_data.svg",
    )
    create_line_chart_by_genotype(
        cv_wavelengths,
        cv_records,
        metric_label="Coeficiente de variacao",
        y_label="CV (%)",
        output_path=plots_dir / "coef_var_por_genotipo.svg",
    )
    create_sample_count_chart(count_records, plots_dir / "amostras_por_grupo.svg")

    index_files = [
        ("Media espectral por data", "media_por_data.svg"),
        ("Media espectral por genotipo", "media_por_genotipo.svg"),
        ("Coeficiente de variacao por data", "coef_var_por_data.svg"),
        ("Coeficiente de variacao por genotipo", "coef_var_por_genotipo.svg"),
        ("Amostras por grupo", "amostras_por_grupo.svg"),
    ]
    write_index_html(plots_dir, index_files)

    print(f"Plots directory: {plots_dir}")
    for _, file_name in index_files:
        print(f"  - {plots_dir / file_name}")
    print(f"  - {plots_dir / 'index.html'}")


if __name__ == "__main__":
    main()
