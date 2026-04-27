#!/usr/bin/env python3
"""Train and evaluate classifiers for cultivar x condition classes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import cohen_kappa_score, confusion_matrix, f1_score, make_scorer, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict, cross_validate
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

from pipeline_utils import (
    CLASS_LABELS,
    INDEX_COLUMNS,
    assign_class_labels,
    ensure_dirs,
    get_paths,
    save_figure,
    set_plot_style,
    write_csv,
    write_excel_workbook,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa a classificacao 6x6 para cultivar x condicao.")
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
    return parser.parse_args()


def build_model_library(num_classes: int) -> dict[str, Pipeline]:
    return {
        "Random Forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=750,
                        class_weight="balanced_subsample",
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "SVM (RBF)": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", SVC(kernel="rbf", class_weight="balanced", random_state=42)),
            ]
        ),
        "LDA": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
            ]
        ),
        "k-NN (k=5)": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", KNeighborsClassifier(n_neighbors=5, metric="euclidean")),
            ]
        ),
        "XGBoost": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    XGBClassifier(
                        objective="multi:softprob",
                        num_class=num_classes,
                        eval_metric="mlogloss",
                        n_estimators=400,
                        max_depth=4,
                        learning_rate=0.05,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        reg_lambda=1.0,
                        random_state=42,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
    }


def select_classification_bands(boruta_df: pd.DataFrame) -> tuple[list[str], str]:
    confirmed = sorted(boruta_df.loc[boruta_df["status"] == "Confirmado", "banda"].unique())
    if confirmed:
        return confirmed, "confirmadas"
    tentative = sorted(boruta_df.loc[boruta_df["status"] == "Tentativa", "banda"].unique())
    if tentative:
        return tentative, "tentativas"
    fallback = (
        boruta_df.sort_values(["ranking", "comprimento_onda_nm"], ascending=[True, True])["banda"].drop_duplicates().head(20).tolist()
    )
    return fallback, "top20_ranking"


def plot_confusion_matrix(cm: np.ndarray, labels: list[str], output_path: Path) -> None:
    set_plot_style()
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, linewidths=0.5, ax=ax)
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.set_title("Confusion Matrix - Cultivar x condicao")
    save_figure(fig, output_path)


def plot_feature_importance(importance_df: pd.DataFrame, output_path: Path) -> None:
    set_plot_style()
    top_df = importance_df.head(20).copy().sort_values("importancia")
    colors = ["#2e7d32" if value == "indice" else "#1565c0" for value in top_df["tipo"]]
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(top_df["feature_legenda"], top_df["importancia"], color=colors)
    ax.set_xlabel("Importancia")
    ax.set_ylabel("Feature")
    ax.set_title("Top 20 - Importancia de variaveis (Random Forest)")
    save_figure(fig, output_path)


def main() -> None:
    args = parse_args()
    paths = get_paths()
    ensure_dirs(paths)
    input_path = args.input or (paths.processed_dir / "replicatas_bloco_dia.csv")
    boruta_path = args.boruta or (paths.table_dir / "lambdas_boruta_por_dia.csv")

    df = assign_class_labels(pd.read_csv(input_path))
    boruta_df = pd.read_csv(boruta_path)

    selected_bands, selection_source = select_classification_bands(boruta_df)
    features = list(selected_bands) + INDEX_COLUMNS
    feature_manifest_df = pd.DataFrame(
        {
            "feature": features,
            "tipo": ["banda"] * len(selected_bands) + ["indice"] * len(INDEX_COLUMNS),
            "feature_legenda": [feature.replace("band_", "") + " nm" for feature in selected_bands] + INDEX_COLUMNS,
            "origem_bandas": [selection_source] * len(selected_bands) + ["indices_fixos"] * len(INDEX_COLUMNS),
        }
    )

    class_order = ["A", "B", "C", "D", "E", "F"]
    class_labels_display = [
        CLASS_LABELS[("EMB48", "IRR")][1],
        CLASS_LABELS[("EMB48", "NIRR")][1],
        CLASS_LABELS[("BR16", "IRR")][1],
        CLASS_LABELS[("BR16", "NIRR")][1],
        CLASS_LABELS[("CD202", "IRR")][1],
        CLASS_LABELS[("CD202", "NIRR")][1],
    ]

    X = df[features].copy()
    y = pd.Categorical(df["classe"], categories=class_order, ordered=True).codes
    groups = df["grupo_cv"].to_numpy()
    min_groups = int(df.groupby("classe")["grupo_cv"].nunique().min())
    n_splits = min(5, max(2, min_groups))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    splits = list(splitter.split(X, y, groups))

    scorers = {
        "accuracy": "accuracy",
        "f1_macro": make_scorer(f1_score, average="macro"),
        "kappa": make_scorer(cohen_kappa_score),
    }

    model_rows: list[dict[str, object]] = []
    model_library = build_model_library(num_classes=len(class_order))
    for model_name, model in model_library.items():
        scores = cross_validate(model, X, y, cv=splits, scoring=scorers, n_jobs=1)
        model_rows.append(
            {
                "modelo": model_name,
                "accuracy_media": float(scores["test_accuracy"].mean()),
                "accuracy_std": float(scores["test_accuracy"].std(ddof=1)),
                "f1_macro_media": float(scores["test_f1_macro"].mean()),
                "f1_macro_std": float(scores["test_f1_macro"].std(ddof=1)),
                "kappa_media": float(scores["test_kappa"].mean()),
                "kappa_std": float(scores["test_kappa"].std(ddof=1)),
                "n_features": int(len(features)),
                "n_splits_cv": int(n_splits),
                "origem_bandas": selection_source,
            }
        )

    model_scores_df = pd.DataFrame(model_rows).sort_values(["f1_macro_media", "accuracy_media", "kappa_media"], ascending=[False, False, False]).reset_index(drop=True)
    best_model_name = model_scores_df.iloc[0]["modelo"]
    best_model = model_library[best_model_name]

    y_pred = cross_val_predict(best_model, X, y, cv=splits, n_jobs=1)
    cm = confusion_matrix(y, y_pred, labels=np.arange(len(class_order)))
    plot_confusion_matrix(cm, class_labels_display, paths.figure_dir / "confusion_matrix.png")

    precision, recall, f1_values, support = precision_recall_fscore_support(
        y,
        y_pred,
        labels=np.arange(len(class_order)),
        zero_division=0,
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

    rf_imputer = SimpleImputer(strategy="median")
    X_imputed = rf_imputer.fit_transform(X)
    rf_model = RandomForestClassifier(
        n_estimators=1000,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    rf_model.fit(X_imputed, y)
    importance_df = feature_manifest_df.copy()
    importance_df["importancia"] = rf_model.feature_importances_
    importance_df = importance_df.sort_values("importancia", ascending=False).reset_index(drop=True)
    plot_feature_importance(importance_df, paths.figure_dir / "rf_feature_importance_top20.png")

    confusion_df = pd.DataFrame(cm, index=class_labels_display, columns=class_labels_display).reset_index().rename(columns={"index": "Classe verdadeira"})
    prediction_df = df[
        [
            "cultivar",
            "condicao",
            "classe",
            "classe_legenda",
            "data_coleta_iso",
            "dia",
            "replicata",
            "bloco",
        ]
    ].copy()
    prediction_df["classe_predita"] = [class_order[int(value)] for value in y_pred]
    prediction_df["classe_predita_legenda"] = [class_labels_display[int(value)] for value in y_pred]

    write_csv(model_scores_df, paths.table_dir / "escores_modelos.csv")
    write_csv(per_class_df, paths.table_dir / "escores_por_classe.csv")
    write_csv(confusion_df, paths.table_dir / "confusion_matrix.csv")
    write_csv(importance_df, paths.table_dir / "rf_feature_importance.csv")
    write_csv(feature_manifest_df, paths.table_dir / "features_classificacao.csv")
    write_csv(prediction_df, paths.table_dir / "predicoes_classificacao_cv.csv")
    write_excel_workbook(
        paths.table_dir / "resultados_classificacao.xlsx",
        {
            "escores_modelos": model_scores_df,
            "escores_por_classe": per_class_df,
            "confusion_matrix": confusion_df,
            "rf_importancia": importance_df,
            "features": feature_manifest_df,
        },
    )
    print(model_scores_df.to_string(index=False))


if __name__ == "__main__":
    main()
