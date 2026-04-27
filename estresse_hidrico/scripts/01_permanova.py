#!/usr/bin/env python3
"""Run PERMANOVA and PERMDISP analyses for morning-vs-afternoon effects."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pipeline_utils import (
    CONDITION_ORDER,
    CULTIVAR_ORDER,
    DUAL_TURN_DAYS,
    apply_fdr,
    choose_best_metric,
    ensure_dirs,
    get_paths,
    run_permanova_pair,
    save_figure,
    set_plot_style,
    significance_label,
    write_csv,
    write_excel_workbook,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa PERMANOVA/PERMDISP para o experimento de estresse hidrico.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="CSV de replicatas por bloco e turno. Default: dados/processados/replicatas_bloco_turno.csv",
    )
    return parser.parse_args()


def build_qvalue_plot(df: pd.DataFrame, output_path: Path) -> None:
    set_plot_style()
    plot_df = df.copy()
    plot_df["rotulo"] = plot_df["cultivar"] + " | " + plot_df["condicao"] + " | " + plot_df["comparacao"]
    q_values = np.clip(plot_df["q_value"].to_numpy(dtype=float), 1e-4, 1.0)
    heights = -np.log10(q_values)
    colors = ["#1565c0" if value == "Sim" else "#90a4ae" for value in plot_df["significativo"]]

    fig, ax = plt.subplots(figsize=(13, 6))
    bars = ax.bar(plot_df["rotulo"], heights, color=colors)
    ax.axhline(-np.log10(0.05), color="#d32f2f", linestyle="--", linewidth=1.2, label="q = 0.05")
    ax.set_ylabel("-log10(q-valor)")
    ax.set_title("PERMANOVA selecionada por comparacao")
    ax.set_xticklabels(plot_df["rotulo"], rotation=35, ha="right")
    ax.legend()
    for bar, metric in zip(bars, plot_df["metrica"], strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.03, metric, ha="center", va="bottom", fontsize=9)
    save_figure(fig, output_path)


def main() -> None:
    args = parse_args()
    paths = get_paths()
    ensure_dirs(paths)
    input_path = args.input or (paths.processed_dir / "replicatas_bloco_turno.csv")
    df = pd.read_csv(input_path)

    dual_df = df[(df["dia"].isin(DUAL_TURN_DAYS)) & (df["turno"].isin(["manha", "tarde"]))].copy()
    metric_rows: list[dict[str, object]] = []
    selected_rows: list[dict[str, object]] = []
    test_order = 0

    for cultivar in CULTIVAR_ORDER:
        for condition in CONDITION_ORDER:
            subset = dual_df[(dual_df["cultivar"] == cultivar) & (dual_df["condicao"] == condition)].copy()
            if subset["turno"].nunique() < 2:
                continue
            current_rows: list[dict[str, object]] = []
            for metric in ["braycurtis", "euclidean"]:
                result = run_permanova_pair(subset, grouping_column="turno", metric=metric)
                row = {
                    "teste_id": f"{cultivar}_{condition}_turno",
                    "ordem": test_order,
                    "cultivar": cultivar,
                    "condicao": condition,
                    "comparacao": "Manha vs Tarde",
                    **result,
                }
                current_rows.append(row)
                metric_rows.append(row)
            selected_rows.append(choose_best_metric(current_rows))
            test_order += 1

    for turno in ["manha", "tarde"]:
        subset = dual_df[dual_df["turno"] == turno].copy()
        if subset["condicao"].nunique() < 2:
            continue
        current_rows = []
        for metric in ["braycurtis", "euclidean"]:
            result = run_permanova_pair(subset, grouping_column="condicao", metric=metric)
            row = {
                "teste_id": f"Todos_IRR_NIRR_{turno}",
                "ordem": test_order,
                "cultivar": "Todos",
                "condicao": "IRR vs NIRR",
                "comparacao": turno.title(),
                **result,
            }
            current_rows.append(row)
            metric_rows.append(row)
        selected_rows.append(choose_best_metric(current_rows))
        test_order += 1

    metrics_df = pd.DataFrame(metric_rows).sort_values(["ordem", "metrica"]).reset_index(drop=True)
    selected_df = pd.DataFrame(selected_rows).sort_values(["ordem"]).reset_index(drop=True)
    selected_df = apply_fdr(selected_df, p_column="p_value", output_column="q_value")
    selected_df["significativo"] = selected_df["q_value"].map(significance_label)

    permdisp_df = selected_df[
        [
            "cultivar",
            "condicao",
            "comparacao",
            "metrica",
            "permdisp_F",
            "permdisp_p_value",
        ]
    ].copy()
    permdisp_df = apply_fdr(permdisp_df, p_column="permdisp_p_value", output_column="permdisp_q_value")
    permdisp_df["homogeneidade_ok"] = permdisp_df["permdisp_q_value"].map(lambda value: "Sim" if value >= 0.05 else "Nao")

    write_csv(metrics_df, paths.table_dir / "resultados_permanova_metricas.csv")
    write_csv(selected_df, paths.table_dir / "resultados_permanova.csv")
    write_csv(permdisp_df, paths.table_dir / "resultados_permdisp.csv")
    write_excel_workbook(
        paths.table_dir / "resultados_permanova.xlsx",
        {
            "permanova_selecionada": selected_df,
            "permanova_metricas": metrics_df,
            "permdisp": permdisp_df,
        },
    )
    build_qvalue_plot(selected_df, paths.figure_dir / "permanova_pvalores.png")
    print(selected_df[["cultivar", "condicao", "comparacao", "metrica", "F", "p_value", "q_value", "R2", "significativo"]].to_string(index=False))


if __name__ == "__main__":
    main()
