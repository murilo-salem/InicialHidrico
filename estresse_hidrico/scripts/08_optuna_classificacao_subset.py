#!/usr/bin/env python3
"""Run Optuna hyperparameter tuning for the 6-class classifier on a band subset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import cohen_kappa_score, confusion_matrix, f1_score, make_scorer, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict, cross_validate
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


INDEX_COLUMNS = ["NDVI", "EVI", "WBI", "PRI", "SIPI", "REP"]
CLASS_LABELS = {
    ("EMB48", "IRR"): ("A", "A (EMB48 IRR)"),
    ("EMB48", "NIRR"): ("B", "B (EMB48 NIRR)"),
    ("BR16", "IRR"): ("C", "C (BR16 IRR)"),
    ("BR16", "NIRR"): ("D", "D (BR16 NIRR)"),
    ("CD202", "IRR"): ("E", "E (CD202 IRR)"),
    ("CD202", "NIRR"): ("F", "F (CD202 NIRR)"),
}
CLASS_ORDER = ["A", "B", "C", "D", "E", "F"]


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    parser = argparse.ArgumentParser(
        description="Executa Optuna na classificacao 6x6 com um subconjunto explicito de bandas."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
        help="CSV de replicatas por bloco e dia.",
    )
    parser.add_argument(
        "--subset-csv",
        type=Path,
        required=True,
        help="CSV com colunas subset, band, wavelength_nm.",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=80,
        help="Numero de trials do Optuna.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed para reproducibilidade.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "optuna_classificacao_subset",
        help="Diretorio de saida.",
    )
    return parser.parse_args()


def assign_class_labels(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    labels = frame.apply(lambda row: CLASS_LABELS[(row["cultivar"], row["condicao"])], axis=1)
    frame["classe"] = [item[0] for item in labels]
    frame["classe_legenda"] = [item[1] for item in labels]
    frame["grupo_cv"] = frame["classe"] + "_B" + frame["replicata"].astype(str)
    return frame


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def plot_confusion_matrix(cm: np.ndarray, labels: list[str], output_path: Path, title_suffix: str) -> None:
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 300
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(cm, cmap="Blues")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    for row_idx in range(cm.shape[0]):
        for col_idx in range(cm.shape[1]):
            ax.text(col_idx, row_idx, int(cm[row_idx, col_idx]), ha="center", va="center", color="black")
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.set_title(f"Confusion Matrix - {title_suffix}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_pipeline(trial: optuna.Trial, seed: int) -> tuple[str, Pipeline]:
    model_name = trial.suggest_categorical("model", ["LDA", "SVM_RBF", "RandomForest", "KNN"])

    if model_name == "LDA":
        solver = trial.suggest_categorical("lda_solver", ["lsqr", "eigen"])
        shrinkage_mode = trial.suggest_categorical("lda_shrinkage_mode", ["auto", "float"])
        shrinkage: str | float = "auto"
        if shrinkage_mode == "float":
            shrinkage = trial.suggest_float("lda_shrinkage", 1e-4, 1.0, log=True)
        model = LinearDiscriminantAnalysis(solver=solver, shrinkage=shrinkage)
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", model),
            ]
        )
        return model_name, pipeline

    if model_name == "SVM_RBF":
        c_value = trial.suggest_float("svm_c", 1e-2, 1e2, log=True)
        gamma = trial.suggest_float("svm_gamma", 1e-4, 1e1, log=True)
        model = SVC(
            kernel="rbf",
            C=c_value,
            gamma=gamma,
            class_weight="balanced",
            random_state=seed,
        )
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", model),
            ]
        )
        return model_name, pipeline

    if model_name == "RandomForest":
        n_estimators = trial.suggest_int("rf_n_estimators", 150, 700, step=50)
        max_depth = trial.suggest_int("rf_max_depth", 3, 20)
        min_samples_split = trial.suggest_int("rf_min_samples_split", 2, 10)
        min_samples_leaf = trial.suggest_int("rf_min_samples_leaf", 1, 5)
        max_features = trial.suggest_categorical("rf_max_features", ["sqrt", "log2", None])
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
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", model),
            ]
        )
        return model_name, pipeline

    n_neighbors = trial.suggest_int("knn_n_neighbors", 3, 21)
    weights = trial.suggest_categorical("knn_weights", ["uniform", "distance"])
    p_value = trial.suggest_int("knn_p", 1, 2)
    model = KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights, p=p_value)
    pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", model),
        ]
    )
    return model_name, pipeline


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = assign_class_labels(pd.read_csv(args.input))
    subset_df = pd.read_csv(args.subset_csv, encoding="utf-8-sig")
    selected_bands = subset_df["band"].tolist()
    subset_name = str(subset_df["subset"].iloc[0]) if not subset_df.empty else args.subset_csv.stem

    feature_columns = list(selected_bands) + INDEX_COLUMNS
    X = df[feature_columns].copy()
    y = pd.Categorical(df["classe"], categories=CLASS_ORDER, ordered=True).codes
    groups = df["grupo_cv"].to_numpy()
    class_labels_display = [
        CLASS_LABELS[("EMB48", "IRR")][1],
        CLASS_LABELS[("EMB48", "NIRR")][1],
        CLASS_LABELS[("BR16", "IRR")][1],
        CLASS_LABELS[("BR16", "NIRR")][1],
        CLASS_LABELS[("CD202", "IRR")][1],
        CLASS_LABELS[("CD202", "NIRR")][1],
    ]

    min_groups = int(df.groupby("classe")["grupo_cv"].nunique().min())
    n_splits = min(5, max(2, min_groups))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=args.seed)
    splits = list(splitter.split(X, y, groups))

    scorers = {
        "accuracy": "accuracy",
        "f1_macro": make_scorer(f1_score, average="macro"),
        "kappa": make_scorer(cohen_kappa_score),
    }

    sampler = optuna.samplers.TPESampler(seed=args.seed)
    study = optuna.create_study(direction="maximize", sampler=sampler, study_name=f"optuna_{subset_name}")

    def objective(trial: optuna.Trial) -> float:
        model_name, pipeline = build_pipeline(trial, args.seed)
        scores = cross_validate(pipeline, X, y, cv=splits, scoring=scorers, n_jobs=1)
        accuracy = float(scores["test_accuracy"].mean())
        f1_macro = float(scores["test_f1_macro"].mean())
        kappa = float(scores["test_kappa"].mean())
        combined_objective = f1_macro + 1e-3 * accuracy + 1e-4 * kappa
        trial.set_user_attr("model", model_name)
        trial.set_user_attr("accuracy", accuracy)
        trial.set_user_attr("f1_macro", f1_macro)
        trial.set_user_attr("kappa", kappa)
        return combined_objective

    study.optimize(objective, n_trials=args.n_trials, show_progress_bar=False)

    trials_df = study.trials_dataframe().copy()
    if not trials_df.empty:
        rename_map = {"value": "objective"}
        trials_df = trials_df.rename(columns=rename_map)
        trials_df["user_attrs_accuracy"] = [trial.user_attrs.get("accuracy") for trial in study.trials]
        trials_df["user_attrs_f1_macro"] = [trial.user_attrs.get("f1_macro") for trial in study.trials]
        trials_df["user_attrs_kappa"] = [trial.user_attrs.get("kappa") for trial in study.trials]
        trials_df["user_attrs_model"] = [trial.user_attrs.get("model") for trial in study.trials]
        trials_df = trials_df.sort_values("objective", ascending=False).reset_index(drop=True)
    write_csv(trials_df, output_dir / f"optuna_trials_{subset_name}.csv")

    best_trial = study.best_trial
    best_model_name, best_pipeline = build_pipeline(best_trial, args.seed)
    best_scores = cross_validate(best_pipeline, X, y, cv=splits, scoring=scorers, n_jobs=1)
    y_pred = cross_val_predict(best_pipeline, X, y, cv=splits, n_jobs=1)
    cm = confusion_matrix(y, y_pred, labels=np.arange(len(CLASS_ORDER)))
    precision, recall, f1_values, support = precision_recall_fscore_support(
        y,
        y_pred,
        labels=np.arange(len(CLASS_ORDER)),
        zero_division=0,
    )

    score_df = pd.DataFrame(
        [
            {
                "subset": subset_name,
                "best_model": best_model_name,
                "n_bands": int(len(selected_bands)),
                "n_features_total": int(len(feature_columns)),
                "n_trials": int(args.n_trials),
                "n_splits_cv": int(n_splits),
                "objective": float(best_trial.value),
                "accuracy_media": float(best_scores["test_accuracy"].mean()),
                "accuracy_std": float(best_scores["test_accuracy"].std(ddof=1)),
                "f1_macro_media": float(best_scores["test_f1_macro"].mean()),
                "f1_macro_std": float(best_scores["test_f1_macro"].std(ddof=1)),
                "kappa_media": float(best_scores["test_kappa"].mean()),
                "kappa_std": float(best_scores["test_kappa"].std(ddof=1)),
            }
        ]
    )
    per_class_df = pd.DataFrame(
        {
            "Classe": class_labels_display,
            "Precisao": precision,
            "Recall": recall,
            "F1-score": f1_values,
            "Suporte": support,
        }
    )
    confusion_df = pd.DataFrame(cm, index=class_labels_display, columns=class_labels_display).reset_index().rename(
        columns={"index": "Classe verdadeira"}
    )

    params_payload = {
        "subset": subset_name,
        "best_model": best_model_name,
        "objective": float(best_trial.value),
        "metrics": {
            "accuracy_media": float(best_scores["test_accuracy"].mean()),
            "f1_macro_media": float(best_scores["test_f1_macro"].mean()),
            "kappa_media": float(best_scores["test_kappa"].mean()),
        },
        "params": best_trial.params,
    }
    (output_dir / f"best_params_{subset_name}.json").write_text(
        json.dumps(params_payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    write_csv(score_df, output_dir / f"optuna_best_scores_{subset_name}.csv")
    write_csv(confusion_df, output_dir / f"optuna_confusion_matrix_{subset_name}.csv")
    write_csv(per_class_df, output_dir / f"optuna_per_class_scores_{subset_name}.csv")
    plot_confusion_matrix(cm, class_labels_display, output_dir / f"optuna_confusion_matrix_{subset_name}.png", f"{subset_name} + Optuna")

    top_trials_lines = [
        "# Optuna - classificacao subset",
        "",
        f"- subset: `{subset_name}`",
        f"- trials: `{args.n_trials}`",
        f"- best model: `{best_model_name}`",
        f"- accuracy: `{float(best_scores['test_accuracy'].mean()):.6f}`",
        f"- f1_macro: `{float(best_scores['test_f1_macro'].mean()):.6f}`",
        f"- kappa: `{float(best_scores['test_kappa'].mean()):.6f}`",
        "",
        "## Best params",
        "",
        "```json",
        json.dumps(best_trial.params, indent=2, ensure_ascii=True),
        "```",
        "",
        "## Top 10 trials",
        "",
        "| rank | trial | model | objective | f1_macro | accuracy | kappa |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for rank, trial in enumerate(sorted(study.trials, key=lambda item: item.value if item.value is not None else -np.inf, reverse=True)[:10], start=1):
        top_trials_lines.append(
            f"| {rank} | {trial.number} | {trial.user_attrs.get('model')} | "
            f"{float(trial.value):.6f} | {float(trial.user_attrs.get('f1_macro')):.6f} | "
            f"{float(trial.user_attrs.get('accuracy')):.6f} | {float(trial.user_attrs.get('kappa')):.6f} |"
        )
    (output_dir / f"optuna_summary_{subset_name}.md").write_text("\n".join(top_trials_lines) + "\n", encoding="utf-8")

    print(f"Output directory: {output_dir}")
    print(f"Subset: {subset_name} | bands={len(selected_bands)} | total_features={len(feature_columns)}")
    print(f"Trials: {args.n_trials}")
    print(f"Best model: {best_model_name}")
    print(f"Accuracy: {float(best_scores['test_accuracy'].mean()):.6f}")
    print(f"F1-macro: {float(best_scores['test_f1_macro'].mean()):.6f}")
    print(f"Kappa: {float(best_scores['test_kappa'].mean()):.6f}")
    print("Best params:")
    print(json.dumps(best_trial.params, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
