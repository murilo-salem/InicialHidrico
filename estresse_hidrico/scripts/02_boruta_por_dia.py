#!/usr/bin/env python3
"""Select informative wavelengths by day using Boruta."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from boruta import BorutaPy
from sklearn.ensemble import RandomForestClassifier

from pipeline_utils import (
    ensure_dirs,
    get_band_columns,
    get_paths,
    ordered_days,
    save_figure,
    set_plot_style,
    write_csv,
    write_excel_workbook,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa Boruta por dia para discriminar IRR vs NIRR.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="CSV de replicatas por bloco e dia. Default: dados/processados/replicatas_bloco_dia.csv",
    )
    return parser.parse_args()


def status_from_selector(confirmed: bool, tentative: bool) -> str:
    if confirmed:
        return "Confirmado"
    if tentative:
        return "Tentativa"
    return "Rejeitado"


def plot_presence_heatmap(presence_df: pd.DataFrame, output_path: Path) -> None:
    set_plot_style()
    if presence_df.empty:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "Nenhuma banda confirmada pelo Boruta.", ha="center", va="center")
        ax.axis("off")
        save_figure(fig, output_path)
        return

    fig_height = max(4.0, min(18.0, 0.14 * len(presence_df.index)))
    fig, ax = plt.subplots(figsize=(8, fig_height))
    sns.heatmap(
        presence_df,
        cmap=sns.color_palette(["#eceff1", "#1565c0"], as_cmap=True),
        linewidths=0.2,
        linecolor="#fafafa",
        cbar=False,
        ax=ax,
    )
    ax.set_xlabel("Dia")
    ax.set_ylabel("Comprimento de onda (nm)")
    ax.set_title("Presenca de bandas confirmadas por dia")
    save_figure(fig, output_path)


def main() -> None:
    args = parse_args()
    paths = get_paths()
    ensure_dirs(paths)
    input_path = args.input or (paths.processed_dir / "replicatas_bloco_dia.csv")
    df = pd.read_csv(input_path)
    band_columns = get_band_columns(df)
    day_labels = ordered_days(df["dia"].unique())

    boruta_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for day_label in day_labels:
        day_df = df[df["dia"] == day_label].copy()
        X = day_df[band_columns].to_numpy(dtype=float)
        y = (day_df["condicao"] == "NIRR").astype(int).to_numpy()
        if len(set(y)) < 2:
            continue

        estimator = RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )
        selector = BorutaPy(
            estimator=estimator,
            n_estimators="auto",
            alpha=0.05,
            max_iter=100,
            random_state=42,
            verbose=0,
        )
        selector.fit(X, y)

        for band_column, ranking, confirmed, tentative in zip(
            band_columns,
            selector.ranking_,
            selector.support_,
            selector.support_weak_,
            strict=True,
        ):
            boruta_rows.append(
                {
                    "dia": day_label,
                    "banda": band_column,
                    "comprimento_onda_nm": int(band_column.split("_", 1)[1]),
                    "status": status_from_selector(bool(confirmed), bool(tentative)),
                    "ranking": int(ranking),
                }
            )

        summary_rows.append(
            {
                "dia": day_label,
                "confirmadas": int(selector.support_.sum()),
                "tentativas": int(selector.support_weak_.sum()),
                "rejeitadas": int((~selector.support_ & ~selector.support_weak_).sum()),
            }
        )

    boruta_df = pd.DataFrame(boruta_rows).sort_values(["dia", "comprimento_onda_nm"]).reset_index(drop=True)
    summary_df = pd.DataFrame(summary_rows).sort_values(["dia"]).reset_index(drop=True)

    confirmed_df = boruta_df[boruta_df["status"] == "Confirmado"].copy()
    tentative_df = boruta_df[boruta_df["status"] == "Tentativa"].copy()
    recurrent_df = (
        confirmed_df.groupby(["banda", "comprimento_onda_nm"], as_index=False)
        .agg(dias_confirmados=("dia", "nunique"))
        .sort_values(["dias_confirmados", "comprimento_onda_nm"], ascending=[False, True])
        .reset_index(drop=True)
    )
    presence_df = (
        confirmed_df.assign(presente=1)
        .pivot_table(index="comprimento_onda_nm", columns="dia", values="presente", fill_value=0, aggfunc="max")
        .sort_index()
    )
    if not presence_df.empty:
        ordered_columns = [day for day in ordered_days(presence_df.columns) if day in presence_df.columns]
        presence_df = presence_df[ordered_columns]
        presence_df.index.name = "comprimento_onda_nm"

    write_csv(boruta_df, paths.table_dir / "lambdas_boruta_por_dia.csv")
    write_csv(summary_df, paths.table_dir / "resumo_boruta_por_dia.csv")
    write_csv(recurrent_df, paths.table_dir / "lambdas_confirmados_recorrentes.csv")
    write_csv(tentative_df, paths.table_dir / "lambdas_tentativas_por_dia.csv")
    write_excel_workbook(
        paths.table_dir / "resultados_boruta.xlsx",
        {
            "boruta_completo": boruta_df,
            "resumo_por_dia": summary_df,
            "confirmados_recorrentes": recurrent_df,
            "tentativas": tentative_df,
        },
    )
    plot_presence_heatmap(presence_df, paths.figure_dir / "heatmap_lambdas_confirmados.png")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
