#!/usr/bin/env python3
"""Assemble a publication panel and a concise markdown report."""

from __future__ import annotations

import argparse

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd

from pipeline_utils import ensure_dirs, get_paths, save_figure, set_plot_style, write_excel_workbook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monta painel final de figuras e um relatorio markdown conciso.")
    return parser.parse_args()


def build_panel(paths) -> None:
    figure_specs = [
        ("A. PERMANOVA", paths.figure_dir / "permanova_pvalores.png"),
        ("B. Heatmap Boruta", paths.figure_dir / "heatmap_lambdas_confirmados.png"),
        ("C. Confusion Matrix", paths.figure_dir / "confusion_matrix.png"),
        ("D. RF Importance", paths.figure_dir / "rf_feature_importance_top20.png"),
    ]

    set_plot_style()
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    for axis, (title, image_path) in zip(axes.flatten(), figure_specs, strict=True):
        image = mpimg.imread(image_path)
        axis.imshow(image)
        axis.axis("off")
        axis.set_title(title)
    save_figure(fig, paths.figure_dir / "painel_resumo_estresse_hidrico.png")


def build_report(paths) -> None:
    integridade = pd.read_csv(paths.table_dir / "integridade_dados.csv")
    cronograma = pd.read_csv(paths.table_dir / "cronograma_dias.csv")
    permanova = pd.read_csv(paths.table_dir / "resultados_permanova.csv")
    boruta = pd.read_csv(paths.table_dir / "lambdas_confirmados_recorrentes.csv")
    modelos = pd.read_csv(paths.table_dir / "escores_modelos.csv")
    classes = pd.read_csv(paths.table_dir / "escores_por_classe.csv")

    best_model = modelos.sort_values(["f1_macro_media", "accuracy_media"], ascending=[False, False]).iloc[0]
    significant_permanova = permanova[permanova["significativo"] == "Sim"]
    top_bands = boruta.head(10)

    lines = [
        "# Relatorio de resultados - estresse hidrico em soja",
        "",
        "## Contexto do dataset",
        "",
    ]
    for row in cronograma.itertuples(index=False):
        lines.append(
            f"- {row.data_coleta_iso} -> {row.dia} | turnos: {row.turnos_originais} | amostras brutas: {row.amostras_brutas}"
        )
    lines.extend(
        [
            "",
            "## Integridade",
            "",
        ]
    )
    for row in integridade.itertuples(index=False):
        lines.append(f"- {row.metrica}: {row.valor}")

    lines.extend(
        [
            "",
            "## Q1 - PERMANOVA",
            "",
        ]
    )
    if significant_permanova.empty:
        lines.append("- Nenhuma comparacao permaneceu significativa apos FDR.")
    else:
        for row in significant_permanova.itertuples(index=False):
            lines.append(
                "- "
                f"{row.cultivar} | {row.condicao} | {row.comparacao} | "
                f"F={row.F:.4f}, p={row.p_value:.4f}, q={row.q_value:.4f}, R2={row.R2:.4f}, metrica={row.metrica}"
            )

    lines.extend(
        [
            "",
            "## Q2 - Boruta",
            "",
            f"- Bandas confirmadas recorrentes (top 10): {', '.join(str(int(value)) for value in top_bands['comprimento_onda_nm'].tolist()) if not top_bands.empty else 'nenhuma'}",
            "",
            "## Q3 - Classificacao",
            "",
            f"- Melhor modelo: {best_model['modelo']}",
            f"- Accuracy media: {best_model['accuracy_media']:.4f}",
            f"- F1-macro medio: {best_model['f1_macro_media']:.4f}",
            f"- Kappa medio: {best_model['kappa_media']:.4f}",
            "",
            "### Escores por classe",
            "",
        ]
    )
    for _, row in classes.iterrows():
        lines.append(
            f"- {row['Classe']}: Precisao={row['Precisao']:.4f}, Recall={row['Recall']:.4f}, "
            f"F1={row['F1-score']:.4f}, Suporte={int(row['Suporte'])}"
        )

    report_path = paths.output_dir / "relatorio_resultados.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    write_excel_workbook(
        paths.table_dir / "sintese_final.xlsx",
        {
            "integridade": integridade,
            "cronograma": cronograma,
            "permanova": permanova,
            "boruta_recorrente": boruta,
            "modelos": modelos,
            "classes": classes,
        },
    )


def main() -> None:
    parse_args()
    paths = get_paths()
    ensure_dirs(paths)
    build_panel(paths)
    build_report(paths)
    print((paths.figure_dir / "painel_resumo_estresse_hidrico.png").as_posix())


if __name__ == "__main__":
    main()
