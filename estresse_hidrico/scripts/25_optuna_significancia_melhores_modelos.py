#!/usr/bin/env python3
"""Aggressive Optuna search on best models from significance-based k-fold results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import optuna
import pandas as pd
from sklearn.base import clone
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import cohen_kappa_score, confusion_matrix, f1_score, make_scorer, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from significance_classification_utils import (
    TARGET_SPECS,
    build_group_labels,
    prepare_targets,
    resolve_class_order,
    select_recurrent_bands,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    workspace_dir = project_dir.parent
    parser = argparse.ArgumentParser(
        description=(
            "Executa Optuna agressivo nos melhores modelos da rodada k-fold=4 "
            "com bandas significativas."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
    )
    parser.add_argument(
        "--significance-dir",
        type=Path,
        default=workspace_dir / "TestesSignfDiniz" / "TOP5_POR_DIA_TURNO",
    )
    parser.add_argument(
        "--best-models-csv",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "classificacao_significancia_global_2026-05-19" / "melhor_modelo_por_alvo.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "optuna_significancia_melhores_modelos",
    )
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--n-trials", type=int, default=250, help="Trials por alvo.")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def build_pipeline_for_target_model(model_name: str, trial: optuna.Trial, seed: int) -> Pipeline:
    if model_name == "Random Forest":
        n_estimators = trial.suggest_int("rf_n_estimators", 300, 1500, step=50)
        max_depth = trial.suggest_int("rf_max_depth", 3, 30)
        min_samples_split = trial.suggest_int("rf_min_samples_split", 2, 20)
        min_samples_leaf = trial.suggest_int("rf_min_samples_leaf", 1, 10)
        max_features = trial.suggest_categorical("rf_max_features", ["sqrt", "log2", None, 0.5, 0.8, 1.0])
        class_weight = trial.suggest_categorical("rf_class_weight", ["balanced", "balanced_subsample", None])
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            max_features=max_features,
            class_weight=class_weight,
            random_state=seed,
            n_jobs=-1,
        )
        return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", model)])

    if model_name == "LDA":
        solver = trial.suggest_categorical("lda_solver", ["lsqr", "eigen"])
        shrinkage_mode = trial.suggest_categorical("lda_shrinkage_mode", ["auto", "float"])
        shrinkage: str | float = "auto"
        if shrinkage_mode == "float":
            shrinkage = trial.suggest_float("lda_shrinkage", 1e-5, 1.0, log=True)
        model = LinearDiscriminantAnalysis(solver=solver, shrinkage=shrinkage)
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", model),
            ]
        )

    raise ValueError(f"Modelo nao suportado para tuning: {model_name}")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = prepare_targets(pd.read_csv(args.input.resolve()))
    best_models_df = pd.read_csv(args.best_models_csv.resolve())
    band_columns = [column for column in frame.columns if str(column).startswith("band_")]
    all_summary_rows: list[dict[str, object]] = []

    for target_name, spec in TARGET_SPECS.items():
        label_column = spec["label_column"]
        analysis_source = spec["analysis_source"]
        target_out = output_dir / target_name
        target_out.mkdir(parents=True, exist_ok=True)

        selected_bands_df = select_recurrent_bands(
            significance_dir=args.significance_dir.resolve(),
            analysis_source=analysis_source,
            top_n=args.top_n,
            band_columns=band_columns,
        )
        feature_columns = selected_bands_df["band_column"].tolist()
        write_csv(selected_bands_df, target_out / "bandas_selecionadas.csv")

        best_row = best_models_df.loc[best_models_df["target"] == target_name]
        if best_row.empty:
            raise ValueError(f"Nenhum melhor modelo encontrado para alvo={target_name}.")
        model_name = str(best_row.iloc[0]["model"])
        if model_name not in {"Random Forest", "LDA"}:
            raise ValueError(f"Modelo vencedor inesperado para alvo={target_name}: {model_name}")

        class_names = resolve_class_order(target_name, frame[label_column].tolist())
        label_to_index = {label: idx for idx, label in enumerate(class_names)}
        x = frame[feature_columns].copy()
        y = frame[label_column].map(label_to_index).to_numpy(dtype=int)
        groups = build_group_labels(frame[label_column], frame["replicata"])
        min_groups = int(pd.Series(groups).groupby(frame[label_column]).nunique().min())
        n_splits = min(5, max(2, min_groups))
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=args.seed)
        splits = list(splitter.split(x, y, groups))

        scorers = {
            "accuracy": "accuracy",
            "f1_macro": make_scorer(f1_score, average="macro", zero_division=0),
            "kappa": make_scorer(cohen_kappa_score),
        }
        sampler = optuna.samplers.TPESampler(seed=args.seed, multivariate=True, n_startup_trials=min(40, args.n_trials))
        study = optuna.create_study(direction="maximize", sampler=sampler, study_name=f"optuna_{target_name}_{model_name}")

        def objective(trial: optuna.Trial) -> float:
            pipeline = build_pipeline_for_target_model(model_name, trial, args.seed)
            scores = cross_validate(pipeline, x, y, cv=splits, scoring=scorers, n_jobs=1)
            accuracy = float(scores["test_accuracy"].mean())
            f1_macro = float(scores["test_f1_macro"].mean())
            kappa = float(scores["test_kappa"].mean())
            objective_value = f1_macro + 1e-3 * accuracy + 1e-4 * kappa
            trial.set_user_attr("accuracy", accuracy)
            trial.set_user_attr("f1_macro", f1_macro)
            trial.set_user_attr("kappa", kappa)
            return objective_value

        study.optimize(objective, n_trials=args.n_trials, show_progress_bar=False)

        trials_df = study.trials_dataframe().rename(columns={"value": "objective"})
        if not trials_df.empty:
            trials_df["accuracy"] = [trial.user_attrs.get("accuracy") for trial in study.trials]
            trials_df["f1_macro"] = [trial.user_attrs.get("f1_macro") for trial in study.trials]
            trials_df["kappa"] = [trial.user_attrs.get("kappa") for trial in study.trials]
            trials_df = trials_df.sort_values("objective", ascending=False).reset_index(drop=True)
        write_csv(trials_df, target_out / "optuna_trials.csv")

        best_trial = study.best_trial
        best_pipeline = build_pipeline_for_target_model(model_name, best_trial, args.seed)
        best_pipeline = clone(best_pipeline)
        best_scores = cross_validate(best_pipeline, x, y, cv=splits, scoring=scorers, n_jobs=1)
        y_pred = cross_val_predict(best_pipeline, x, y, cv=splits, n_jobs=1)
        cm = confusion_matrix(y, y_pred, labels=np.arange(len(class_names)))
        precision, recall, f1_values, support = precision_recall_fscore_support(
            y, y_pred, labels=np.arange(len(class_names)), zero_division=0
        )

        metrics_row = {
            "target": target_name,
            "model": model_name,
            "n_trials": int(args.n_trials),
            "cv_splits": int(n_splits),
            "n_bandas": int(len(feature_columns)),
            "bandas": "|".join(feature_columns),
            "objective": float(best_trial.value),
            "accuracy_media": float(best_scores["test_accuracy"].mean()),
            "accuracy_std": float(best_scores["test_accuracy"].std(ddof=1)),
            "f1_macro_media": float(best_scores["test_f1_macro"].mean()),
            "f1_macro_std": float(best_scores["test_f1_macro"].std(ddof=1)),
            "kappa_media": float(best_scores["test_kappa"].mean()),
            "kappa_std": float(best_scores["test_kappa"].std(ddof=1)),
            "best_params": json.dumps(best_trial.params, ensure_ascii=True, sort_keys=True),
        }
        write_csv(pd.DataFrame([metrics_row]), target_out / "optuna_best_scores.csv")
        all_summary_rows.append(metrics_row)

        per_class_df = pd.DataFrame(
            {
                "target": target_name,
                "model": model_name,
                "classe": class_names,
                "precision": precision,
                "recall": recall,
                "f1": f1_values,
                "support": support,
            }
        )
        write_csv(per_class_df, target_out / "optuna_per_class_scores.csv")

        confusion_df = pd.DataFrame(cm, index=class_names, columns=class_names).reset_index(names="real")
        confusion_df.insert(0, "target", target_name)
        confusion_df.insert(1, "model", model_name)
        write_csv(confusion_df, target_out / "optuna_confusion_matrix.csv")

        print(
            f"[{target_name}] model={model_name} trials={args.n_trials} "
            f"F1={metrics_row['f1_macro_media']:.4f} ACC={metrics_row['accuracy_media']:.4f} "
            f"KAPPA={metrics_row['kappa_media']:.4f}"
        )

    summary_df = pd.DataFrame(all_summary_rows).sort_values("f1_macro_media", ascending=False).reset_index(drop=True)
    write_csv(summary_df, output_dir / "optuna_resumo_geral.csv")
    print(f"\nOutput: {output_dir}")


if __name__ == "__main__":
    main()
