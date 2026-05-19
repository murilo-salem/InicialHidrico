#!/usr/bin/env python3
"""Utilities for classification experiments driven by significance-ranked bands."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd


TARGET_SPECS: dict[str, dict[str, str]] = {
    "condicao": {
        "label_column": "target_condicao",
        "analysis_source": "cond",
        "display_name": "Condicao",
    },
    "condicao_genotipo": {
        "label_column": "target_condicao_genotipo",
        "analysis_source": "gen_cond",
        "display_name": "Condicao x Genotipo",
    },
    "condicao_genotipo_turno": {
        "label_column": "target_condicao_genotipo_turno",
        "analysis_source": "gen_cond",
        "display_name": "Condicao x Genotipo x Turno",
    },
}


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def sanitize_token(value: str) -> str:
    token = re.sub(r"[^0-9A-Za-z]+", "_", str(value)).strip("_")
    return token or "value"


def sanitize_model_name(model_name: str) -> str:
    return sanitize_token(model_name)


def wavelength_to_band_column(wavelength_nm: int) -> str:
    return f"band_{int(wavelength_nm)}"


def band_column_to_wavelength(band_column: str) -> int:
    return int(str(band_column).split("_", 1)[1])


def ensure_turn_label(frame: pd.DataFrame) -> pd.Series:
    if "turnos_disponiveis" in frame.columns:
        labels = frame["turnos_disponiveis"].fillna("").astype(str).str.strip()
        return labels.where(labels != "", "unico")
    if "n_turnos_agregados" in frame.columns:
        return np.where(
            pd.to_numeric(frame["n_turnos_agregados"], errors="coerce").fillna(1).to_numpy() > 1,
            "manha + tarde",
            "unico",
        )
    return pd.Series(["unico"] * len(frame), index=frame.index, dtype="object")


def prepare_targets(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    prepared["turno_label"] = ensure_turn_label(prepared)
    prepared["target_condicao"] = prepared["condicao"].astype(str)
    prepared["target_condicao_genotipo"] = (
        prepared["condicao"].astype(str) + "|" + prepared["cultivar"].astype(str)
    )
    prepared["target_condicao_genotipo_turno"] = (
        prepared["condicao"].astype(str)
        + "|"
        + prepared["cultivar"].astype(str)
        + "|"
        + prepared["turno_label"].astype(str)
    )
    return prepared


def build_group_labels(labels: pd.Series, replicates: pd.Series) -> np.ndarray:
    return (
        labels.astype(str).str.strip() + "_B" + replicates.astype(str).str.strip()
    ).to_numpy(dtype=object)


def resolve_class_order(target_name: str, labels: Iterable[str]) -> list[str]:
    unique_values = sorted({str(value) for value in labels})
    if target_name == "condicao" and {"IRR", "NIRR"}.issubset(unique_values):
        return ["NIRR", "IRR"]
    return unique_values


def available_band_columns(frame: pd.DataFrame) -> list[str]:
    return sorted(
        [column for column in frame.columns if str(column).startswith("band_")],
        key=band_column_to_wavelength,
    )


def _read_top5_consolidated(significance_dir: Path) -> pd.DataFrame:
    consolidated = significance_dir / "TOP5_TODOS_DIAS_TURNOS_CONSOLIDADO.csv"
    if consolidated.exists():
        table = pd.read_csv(consolidated)
    else:
        parts: list[pd.DataFrame] = []
        for path in sorted(significance_dir.glob("TOP5_*.csv")):
            if path.name == "TOP5_TODOS_DIAS_TURNOS_CONSOLIDADO.csv":
                continue
            parts.append(pd.read_csv(path))
        if not parts:
            raise FileNotFoundError(
                f"Nenhum arquivo TOP5 foi encontrado em {significance_dir}."
            )
        table = pd.concat(parts, ignore_index=True)

    required = {"analysis", "rank", "wavelength_nm", "q_FDR_BH"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(
            f"Arquivo consolidado de significancia sem colunas obrigatorias: {sorted(missing)}"
        )

    normalized = table.copy()
    normalized["analysis"] = normalized["analysis"].astype(str).str.strip()
    normalized["rank"] = pd.to_numeric(normalized["rank"], errors="coerce")
    normalized["wavelength_nm"] = pd.to_numeric(normalized["wavelength_nm"], errors="coerce")
    normalized["q_FDR_BH"] = pd.to_numeric(normalized["q_FDR_BH"], errors="coerce")
    normalized = normalized.dropna(subset=["analysis", "rank", "wavelength_nm"]).reset_index(drop=True)
    normalized["rank"] = normalized["rank"].astype(int)
    normalized["wavelength_int"] = normalized["wavelength_nm"].round().astype(int)
    return normalized


def _resolve_band_mapping(
    wavelength_nm: int,
    band_lookup: dict[int, str],
    band_wavelengths: list[int],
) -> tuple[str, int, bool]:
    if wavelength_nm in band_lookup:
        return band_lookup[wavelength_nm], wavelength_nm, True
    nearest = min(band_wavelengths, key=lambda candidate: (abs(candidate - wavelength_nm), candidate))
    return band_lookup[nearest], nearest, False


def select_recurrent_bands(
    significance_dir: Path,
    analysis_source: str,
    top_n: int,
    band_columns: list[str],
) -> pd.DataFrame:
    table = _read_top5_consolidated(significance_dir)
    subset = table.loc[table["analysis"] == analysis_source].copy()
    if subset.empty:
        raise ValueError(
            f"Nenhuma linha de analise={analysis_source!r} foi encontrada em {significance_dir}."
        )

    grouped = (
        subset.groupby("wavelength_int", as_index=False)
        .agg(
            frequency=("wavelength_int", "size"),
            mean_rank=("rank", "mean"),
            best_rank=("rank", "min"),
            min_q=("q_FDR_BH", "min"),
        )
        .sort_values(
            ["frequency", "mean_rank", "best_rank", "min_q", "wavelength_int"],
            ascending=[False, True, True, True, True],
        )
        .reset_index(drop=True)
    )

    if not band_columns:
        raise ValueError("A lista de bandas disponiveis no dataset esta vazia.")

    band_lookup = {band_column_to_wavelength(column): column for column in band_columns}
    band_wavelengths = sorted(band_lookup)
    selected_rows: list[dict[str, object]] = []
    used_columns: set[str] = set()

    for _, row in grouped.iterrows():
        band_column, resolved_wavelength, exact_match = _resolve_band_mapping(
            int(row["wavelength_int"]),
            band_lookup,
            band_wavelengths,
        )
        if band_column in used_columns:
            continue
        used_columns.add(band_column)
        selected_rows.append(
            {
                "analysis_source": analysis_source,
                "rank_recurrence": len(selected_rows) + 1,
                "wavelength_nm": int(row["wavelength_int"]),
                "frequency": int(row["frequency"]),
                "mean_rank": float(row["mean_rank"]),
                "best_rank": int(row["best_rank"]),
                "min_q": float(row["min_q"]) if np.isfinite(row["min_q"]) else np.nan,
                "band_column": band_column,
                "resolved_wavelength_nm": int(resolved_wavelength),
                "resolved_exact_match": bool(exact_match),
            }
        )
        if len(selected_rows) == top_n:
            break

    if len(selected_rows) < top_n:
        raise ValueError(
            f"So foi possivel selecionar {len(selected_rows)} bandas unicas para {analysis_source}; "
            f"eram esperadas {top_n}."
        )

    return pd.DataFrame(selected_rows)


def build_model_library(num_classes: int, random_state: int = 42) -> dict[str, object]:
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    from xgboost import XGBClassifier

    if num_classes < 2:
        raise ValueError("A classificacao exige pelo menos 2 classes.")

    if num_classes == 2:
        xgb_model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            n_estimators=400,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            random_state=random_state,
            n_jobs=1,
        )
    else:
        xgb_model = XGBClassifier(
            objective="multi:softprob",
            num_class=num_classes,
            eval_metric="mlogloss",
            n_estimators=400,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            random_state=random_state,
            n_jobs=1,
        )

    return {
        "Random Forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=750,
                        class_weight="balanced_subsample",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "SVM (RBF)": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    SVC(
                        kernel="rbf",
                        class_weight="balanced",
                        random_state=random_state,
                        probability=True,
                    ),
                ),
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
                ("model", xgb_model),
            ]
        ),
    }


@dataclass
class EvaluationArtifacts:
    metrics_row: dict[str, object]
    per_class_df: pd.DataFrame
    predictions_df: pd.DataFrame
    confusion_df: pd.DataFrame
    confusion_matrix: np.ndarray


def evaluate_model_cv(
    model_name: str,
    model: object,
    frame: pd.DataFrame,
    feature_columns: list[str],
    label_column: str,
    target_name: str,
    class_names: list[str],
    groups: np.ndarray,
    n_splits: int,
    train_augmenter: Callable[[pd.DataFrame, np.ndarray, int], tuple[pd.DataFrame, np.ndarray]] | None = None,
) -> EvaluationArtifacts:
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
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    splits = list(splitter.split(x, y, groups))

    oof_predictions = np.empty_like(y)
    oof_probabilities = np.full((len(frame), len(class_names)), np.nan, dtype=np.float64)
    fold_rows: list[dict[str, float]] = []
    irr_index = class_names.index("IRR") if "IRR" in class_names else None

    for fold_index, (train_idx, test_idx) in enumerate(splits, start=1):
        fitted = clone(model)
        x_train = x.iloc[train_idx]
        x_test = x.iloc[test_idx]
        y_train = y[train_idx]
        y_test = y[test_idx]
        if train_augmenter is not None:
            x_train, y_train = train_augmenter(x_train, y_train, fold_index)
        fitted.fit(x_train, y_train)
        y_pred = fitted.predict(x_test)
        y_prob = fitted.predict_proba(x_test)

        oof_predictions[test_idx] = y_pred
        oof_probabilities[test_idx, : y_prob.shape[1]] = y_prob

        row = {
            "fold": float(fold_index),
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred)),
            "f1_macro": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
            "kappa": float(cohen_kappa_score(y_test, y_pred)),
        }
        if len(class_names) == 2 and irr_index is not None:
            row["roc_auc"] = float(roc_auc_score((y_test == irr_index).astype(int), y_prob[:, irr_index]))
        else:
            row["roc_auc"] = np.nan
        fold_rows.append(row)

    fold_df = pd.DataFrame(fold_rows)
    metric_row = {
        "target": target_name,
        "model": model_name,
        "classes": "; ".join(class_names),
        "n_classes": int(len(class_names)),
        "n_samples": int(len(frame)),
        "n_groups": int(pd.Index(groups).nunique()),
        "cv_splits": int(len(splits)),
        "n_bandas": int(len(feature_columns)),
        "bandas": "|".join(feature_columns),
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
        for column in [
            "cultivar",
            "condicao",
            "data_coleta_iso",
            "dia",
            "replicata",
            "bloco",
            "turnos_disponiveis",
            "turno_label",
        ]
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
        predictions_df[f"prob_{sanitize_token(class_name)}"] = oof_probabilities[:, class_index]

    matrix = confusion_matrix(y, oof_predictions, labels=np.arange(len(class_names)))
    confusion_df = pd.DataFrame(matrix, index=class_names, columns=class_names).reset_index(names="real")
    confusion_df.insert(0, "target", target_name)
    confusion_df.insert(1, "model", model_name)

    return EvaluationArtifacts(
        metrics_row=metric_row,
        per_class_df=per_class_df,
        predictions_df=predictions_df,
        confusion_df=confusion_df,
        confusion_matrix=matrix,
    )


def choose_best_model(metrics_df: pd.DataFrame) -> pd.Series:
    ranking = metrics_df.sort_values(
        ["f1_macro_media", "balanced_accuracy_media", "accuracy_media", "kappa_media"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    return ranking.iloc[0]


def plot_confusion_matrix(
    confusion: np.ndarray,
    class_names: list[str],
    title: str,
    output_path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 6.0))
    image = ax.imshow(confusion, cmap="Blues", vmin=0)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks(np.arange(len(class_names)))
    ax.set_yticks(np.arange(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predito")
    ax.set_ylabel("Real")
    ax.set_title(title)
    for row_index in range(confusion.shape[0]):
        for col_index in range(confusion.shape[1]):
            ax.text(
                col_index,
                row_index,
                str(int(confusion[row_index, col_index])),
                ha="center",
                va="center",
                color="#111827",
                fontsize=9,
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
