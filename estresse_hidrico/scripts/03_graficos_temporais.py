#!/usr/bin/env python3
"""Generate temporal plots for selected wavelengths and vegetation indices."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from pipeline_utils import (
    INDEX_COLUMNS,
    ATMOSPHERIC_INTERVALS,
    build_block_day_spectral_dataset,
    build_ratio_std_curve,
    display_day_label,
    ensure_dirs,
    get_band_columns,
    get_paths,
    ordered_days,
    plot_temporal_feature,
    resolve_input_path,
    save_figure,
    set_plot_style,
    write_csv,
    write_excel_workbook,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera series temporais para bandas Boruta e indices de vegetacao.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="CSV de replicatas por bloco e dia. Default: dados/processados/replicatas_bloco_dia.csv",
    )
    parser.add_argument(
        "--boruta",
        type=Path,
        default=None,
        help="CSV de Boruta por dia. Default: outputs/tabelas/lambdas_boruta_por_dia.csv",
    )
    parser.add_argument(
        "--raw-input",
        type=Path,
        default=None,
        help="Workbook bruto para o Painel B. Default: base_dados_unificada.xlsx",
    )
    return parser.parse_args()


def select_temporal_bands(boruta_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    confirmed = boruta_df[boruta_df["status"] == "Confirmado"].copy()
    recurrent = (
        confirmed.groupby(["banda", "comprimento_onda_nm"], as_index=False)
        .agg(dias_confirmados=("dia", "nunique"))
        .sort_values(["dias_confirmados", "comprimento_onda_nm"], ascending=[False, True])
        .reset_index(drop=True)
    )
    recurrent = recurrent[recurrent["dias_confirmados"] >= 2]
    if not recurrent.empty:
        return recurrent, "confirmado_em_pelo_menos_2_dias"

    if not confirmed.empty:
        fallback = (
            confirmed.groupby(["banda", "comprimento_onda_nm"], as_index=False)
            .agg(dias_confirmados=("dia", "nunique"))
            .sort_values(["dias_confirmados", "comprimento_onda_nm"], ascending=[False, True])
            .reset_index(drop=True)
        )
        return fallback.head(10), "fallback_confirmados_disponiveis"

    tentative = boruta_df[boruta_df["status"] == "Tentativa"].copy()
    fallback = (
        tentative.groupby(["banda", "comprimento_onda_nm"], as_index=False)
        .agg(dias_tentativos=("dia", "nunique"))
        .sort_values(["dias_tentativos", "comprimento_onda_nm"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return fallback.head(10).rename(columns={"dias_tentativos": "dias_confirmados"}), "fallback_tentativas"


def peak_annotation_mask(wavelengths: np.ndarray) -> np.ndarray:
    mask = np.ones_like(wavelengths, dtype=bool)
    exclusion_zones = [
        (350, 370),
        (2490, 2500),
        (1350, 1600),
        (1800, 2200),
    ]
    for start, end in ATMOSPHERIC_INTERVALS + exclusion_zones:
        mask &= ~((wavelengths >= start) & (wavelengths <= end))
    return mask


def extract_ratio_peaks(curve_df: pd.DataFrame, confirmed_df: pd.DataFrame, top_n: int = 4) -> pd.DataFrame:
    wavelengths = curve_df["comprimento_onda_nm"].to_numpy(dtype=int)
    response = curve_df["ratio_std"].to_numpy(dtype=float)
    valid_mask = peak_annotation_mask(wavelengths)
    valid_x = wavelengths[valid_mask]
    valid_y = response[valid_mask]

    if len(valid_x) == 0:
        return pd.DataFrame(columns=["peak_rank", "peak_nm", "ratio_std", "matched_boruta_nm", "matched_boruta"])

    prominence = max(float(np.nanstd(valid_y)) * 0.35, 1e-6)
    peak_indices, _ = find_peaks(valid_y, prominence=prominence, distance=12)
    if len(peak_indices) == 0:
        peak_indices = np.argsort(valid_y)[-top_n:]

    peak_indices = sorted(peak_indices, key=lambda idx: valid_y[idx], reverse=True)[:top_n]
    confirmed_wavelengths = confirmed_df["comprimento_onda_nm"].to_numpy(dtype=int) if not confirmed_df.empty else np.array([], dtype=int)

    rows: list[dict[str, object]] = []
    for rank, peak_idx in enumerate(peak_indices, start=1):
        peak_nm = int(valid_x[peak_idx])
        peak_value = float(valid_y[peak_idx])
        matched_nm = None
        matched = False
        if len(confirmed_wavelengths) > 0:
            nearest_idx = int(np.argmin(np.abs(confirmed_wavelengths - peak_nm)))
            nearest_nm = int(confirmed_wavelengths[nearest_idx])
            if abs(nearest_nm - peak_nm) <= 3:
                matched_nm = nearest_nm
                matched = True
        rows.append(
            {
                "peak_rank": rank,
                "peak_nm": peak_nm,
                "ratio_std": peak_value,
                "matched_boruta_nm": matched_nm,
                "matched_boruta": "Sim" if matched else "Nao",
            }
        )
    return pd.DataFrame(rows)


def plot_ratio_curve(
    curve_df: pd.DataFrame,
    day_label: str,
    output_path: Path,
    confirmed_df: pd.DataFrame,
    peak_df: pd.DataFrame,
) -> None:
    set_plot_style()
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.plot(curve_df["comprimento_onda_nm"], curve_df["ratio_std"], color="#2ca25f", linewidth=1.2)
    ax.fill_between(curve_df["comprimento_onda_nm"], curve_df["ratio_std"], color="#2ca25f", alpha=0.2)
    for start, end in ATMOSPHERIC_INTERVALS:
        ax.axvspan(start, end, color="#b0bec5", alpha=0.25, linewidth=0)
    if not confirmed_df.empty:
        y0, y1 = ax.get_ylim()
        rug_height = (y1 - y0) * 0.04
        ax.vlines(
            confirmed_df["comprimento_onda_nm"].to_numpy(dtype=float),
            y0,
            y0 + rug_height,
            color="#1565c0",
            alpha=0.55,
            linewidth=1.0,
        )
        ax.set_ylim(y0, y1)
    for row in peak_df.itertuples(index=False):
        ax.scatter(row.peak_nm, row.ratio_std, color="#d32f2f", s=28, zorder=5)
        label = f"{int(row.peak_nm)} nm"
        if row.matched_boruta == "Sim":
            label += f" | Boruta {int(row.matched_boruta_nm)}"
        ax.annotate(
            label,
            (row.peak_nm, row.ratio_std),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
            color="#5d4037",
        )
    ax.set_xlabel("Comprimento de onda (nm)")
    ax.set_ylabel("Desvio padrao do quociente NIRR/IRR")
    ax.set_title(f"Painel B - Desvio padrao do quociente NIRR/IRR - {display_day_label(day_label).replace(chr(10), ' ')}")
    save_figure(fig, output_path)


def plot_ratio_placeholder(output_path: Path, title: str, note: str) -> None:
    set_plot_style()
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.text(0.5, 0.55, title, ha="center", va="center", fontsize=14, fontweight="bold")
    ax.text(0.5, 0.40, note, ha="center", va="center", fontsize=11)
    ax.axis("off")
    save_figure(fig, output_path)


def main() -> None:
    args = parse_args()
    paths = get_paths()
    ensure_dirs(paths)
    input_path = args.input or (paths.processed_dir / "replicatas_bloco_dia.csv")
    boruta_path = args.boruta or (paths.table_dir / "lambdas_boruta_por_dia.csv")
    raw_input_path = resolve_input_path(args.raw_input)

    df = pd.read_csv(input_path)
    boruta_df = pd.read_csv(boruta_path)
    band_columns = get_band_columns(df)
    day_labels = ordered_days(df["dia"].unique())
    ratio_block_day_df, full_ratio_band_columns = build_block_day_spectral_dataset(
        raw_input_path,
        remove_atmospheric_bands=False,
    )

    selected_bands_df, selection_source = select_temporal_bands(boruta_df)
    selected_bands_df = selected_bands_df.sort_values("comprimento_onda_nm").reset_index(drop=True)
    selected_bands_df["origem_selecao_temporal"] = selection_source
    write_csv(selected_bands_df, paths.table_dir / "bandas_temporais_selecionadas.csv")

    temporal_rows: list[dict[str, object]] = []
    for _, row in selected_bands_df.iterrows():
        band_column = row["banda"]
        wavelength_nm = int(row["comprimento_onda_nm"])
        fig = plot_temporal_feature(
            df,
            feature_name=band_column,
            day_labels=day_labels,
            ylabel=f"Reflectancia suavizada ({wavelength_nm} nm)",
            title=f"Evolucao temporal - {wavelength_nm} nm",
        )
        save_figure(fig, paths.figure_dir / f"temporal_{wavelength_nm}nm.png")
        for condition in ["IRR", "NIRR"]:
            for day_label in day_labels:
                subset = df[(df["dia"] == day_label) & (df["condicao"] == condition)]
                temporal_rows.append(
                    {
                        "feature": band_column,
                        "tipo": "banda",
                        "feature_legenda": f"{wavelength_nm} nm",
                        "dia": day_label,
                        "condicao": condition,
                        "media": float(subset[band_column].mean()),
                        "desvio_padrao": float(subset[band_column].std(ddof=1)),
                        "n": int(len(subset)),
                    }
                )

    for index_name in INDEX_COLUMNS:
        fig = plot_temporal_feature(
            df,
            feature_name=index_name,
            day_labels=day_labels,
            ylabel=index_name,
            title=f"Indice de vegetacao - {index_name}",
        )
        save_figure(fig, paths.figure_dir / f"temporal_{index_name}.png")
        for condition in ["IRR", "NIRR"]:
            for day_label in day_labels:
                subset = df[(df["dia"] == day_label) & (df["condicao"] == condition)]
                temporal_rows.append(
                    {
                        "feature": index_name,
                        "tipo": "indice",
                        "feature_legenda": index_name,
                        "dia": day_label,
                        "condicao": condition,
                        "media": float(subset[index_name].mean()),
                        "desvio_padrao": float(subset[index_name].std(ddof=1)),
                        "n": int(len(subset)),
                    }
                )

    ratio_long_rows: list[pd.DataFrame] = []
    peak_long_rows: list[pd.DataFrame] = []
    ratio_day_labels = ordered_days(ratio_block_day_df["dia"].unique())
    for day_label in ratio_day_labels:
        day_df = ratio_block_day_df[ratio_block_day_df["dia"] == day_label].copy()
        ratio_curve_df = build_ratio_std_curve(day_df, full_ratio_band_columns)
        if ratio_curve_df.empty:
            continue
        confirmed_day_df = boruta_df[(boruta_df["dia"] == day_label) & (boruta_df["status"] == "Confirmado")].copy()
        peak_df = extract_ratio_peaks(ratio_curve_df, confirmed_day_df, top_n=4)
        ratio_curve_df.insert(0, "dia", day_label)
        ratio_long_rows.append(ratio_curve_df)
        if not peak_df.empty:
            peak_df.insert(0, "dia", day_label)
            peak_long_rows.append(peak_df)
        plot_ratio_curve(
            ratio_curve_df,
            day_label,
            paths.figure_dir / f"desvio_quociente_{day_label}.png",
            confirmed_day_df,
            peak_df,
        )

    if "recuperacao" not in ratio_day_labels:
        plot_ratio_placeholder(
            paths.figure_dir / "desvio_quociente_recuperacao.png",
            "Painel B - Recuperacao",
            "O workbook atual nao possui coleta separada para o dia de recuperacao.",
        )

    temporal_summary_df = pd.DataFrame(temporal_rows)
    ratio_summary_df = pd.concat(ratio_long_rows, ignore_index=True) if ratio_long_rows else pd.DataFrame()
    ratio_peaks_df = pd.concat(peak_long_rows, ignore_index=True) if peak_long_rows else pd.DataFrame()

    write_csv(temporal_summary_df, paths.table_dir / "series_temporais_resumo.csv")
    if not ratio_summary_df.empty:
        write_csv(ratio_summary_df, paths.table_dir / "desvio_quociente_por_dia.csv")
    if not ratio_peaks_df.empty:
        write_csv(ratio_peaks_df, paths.table_dir / "desvio_quociente_picos_por_dia.csv")

    write_excel_workbook(
        paths.table_dir / "resultados_temporais.xlsx",
        {
            "bandas_selecionadas": selected_bands_df,
            "series_temporais": temporal_summary_df,
            "desvio_quociente": ratio_summary_df,
            "picos_quociente": ratio_peaks_df,
        },
    )
    print(selected_bands_df.to_string(index=False))


if __name__ == "__main__":
    main()
