#!/usr/bin/env python3
"""Run the 6-class LDA classification with a user-provided spectral subset."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.impute import SimpleImputer
from sklearn.metrics import cohen_kappa_score, confusion_matrix, f1_score, make_scorer, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

INDEX_COLUMNS = ["NDVI", "EVI", "WBI", "PRI", "SIPI", "REP"]
CLASS_LABELS = {
    ("EMB48", "IRR"): ("A", "A (EMB48 IRR)"),
    ("EMB48", "NIRR"): ("B", "B (EMB48 NIRR)"),
    ("BR16", "IRR"): ("C", "C (BR16 IRR)"),
    ("BR16", "NIRR"): ("D", "D (BR16 NIRR)"),
    ("CD202", "IRR"): ("E", "E (CD202 IRR)"),
    ("CD202", "NIRR"): ("F", "F (CD202 NIRR)"),
}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    parser = argparse.ArgumentParser(
        description="Executa a classificacao 6x6 com um subconjunto explicito de bandas."
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
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "classificacao_subset_bandas",
        help="Diretorio de saida para tabelas e figura.",
    )
    return parser.parse_args()


def lda_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        ]
    )


def assign_class_labels(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    labels = frame.apply(lambda row: CLASS_LABELS[(row["cultivar"], row["condicao"])], axis=1)
    frame["classe"] = [item[0] for item in labels]
    frame["classe_legenda"] = [item[1] for item in labels]
    frame["grupo_cv"] = frame["classe"] + "_B" + frame["replicata"].astype(str)
    return frame


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


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = assign_class_labels(pd.read_csv(args.input))
    subset_df = pd.read_csv(args.subset_csv, encoding="utf-8-sig")
    selected_bands = subset_df["band"].tolist()
    subset_name = str(subset_df["subset"].iloc[0]) if not subset_df.empty else args.subset_csv.stem

    features = list(selected_bands) + INDEX_COLUMNS
    X = df[features].copy()
    class_order = ["A", "B", "C", "D", "E", "F"]
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
    scores = cross_validate(lda_pipeline(), X, y, cv=splits, scoring=scorers, n_jobs=1)

    y_pred = cross_val_predict(lda_pipeline(), X, y, cv=splits, n_jobs=1)
    class_labels_display = [
        CLASS_LABELS[("EMB48", "IRR")][1],
        CLASS_LABELS[("EMB48", "NIRR")][1],
        CLASS_LABELS[("BR16", "IRR")][1],
        CLASS_LABELS[("BR16", "NIRR")][1],
        CLASS_LABELS[("CD202", "IRR")][1],
        CLASS_LABELS[("CD202", "NIRR")][1],
    ]
    cm = confusion_matrix(y, y_pred, labels=np.arange(len(class_order)))
    plot_confusion_matrix(
        cm,
        class_labels_display,
        output_dir / f"confusion_matrix_{subset_name}.png",
        f"Cultivar x condicao ({subset_name})",
    )

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
    confusion_df = pd.DataFrame(cm, index=class_labels_display, columns=class_labels_display).reset_index().rename(
        columns={"index": "Classe verdadeira"}
    )
    score_df = pd.DataFrame(
        [
            {
                "subset": subset_name,
                "n_bands": int(len(selected_bands)),
                "n_features_total": int(len(features)),
                "n_splits_cv": int(n_splits),
                "accuracy_media": float(scores["test_accuracy"].mean()),
                "accuracy_std": float(scores["test_accuracy"].std(ddof=1)),
                "f1_macro_media": float(scores["test_f1_macro"].mean()),
                "f1_macro_std": float(scores["test_f1_macro"].std(ddof=1)),
                "kappa_media": float(scores["test_kappa"].mean()),
                "kappa_std": float(scores["test_kappa"].std(ddof=1)),
            }
        ]
    )
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

    write_csv(score_df, output_dir / f"lda_scores_{subset_name}.csv")
    write_csv(confusion_df, output_dir / f"confusion_matrix_{subset_name}.csv")
    write_csv(per_class_df, output_dir / f"per_class_scores_{subset_name}.csv")
    write_csv(prediction_df, output_dir / f"predictions_{subset_name}.csv")

    print(f"Output directory: {output_dir}")
    print(f"Subset: {subset_name} | bands={len(selected_bands)} | total_features={len(features)}")
    print(f"Accuracy: {float(scores['test_accuracy'].mean()):.6f}")
    print(f"F1-macro: {float(scores['test_f1_macro'].mean()):.6f}")
    print(f"Kappa: {float(scores['test_kappa'].mean()):.6f}")
    print("Confusion matrix:")
    for row in cm.tolist():
        print(",".join(str(int(value)) for value in row))


if __name__ == "__main__":
    main()
