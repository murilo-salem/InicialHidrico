#!/usr/bin/env python3
"""Classification with fold-local spectral augmentation for significant bands."""

from __future__ import annotations

import argparse
from functools import partial
from pathlib import Path

import numpy as np
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
            "Executa classificacao global com bandas significativas comparando "
            "baseline e augmentation espectral aplicada apenas no treino de cada fold."
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
        default=project_dir / "outputs" / "tabelas" / "classificacao_significancia_augmentation",
        help="Diretorio de saida para tabelas.",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=project_dir / "outputs" / "figuras" / "classificacao_significancia_augmentation",
        help="Diretorio de saida para figuras.",
    )
    parser.add_argument("--top-n", type=int, default=5, help="Numero de bandas recorrentes por alvo.")
    parser.add_argument(
        "--copies-per-sample",
        type=int,
        default=3,
        help="Numero de espectros sinteticos gerados para cada amostra real de treino.",
    )
    parser.add_argument(
        "--noise-std-fraction",
        type=float,
        default=0.015,
        help="Desvio do ruido gaussiano como fracao do desvio-padrao da banda no treino.",
    )
    parser.add_argument(
        "--scale-range",
        type=float,
        default=0.02,
        help="Intervalo multiplicativo por amostra: 0.02 equivale a [0.98, 1.02].",
    )
    parser.add_argument(
        "--offset-std-fraction",
        type=float,
        default=0.005,
        help="Desvio do offset aditivo como fracao do desvio-padrao da banda no treino.",
    )
    parser.add_argument(
        "--no-clip",
        action="store_true",
        help="Desativa o recorte dos sinteticos para o intervalo observado no treino.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semente aleatoria base.")
    return parser.parse_args()


