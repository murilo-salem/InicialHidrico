#!/usr/bin/env python3
"""Plot daily mean spectral signatures with Boruta and Kruskal selections."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy.stats import kruskal


BORUTA_COLOR = "#2e7d32"
KRUSKAL_COLOR = "#c62828"
SIGNATURE_COLOR = "#1f2937"
DAY_ORDER = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9"]
DAY_TITLE = {
    "dia2": "Dia 2 (23/02)",
    "dia3": "Dia 3 (24/02)",
    "dia4": "Dia 4 (25/02)",
    "dia5": "Dia 5 (26/02)",
    "dia6": "Dia 6 (27/02)",
    "dia9": "Dia 9 (02/03)",
}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    parser = argparse.ArgumentParser(
        description="Plota assinaturas medias por dia com bandas Boruta e Kruskal."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
        help="CSV base da classificacao.",
    )
    parser.add_argument(
        "--boruta-csv",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "lambdas_boruta_por_dia.csv",
        help="CSV do Boruta por dia.",
    )
    parser.add_argument(
        "--top-k-kruskal",
        type=int,
        default=20,
        help="Numero de bandas top do Kruskal por dia.",
    )
    parser.add_argument(
        "--output-figure",
        type=Path,
        default=project_dir / "outputs" / "figuras" / "assinatura_media_boruta_vs_kruskal_por_dia.png",
        help="Figura de saida.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "boruta_kruskal_por_dia",
        help="Diretorio para tabelas auxiliares.",
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


def format_ranges(ranges: list[tuple[int, int]]) -> str:
    if not ranges:
        return ""
    parts: list[str] = []
    for start, end in ranges:
        if start == end:
            parts.append(str(start))
        else:
            parts.append(f"{start}-{end}")
    return "; ".join(parts)


def adjust_pvalues_bh(pvalues: np.ndarray) -> np.ndarray:
    adjusted = np.full_like(pvalues, np.nan, dtype=np.float64)
    finite_mask = np.isfinite(pvalues)
    finite_values = pvalues[finite_mask]
    if finite_values.size == 0:
        return adjusted
    order = np.argsort(finite_values)
    ordered = finite_values[order]
    n = ordered.size
    ranks = np.arange(1, n + 1, dtype=np.float64)
    bh = ordered * n / ranks
    bh = np.minimum.accumulate(bh[::-1])[::-1]
    bh = np.clip(bh, 0.0, 1.0)
    restored = np.empty_like(ordered)
    restored[order] = bh
    adjusted[finite_mask] = restored
    return adjusted


def compute_kruskal_per_day(df: pd.DataFrame, band_columns: list[str], top_k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for day in DAY_ORDER:
        day_df = df[df["dia"] == day].copy()
        irr = day_df[day_df["condicao"] == "IRR"]
        nirr = day_df[day_df["condicao"] == "NIRR"]
        rows: list[dict[str, object]] = []

        for band in band_columns:
            group_irr = irr[band].to_numpy(dtype=np.float64)
            group_nirr = nirr[band].to_numpy(dtype=np.float64)
            if group_irr.size < 3 or group_nirr.size < 3:
                rows.append(
                    {
                        "dia": day,
                        "band": band,
                        "wavelength_nm": band_to_nm(band),
                        "h_stat": np.nan,
                        "p_value": np.nan,
                        "mean_irrigated": float(np.nanmean(group_irr)),
                        "mean_non_irrigated": float(np.nanmean(group_nirr)),
                        "direction": np.nan,
                    }
                )
                continue
            stat, p_value = kruskal(group_irr, group_nirr, nan_policy="omit")
            mean_irr = float(np.nanmean(group_irr))
            mean_nirr = float(np.nanmean(group_nirr))
            rows.append(
                {
                    "dia": day,
                    "band": band,
                    "wavelength_nm": band_to_nm(band),
                    "h_stat": float(stat),
                    "p_value": float(p_value),
                    "mean_irrigated": mean_irr,
                    "mean_non_irrigated": mean_nirr,
                    "direction": "irrigado" if mean_irr >= mean_nirr else "nao_irrigado",
                }
            )

        day_result = pd.DataFrame(rows)
        day_result["q_value"] = adjust_pvalues_bh(day_result["p_value"].to_numpy(dtype=np.float64))
        day_result = day_result.sort_values(
            ["q_value", "p_value", "h_stat", "wavelength_nm"],
            ascending=[True, True, False, True],
        ).reset_index(drop=True)
        day_result["rank_kruskal"] = np.arange(1, len(day_result) + 1)
        day_result["selected_top_k"] = day_result["rank_kruskal"] <= top_k
        all_rows.extend(day_result.to_dict(orient="records"))

        selected = day_result[day_result["selected_top_k"]].copy()
        selected_wavelengths = selected["wavelength_nm"].astype(int).tolist()
        ranges = collapse_consecutive_ranges(selected_wavelengths)
        summary_rows.append(
            {
                "dia": day,
                "kruskal_count": int(selected.shape[0]),
                "kruskal_ranges": format_ranges(ranges),
            }
        )

    return pd.DataFrame(all_rows), pd.DataFrame(summary_rows)


def load_boruta_confirmed_by_day(boruta_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    boruta_df = pd.read_csv(boruta_csv, encoding="utf-8-sig")
    confirmed = boruta_df[boruta_df["status"] == "Confirmado"].copy()
    summary_rows: list[dict[str, object]] = []
    for day in DAY_ORDER:
        day_df = confirmed[confirmed["dia"] == day].copy()
        wavelengths = sorted(day_df["comprimento_onda_nm"].astype(int).tolist())
        ranges = collapse_consecutive_ranges(wavelengths)
        summary_rows.append(
            {
                "dia": day,
                "boruta_count": int(day_df.shape[0]),
                "boruta_ranges": format_ranges(ranges),
            }
        )
    return confirmed, pd.DataFrame(summary_rows)


def add_range_spans(ax: plt.Axes, ranges: list[tuple[int, int]], color: str, alpha: float) -> None:
    for start, end in ranges:
        ax.axvspan(start - 0.5, end + 0.5, color=color, alpha=alpha, linewidth=0)


def plot_panel(
    df: pd.DataFrame,
    band_columns: list[str],
    boruta_confirmed_df: pd.DataFrame,
    kruskal_selected_df: pd.DataFrame,
    output_path: Path,
) -> None:
    wavelengths = np.asarray([band_to_nm(column) for column in band_columns], dtype=np.int32)
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 300
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True, sharey=True)

    for ax, day in zip(axes.flat, DAY_ORDER):
        day_df = df[df["dia"] == day].copy()
        mean_signature = day_df[band_columns].mean(axis=0).to_numpy(dtype=np.float64)
        mean_series = pd.Series(mean_signature, index=wavelengths)

        boruta_wavelengths = sorted(
            boruta_confirmed_df.loc[boruta_confirmed_df["dia"] == day, "comprimento_onda_nm"].astype(int).tolist()
        )
        kruskal_wavelengths = sorted(
            kruskal_selected_df.loc[kruskal_selected_df["dia"] == day, "wavelength_nm"].astype(int).tolist()
        )
        boruta_ranges = collapse_consecutive_ranges(boruta_wavelengths)
        kruskal_ranges = collapse_consecutive_ranges(kruskal_wavelengths)

        add_range_spans(ax, boruta_ranges, BORUTA_COLOR, alpha=0.12)
        add_range_spans(ax, kruskal_ranges, KRUSKAL_COLOR, alpha=0.22)

        ax.plot(wavelengths, mean_signature, color=SIGNATURE_COLOR, linewidth=1.6, zorder=2)
        if boruta_wavelengths:
            ax.scatter(
                boruta_wavelengths,
                mean_series.loc[boruta_wavelengths].to_numpy(dtype=np.float64),
                s=14,
                color=BORUTA_COLOR,
                edgecolors="none",
                alpha=0.85,
                zorder=3,
            )
        if kruskal_wavelengths:
            ax.scatter(
                kruskal_wavelengths,
                mean_series.loc[kruskal_wavelengths].to_numpy(dtype=np.float64),
                s=28,
                color=KRUSKAL_COLOR,
                edgecolors="white",
                linewidths=0.35,
                alpha=0.95,
                zorder=4,
            )

        ax.set_title(f"{DAY_TITLE[day]} | Boruta={len(boruta_wavelengths)} | Kruskal={len(kruskal_wavelengths)}")
        ax.grid(alpha=0.15)
        ax.set_xlim(int(wavelengths.min()), int(wavelengths.max()))

    for ax in axes[1, :]:
        ax.set_xlabel("Comprimento de onda (nm)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Media processada")

    legend_items = [
        Line2D([0], [0], color=SIGNATURE_COLOR, lw=1.6, label="Assinatura media do dia"),
        Patch(facecolor=BORUTA_COLOR, alpha=0.12, edgecolor="none", label="Boruta por dia"),
        Patch(facecolor=KRUSKAL_COLOR, alpha=0.22, edgecolor="none", label="Kruskal por dia"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=BORUTA_COLOR, markersize=6, label="Pontos Boruta"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=KRUSKAL_COLOR, markeredgecolor="white", markersize=7, label="Pontos Kruskal"),
    ]
    fig.legend(handles=legend_items, loc="upper center", ncol=5, frameon=True, bbox_to_anchor=(0.5, 1.01))
    fig.suptitle("Assinatura media por dia com bandas do Boruta e do Kruskal", y=1.05, fontsize=15)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input)
    band_columns = sorted(
        [column for column in df.columns if column.startswith("band_")],
        key=band_to_nm,
    )
    boruta_confirmed_df, boruta_summary_df = load_boruta_confirmed_by_day(args.boruta_csv)
    kruskal_all_df, kruskal_summary_df = compute_kruskal_per_day(df, band_columns, args.top_k_kruskal)
    kruskal_selected_df = kruskal_all_df[kruskal_all_df["selected_top_k"]].copy()

    summary_df = boruta_summary_df.merge(kruskal_summary_df, on="dia", how="outer")
    summary_df = summary_df[["dia", "boruta_count", "boruta_ranges", "kruskal_count", "kruskal_ranges"]]

    boruta_confirmed_df.to_csv(output_dir / "boruta_confirmadas_por_dia.csv", index=False, encoding="utf-8-sig")
    kruskal_all_df.to_csv(output_dir / "kruskal_ranking_por_dia.csv", index=False, encoding="utf-8-sig")
    kruskal_selected_df.to_csv(output_dir / "kruskal_top20_por_dia.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(output_dir / "resumo_boruta_kruskal_por_dia.csv", index=False, encoding="utf-8-sig")

    plot_panel(df, band_columns, boruta_confirmed_df, kruskal_selected_df, args.output_figure)

    print(
        {
            "figure": str(args.output_figure.resolve()),
            "summary_csv": str((output_dir / "resumo_boruta_kruskal_por_dia.csv").resolve()),
            "kruskal_topk": int(args.top_k_kruskal),
        }
    )
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
