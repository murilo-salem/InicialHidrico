#!/usr/bin/env python3
"""F1-macro optimization for significance-band classification experiments."""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from significance_augmentation_utils import (
    augment_spectral_jitter,
    augment_spectral_mixup,
    prune_correlated_features,
)
from significance_classification_utils import (
    TARGET_SPECS,
    available_band_columns,
    build_group_labels,
    build_model_library,
    plot_confusion_matrix,
    prepare_targets,
    resolve_class_order,
    sanitize_model_name,
    select_recurrent_bands,
    write_csv,
)


@dataclass
class TunedArtifacts:
    metrics_row: dict[str, object]
    per_class_df: pd.DataFrame
    predictions_df: pd.DataFrame
    confusion_df: pd.DataFrame
    confusion_matrix: np.ndarray
    fold_details_df: pd.DataFrame


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    workspace_dir = project_dir.parent
    parser = argparse.ArgumentParser(
        description="Otimiza F1-macro com top_n, poda de correlacao, augmentation e tuning aninhado."
    )
    parser.add_argument("--input", type=Path, default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv")
    parser.add_argument(
        "--significance-dir",
        type=Path,
        default=workspace_dir / "TestesSignfDiniz" / "TOP5_POR_DIA_TURNO",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "otimizacao_f1_significancia",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=project_dir / "outputs" / "figuras" / "otimizacao_f1_significancia",
    )
    parser.add_argument("--top-n-values", default="5,8,10,15,20")
    parser.add_argument("--targets", default=",".join(TARGET_SPECS), help="Alvos a executar, separados por virgula.")
    parser.add_argument("--variants", default="baseline,jitter,mixup")
    parser.add_argument("--models", default="SVM (RBF),LDA,Random Forest,XGBoost")
    parser.add_argument("--correlation-threshold", type=float, default=0.95)
    parser.add_argument("--candidate-multiplier", type=int, default=4)
    parser.add_argument("--max-candidates-per-model", type=int, default=4)
    parser.add_argument("--inner-splits", type=int, default=3)
    parser.add_argument("--copies-per-sample", type=int, default=3)
    parser.add_argument("--noise-std-fraction", type=float, default=0.015)
    parser.add_argument("--scale-range", type=float, default=0.02)
    parser.add_argument("--offset-std-fraction", type=float, default=0.005)
    parser.add_argument("--mixup-alpha", type=float, default=0.4)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_int_csv(value: str) -> list[int]:
    parsed = [int(item) for item in parse_csv_list(value)]
    if not parsed:
        raise ValueError("A lista de top_n nao pode ficar vazia.")
    return parsed


def parameter_grid(options: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(options)
    return [dict(zip(keys, values)) for values in itertools.product(*(options[key] for key in keys))]


def tuned_param_candidates(model_name: str, max_candidates: int) -> list[dict[str, Any]]:
    grids: dict[str, list[dict[str, Any]]] = {
        "SVM (RBF)": [
            {"model__C": 1.0, "model__gamma": "scale"},
            {"model__C": 3.0, "model__gamma": "scale"},
            {"model__C": 1.0, "model__gamma": 0.03},
            {"model__C": 3.0, "model__gamma": 0.03},
            {"model__C": 10.0, "model__gamma": "scale"},
            {"model__C": 1.0, "model__gamma": 0.10},
            {"model__C": 10.0, "model__gamma": 0.03},
            {"model__C": 0.3, "model__gamma": "scale"},
        ],
        "LDA": parameter_grid({"model__shrinkage": ["auto", 0.05, 0.10, 0.20, 0.50, 0.80]}),
        "Random Forest": [
            {"model__n_estimators": 300, "model__max_features": "sqrt", "model__max_depth": None, "model__min_samples_leaf": 1},
            {"model__n_estimators": 300, "model__max_features": "sqrt", "model__max_depth": 6, "model__min_samples_leaf": 2},
            {"model__n_estimators": 300, "model__max_features": 0.60, "model__max_depth": None, "model__min_samples_leaf": 2},
            {"model__n_estimators": 300, "model__max_features": 1.00, "model__max_depth": 6, "model__min_samples_leaf": 2},
            {"model__n_estimators": 500, "model__max_features": "sqrt", "model__max_depth": 4, "model__min_samples_leaf": 4},
            {"model__n_estimators": 500, "model__max_features": 0.60, "model__max_depth": 8, "model__min_samples_leaf": 1},
        ],
        "XGBoost": [
            {"model__n_estimators": 180, "model__max_depth": 2, "model__learning_rate": 0.05, "model__subsample": 0.90, "model__colsample_bytree": 0.90, "model__reg_lambda": 1.0},
            {"model__n_estimators": 240, "model__max_depth": 3, "model__learning_rate": 0.05, "model__subsample": 0.90, "model__colsample_bytree": 0.80, "model__reg_lambda": 2.0},
            {"model__n_estimators": 300, "model__max_depth": 2, "model__learning_rate": 0.03, "model__subsample": 0.80, "model__colsample_bytree": 0.90, "model__reg_lambda": 3.0},
            {"model__n_estimators": 220, "model__max_depth": 4, "model__learning_rate": 0.04, "model__subsample": 0.80, "model__colsample_bytree": 0.80, "model__reg_lambda": 1.0},
        ],
        "k-NN (k=5)": parameter_grid({"model__n_neighbors": [3, 5, 7, 9], "model__weights": ["uniform", "distance"]}),
    }
    candidates = grids.get(model_name, [{}])
    if max_candidates > 0:
        return candidates[:max_candidates]
    return candidates


def make_augmenter(variant: str, args: argparse.Namespace):
    if variant == "baseline":
        return None
    if variant == "jitter":
        return partial(
            augment_spectral_jitter,
            copies_per_sample=args.copies_per_sample,
            noise_std_fraction=args.noise_std_fraction,
            scale_range=args.scale_range,
            offset_std_fraction=args.offset_std_fraction,
            clip_to_train_range=True,
            random_state=args.seed,
        )
    if variant == "mixup":
        return partial(
            augment_spectral_mixup,
            copies_per_sample=args.copies_per_sample,
            alpha=args.mixup_alpha,
            clip_to_train_range=True,
            random_state=args.seed,
        )
    raise ValueError(f"Variante desconhecida: {variant}")


def select_feature_pool(
    frame: pd.DataFrame,
    significance_dir: Path,
    analysis_source: str,
    band_columns: list[str],
    top_n: int,
    candidate_multiplier: int,
    correlation_threshold: float,
) -> tuple[list[str], pd.DataFrame]:
    pool_n = max(top_n, top_n * max(1, candidate_multiplier))
    try:
        selected_df = select_recurrent_bands(significance_dir, analysis_source, pool_n, band_columns)
    except ValueError:
        selected_df = select_recurrent_bands(significance_dir, analysis_source, top_n, band_columns)
    ordered_features = selected_df["band_column"].tolist()
    pruned = prune_correlated_features(
        frame,
        ordered_features,
        max_features=top_n,
        correlation_threshold=correlation_threshold,
    )
    if not pruned:
        raise ValueError(f"Nenhuma banda restou apos poda para {analysis_source} top_n={top_n}.")
    manifest = selected_df.loc[selected_df["band_column"].isin(pruned)].copy()
    manifest["selected_after_pruning"] = True
    return pruned, manifest


def compute_n_splits(labels: pd.Series, groups: np.ndarray, requested: int) -> int:
    per_class_groups = pd.Series(groups).groupby(labels.reset_index(drop=True)).nunique()
    min_groups = int(per_class_groups.min())
    return min(requested, max(2, min_groups))


def choose_best_params(
    base_model: object,
    param_candidates: list[dict[str, Any]],
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    groups_train: np.ndarray,
    augmenter,
    *,
    outer_fold: int,
    inner_splits: int,
    seed: int,
) -> tuple[dict[str, Any], float]:
    from sklearn.base import clone
    from sklearn.metrics import f1_score
    from sklearn.model_selection import StratifiedGroupKFold

    labels = pd.Series(y_train)
    n_splits = compute_n_splits(labels, groups_train, inner_splits)
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed + outer_fold)
    splits = list(splitter.split(x_train, y_train, groups_train))
    best_params: dict[str, Any] = {}
    best_score = -np.inf

    for candidate_index, params in enumerate(param_candidates):
        scores: list[float] = []
        for inner_fold, (inner_train_idx, inner_val_idx) in enumerate(splits, start=1):
            fitted = clone(base_model).set_params(**params)
            x_inner_train = x_train.iloc[inner_train_idx]
            y_inner_train = y_train[inner_train_idx]
            if augmenter is not None:
                x_inner_train, y_inner_train = augmenter(x_inner_train, y_inner_train, outer_fold * 100 + inner_fold)
            fitted.fit(x_inner_train, y_inner_train)
            pred = fitted.predict(x_train.iloc[inner_val_idx])
            scores.append(float(f1_score(y_train[inner_val_idx], pred, average="macro", zero_division=0)))
        mean_score = float(np.mean(scores))
        if mean_score > best_score:
            best_score = mean_score
            best_params = dict(params)

    return best_params, best_score


def evaluate_tuned_model_cv(
    *,
    model_name: str,
    base_model: object,
    param_candidates: list[dict[str, Any]],
    frame: pd.DataFrame,
    feature_columns: list[str],
    label_column: str,
    target_name: str,
    class_names: list[str],
    groups: np.ndarray,
    n_splits: int,
    inner_splits: int,
    augmenter,
    seed: int,
) -> TunedArtifacts:
    from sklearn.base import clone
    from sklearn.metrics import (
        accuracy_score,
        balanced_accuracy_score,
        cohen_kappa_score,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
        roc_auc_score,
    )
    from sklearn.model_selection import StratifiedGroupKFold

    label_to_index = {label: index for index, label in enumerate(class_names)}
    y = frame[label_column].map(label_to_index).to_numpy(dtype=int)
    x = frame[feature_columns].copy()
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    splits = list(splitter.split(x, y, groups))

    oof_predictions = np.empty_like(y)
    oof_probabilities = np.full((len(frame), len(class_names)), np.nan, dtype=np.float64)
    fold_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, float]] = []
    irr_index = class_names.index("IRR") if "IRR" in class_names else None

    for outer_fold, (train_idx, test_idx) in enumerate(splits, start=1):
        x_train = x.iloc[train_idx]
        y_train = y[train_idx]
        groups_train = groups[train_idx]
        best_params, inner_f1 = choose_best_params(
            base_model,
            param_candidates,
            x_train,
            y_train,
            groups_train,
            augmenter,
            outer_fold=outer_fold,
            inner_splits=inner_splits,
            seed=seed,
        )

        fitted = clone(base_model).set_params(**best_params)
        x_fit = x_train
        y_fit = y_train
        if augmenter is not None:
            x_fit, y_fit = augmenter(x_fit, y_fit, outer_fold)
        fitted.fit(x_fit, y_fit)
        y_test = y[test_idx]
        y_pred = fitted.predict(x.iloc[test_idx])
        y_prob = fitted.predict_proba(x.iloc[test_idx])
        oof_predictions[test_idx] = y_pred
        oof_probabilities[test_idx, : y_prob.shape[1]] = y_prob

        row = {
            "fold": float(outer_fold),
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred)),
            "f1_macro": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
            "kappa": float(cohen_kappa_score(y_test, y_pred)),
        }
        if len(class_names) == 2 and irr_index is not None:
            row["roc_auc"] = float(roc_auc_score((y_test == irr_index).astype(int), y_prob[:, irr_index]))
        else:
            row["roc_auc"] = np.nan
        metric_rows.append(row)
        fold_rows.append(
            {
                "target": target_name,
                "model": model_name,
                "fold": outer_fold,
                "inner_f1_macro": inner_f1,
                "best_params": json.dumps(best_params, sort_keys=True),
                "train_samples_real": int(len(train_idx)),
                "train_samples_after_augmentation": int(len(x_fit)),
                "test_samples": int(len(test_idx)),
            }
        )

    fold_df = pd.DataFrame(metric_rows)
    metrics_row = {
        "target": target_name,
        "model": model_name,
        "classes": "; ".join(class_names),
        "n_classes": int(len(class_names)),
        "n_samples": int(len(frame)),
        "n_groups": int(pd.Index(groups).nunique()),
        "cv_splits": int(len(splits)),
        "inner_splits": int(inner_splits),
        "n_bandas": int(len(feature_columns)),
        "bandas": "|".join(feature_columns),
        "n_param_candidates": int(len(param_candidates)),
        "accuracy_media": float(fold_df["accuracy"].mean()),
        "accuracy_std": float(fold_df["accuracy"].std(ddof=1)),
        "balanced_accuracy_media": float(fold_df["balanced_accuracy"].mean()),
        "balanced_accuracy_std": float(fold_df["balanced_accuracy"].std(ddof=1)),
        "f1_macro_media": float(fold_df["f1_macro"].mean()),
        "f1_macro_std": float(fold_df["f1_macro"].std(ddof=1)),
        "kappa_media": float(fold_df["kappa"].mean()),
        "kappa_std": float(fold_df["kappa"].std(ddof=1)),
        "roc_auc_media": float(fold_df["roc_auc"].mean()) if fold_df["roc_auc"].notna().any() else np.nan,
        "roc_auc_std": float(fold_df["roc_auc"].std(ddof=1)) if fold_df["roc_auc"].notna().any() else np.nan,
    }

    precision, recall, f1_values, support = precision_recall_fscore_support(
        y,
        oof_predictions,
        labels=np.arange(len(class_names)),
        zero_division=0,
    )
    per_class_df = pd.DataFrame(
        {
            "target": target_name,
            "model": model_name,
            "classe": class_names,
            "classe_codigo": np.arange(len(class_names), dtype=int),
            "precision": precision,
            "recall": recall,
            "f1": f1_values,
            "support": support,
        }
    )

    prediction_columns = [
        column
        for column in ["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco", "turno_label"]
        if column in frame.columns
    ]
    predictions_df = frame[prediction_columns].copy()
    predictions_df["target"] = target_name
    predictions_df["model"] = model_name
    predictions_df["y_true"] = y
    predictions_df["y_pred"] = oof_predictions
    predictions_df["label_true"] = [class_names[index] for index in y]
    predictions_df["label_pred"] = [class_names[index] for index in oof_predictions]
    predictions_df["acertou"] = predictions_df["y_true"] == predictions_df["y_pred"]
    for class_index, class_name in enumerate(class_names):
        predictions_df[f"prob_{sanitize_model_name(class_name)}"] = oof_probabilities[:, class_index]

    matrix = confusion_matrix(y, oof_predictions, labels=np.arange(len(class_names)))
    confusion_df = pd.DataFrame(matrix, index=class_names, columns=class_names).reset_index(names="real")
    confusion_df.insert(0, "target", target_name)
    confusion_df.insert(1, "model", model_name)

    return TunedArtifacts(
        metrics_row=metrics_row,
        per_class_df=per_class_df,
        predictions_df=predictions_df,
        confusion_df=confusion_df,
        confusion_matrix=matrix,
        fold_details_df=pd.DataFrame(fold_rows),
    )