def augment_spectral_training_data(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    fold_index: int,
    *,
    copies_per_sample: int,
    noise_std_fraction: float,
    scale_range: float,
    offset_std_fraction: float,
    clip_to_train_range: bool,
    random_state: int,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Create conservative spectral jitter copies using training-fold statistics only."""
    if copies_per_sample <= 0:
        return x_train.copy(), y_train.copy()

    values = x_train.to_numpy(dtype=np.float64, copy=True)
    rng = np.random.default_rng(random_state + fold_index * 1009)
    feature_std = np.nanstd(values, axis=0, ddof=1)
    fallback_std = np.nanmedian(feature_std[feature_std > 0])
    if not np.isfinite(fallback_std) or fallback_std <= 0:
        fallback_std = 1.0
    feature_std = np.where(np.isfinite(feature_std) & (feature_std > 0), feature_std, fallback_std)

    synthetic_blocks: list[np.ndarray] = []
    for _ in range(copies_per_sample):
        scale = rng.uniform(1.0 - scale_range, 1.0 + scale_range, size=(len(values), 1))
        noise = rng.normal(0.0, feature_std * noise_std_fraction, size=values.shape)
        offset = rng.normal(0.0, feature_std * offset_std_fraction, size=values.shape)
        synthetic = values * scale + noise + offset
        if clip_to_train_range:
            train_min = np.nanmin(values, axis=0)
            train_max = np.nanmax(values, axis=0)
            synthetic = np.clip(synthetic, train_min, train_max)
        synthetic_blocks.append(synthetic)

    synthetic_values = np.vstack(synthetic_blocks)
    x_augmented = pd.concat(
        [
            x_train.reset_index(drop=True),
            pd.DataFrame(synthetic_values, columns=x_train.columns),
        ],
        ignore_index=True,
    )
    y_augmented = np.concatenate([y_train, np.tile(y_train, copies_per_sample)])
    return x_augmented, y_augmented


def add_experiment_metadata(
    metrics_row: dict[str, object],
    *,
    variant: str,
    args: argparse.Namespace,
) -> dict[str, object]:
    enriched = dict(metrics_row)
    enriched["experiment_variant"] = variant
    enriched["augmentation_method"] = "spectral_jitter" if variant == "augmentation" else "none"
    enriched["copies_per_sample"] = int(args.copies_per_sample) if variant == "augmentation" else 0
    enriched["noise_std_fraction"] = float(args.noise_std_fraction) if variant == "augmentation" else 0.0
    enriched["scale_range"] = float(args.scale_range) if variant == "augmentation" else 0.0
    enriched["offset_std_fraction"] = float(args.offset_std_fraction) if variant == "augmentation" else 0.0
    enriched["clip_to_train_range"] = bool(not args.no_clip) if variant == "augmentation" else False
    return enriched


def build_comparison_table(metrics_df: pd.DataFrame) -> pd.DataFrame:
    id_columns = ["target", "model"]
    metric_columns = [
        "accuracy_media",
        "balanced_accuracy_media",
        "f1_macro_media",
        "kappa_media",
        "roc_auc_media",
    ]
    baseline = metrics_df.loc[metrics_df["experiment_variant"] == "baseline", id_columns + metric_columns]
    augmented = metrics_df.loc[metrics_df["experiment_variant"] == "augmentation", id_columns + metric_columns]
    comparison = baseline.merge(augmented, on=id_columns, suffixes=("_baseline", "_augmentation"))
    for metric in metric_columns:
        comparison[f"delta_{metric}"] = comparison[f"{metric}_augmentation"] - comparison[f"{metric}_baseline"]
    return comparison.sort_values(["target", "delta_f1_macro_media"], ascending=[True, False])


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

    augmenter = partial(
        augment_spectral_training_data,
        copies_per_sample=args.copies_per_sample,
        noise_std_fraction=args.noise_std_fraction,
        scale_range=args.scale_range,
        offset_std_fraction=args.offset_std_fraction,
        clip_to_train_range=not args.no_clip,
        random_state=args.seed,
    )

    all_metric_rows: list[dict[str, object]] = []
    best_rows: list[dict[str, object]] = []
    band_manifest_rows: list[pd.DataFrame] = []
    summary_lines = [
        "# Classificacao com augmentation espectral",
        "",
        f"- Dataset: `{input_path}`",
        f"- Significancia: `{significance_dir}`",
        f"- Numero de bandas por alvo: `{args.top_n}`",
        f"- Metodo: `spectral_jitter`, copias por amostra: `{args.copies_per_sample}`",
        f"- Ruido: `{args.noise_std_fraction}`, escala: `+/-{args.scale_range}`, offset: `{args.offset_std_fraction}`",
        "",
        "| alvo | variante | melhor_modelo | accuracy | balanced_acc | f1_macro | roc_auc | kappa |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    print("\n" + "=" * 96)
    print("CLASSIFICACAO COM AUGMENTATION ESPECTRAL FOLD-LOCAL")
    print(f"Dataset: {input_path}")
    print(f"Significance: {significance_dir}")
    print("=" * 96 + "\n")

    for target_name, spec in TARGET_SPECS.items():
        label_column = spec["label_column"]
        analysis_source = spec["analysis_source"]
        selected_bands_df = select_recurrent_bands(
            significance_dir=significance_dir,
            analysis_source=analysis_source,
            top_n=args.top_n,
            band_columns=band_columns,
        )
        selected_bands_df.insert(0, "target", target_name)
        band_manifest_rows.append(selected_bands_df)
        features = selected_bands_df["band_column"].tolist()

        class_names = resolve_class_order(target_name, frame[label_column].tolist())
        groups = build_group_labels(frame[label_column], frame["replicata"])
        min_groups = int(pd.Series(groups).groupby(frame[label_column]).nunique().min())
        n_splits = min(5, max(2, min_groups))

        for variant, fold_augmenter in [("baseline", None), ("augmentation", augmenter)]:
            target_dir = output_dir / variant / target_name
            target_dir.mkdir(parents=True, exist_ok=True)
            models = build_model_library(num_classes=len(class_names), random_state=args.seed)
            target_metric_rows: list[dict[str, object]] = []
            per_model_artifacts: dict[str, object] = {}

            print(f"[{target_name} | {variant}] classes={len(class_names)} | features={features}")
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
                    train_augmenter=fold_augmenter,
                )
                metrics_row = add_experiment_metadata(artifacts.metrics_row, variant=variant, args=args)
                metrics_row["analysis_source"] = analysis_source
                target_metric_rows.append(metrics_row)
                all_metric_rows.append(metrics_row)
                per_model_artifacts[model_name] = artifacts

                model_slug = sanitize_model_name(model_name)
                write_csv(pd.DataFrame([metrics_row]), target_dir / f"metricas_{model_slug}.csv")
                write_csv(artifacts.per_class_df, target_dir / f"metricas_por_classe_{model_slug}.csv")
                write_csv(artifacts.predictions_df, target_dir / f"predicoes_cv_{model_slug}.csv")
                write_csv(artifacts.confusion_df, target_dir / f"matriz_confusao_{model_slug}.csv")
                plot_confusion_matrix(
                    confusion=artifacts.confusion_matrix,
                    class_names=class_names,
                    title=f"{target_name} - {variant} - {model_name}",
                    output_path=figure_dir / variant / target_name / f"matriz_confusao_{model_slug}.png",
                )

            metrics_df = pd.DataFrame(target_metric_rows)
            write_csv(metrics_df, target_dir / "metricas_todas_modelos.csv")
            best_row = dict(choose_best_model(metrics_df))
            best_row["experiment_variant"] = variant
            best_rows.append(best_row)
            summary_lines.append(
                f"| {target_name} | {variant} | {best_row['model']} | "
                f"{best_row['accuracy_media']:.4f} | {best_row['balanced_accuracy_media']:.4f} | "
                f"{best_row['f1_macro_media']:.4f} | {best_row['roc_auc_media']:.4f} | "
                f"{best_row['kappa_media']:.4f} |"
            )

    all_metrics_df = pd.DataFrame(all_metric_rows)
    comparison_df = build_comparison_table(all_metrics_df)
    best_metrics_df = pd.DataFrame(best_rows)
    band_manifest_df = pd.concat(band_manifest_rows, ignore_index=True)

    write_csv(all_metrics_df, output_dir / "classification_metrics.csv")
    write_csv(comparison_df, output_dir / "comparacao_sem_vs_com_augmentation.csv")
    write_csv(best_metrics_df, output_dir / "melhor_modelo_por_alvo_variante.csv")
    write_csv(band_manifest_df, output_dir / "bandas_usadas_por_alvo.csv")
    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("\n" + "=" * 96)
    print(f"OUTPUT:  {output_dir}")
    print(f"FIGURES: {figure_dir}")
    print("=" * 96)


if __name__ == "__main__":
    main()
