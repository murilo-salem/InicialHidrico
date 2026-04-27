#!/usr/bin/env python3
"""Generate raw reflectance plots by genotype for irrigated vs non-irrigated samples."""

from __future__ import annotations

import argparse
import html
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from generate_descriptive_stats import (
    META_COLUMNS,
    RunningStats,
    format_number,
    iter_sheet_rows,
    normalize_metadata,
    write_csv,
)


GENOTYPE_ORDER = ["BR16", "CD202", "EMB48"]
CONDITION_ORDER = ["irrigado", "nao_irrigado"]
TURN_ORDER = ["manha", "tarde"]

GENOTYPE_COLORS = {
    "BR16": "#2563eb",
    "CD202": "#c2410c",
    "EMB48": "#0f766e",
}
CONDITION_TITLES = {
    "irrigado": "Irrigado",
    "nao_irrigado": "Nao irrigado",
}
TURN_TITLES = {
    "manha": "Manha",
    "tarde": "Tarde",
}
X_TICKS = [350, 700, 1050, 1400, 1750, 2100, 2500]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate raw-reflectance mean and coefficient-of-variation plots by "
            "date, genotype, irrigation condition and shift."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("base_dados_unificada.xlsx"),
        help="Path to the raw workbook with reflectance values.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/reflectancia_bruta_genotipos"),
        help="Directory where tables and plots will be written.",
    )
    return parser.parse_args()


def _sort_date(value: str) -> tuple[int, str]:
    return (0, value)


def _sort_turn(value: str) -> tuple[int, str]:
    return (TURN_ORDER.index(value), value) if value in TURN_ORDER else (99, value)


def _sort_genotype(value: str) -> tuple[int, str]:
    return (GENOTYPE_ORDER.index(value), value) if value in GENOTYPE_ORDER else (99, value)


def _sort_condition(value: str) -> tuple[int, str]:
    return (CONDITION_ORDER.index(value), value) if value in CONDITION_ORDER else (99, value)


def _make_stats(size: int, stats_map: dict[tuple[str, ...], RunningStats], key: tuple[str, ...]) -> RunningStats:
    stats = stats_map.get(key)
    if stats is None:
        stats = RunningStats.create(size)
        stats_map[key] = stats
    return stats


