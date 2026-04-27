#!/usr/bin/env python3
"""Generate spectral signature plots for irrigated versus non-irrigated plants."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pipeline_utils import (
    ATMOSPHERIC_INTERVALS,
    build_block_day_spectral_dataset,
    display_day_label,
    ensure_dirs,
    get_paths,
    ordered_days,
    resolve_input_path,
    save_figure,
    set_plot_style,
    write_csv,
)


CONDITION_STYLES = {
    "IRR": {"label": "Irrigado", "color": "#1565c0", "linestyle": "-"},
    "NIRR": {"label": "Nao irrigado", "color": "#c62828", "linestyle": "--"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera assinaturas espectrais IRR vs NIRR.")
    parser.add_argument(
        "--raw-input",
        type=Path,
        default=None,
        help="Workbook bruto. Default: base_dados_unificada.xlsx",
    )
    return parser.parse_args()


def summarize_signatures(
    df: pd.DataFrame,
    band_columns: list[str],
    group_columns: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for keys, subset in df.groupby(group_columns, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_values = dict(zip(group_columns, keys))
        means = subset[band_columns].mean()
        stds = subset[band_columns].std(ddof=1).fillna(0.0)
        sample_count = int(len(subset))
        for band_column in band_columns:
            rows.append(
                {
                    **key_values,
                    "banda": band_column,
                    "comprimento_onda_nm": int(band_column.split("_", 1)[1]),
                    "media_reflectancia": float(means[band_column]),
                    "desvio_padrao": float(stds[band_column]),
                    "n": sample_count,
                }
            )
    return pd.DataFrame(rows)


def add_atmospheric_spans(ax: plt.Axes) -> None:
    for start, end in ATMOSPHERIC_INTERVALS:
        ax.axvspan(start, end, color="#b0bec5", alpha=0.18, linewidth=0)


def plot_signature(ax: plt.Axes, summary_df: pd.DataFrame) -> None:
    for condition in ["IRR", "NIRR"]:
        subset = (
            summary_df[summary_df["condicao"] == condition]
            .sort_values("comprimento_onda_nm")
            .reset_index(drop=True)
        )
        if subset.empty:
            continue
        style = CONDITION_STYLES[condition]
        x = subset["comprimento_onda_nm"].to_numpy(dtype=float)
        y = subset["media_reflectancia"].to_numpy(dtype=float)
        sd = subset["desvio_padrao"].to_numpy(dtype=float)
        ax.plot(
            x,
            y,
            color=style["color"],
            linestyle=style["linestyle"],
            linewidth=1.8,
            label=style["label"],
        )
        ax.fill_between(x, y - sd, y + sd, color=style["color"], alpha=0.14)
    add_atmospheric_spans(ax)
    ax.set_xlim(350, 2500)
    ax.grid(alpha=0.15)


def create_overall_figure(summary_df: pd.DataFrame, output_path: Path) -> None:
    set_plot_style()
    fig, ax = plt.subplots(figsize=(13, 5.6))
    plot_signature(ax, summary_df)
    ax.set_xlabel("Comprimento de onda (nm)")
    ax.set_ylabel("Reflectancia suavizada")
    ax.set_title("Assinatura espectral media - Irrigado vs Nao irrigado")
    ax.legend(loc="upper right", frameon=True)
    save_figure(fig, output_path)


def create_by_day_figure(summary_df: pd.DataFrame, day_labels: list[str], output_path: Path) -> None:
    set_plot_style()
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True, sharey=True)
    handles = None
    labels = None
    for ax, day_label in zip(axes.flat, day_labels):
        day_subset = summary_df[summary_df["dia"] == day_label]
        plot_signature(ax, day_subset)
        ax.set_title(display_day_label(day_label).replace("\n", " "))
        if handles is None:
            handles, labels = ax.get_legend_handles_labels()
    for ax in axes[1, :]:
        ax.set_xlabel("Comprimento de onda (nm)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Reflectancia suavizada")
    if handles and labels:
        fig.legend(handles, labels, loc="upper center", ncol=2, frameon=True, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Assinaturas espectrais por dia - Irrigado vs Nao irrigado", y=1.06, fontsize=14)
    save_figure(fig, output_path)


def main() -> None:
    args = parse_args()
    paths = get_paths()
    ensure_dirs(paths)
    raw_input_path = resolve_input_path(args.raw_input)

    block_day_df, band_columns = build_block_day_spectral_dataset(
        raw_input_path,
        remove_atmospheric_bands=False,
    )
    day_labels = ordered_days(block_day_df["dia"].unique())

    overall_summary = summarize_signatures(block_day_df, band_columns, ["condicao"])
    day_summary = summarize_signatures(block_day_df, band_columns, ["dia", "condicao"])

    write_csv(overall_summary, paths.table_dir / "assinatura_espectral_irr_vs_nirr_media.csv")
    write_csv(day_summary, paths.table_dir / "assinatura_espectral_irr_vs_nirr_por_dia.csv")

    create_overall_figure(
        overall_summary,
        paths.figure_dir / "assinatura_espectral_irr_vs_nirr_media.png",
    )
    create_by_day_figure(
        day_summary,
        day_labels,
        paths.figure_dir / "assinatura_espectral_irr_vs_nirr_por_dia.png",
    )

    print(
        {
            "dias_plotados": day_labels,
            "figura_media": str(paths.figure_dir / "assinatura_espectral_irr_vs_nirr_media.png"),
            "figura_por_dia": str(paths.figure_dir / "assinatura_espectral_irr_vs_nirr_por_dia.png"),
        }
    )


if __name__ == "__main__":
    main()
