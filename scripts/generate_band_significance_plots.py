#!/usr/bin/env python3
"""Generate plots for the band-significance analyses.

Plots produced:
- top ranked bands
- dominant spectral regions by significance threshold
- comparison between Kruskal-Wallis, Pearson, Spearman and t-test
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate band-significance plots.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("dados_processados_soft/plsr_pca_irrigacao"),
        help="Directory containing the significance CSV outputs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft/plsr_pca_irrigacao/figuras_band_significance"),
        help="Directory where plots will be written.",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def make_top_bands_plot(rows: list[dict[str, str]], output_path: Path, top_n: int = 20) -> None:
    top = rows[:top_n]
    bands = [str(row["band"]) for row in top][::-1]
    scores = [float(row["ranking_score"]) for row in top][::-1]
    colors = ["#0f766e" if row["direction_label"] == "irrigado" else "#c2410c" for row in top][::-1]

    fig, ax = plt.subplots(figsize=(11, 7), constrained_layout=True)
    ax.barh(bands, scores, color=colors)
    ax.set_xlabel("Ranking score")
    ax.set_title(f"Top {top_n} bandas por significancia estatistica")
    ax.grid(alpha=0.2, axis="x")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def make_regions_plot(region_rows: list[dict[str, str]], output_path: Path) -> None:
    thresholds = sorted({float(row["threshold"]) for row in region_rows}, reverse=True)
    top_per_threshold: dict[float, list[dict[str, str]]] = {}
    for threshold in thresholds:
        subset = [row for row in region_rows if float(row["threshold"]) == threshold]
        subset.sort(key=lambda row: int(row["rank"]))
        top_per_threshold[threshold] = subset[:10]

    fig, axes = plt.subplots(len(thresholds), 1, figsize=(12, 15), constrained_layout=True)
    if len(thresholds) == 1:
        axes = [axes]

    for ax, threshold in zip(axes, thresholds, strict=False):
        subset = top_per_threshold[threshold]
        labels = [f"{row['region_start']}-{row['region_end']}" for row in subset][::-1]
        values = [int(row["n_bands"]) for row in subset][::-1]
        ax.barh(labels, values, color="#2563eb")
        ax.set_title(f"Top regioes contiguas - q < {threshold:g}")
        ax.set_xlabel("Numero de bandas contiguas")
        ax.grid(axis="x", alpha=0.2)

    fig.suptitle("Regioes espectrais dominantes por limiar de significancia", fontsize=14, y=1.01)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_tests_comparison_plot(ranking_rows: list[dict[str, str]], output_path: Path) -> None:
    thresholds = [0.05, 0.01, 0.001, 0.0001, 0.00001]
    methods = [
        ("Kruskal-Wallis", "kruskal_pvalue_adj", "#1d4ed8"),
        ("t-test", "ttest_pvalue_adj", "#0f766e"),
        ("Pearson", "pearson_pvalue_adj", "#b45309"),
        ("Spearman", "spearman_pvalue_adj", "#7c3aed"),
    ]

    counts_by_method = {label: [] for label, _, _ in methods}
    for threshold in thresholds:
        for label, column, _ in methods:
            count = sum(
                1
                for row in ranking_rows
                if row.get(column)
                and row[column] != ""
                and float(row[column]) < threshold
            )
            counts_by_method[label].append(count)

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for label, _, color in methods:
        ax.plot(
            thresholds,
            counts_by_method[label],
            marker="o",
            linewidth=2.0,
            color=color,
            label=label,
        )
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xlabel("Limiar de p-value ajustado")
    ax.set_ylabel("Numero de bandas significativas")
    ax.set_title("Comparacao entre Kruskal-Wallis, t-test, Pearson e Spearman")
    ax.grid(alpha=0.2, which="both")
    ax.legend(loc="best")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def write_summary(path: Path, top_path: Path, region_path: Path, comparison_path: Path) -> None:
    lines = [
        "# Graficos gerados para a analise de significancia de bandas",
        "",
        "## Itens atendidos",
        "",
        "- `2`: ranking das bandas mais significativas",
        "- `3`: regioes espectrais dominantes por limiar de significancia",
        "- `4`: comparacao entre Kruskal-Wallis, Pearson, Spearman e t-test",
        "",
        "## Arquivos",
        "",
        f"- Top bands: `{top_path.name}`",
        f"- Regions: `{region_path.name}`",
        f"- Comparison: `{comparison_path.name}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    ranking_rows = read_csv_rows(input_dir / "band_significance" / "band_significance_ranking.csv")
    region_rows = read_csv_rows(input_dir / "regioes_dominantes_por_threshold.csv")

    top_path = output_dir / "top_bandas_significativas.png"
    region_path = output_dir / "regioes_dominantes_por_threshold.png"
    comparison_path = output_dir / "comparacao_testes_estatisticos.png"
    summary_path = output_dir / "README_graficos.md"

    make_top_bands_plot(ranking_rows, top_path, top_n=20)
    make_regions_plot(region_rows, region_path)
    make_tests_comparison_plot(ranking_rows, comparison_path)
    write_summary(summary_path, top_path, region_path, comparison_path)

    print(f"Output directory: {output_dir}")
    print(f"Top bands plot: {top_path}")
    print(f"Regions plot: {region_path}")
    print(f"Comparison plot: {comparison_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
