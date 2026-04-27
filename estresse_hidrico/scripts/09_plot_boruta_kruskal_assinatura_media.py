#!/usr/bin/env python3
"""Plot the global mean spectral signature with Boruta and Kruskal band overlays."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


BORUTA_COLOR = "#2e7d32"
KRUSKAL_COLOR = "#c62828"
SIGNATURE_COLOR = "#1f2937"


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    parser = argparse.ArgumentParser(
        description="Plota a assinatura media com destaque para bandas Boruta e Kruskal."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
        help="CSV base da classificacao.",
    )
    parser.add_argument(
        "--boruta-features-csv",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "features_classificacao.csv",
        help="CSV das features da classificacao original.",
    )
    parser.add_argument(
        "--kruskal-subset-csv",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "reducao_bandas_p_teste" / "kruskal_top_20.csv",
        help="CSV do subconjunto reduzido por Kruskal.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "outputs" / "figuras" / "assinatura_media_boruta_vs_kruskal.png",
        help="Figura de saida.",
    )
    return parser.parse_args()


def band_to_nm(band_name: str) -> int:
    return int(str(band_name).split("_", 1)[1])


def collapse_consecutive_ranges(wavelengths: list[int]) -> list[tuple[int, int]]:
    if not wavelengths:
        return []
    ordered = sorted(set(wavelengths))
    ranges: list[tuple[int, int]] = []
    start = ordered[0]
    end = ordered[0]
    for value in ordered[1:]:
        if value == end + 1:
            end = value
            continue
        ranges.append((start, end))
        start = value
        end = value
    ranges.append((start, end))
    return ranges


def load_boruta_wavelengths(features_csv: Path) -> list[int]:
    features_df = pd.read_csv(features_csv, encoding="utf-8-sig")
    bands = features_df.loc[features_df["tipo"] == "banda", "feature"].tolist()
    return sorted(band_to_nm(item) for item in bands)


def load_kruskal_wavelengths(subset_csv: Path) -> list[int]:
    subset_df = pd.read_csv(subset_csv, encoding="utf-8-sig")
    if "wavelength_nm" in subset_df.columns:
        return sorted(int(value) for value in subset_df["wavelength_nm"].tolist())
    return sorted(band_to_nm(item) for item in subset_df["band"].tolist())


def add_range_spans(ax: plt.Axes, ranges: list[tuple[int, int]], color: str, alpha: float) -> None:
    for start, end in ranges:
        left = start - 0.5
        right = end + 0.5
        ax.axvspan(left, right, color=color, alpha=alpha, linewidth=0)


def main() -> None:
    args = parse_args()

    df = pd.read_csv(args.input)
    band_columns = sorted(
        [column for column in df.columns if column.startswith("band_")],
        key=band_to_nm,
    )
    wavelengths = np.asarray([band_to_nm(column) for column in band_columns], dtype=np.int32)
    mean_signature = df[band_columns].mean(axis=0).to_numpy(dtype=np.float64)

    boruta_wavelengths = load_boruta_wavelengths(args.boruta_features_csv)
    kruskal_wavelengths = load_kruskal_wavelengths(args.kruskal_subset_csv)
    boruta_ranges = collapse_consecutive_ranges(boruta_wavelengths)
    kruskal_ranges = collapse_consecutive_ranges(kruskal_wavelengths)

    mean_series = pd.Series(mean_signature, index=wavelengths)
    boruta_values = mean_series.loc[boruta_wavelengths].to_numpy(dtype=np.float64)
    kruskal_values = mean_series.loc[kruskal_wavelengths].to_numpy(dtype=np.float64)

    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 300
    fig, ax = plt.subplots(figsize=(14, 6.2))

    add_range_spans(ax, boruta_ranges, BORUTA_COLOR, alpha=0.12)
    add_range_spans(ax, kruskal_ranges, KRUSKAL_COLOR, alpha=0.22)

    ax.plot(
        wavelengths,
        mean_signature,
        color=SIGNATURE_COLOR,
        linewidth=1.8,
        label="Assinatura media global",
        zorder=2,
    )
    ax.scatter(
        boruta_wavelengths,
        boruta_values,
        s=18,
        color=BORUTA_COLOR,
        edgecolors="none",
        alpha=0.85,
        zorder=3,
    )
    ax.scatter(
        kruskal_wavelengths,
        kruskal_values,
        s=34,
        color=KRUSKAL_COLOR,
        edgecolors="white",
        linewidths=0.4,
        alpha=0.95,
        zorder=4,
    )

    ax.set_xlim(int(wavelengths.min()), int(wavelengths.max()))
    ax.set_xlabel("Comprimento de onda (nm)")
    ax.set_ylabel("Media processada")
    ax.set_title("Assinatura media com bandas do Boruta e do Kruskal")
    ax.grid(alpha=0.15)

    legend_items = [
        Line2D([0], [0], color=SIGNATURE_COLOR, lw=1.8, label="Assinatura media global"),
        Patch(facecolor=BORUTA_COLOR, alpha=0.12, edgecolor="none", label="Boruta (148 bandas)"),
        Patch(facecolor=KRUSKAL_COLOR, alpha=0.22, edgecolor="none", label="Kruskal (20 bandas)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=BORUTA_COLOR, markersize=6, label="Pontos Boruta"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=KRUSKAL_COLOR, markeredgecolor="white", markersize=7, label="Pontos Kruskal"),
    ]
    ax.legend(handles=legend_items, loc="best", frameon=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(args.output, bbox_inches="tight")
    plt.close(fig)

    print(
        {
            "output": str(args.output.resolve()),
            "boruta_ranges": boruta_ranges,
            "kruskal_ranges": kruskal_ranges,
        }
    )


if __name__ == "__main__":
    main()
