#!/usr/bin/env python3
"""Binary irrigation classification (IRR vs NIRR) per day × genotype using 6 spectral features."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    make_scorer,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict, cross_validate
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

DISPLAY_LABELS = {
    "NIRR": "Nao irrigado",
    "IRR": "Irrigado",
}
IRR_LABEL = "IRR"
NIRR_LABEL = "NIRR"


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    default_output_dir = project_dir / "outputs" / "tabelas" / "classificacao_irrigacao_por_dia_genotipo"
    default_figure_dir = project_dir / "outputs" / "figuras" / "classificacao_irrigacao_por_dia_genotipo"
    parser = argparse.ArgumentParser(
        description="Classificacao binaria IRR vs NIRR por dia e genotipo usando bandas 1200, 1450, 1950, 970, 670 e NDRE."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
        help="CSV base de replicatas por bloco e dia.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help="Diretorio para tabelas e resumos.",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=default_figure_dir,
        help="Diretorio para figuras.",
    )
    return parser.parse_args()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def set_plot_style() -> None:
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 300
    plt.rcParams["axes.titlesize"] = 13
    plt.rcParams["axes.labelsize"] = 11


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def calculate_ndre(df: pd.DataFrame) -> pd.Series:
    nir = df["band_800"].values
    rededge = df["band_720"].values
    return (nir - rededge) / (nir + rededge)


def build_feature_columns() -> list[str]:
    return ["band_1200", "band_1451", "band_1951", "band_970", "band_670"]


def build_model_library(num_classes: int = 2) -> dict[str, Pipeline]:
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
                ("model", SVC(kernel="rbf", class_weight="balanced", random_state=42, probability=True)),
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
                        objective="binary:logistic",
                        eval_metric="logloss",
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


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["target_binary"] = (frame["condicao"] == IRR_LABEL).astype(int)
    frame["grupo_cv"] = (
        frame["cultivar"].astype(str) + "_" + frame["condicao"].astype(str) + "_B" + frame["replicata"].astype(str)
    )
    frame["NDRE"] = calculate_ndre(frame)
    return frame


def plot_confusion_matrix(cm: np.ndarray, output_path: Path, title: str) -> None:
    set_plot_style()
    fig, ax = plt.subplots(figsize=(5.5, 4.6))
    image = ax.imshow(cm, cmap="Blues", vmin=0)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels([DISPLAY_LABELS[NIRR_LABEL], DISPLAY_LABELS[IRR_LABEL]])
    ax.set_yticklabels([DISPLAY_LABELS[NIRR_LABEL], DISPLAY_LABELS[IRR_LABEL]])
    ax.set_xlabel("Predito")
    ax.set_ylabel("Real")
    ax.set_title(title)
    for row_index in range(cm.shape[0]):
        for col_index in range(cm.shape[1]):
            ax.text(col_index, row_index, str(int(cm[row_index, col_index])), ha="center", va="center", color="#111827", fontsize=11)
    save_figure(fig, output_path)


def evaluate_single_model(
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: np.ndarray,
    groups: np.ndarray,
    n_splits: int,
) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    splits = list(splitter.split(X, y, groups))
    scorers = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "f1_irrigado": make_scorer(f1_score, pos_label=1),
        "f1_macro": make_scorer(f1_score, average="macro"),
        "roc_auc": "roc_auc",
        "kappa": make_scorer(cohen_kappa_score),
    }
    scores = cross_validate(pipeline, X, y, cv=splits, scoring=scorers, n_jobs=-1)
    y_pred = cross_val_predict(pipeline, X, y, cv=splits, n_jobs=1)
    y_prob = cross_val_predict(pipeline, X, y, cv=splits, method="predict_proba", n_jobs=1)[:, 1]
    return scores, y_pred, y_prob, splits


def run_classification(
    frame: pd.DataFrame,
    dia: str,
    cultivar: str,
    features: list[str],
    output_dir: Path,
    figure_dir: Path,
) -> list[dict]:
    analysis_id = f"{dia}_{cultivar}"
    analysis_label = f"{dia} - {cultivar}"

    X = frame[features].copy()
    y = frame["target_binary"].to_numpy(dtype=int)
    groups = frame["grupo_cv"].to_numpy()

    group_counts = (
        frame.groupby("condicao")
        .agg(n_amostras=("condicao", "size"), n_grupos=("grupo_cv", "nunique"))
        .reset_index()
        .sort_values("condicao")
    )

    min_groups = int(group_counts["n_grupos"].min())
    n_splits = min(5, max(2, min_groups))

    models = build_model_library()
    results = []

    for model_name, pipeline in models.items():
        scores, y_pred, y_prob, splits = evaluate_single_model(pipeline, X, y, groups, n_splits)

        cm = confusion_matrix(y, y_pred, labels=[0, 1])
        precision, recall, f1_values, support = precision_recall_fscore_support(y, y_pred, labels=[0, 1], zero_division=0)

        metrics = {
            "analysis_id": analysis_id,
            "analysis_label": analysis_label,
            "dia": dia,
            "cultivar": cultivar,
            "modelo": model_name,
            "n_bandas": len(features),
            "bandas": "|".join(features),
            "n_amostras": int(len(frame)),
            "n_grupos": int(frame["grupo_cv"].nunique()),
            "n_splits_cv": int(n_splits),
            "accuracy_media": float(scores["test_accuracy"].mean()),
            "accuracy_std": float(scores["test_accuracy"].std(ddof=1)),
            "balanced_accuracy_media": float(scores["test_balanced_accuracy"].mean()),
            "balanced_accuracy_std": float(scores["test_balanced_accuracy"].std(ddof=1)),
            "f1_irrigado_media": float(scores["test_f1_irrigado"].mean()),
            "f1_irrigado_std": float(scores["test_f1_irrigado"].std(ddof=1)),
            "f1_macro_media": float(scores["test_f1_macro"].mean()),
            "f1_macro_std": float(scores["test_f1_macro"].std(ddof=1)),
            "roc_auc_media": float(scores["test_roc_auc"].mean()),
            "roc_auc_std": float(scores["test_roc_auc"].std(ddof=1)),
            "kappa_media": float(scores["test_kappa"].mean()),
            "kappa_std": float(scores["test_kappa"].std(ddof=1)),
        }
        results.append(metrics)

        per_class_df = pd.DataFrame(
            {
                "analysis_id": analysis_id,
                "analysis_label": analysis_label,
                "dia": dia,
                "cultivar": cultivar,
                "modelo": model_name,
                "classe": [DISPLAY_LABELS[NIRR_LABEL], DISPLAY_LABELS[IRR_LABEL]],
                "classe_codigo": [0, 1],
                "precision": precision,
                "recall": recall,
                "f1": f1_values,
                "support": support,
            }
        )

        predictions_df = frame[["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco", "grupo_cv"]].copy()
        predictions_df["analysis_id"] = analysis_id
        predictions_df["analysis_label"] = analysis_label
        predictions_df["modelo"] = model_name
        predictions_df["y_true"] = y
        predictions_df["y_pred"] = y_pred
        predictions_df["prob_irrigado"] = y_prob
        predictions_df["acertou"] = predictions_df["y_true"] == predictions_df["y_pred"]

        confusion_df = pd.DataFrame(
            cm,
            index=[DISPLAY_LABELS[NIRR_LABEL], DISPLAY_LABELS[IRR_LABEL]],
            columns=[DISPLAY_LABELS[NIRR_LABEL], DISPLAY_LABELS[IRR_LABEL]],
        ).reset_index(names="real")
        confusion_df.insert(0, "analysis_id", analysis_id)
        confusion_df.insert(1, "analysis_label", analysis_label)
        confusion_df.insert(2, "dia", dia)
        confusion_df.insert(3, "cultivar", cultivar)
        confusion_df.insert(4, "modelo", model_name)

        sub_dir = output_dir / dia / cultivar
        fig_sub_dir = figure_dir / dia / cultivar
        sub_dir.mkdir(parents=True, exist_ok=True)
        fig_sub_dir.mkdir(parents=True, exist_ok=True)

        model_clean = model_name.replace(" ", "_").replace("(", "").replace(")", "").replace("=", "").replace(",", "")
        write_csv(pd.DataFrame([metrics]), sub_dir / f"metricas_{model_clean}.csv")
        write_csv(per_class_df, sub_dir / f"metricas_por_classe_{model_clean}.csv")
        write_csv(predictions_df, sub_dir / f"predicoes_cv_{model_clean}.csv")
        write_csv(confusion_df, sub_dir / f"matriz_confusao_{model_clean}.csv")

        plot_confusion_matrix(cm, fig_sub_dir / f"matriz_confusao_{model_clean}.png", f"{analysis_label} - {model_name}")

    metrics_df = pd.DataFrame(results)
    write_csv(metrics_df, output_dir / dia / cultivar / "metricas_todas_modelos.csv")

    return results


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    figure_dir = args.figure_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    raw_features = build_feature_columns()
    raw_df = pd.read_csv(args.input)
    missing = [f for f in raw_features if f not in raw_df.columns]
    if missing:
        raise ValueError(f"Bandas ausentes no dataset: {missing}")
    for col in ["band_800", "band_720"]:
        if col not in raw_df.columns:
            raise ValueError(f"Banda necessaria para NDRE ausente: {col}")
    features = raw_features + ["NDRE"]

    frame = prepare_frame(raw_df)

    dias = sorted(frame["dia"].dropna().astype(str).unique())
    cultivares = sorted(frame["cultivar"].dropna().astype(str).unique())

    all_results = []
    best_results = []

    print(f"\n{'='*80}")
    print("CLASSIFICACAO IRR vs NIRR - POR DIA E GENOTIPO")
    print(f"Features: {features}")
    print(f"{'='*80}\n")

    for dia in dias:
        for cultivar in cultivares:
            subset = frame[(frame["dia"] == dia) & (frame["cultivar"] == cultivar)].copy()

            if len(subset) < 4:
                print(f"[{dia}][{cultivar}] Pulando - apenas {len(subset)} amostras")
                continue

            n_irr = (subset["condicao"] == IRR_LABEL).sum()
            n_nirr = (subset["condicao"] == NIRR_LABEL).sum()

            if n_irr < 2 or n_nirr < 2:
                print(f"[{dia}][{cultivar}] Pulando - IRR={n_irr}, NIRR={n_nirr}")
                continue

            print(f"[{dia}][{cultivar}] Amostras: {len(subset)} (IRR={n_irr}, NIRR={n_nirr})")

            results = run_classification(subset, dia, cultivar, features, output_dir, figure_dir)
            all_results.extend(results)

            metrics_df = pd.DataFrame(results)
            best_idx = metrics_df["f1_macro_media"].idxmax()
            best_row = metrics_df.loc[best_idx]
            best_results.append(best_row)

            print(
                f"   -> Best: {best_row['modelo']} | "
                f"ACC={best_row['accuracy_media']:.4f} | "
                f"BAC={best_row['balanced_accuracy_media']:.4f} | "
                f"F1_MACRO={best_row['f1_macro_media']:.4f} | "
                f"AUC={best_row['roc_auc_media']:.4f} | "
                f"KAPPA={best_row['kappa_media']:.4f}"
            )

    all_metrics_df = pd.DataFrame(all_results)
    write_csv(all_metrics_df, output_dir / "metricas_todas_analises.csv")

    best_metrics_df = pd.DataFrame(best_results)
    write_csv(best_metrics_df, output_dir / "melhor_modelo_cada_analise.csv")

    pivoted = all_metrics_df.pivot_table(
        index=["dia", "cultivar", "n_amostras", "n_grupos"],
        columns="modelo",
        values=["accuracy_media", "balanced_accuracy_media", "f1_macro_media", "roc_auc_media", "kappa_media"],
    )
    pivoted.columns = ["_".join(col).strip() for col in pivoted.columns.values]
    pivoted = pivoted.reset_index()
    write_csv(pivoted, output_dir / "comparativo_todos_modelos.csv")

    lines = [
        "# Classificacao IRR vs NIRR - Por Dia e Genotipo\n",
        f"## Features: {', '.join(features)}\n",
        "| dia | cultivar | n_amostras | melhor_modelo | accuracy | balanced_acc | f1_macro | roc_auc | kappa |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in best_metrics_df.sort_values(["dia", "cultivar"]).iterrows():
        lines.append(
            f"| {row['dia']} | {row['cultivar']} | {row['n_amostras']} | {row['modelo']} | "
            f"{row['accuracy_media']:.4f} | {row['balanced_accuracy_media']:.4f} | "
            f"{row['f1_macro_media']:.4f} | {row['roc_auc_media']:.4f} | {row['kappa_media']:.4f} |"
        )

    summary_path = output_dir / "resumo_comparativo.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n{'='*80}")
    print(f"OUTPUT: {output_dir}")
    print(f"FIGURES: {figure_dir}")
    print(f"{'='*80}")
    print("\nResumen global:")
    for _, row in best_metrics_df.sort_values(["dia", "cultivar"]).iterrows():
        print(
            f"  {row['dia']} | {row['cultivar']} | {row['modelo']} | "
            f"F1={row['f1_macro_media']:.4f} | ACC={row['accuracy_media']:.4f}"
        )


if __name__ == "__main__":
    main()