def add_scenario_columns(df: pd.DataFrame, scenario: dict[str, object]) -> pd.DataFrame:
    enriched = df.copy()
    for key, value in scenario.items():
        enriched[key] = value
    scenario_columns = list(scenario)
    remaining_columns = [column for column in enriched.columns if column not in scenario_columns]
    return enriched[scenario_columns + remaining_columns]


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    significance_dir = args.significance_dir.resolve()
    output_dir = args.output_dir.resolve()
    figure_dir = args.figure_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    top_n_values = parse_int_csv(args.top_n_values)
    targets = parse_csv_list(args.targets)
    variants = parse_csv_list(args.variants)
    requested_models = parse_csv_list(args.models)
    frame = prepare_targets(pd.read_csv(input_path))
    band_columns = available_band_columns(frame)

    all_metric_rows: list[dict[str, object]] = []
    all_per_class: list[pd.DataFrame] = []
    all_fold_details: list[pd.DataFrame] = []
    all_band_manifests: list[pd.DataFrame] = []
    artifact_lookup: dict[tuple[str, int, str, str], TunedArtifacts] = {}

    print("\n" + "=" * 100)
    print("OTIMIZACAO F1-MACRO COM BANDAS SIGNIFICATIVAS")
    print(f"Targets: {targets} | Top N: {top_n_values} | variantes: {variants} | modelos: {requested_models}")
    print("=" * 100 + "\n")

    invalid_targets = sorted(set(targets) - set(TARGET_SPECS))
    if invalid_targets:
        raise ValueError(f"Alvos desconhecidos: {invalid_targets}")

    for target_name in targets:
        spec = TARGET_SPECS[target_name]
        label_column = spec["label_column"]
        analysis_source = spec["analysis_source"]
        class_names = resolve_class_order(target_name, frame[label_column].tolist())
        groups = build_group_labels(frame[label_column], frame["replicata"])
        n_splits = compute_n_splits(frame[label_column], groups, requested=5)
        base_models = build_model_library(num_classes=len(class_names), random_state=args.seed)
        models = {name: model for name, model in base_models.items() if name in requested_models}
        if not models:
            raise ValueError(f"Nenhum modelo solicitado foi encontrado: {requested_models}")

        for top_n in top_n_values:
            features, manifest = select_feature_pool(
                frame,
                significance_dir,
                analysis_source,
                band_columns,
                top_n,
                args.candidate_multiplier,
                args.correlation_threshold,
            )
            manifest.insert(0, "top_n_requested", top_n)
            manifest.insert(0, "target", target_name)
            all_band_manifests.append(manifest)
            print(f"[{target_name}] top_n={top_n} -> {len(features)} bandas apos poda")

            for variant in variants:
                augmenter = make_augmenter(variant, args)
                for model_name, model in models.items():
                    param_candidates = tuned_param_candidates(model_name, args.max_candidates_per_model)
                    scenario = {
                        "target": target_name,
                        "top_n_requested": top_n,
                        "n_features_after_pruning": len(features),
                        "variant": variant,
                        "model": model_name,
                    }
                    print(f"  - {variant} | {model_name} | candidatos={len(param_candidates)}")
                    artifacts = evaluate_tuned_model_cv(
                        model_name=model_name,
                        base_model=model,
                        param_candidates=param_candidates,
                        frame=frame,
                        feature_columns=features,
                        label_column=label_column,
                        target_name=target_name,
                        class_names=class_names,
                        groups=groups,
                        n_splits=n_splits,
                        inner_splits=args.inner_splits,
                        augmenter=augmenter,
                        seed=args.seed,
                    )
                    row = dict(artifacts.metrics_row)
                    row.update(
                        {
                            "top_n_requested": top_n,
                            "n_features_after_pruning": len(features),
                            "variant": variant,
                            "augmentation_method": variant,
                            "correlation_threshold": args.correlation_threshold,
                            "analysis_source": analysis_source,
                        }
                    )
                    all_metric_rows.append(row)
                    all_per_class.append(add_scenario_columns(artifacts.per_class_df, scenario))
                    all_fold_details.append(add_scenario_columns(artifacts.fold_details_df, scenario))
                    artifact_lookup[(target_name, top_n, variant, model_name)] = artifacts

    metrics_df = pd.DataFrame(all_metric_rows)
    per_class_df = pd.concat(all_per_class, ignore_index=True)
    fold_details_df = pd.concat(all_fold_details, ignore_index=True)
    band_manifest_df = pd.concat(all_band_manifests, ignore_index=True)
    ranking_df = metrics_df.sort_values(
        ["target", "f1_macro_media", "balanced_accuracy_media", "kappa_media"],
        ascending=[True, False, False, False],
    )
    best_by_target = ranking_df.groupby("target", as_index=False, sort=False).head(1).reset_index(drop=True)
    best_by_target_topn_variant = (
        ranking_df.groupby(["target", "top_n_requested", "variant"], as_index=False, sort=False)
        .head(1)
        .reset_index(drop=True)
    )

    write_csv(metrics_df, output_dir / "comparacao_f1_macro_otimizacao.csv")
    write_csv(best_by_target, output_dir / "melhores_por_alvo.csv")
    write_csv(best_by_target_topn_variant, output_dir / "melhores_por_alvo_topn_variante.csv")
    write_csv(per_class_df, output_dir / "metricas_por_classe_todos_cenarios.csv")
    write_csv(fold_details_df, output_dir / "detalhes_tuning_por_fold.csv")
    write_csv(band_manifest_df, output_dir / "bandas_por_topn_apos_poda.csv")

    summary_lines = [
        "# Otimizacao F1-macro com bandas significativas",
        "",
        f"- Dataset: `{input_path}`",
        f"- Significancia: `{significance_dir}`",
        f"- Top N avaliados: `{', '.join(map(str, top_n_values))}`",
        f"- Variantes: `{', '.join(variants)}`",
        f"- Modelos: `{', '.join(requested_models)}`",
        "",
        "| alvo | top_n | variante | modelo | bandas | f1_macro | balanced_acc | kappa |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in best_by_target.iterrows():
        target_name = str(row["target"])
        top_n = int(row["top_n_requested"])
        variant = str(row["variant"])
        model_name = str(row["model"])
        artifacts = artifact_lookup[(target_name, top_n, variant, model_name)]
        model_slug = sanitize_model_name(model_name)
        csv_path = output_dir / "melhores_matrizes" / f"matriz_confusao_{target_name}_{variant}_top{top_n}_{model_slug}.csv"
        png_path = figure_dir / "melhores_matrizes" / f"matriz_confusao_{target_name}_{variant}_top{top_n}_{model_slug}.png"
        write_csv(artifacts.confusion_df, csv_path)
        plot_confusion_matrix(
            artifacts.confusion_matrix,
            resolve_class_order(target_name, frame[TARGET_SPECS[target_name]["label_column"]].tolist()),
            f"{target_name} - {variant} - top {top_n} - {model_name}",
            png_path,
        )
        summary_lines.append(
            f"| {target_name} | {top_n} | {variant} | {model_name} | "
            f"{int(row['n_features_after_pruning'])} | {row['f1_macro_media']:.4f} | "
            f"{row['balanced_accuracy_media']:.4f} | {row['kappa_media']:.4f} |"
        )

    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print("\n" + "=" * 100)
    print(f"OUTPUT:  {output_dir}")
    print(f"FIGURES: {figure_dir}")
    print("=" * 100)


if __name__ == "__main__":
    main()
