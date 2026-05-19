#!/usr/bin/env python3
"""Global classification experiments using recurrent top bands from significance tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from significance_classification_utils import (
    TARGET_SPECS,
    available_band_columns,
    build_group_labels,
    build_model_library,
    choose_best_model,
    evaluate_model_cv,
    plot_confusion_matrix,
    prepare_targets,
    resolve_class_order,
    sanitize_model_name,
    select_recurrent_bands,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    workspace_dir = project_dir.parent
    parser = argparse.ArgumentParser(
        description=(
            "Executa classificacao global para condicao, condicao x genotipo e "
            "condicao x genotipo x turno usando bandas recorrentes do TOP5 de significancia."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
        help="CSV agregado por bloco e dia usado nos experimentos globais.",
    )
    parser.add_argument(
        "--significance-dir",
        type=Path,
        default=workspace_dir / "TestesSignfDiniz" / "TOP5_POR_DIA_TURNO",
        help="Diretorio com TOP5_TODOS_DIAS_TURNOS_CONSOLIDADO.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "classificacao_significancia_global",
        help="Diretorio de saida para tabelas e resumos.",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=project_dir / "outputs" / "figuras" / "classificacao_significancia_global",
        help="Diretorio de saida para figuras.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Numero de bandas recorrentes selecionadas por alvo.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    significance_dir = args.significance_dir.resolve()
    output_dir = args.output_dir.resolve()
    figure_dir = args.figure_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    frame = prepare_targets(pd.read_csv(input_path))
    band_columns = available_band_columns(frame)
    if not band_columns:
        raise ValueError("Nenhuma coluna band_* foi encontrada no dataset de entrada.")

    band_manifest_rows: list[pd.DataFrame] = []
    all_metric_rows: list[dict[str, object]] = []
    best_rows: list[dict[str, object]] = []
    summary_lines = [
        "# Classificacao global com bandas do teste de significancia",
        "",
        f"- Dataset: `{input_path}`",
        f"- Significancia: `{significance_dir}`",
        f"- Numero de bandas por alvo: `{args.top_n}`",
        "",
        "| alvo | analise_top5 | bandas | melhor_modelo | accuracy | balanced_acc | f1_macro | roc_auc | kappa |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    print("\n" + "=" * 88)
    print("CLASSIFICACAO GLOBAL COM BANDAS DO TESTE DE SIGNIFICANCIA")
    print(f"Dataset: {input_path}")
    print(f"Significance: {significance_dir}")
    print("=" * 88 + "\n")

    for target_name, spec in TARGET_SPECS.items():
        label_column = spec["label_column"]
        display_name = spec["display_name"]
        analysis_source = spec["analysis_source"]
        target_dir = output_dir / target_name
        target_dir.mkdir(parents=True, exist_ok=True)

        selected_bands_df = select_recurrent_bands(
            significance_dir=significance_dir,
            analysis_source=analysis_source,
            top_n=args.top_n,
            band_columns=band_columns,
        )
        selected_bands_df.insert(0, "target", target_name)
        band_manifest_rows.append(selected_bands_df)
        write_csv(selected_bands_df, target_dir / "bandas_selecionadas.csv")

        features = selected_bands_df["band_column"].tolist()
        class_names = resolve_class_order(target_name, frame[label_column].tolist())
        groups = build_group_labels(frame[label_column], frame["replicata"])
        min_groups = int(pd.Series(groups).groupby(frame[label_column]).nunique().min())
        n_splits = min(5, max(2, min_groups))
        models = build_model_library(num_classes=len(class_names), random_state=42)

        print(f"[{target_name}] classes={len(class_names)} | groups/class={min_groups} | features={features}")

        per_model_artifacts: dict[str, object] = {}
        target_metric_rows: list[dict[str, object]] = []
        for model_name, model in models.items():
            artifacts = evaluate_model_cv(
                model_name=model_name,
                model=model,
                frame=frame,
                feature_columns=features,
                label_column=label_column,
                target_name=target_name,
                class_names=class_names,
                groups=groups,
                n_splits=n_splits,
            )
            metrics_row = dict(artifacts.metrics_row)
            metrics_row["analysis_source"] = analysis_source
            target_metric_rows.append(metrics_row)
            all_metric_rows.append(metrics_row)
            per_model_artifacts[model_name] = artifacts

            model_slug = sanitize_model_name(model_name)
            write_csv(pd.DataFrame([metrics_row]), target_dir / f"metricas_{model_slug}.csv")
            write_csv(artifacts.per_class_df, target_dir / f"metricas_por_classe_{model_slug}.csv")
            write_csv(artifacts.predictions_df, target_dir / f"predicoes_cv_{model_slug}.csv")
            write_csv(artifacts.confusion_df, target_dir / f"matriz_confusao_{model_slug}.csv")

        metrics_df = pd.DataFrame(target_metric_rows)
        write_csv(metrics_df, target_dir / "metricas_todas_modelos.csv")
        best_row = choose_best_model(metrics_df)
        best_rows.append(dict(best_row))

        best_artifacts = per_model_artifacts[str(best_row["model"])]
        best_model_slug = sanitize_model_name(str(best_row["model"]))
        plot_confusion_matrix(
            confusion=best_artifacts.confusion_matrix,
            class_names=class_names,
            title=f"{display_name} - {best_row['model']}",
            output_path=figure_dir / f"matriz_confusao_{target_name}_{best_model_slug}.png",
        )

        summary_lines.append(
            f"| {target_name} | {analysis_source} | {', '.join(features)} | {best_row['model']} | "
            f"{best_row['accuracy_media']:.4f} | {best_row['balanced_accuracy_media']:.4f} | "
            f"{best_row['f1_macro_media']:.4f} | "
            f"{best_row['roc_auc_media']:.4f} | {best_row['kappa_media']:.4f} |"
        )
        print(
            f"   -> Best: {best_row['model']} | ACC={best_row['accuracy_media']:.4f} | "
            f"BAC={best_row['balanced_accuracy_media']:.4f} | "
            f"F1={best_row['f1_macro_media']:.4f} | "
            f"KAPPA={best_row['kappa_media']:.4f}"
        )

    all_metrics_df = pd.DataFrame(all_metric_rows)
    best_metrics_df = pd.DataFrame(best_rows)
    band_manifest_df = pd.concat(band_manifest_rows, ignore_index=True)

    write_csv(all_metrics_df, output_dir / "classification_metrics.csv")
    write_csv(best_metrics_df, output_dir / "melhor_modelo_por_alvo.csv")
    write_csv(band_manifest_df, output_dir / "bandas_usadas_por_alvo.csv")
    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("\n" + "=" * 88)
    print(f"OUTPUT:  {output_dir}")
    print(f"FIGURES: {figure_dir}")
    print("=" * 88)


if __name__ == "__main__":
    main()