def load_grouped_stats(
    workbook_path: Path,
) -> tuple[
    list[float],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    header: list[str | None] | None = None
    wavelength_headers: list[str] = []
    normalization_examples: list[tuple[int, str, str, str]] = []

    stats_by_day: dict[tuple[str, str, str], RunningStats] = {}
    stats_by_day_turn: dict[tuple[str, str, str, str], RunningStats] = {}
    counts_by_day: dict[tuple[str, str, str], int] = {}
    counts_by_day_turn: dict[tuple[str, str, str, str], int] = {}

    for row_number, row_values in iter_sheet_rows(workbook_path):
        if row_number == 1:
            header = row_values
            wavelength_headers = [str(value) for value in header[len(META_COLUMNS) :] if value]
            continue

        if header is None:
            raise ValueError("Header row was not found in the workbook.")

        if len(row_values) < len(header):
            row_values.extend([None] * (len(header) - len(row_values)))

        metadata = normalize_metadata(row_number, row_values, normalization_examples)
        shift = metadata.shift.strip().lower()
        spectral_values: list[float] = []
        for value in row_values[len(META_COLUMNS) : len(META_COLUMNS) + len(wavelength_headers)]:
            if value is None:
                raise ValueError(
                    f"Missing spectral value detected at row {row_number}; the plot pipeline expects complete spectra."
                )
            spectral_values.append(float(value))

        day_key = (
            metadata.collection_date_iso,
            metadata.genotype,
            metadata.condition_label,
        )
        day_turn_key = (
            metadata.collection_date_iso,
            shift,
            metadata.genotype,
            metadata.condition_label,
        )

        _make_stats(len(spectral_values), stats_by_day, day_key).add(spectral_values)
        _make_stats(len(spectral_values), stats_by_day_turn, day_turn_key).add(spectral_values)
        counts_by_day[day_key] = counts_by_day.get(day_key, 0) + 1
        counts_by_day_turn[day_turn_key] = counts_by_day_turn.get(day_turn_key, 0) + 1

    wavelengths = [float(value) for value in wavelength_headers]

    def build_day_records(metric: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for key in sorted(
            stats_by_day,
            key=lambda item: (_sort_date(item[0]), _sort_genotype(item[1]), _sort_condition(item[2])),
        ):
            stats = stats_by_day[key]
            values = stats.mean_values() if metric == "mean" else stats.cv_values()
            rows.append(
                {
                    "date": key[0],
                    "genotype": key[1],
                    "condition": key[2],
                    "n_samples": counts_by_day[key],
                    "values": values,
                }
            )
        return rows

    def build_day_turn_records(metric: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for key in sorted(
            stats_by_day_turn,
            key=lambda item: (
                _sort_date(item[0]),
                _sort_turn(item[1]),
                _sort_genotype(item[2]),
                _sort_condition(item[3]),
            ),
        ):
            stats = stats_by_day_turn[key]
            values = stats.mean_values() if metric == "mean" else stats.cv_values()
            rows.append(
                {
                    "date": key[0],
                    "turno": key[1],
                    "genotype": key[2],
                    "condition": key[3],
                    "n_samples": counts_by_day_turn[key],
                    "values": values,
                }
            )
        return rows

    day_count_rows = [
        {
            "date": key[0],
            "genotype": key[1],
            "condition": key[2],
            "n_samples": counts_by_day[key],
        }
        for key in sorted(
            counts_by_day,
            key=lambda item: (_sort_date(item[0]), _sort_genotype(item[1]), _sort_condition(item[2])),
        )
    ]
    day_turn_count_rows = [
        {
            "date": key[0],
            "turno": key[1],
            "genotype": key[2],
            "condition": key[3],
            "n_samples": counts_by_day_turn[key],
        }
        for key in sorted(
            counts_by_day_turn,
            key=lambda item: (
                _sort_date(item[0]),
                _sort_turn(item[1]),
                _sort_genotype(item[2]),
                _sort_condition(item[3]),
            ),
        )
    ]

    return (
        wavelengths,
        build_day_records("mean"),
        build_day_records("cv"),
        build_day_turn_records("mean"),
        build_day_turn_records("cv"),
        day_count_rows,
        day_turn_count_rows,
    )


def rows_from_records(records: list[dict[str, object]], *, include_turn: bool) -> list[list[str]]:
    rows: list[list[str]] = []
    for record in records:
        row = [str(record["date"])]
        if include_turn:
            row.append(str(record["turno"]))
        row.extend(
            [
                str(record["genotype"]),
                str(record["condition"]),
                str(record["n_samples"]),
            ]
        )
        row.extend(format_number(float(value)) for value in list(record["values"]))
        rows.append(row)
    return rows


def rows_from_counts(records: list[dict[str, object]], *, include_turn: bool) -> list[list[str]]:
    rows: list[list[str]] = []
    for record in records:
        row = [str(record["date"])]
        if include_turn:
            row.append(str(record["turno"]))
        row.extend(
            [
                str(record["genotype"]),
                str(record["condition"]),
                str(record["n_samples"]),
            ]
        )
        rows.append(row)
    return rows


def downsample_series(wavelengths: list[float], values: list[float], max_points: int = 1200) -> tuple[list[float], list[float]]:
    if len(wavelengths) <= max_points:
        return wavelengths, values
    step = max(1, math.ceil(len(wavelengths) / max_points))
    sampled_wavelengths = wavelengths[::step]
    sampled_values = values[::step]
    if sampled_wavelengths[-1] != wavelengths[-1]:
        sampled_wavelengths.append(wavelengths[-1])
        sampled_values.append(values[-1])
    return sampled_wavelengths, sampled_values


def metric_limits(records: list[dict[str, object]]) -> tuple[float, float]:
    values = [
        float(value)
        for record in records
        for value in list(record["values"])
        if math.isfinite(float(value))
    ]
    if not values:
        return (0.0, 1.0)
    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        pad = max(abs(min_value) * 0.05, 0.05)
        return (max(0.0, min_value - pad), max_value + pad)
    pad = (max_value - min_value) * 0.05
    return (max(0.0, min_value - pad), max_value + pad)


def style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor("#fcfcfb")
    ax.grid(True, color="#cbd5e1", alpha=0.55, linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94a3b8")
    ax.spines["bottom"].set_color("#94a3b8")
    ax.tick_params(labelsize=8, colors="#334155")
    ax.set_xlim(350, 2500)
    ax.set_xticks(X_TICKS)
    ax.margins(x=0)


def panel_count_label(panel_records: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for genotype in GENOTYPE_ORDER:
        record = next((item for item in panel_records if item["genotype"] == genotype), None)
        if record is not None:
            parts.append(f"{genotype} n={record['n_samples']}")
    return " | ".join(parts)


def genotype_legend_handles() -> list[Line2D]:
    return [
        Line2D([0], [0], color=GENOTYPE_COLORS[genotype], linewidth=2.0, label=genotype)
        for genotype in GENOTYPE_ORDER
    ]


def plot_condition_by_day(
    wavelengths: list[float],
    records: list[dict[str, object]],
    *,
    condition: str,
    metric_title: str,
    y_label: str,
    output_path: Path,
) -> None:
    date_values = sorted({str(record["date"]) for record in records}, key=_sort_date)
    condition_records = [record for record in records if record["condition"] == condition]
    y_min, y_max = metric_limits(condition_records)

    columns = 3
    rows = max(1, math.ceil(len(date_values) / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(16, max(4.4 * rows, 5.8)), sharex=True, sharey=True)
    axes_list = [axes] if not hasattr(axes, "ravel") else list(axes.ravel())

    for ax, date in zip(axes_list, date_values, strict=False):
        panel_records = [record for record in condition_records if record["date"] == date]
        for genotype in GENOTYPE_ORDER:
            genotype_record = next((item for item in panel_records if item["genotype"] == genotype), None)
            if genotype_record is None:
                continue
            plot_waves, plot_values = downsample_series(wavelengths, list(genotype_record["values"]))
            ax.plot(
                plot_waves,
                plot_values,
                color=GENOTYPE_COLORS[genotype],
                linewidth=1.8,
                label=genotype,
            )

        style_axis(ax)
        ax.set_ylim(y_min, y_max)
        ax.set_title(str(date), fontsize=11, fontweight="bold", color="#0f172a")
        ax.text(
            0.02,
            0.98,
            panel_count_label(panel_records),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            color="#475569",
            bbox={"boxstyle": "round,pad=0.24", "facecolor": "white", "edgecolor": "#e2e8f0", "alpha": 0.9},
        )

    for ax in axes_list[len(date_values) :]:
        ax.set_visible(False)

    fig.suptitle(
        f"{metric_title} | {CONDITION_TITLES.get(condition, condition)} | por dia",
        fontsize=17,
        fontweight="bold",
        y=0.985,
    )
    fig.supxlabel("Comprimento de onda (nm)", fontsize=11, y=0.04)
    fig.supylabel(y_label, fontsize=11, x=0.04)
    fig.legend(
        handles=genotype_legend_handles(),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.955),
        ncol=3,
        frameon=False,
        fontsize=10,
    )
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.09, top=0.88, hspace=0.30, wspace=0.14)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_condition_by_day_turn(
    wavelengths: list[float],
    records: list[dict[str, object]],
    *,
    condition: str,
    metric_title: str,
    y_label: str,
    output_path: Path,
) -> None:
    date_values = sorted({str(record["date"]) for record in records}, key=_sort_date)
    condition_records = [record for record in records if record["condition"] == condition]
    y_min, y_max = metric_limits(condition_records)

    fig, axes = plt.subplots(len(date_values), len(TURN_ORDER), figsize=(16, 18), sharex=True, sharey=True)
    if len(date_values) == 1:
        axes = [axes]

    for row_index, date in enumerate(date_values):
        for col_index, shift in enumerate(TURN_ORDER):
            ax = axes[row_index][col_index]
            panel_records = [
                record
                for record in condition_records
                if record["date"] == date and record["turno"] == shift
            ]
            if not panel_records:
                ax.set_facecolor("#f8fafc")
                ax.set_xticks([])
                ax.set_yticks([])
                for spine in ax.spines.values():
                    spine.set_visible(False)
                ax.set_title(f"{date} | {TURN_TITLES.get(shift, shift)}", fontsize=10, fontweight="bold")
                ax.text(
                    0.5,
                    0.52,
                    "Sem amostras",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=10,
                    color="#94a3b8",
                )
                continue

            for genotype in GENOTYPE_ORDER:
                genotype_record = next((item for item in panel_records if item["genotype"] == genotype), None)
                if genotype_record is None:
                    continue
                plot_waves, plot_values = downsample_series(wavelengths, list(genotype_record["values"]))
                ax.plot(
                    plot_waves,
                    plot_values,
                    color=GENOTYPE_COLORS[genotype],
                    linewidth=1.8,
                )

            style_axis(ax)
            ax.set_ylim(y_min, y_max)
            ax.set_title(f"{date} | {TURN_TITLES.get(shift, shift)}", fontsize=10, fontweight="bold", color="#0f172a")
            ax.text(
                0.02,
                0.98,
                panel_count_label(panel_records),
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.8,
                color="#475569",
                bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "#e2e8f0", "alpha": 0.9},
            )

    fig.suptitle(
        f"{metric_title} | {CONDITION_TITLES.get(condition, condition)} | por dia e turno",
        fontsize=17,
        fontweight="bold",
        y=0.992,
    )
    fig.supxlabel("Comprimento de onda (nm)", fontsize=11, y=0.02)
    fig.supylabel(y_label, fontsize=11, x=0.03)
    fig.legend(
        handles=genotype_legend_handles(),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.972),
        ncol=3,
        frameon=False,
        fontsize=10,
    )
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.05, top=0.95, hspace=0.34, wspace=0.14)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def write_summary_markdown(
    output_path: Path,
    *,
    workbook_path: Path,
    figure_paths: list[Path],
    table_paths: list[Path],
    day_turn_count_rows: list[dict[str, object]],
) -> None:
    dates = sorted({str(item["date"]) for item in day_turn_count_rows}, key=_sort_date)
    turns = sorted({str(item["turno"]) for item in day_turn_count_rows}, key=_sort_turn)

    lines = [
        "# Reflectancia bruta por genotipo",
        "",
        f"- Base analisada: `{workbook_path.name}`",
        "- Sinal usado: reflectancia bruta da planilha original",
        f"- Datas encontradas: {', '.join(dates)}",
        f"- Turnos encontrados: {', '.join(turns)}",
        "- Condicoes separadas em figuras independentes: irrigado e nao_irrigado",
        "- Cada painel plota os 3 genotipos no mesmo grafico",
        "- Foram geradas figuras de media e coeficiente de variacao por dia e por dia x turno",
        "",
        "## Tabelas",
        "",
    ]

    for path in table_paths:
        lines.append(f"- `{path.relative_to(output_path.parent)}`")

    lines.extend(["", "## Figuras", ""])
    for path in figure_paths:
        lines.append(f"- `{path.relative_to(output_path.parent)}`")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index_html(output_path: Path, figure_paths: list[Path]) -> None:
    cards = "\n".join(
        (
            f'<section class="card">'
            f"<h2>{html.escape(path.stem.replace('_', ' '))}</h2>"
            f'<p><a href="{html.escape(path.relative_to(output_path.parent).as_posix())}">{html.escape(path.name)}</a></p>'
            f'<img src="{html.escape(path.relative_to(output_path.parent).as_posix())}" alt="{html.escape(path.stem)}"/>'
            f"</section>"
        )
        for path in figure_paths
    )
    markup = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Reflectancia bruta por genotipo</title>
  <style>
    :root {{
      --bg: #eef2f7;
      --card: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --line: #dbe2ea;
    }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
    }}
    main {{
      max-width: 1680px;
      margin: 0 auto;
      padding: 28px 24px 44px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 22px;
      margin-top: 26px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
    }}
    .card h2 {{
      margin: 0 0 8px;
      font-size: 18px;
      text-transform: capitalize;
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
      border-radius: 12px;
      background: #fff;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Reflectancia bruta por genotipo</h1>
    <p>Figuras separadas por condicao de irrigacao, com media e coeficiente de variacao por dia e por dia x turno.</p>
    <div class="grid">
      {cards}
    </div>
  </main>
</body>
</html>
"""
    output_path.write_text(markup, encoding="utf-8")


def main() -> None:
    args = parse_args()
    workbook_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    figures_dir = output_dir / "figuras"
    tables_dir = output_dir / "tabelas"

    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    (
        wavelengths,
        day_mean_records,
        day_cv_records,
        day_turn_mean_records,
        day_turn_cv_records,
        day_count_rows,
        day_turn_count_rows,
    ) = load_grouped_stats(workbook_path)

    spectral_header_day = [
        "data_coleta",
        "genotipo",
        "condicao",
        "n_amostras",
        *[str(int(value)) for value in wavelengths],
    ]
    spectral_header_day_turn = [
        "data_coleta",
        "turno",
        "genotipo",
        "condicao",
        "n_amostras",
        *[str(int(value)) for value in wavelengths],
    ]

    table_paths = [
        tables_dir / "reflectancia_bruta_media_por_data_genotipo_condicao.csv",
        tables_dir / "reflectancia_bruta_cv_por_data_genotipo_condicao.csv",
        tables_dir / "reflectancia_bruta_media_por_data_turno_genotipo_condicao.csv",
        tables_dir / "reflectancia_bruta_cv_por_data_turno_genotipo_condicao.csv",
        tables_dir / "contagem_amostras_por_data_genotipo_condicao.csv",
        tables_dir / "contagem_amostras_por_data_turno_genotipo_condicao.csv",
    ]

    write_csv(table_paths[0], spectral_header_day, rows_from_records(day_mean_records, include_turn=False))
    write_csv(table_paths[1], spectral_header_day, rows_from_records(day_cv_records, include_turn=False))
    write_csv(
        table_paths[2],
        spectral_header_day_turn,
        rows_from_records(day_turn_mean_records, include_turn=True),
    )
    write_csv(
        table_paths[3],
        spectral_header_day_turn,
        rows_from_records(day_turn_cv_records, include_turn=True),
    )
    write_csv(
        table_paths[4],
        ["data_coleta", "genotipo", "condicao", "n_amostras"],
        rows_from_counts(day_count_rows, include_turn=False),
    )
    write_csv(
        table_paths[5],
        ["data_coleta", "turno", "genotipo", "condicao", "n_amostras"],
        rows_from_counts(day_turn_count_rows, include_turn=True),
    )

    figure_paths = [
        figures_dir / "media_reflectancia_bruta_irrigado_por_dia.png",
        figures_dir / "media_reflectancia_bruta_nao_irrigado_por_dia.png",
        figures_dir / "cv_reflectancia_bruta_irrigado_por_dia.png",
        figures_dir / "cv_reflectancia_bruta_nao_irrigado_por_dia.png",
        figures_dir / "media_reflectancia_bruta_irrigado_por_dia_turno.png",
        figures_dir / "media_reflectancia_bruta_nao_irrigado_por_dia_turno.png",
        figures_dir / "cv_reflectancia_bruta_irrigado_por_dia_turno.png",
        figures_dir / "cv_reflectancia_bruta_nao_irrigado_por_dia_turno.png",
    ]

    plot_condition_by_day(
        wavelengths,
        day_mean_records,
        condition="irrigado",
        metric_title="Reflectancia bruta media por genotipo",
        y_label="Reflectancia media",
        output_path=figure_paths[0],
    )
    plot_condition_by_day(
        wavelengths,
        day_mean_records,
        condition="nao_irrigado",
        metric_title="Reflectancia bruta media por genotipo",
        y_label="Reflectancia media",
        output_path=figure_paths[1],
    )
    plot_condition_by_day(
        wavelengths,
        day_cv_records,
        condition="irrigado",
        metric_title="Coeficiente de variacao da reflectancia bruta",
        y_label="CV (%)",
        output_path=figure_paths[2],
    )
    plot_condition_by_day(
        wavelengths,
        day_cv_records,
        condition="nao_irrigado",
        metric_title="Coeficiente de variacao da reflectancia bruta",
        y_label="CV (%)",
        output_path=figure_paths[3],
    )
    plot_condition_by_day_turn(
        wavelengths,
        day_turn_mean_records,
        condition="irrigado",
        metric_title="Reflectancia bruta media por genotipo",
        y_label="Reflectancia media",
        output_path=figure_paths[4],
    )
    plot_condition_by_day_turn(
        wavelengths,
        day_turn_mean_records,
        condition="nao_irrigado",
        metric_title="Reflectancia bruta media por genotipo",
        y_label="Reflectancia media",
        output_path=figure_paths[5],
    )
    plot_condition_by_day_turn(
        wavelengths,
        day_turn_cv_records,
        condition="irrigado",
        metric_title="Coeficiente de variacao da reflectancia bruta",
        y_label="CV (%)",
        output_path=figure_paths[6],
    )
    plot_condition_by_day_turn(
        wavelengths,
        day_turn_cv_records,
        condition="nao_irrigado",
        metric_title="Coeficiente de variacao da reflectancia bruta",
        y_label="CV (%)",
        output_path=figure_paths[7],
    )

    summary_path = output_dir / "resumo_reflectancia_bruta_genotipos.md"
    index_path = output_dir / "index.html"
    write_summary_markdown(
        summary_path,
        workbook_path=workbook_path,
        figure_paths=figure_paths,
        table_paths=table_paths,
        day_turn_count_rows=day_turn_count_rows,
    )
    write_index_html(index_path, figure_paths)

    print(f"Output directory: {output_dir}")
    print("Tables:")
    for path in table_paths:
        print(f"  - {path}")
    print("Figures:")
    for path in figure_paths:
        print(f"  - {path}")
    print(f"  - {summary_path}")
    print(f"  - {index_path}")


if __name__ == "__main__":
    main()
