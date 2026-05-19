#!/usr/bin/env python3
"""Binary irrigation classification using the diversified spectral subset."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    make_scorer,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CONDITION_POSITIVE = "IRR"
CONDITION_NEGATIVE = "NIRR"
DISPLAY_LABELS = {
    CONDITION_NEGATIVE: "Nao irrigado",
    CONDITION_POSITIVE: "Irrigado",
}


@dataclass(frozen=True)
class BinaryEvaluationResult:
    analysis_id: str
    analysis_label: str
    scope: str
    cultivar: str | None
    bands: list[str]
    metrics_row: pd.Series
    per_class_df: pd.DataFrame
    predictions_df: pd.DataFrame
    confusion_df: pd.DataFrame
    coefficient_df: pd.DataFrame
    group_counts_df: pd.DataFrame
    confusion_matrix_array: np.ndarray


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    default_table_dir = project_dir / "outputs" / "tabelas" / "classificacao_irrigacao_bandas_diversificadas"
    default_figure_dir = project_dir / "outputs" / "figuras" / "classificacao_irrigacao_bandas_diversificadas"
    parser = argparse.ArgumentParser(
        description="Classificacao binaria IRR vs NIRR usando as bandas diversificadas selecionadas."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
        help="CSV base de replicatas por bloco e dia.",
    )
    parser.add_argument(
        "--bands-csv",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "diversificacao_bandas_correlacao" / "subset_recomendado_bandas.csv",
        help="CSV com as bandas selecionadas.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_table_dir,
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


def load_bands(path: Path) -> list[str]:
    bands_df = pd.read_csv(path, encoding="utf-8-sig")
    if "band" not in bands_df.columns:
        raise ValueError(f"Arquivo de bandas sem coluna 'band': {path}")
    bands = bands_df["band"].dropna().astype(str).drop_duplicates().tolist()
    if not bands:
        raise ValueError(f"Nenhuma banda encontrada em {path}")
    return bands


def build_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        ]
    )


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["target_label"] = frame["condicao"].astype(str)
    frame["target_binary"] = (frame["target_label"] == CONDITION_POSITIVE).astype(int)
    frame["grupo_cv"] = (
        frame["cultivar"].astype(str)
        + "_"
        + frame["condicao"].astype(str)
        + "_B"
        + frame["replicata"].astype(str)
    )
    return frame


def plot_confusion_matrix(cm: np.ndarray, output_path: Path, title: str) -> None:
    set_plot_style()
    fig, ax = plt.subplots(figsize=(5.5, 4.6))
    image = ax.imshow(cm, cmap="Blues", vmin=0)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels([DISPLAY_LABELS[CONDITION_NEGATIVE], DISPLAY_LABELS[CONDITION_POSITIVE]])
    ax.set_yticklabels([DISPLAY_LABELS[CONDITION_NEGATIVE], DISPLAY_LABELS[CONDITION_POSITIVE]])
    ax.set_xlabel("Predito")
    ax.set_ylabel("Real")
    ax.set_title(title)

    for row_index in range(cm.shape[0]):
        for col_index in range(cm.shape[1]):
            ax.text(
                col_index,
                row_index,
                str(int(cm[row_index, col_index])),
                ha="center",
                va="center",
                color="#111827",
                fontsize=11,
            )

    save_figure(fig, output_path)


def write_summary(
    path: Path,
    *,
    result: BinaryEvaluationResult,
) -> None:
    metrics_row = result.metrics_row
    group_counts = result.group_counts_df
    lines = [
        f"# {result.analysis_label}",
        "",
        "## Configuracao",
        "",
        "- modelo: `LDA (solver=lsqr, shrinkage=auto)`",
        f"- bandas: `{', '.join(result.bands)}`",
        f"- escopo: `{result.scope}`",
    ]
    if result.cultivar is not None:
        lines.append(f"- genotipo: `{result.cultivar}`")
    lines.extend(
        [
            f"- n amostras: `{int(metrics_row['n_amostras'])}`",
            f"- n grupos CV: `{int(metrics_row['n_grupos'])}`",
            f"- n folds: `{int(metrics_row['n_splits_cv'])}`",
            "",
            "## Metricas CV",
            "",
            f"- accuracy: `{metrics_row['accuracy_media']:.6f} +- {metrics_row['accuracy_std']:.6f}`",
            f"- balanced accuracy: `{metrics_row['balanced_accuracy_media']:.6f} +- {metrics_row['balanced_accuracy_std']:.6f}`",
            f"- F1 irrigado: `{metrics_row['f1_irrigado_media']:.6f} +- {metrics_row['f1_irrigado_std']:.6f}`",
            f"- F1 macro: `{metrics_row['f1_macro_media']:.6f} +- {metrics_row['f1_macro_std']:.6f}`",
            f"- ROC AUC: `{metrics_row['roc_auc_media']:.6f} +- {metrics_row['roc_auc_std']:.6f}`",
            f"- kappa: `{metrics_row['kappa_media']:.6f} +- {metrics_row['kappa_std']:.6f}`",
            "",
            "## Distribuicao de grupos por classe",
            "",
            "| condicao | n amostras | n grupos |",
            "| --- | ---: | ---: |",
        ]
    )
    for row in group_counts.itertuples(index=False):
        lines.append(f"| {row.condicao} | {row.n_amostras} | {row.n_grupos} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_comparison_summary(path: Path, *, bands: list[str], overall_result: BinaryEvaluationResult, genotype_df: pd.DataFrame) -> None:
    overall = overall_result.metrics_row
    lines = [
        "# Comparativo IRR vs NIRR por genotipo",
        "",
        f"- bandas: `{', '.join(bands)}`",
        f"- resultado global F1-macro: `{overall['f1_macro_media']:.6f}`",
        f"- resultado global accuracy: `{overall['accuracy_media']:.6f}`",
        "",
        "| genotipo | n amostras | n grupos | folds | accuracy | balanced acc | F1 irrigado | F1 macro | AUC | kappa |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in genotype_df.itertuples(index=False):
        lines.append(
            f"| {row.cultivar} | {row.n_amostras} | {row.n_grupos} | {row.n_splits_cv} | "
            f"{row.accuracy_media:.4f} | {row.balanced_accuracy_media:.4f} | {row.f1_irrigado_media:.4f} | "
            f"{row.f1_macro_media:.4f} | {row.roc_auc_media:.4f} | {row.kappa_media:.4f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_binary_classification(
    frame: pd.DataFrame,
    *,
    bands: list[str],
    analysis_id: str,
    analysis_label: str,
    scope: str,
    cultivar: str | None,
) -> BinaryEvaluationResult:
    X = frame[bands].copy()
    y = frame["target_binary"].to_numpy(dtype=int)
    groups = frame["grupo_cv"].to_numpy()

    group_counts = (
        frame.groupby("target_label")
        .agg(n_amostras=("target_label", "size"), n_grupos=("grupo_cv", "nunique"))
        .reset_index()
        .rename(columns={"target_label": "condicao"})
        .sort_values("condicao")
    )

    min_groups = int(group_counts["n_grupos"].min())
    n_splits = min(5, max(2, min_groups))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    splits = list(splitter.split(X, y, groups))

    pipeline = build_pipeline()
    scorers = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "f1_irrigado": make_scorer(f1_score, pos_label=1),
        "f1_macro": make_scorer(f1_score, average="macro"),
        "roc_auc": "roc_auc",
        "kappa": make_scorer(cohen_kappa_score),
    }
    scores = cross_validate(pipeline, X, y, cv=splits, scoring=scorers, n_jobs=1)

    y_pred = cross_val_predict(pipeline, X, y, cv=splits, n_jobs=1)
    y_prob = cross_val_predict(pipeline, X, y, cv=splits, method="predict_proba", n_jobs=1)[:, 1]
    cm = confusion_matrix(y, y_pred, labels=[0, 1])
    precision, recall, f1_values, support = precision_recall_fscore_support(
        y,
        y_pred,
        labels=[0, 1],
        zero_division=0,
    )

    metrics_row = pd.Series(
        {
            "analysis_id": analysis_id,
            "analysis_label": analysis_label,
            "scope": scope,
            "cultivar": cultivar,
            "modelo": "LDA",
            "n_bandas": int(len(bands)),
            "bandas": "|".join(bands),
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
            "accuracy_cv_pred": float(accuracy_score(y, y_pred)),
            "balanced_accuracy_cv_pred": float(balanced_accuracy_score(y, y_pred)),
            "roc_auc_cv_pred": float(roc_auc_score(y, y_prob)),
        }
    )

    per_class_df = pd.DataFrame(
        {
            "analysis_id": analysis_id,
            "analysis_label": analysis_label,
            "scope": scope,
            "cultivar": cultivar,
            "classe": [DISPLAY_LABELS[CONDITION_NEGATIVE], DISPLAY_LABELS[CONDITION_POSITIVE]],
            "classe_codigo": [0, 1],
            "precision": precision,
            "recall": recall,
            "f1": f1_values,
            "support": support,
        }
    )

    predictions_df = frame[
        ["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco", "grupo_cv"]
    ].copy()
    predictions_df["analysis_id"] = analysis_id
    predictions_df["analysis_label"] = analysis_label
    predictions_df["scope"] = scope
    predictions_df["y_true"] = y
    predictions_df["y_pred"] = y_pred
    predictions_df["prob_irrigado"] = y_prob
    predictions_df["predicao_label"] = np.where(predictions_df["y_pred"] == 1, CONDITION_POSITIVE, CONDITION_NEGATIVE)
    predictions_df["acertou"] = predictions_df["y_true"] == predictions_df["y_pred"]

    confusion_df = pd.DataFrame(
        cm,
        index=[DISPLAY_LABELS[CONDITION_NEGATIVE], DISPLAY_LABELS[CONDITION_POSITIVE]],
        columns=[DISPLAY_LABELS[CONDITION_NEGATIVE], DISPLAY_LABELS[CONDITION_POSITIVE]],
    ).reset_index(names="real")
    confusion_df.insert(0, "analysis_id", analysis_id)
    confusion_df.insert(1, "analysis_label", analysis_label)
    confusion_df.insert(2, "scope", scope)
    confusion_df.insert(3, "cultivar", cultivar)

    pipeline.fit(X, y)
    lda_model = pipeline.named_steps["model"]
    coefficient_df = pd.DataFrame(
        {
            "analysis_id": analysis_id,
            "analysis_label": analysis_label,
            "scope": scope,
            "cultivar": cultivar,
            "feature": bands,
            "coeficiente_lda": lda_model.coef_.ravel(),
            "abs_coeficiente_lda": np.abs(lda_model.coef_.ravel()),
        }
    ).sort_values("abs_coeficiente_lda", ascending=False)

    return BinaryEvaluationResult(
        analysis_id=analysis_id,
        analysis_label=analysis_label,
        scope=scope,
        cultivar=cultivar,
        bands=bands,
        metrics_row=metrics_row,
        per_class_df=per_class_df,
        predictions_df=predictions_df,
        confusion_df=confusion_df,
        coefficient_df=coefficient_df,
        group_counts_df=group_counts,
        confusion_matrix_array=cm,
    )


def persist_result(result: BinaryEvaluationResult, *, output_dir: Path, figure_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    write_csv(pd.DataFrame([result.metrics_row]), output_dir / "metricas_classificacao_irrigacao.csv")
    write_csv(result.per_class_df, output_dir / "metricas_por_classe.csv")
    write_csv(result.confusion_df, output_dir / "matriz_confusao.csv")
    write_csv(result.predictions_df, output_dir / "predicoes_cv.csv")
    write_csv(result.coefficient_df, output_dir / "coeficientes_lda.csv")
    write_summary(output_dir / "resumo_classificacao_irrigacao.md", result=result)
    plot_confusion_matrix(
        result.confusion_matrix_array,
        figure_dir / "matriz_confusao_irrigacao.png",
        title=f"Matriz de confusao - {result.analysis_label}",
    )


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    figure_dir = args.figure_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    bands = load_bands(args.bands_csv)
    raw_df = pd.read_csv(args.input)
    missing_bands = [band for band in bands if band not in raw_df.columns]
    if missing_bands:
        raise ValueError(f"Bandas ausentes no dataset: {missing_bands}")

    frame = prepare_frame(raw_df)

    results: list[BinaryEvaluationResult] = []

    overall_result = evaluate_binary_classification(
        frame,
        bands=bands,
        analysis_id="global",
        analysis_label="Classificacao binaria IRR vs NIRR",
        scope="global",
        cultivar=None,
    )
    persist_result(overall_result, output_dir=output_dir, figure_dir=figure_dir)
    results.append(overall_result)

    cultivar_results: list[BinaryEvaluationResult] = []
    for cultivar in sorted(frame["cultivar"].dropna().astype(str).unique()):
        cultivar_frame = frame[frame["cultivar"].astype(str) == cultivar].copy()
        cultivar_result = evaluate_binary_classification(
            cultivar_frame,
            bands=bands,
            analysis_id=f"genotipo_{cultivar}",
            analysis_label=f"Classificacao binaria IRR vs NIRR - {cultivar}",
            scope="por_genotipo",
            cultivar=cultivar,
        )
        persist_result(
            cultivar_result,
            output_dir=output_dir / "por_genotipo" / cultivar,
            figure_dir=figure_dir / "por_genotipo" / cultivar,
        )
        cultivar_results.append(cultivar_result)
        results.append(cultivar_result)

    metrics_df = pd.DataFrame([result.metrics_row for result in results])
    per_class_all_df = pd.concat([result.per_class_df for result in results], ignore_index=True)
    confusion_all_df = pd.concat([result.confusion_df for result in results], ignore_index=True)
    coefficients_all_df = pd.concat([result.coefficient_df for result in results], ignore_index=True)
    predictions_all_df = pd.concat([result.predictions_df for result in results], ignore_index=True)

    genotype_metrics_df = pd.DataFrame([result.metrics_row for result in cultivar_results]).sort_values(
        ["f1_macro_media", "accuracy_media"],
        ascending=[False, False],
    )

    write_csv(metrics_df, output_dir / "metricas_classificacao_irrigacao_todas_analises.csv")
    write_csv(genotype_metrics_df, output_dir / "metricas_classificacao_irrigacao_por_genotipo.csv")
    write_csv(per_class_all_df, output_dir / "metricas_por_classe_todas_analises.csv")
    write_csv(confusion_all_df, output_dir / "matrizes_confusao_todas_analises.csv")
    write_csv(coefficients_all_df, output_dir / "coeficientes_lda_todas_analises.csv")
    write_csv(predictions_all_df, output_dir / "predicoes_cv_todas_analises.csv")
    write_comparison_summary(
        output_dir / "resumo_comparativo_por_genotipo.md",
        bands=bands,
        overall_result=overall_result,
        genotype_df=genotype_metrics_df,
    )

    print(f"Output directory: {output_dir}")
    print(f"Figure directory: {figure_dir}")
    print(f"Bands used: {', '.join(bands)}")
    print(
        "Global | "
        f"ACC={overall_result.metrics_row['accuracy_media']:.6f} | "
        f"BAC={overall_result.metrics_row['balanced_accuracy_media']:.6f} | "
        f"F1_IRR={overall_result.metrics_row['f1_irrigado_media']:.6f} | "
        f"F1_MACRO={overall_result.metrics_row['f1_macro_media']:.6f} | "
        f"AUC={overall_result.metrics_row['roc_auc_media']:.6f} | "
        f"KAPPA={overall_result.metrics_row['kappa_media']:.6f}"
    )
    for result in cultivar_results:
        print(
            f"{result.cultivar} | "
            f"ACC={result.metrics_row['accuracy_media']:.6f} | "
            f"BAC={result.metrics_row['balanced_accuracy_media']:.6f} | "
            f"F1_IRR={result.metrics_row['f1_irrigado_media']:.6f} | "
            f"F1_MACRO={result.metrics_row['f1_macro_media']:.6f} | "
            f"AUC={result.metrics_row['roc_auc_media']:.6f} | "
            f"KAPPA={result.metrics_row['kappa_media']:.6f}"
        )


if __name__ == "__main__":
    main()
