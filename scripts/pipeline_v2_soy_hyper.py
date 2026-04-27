#!/usr/bin/env python3
"""Version 2 hyperspectral pipeline for soybean datasets."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist, squareform
from scipy.stats import f_oneway, pearsonr
from sklearn.base import clone
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_selection import RFE, mutual_info_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier

from generate_descriptive_stats import (
    META_COLUMNS,
    iter_sheet_rows,
    normalize_condition_code,
    normalize_genotype_token,
)


EXPECTED_WAVELENGTHS = np.arange(350, 2501, dtype=np.int32)
DEFAULT_OUTPUT_DIR = Path("outputs_v2")
LOGGER = logging.getLogger("soy_hyper_v2")


@dataclass
class SpectralDataset:
    source_path: Path
    source_kind: str
    sample_ids: list[str]
    row_numbers: list[int]
    raw_block: list[str]
    raw_genotype: list[str]
    raw_condition: list[str]
    raw_date: list[str]
    raw_turno: list[str]
    block: list[str]
    genotype: list[str]
    condition: list[str]
    date_raw: list[str]
    date_iso: list[str]
    turno: list[str]
    wavelengths: np.ndarray
    x: np.ndarray
    normalized_metadata_path: Path


@dataclass
class ClassificationResult:
    target_name: str
    classes: list[str]
    metrics_rows: list[dict[str, object]]
    confusion: np.ndarray
    predictions: np.ndarray
    y_true: np.ndarray


@dataclass
class PLSRResult:
    best_components: int
    cv_rows: list[dict[str, object]]
    metrics: dict[str, float]
    coefficients: np.ndarray
    vip: np.ndarray
    y_pred: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the v2 hyperspectral pipeline.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("base_dados_unificada.xlsx"),
        help="Input dataset (.xlsx or .csv).",
    )
    parser.add_argument(
        "--metadata-csv",
        type=Path,
        default=Path("dados_processados_soft/metadados_normalizados_soft.csv"),
        help="Normalized metadata table used for safe alignment.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where pipeline outputs will be written.",
    )
    parser.add_argument(
        "--classification-targets",
        type=str,
        default="condition,turno",
        help="Comma-separated targets to classify: condition, turno, genotype.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--cv-splits", type=int, default=5, help="Requested CV splits.")
    parser.add_argument(
        "--max-plsr-components",
        type=int,
        default=20,
        help="Maximum PLS components evaluated for the binary target.",
    )
    parser.add_argument(
        "--band-selection-candidate-n",
        type=int,
        default=250,
        help="Number of top bands used for expensive band-selection steps.",
    )
    parser.add_argument(
        "--hvi-candidate-bands",
        type=int,
        default=80,
        help="Number of candidate bands used for HVI pair search.",
    )
    parser.add_argument("--skip-hvi", action="store_true", help="Skip HVI pair search.")
    parser.add_argument("--skip-plsr", action="store_true", help="Skip optional PLSR.")
    return parser.parse_args()


def setup_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(output_dir / "pipeline_v2.log", encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(path: Path, header: list[str], rows: Iterable[Iterable[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow(list(row))


def write_dict_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, default=_json_default)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def load_normalized_metadata(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Normalized metadata file is empty.")
    required = {
        "row_number",
        "nomenclaura",
        "bloco_normalizado",
        "genotipo_normalizado",
        "condicao_normalizada",
        "data_coleta_raw",
        "data_coleta_iso",
        "turno",
    }
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(f"Normalized metadata file is missing columns: {sorted(missing)}")
    return rows


def load_input_rows(input_path: Path) -> tuple[list[str], list[list[str | None]], str]:
    if input_path.suffix.lower() == ".xlsx":
        headers: list[str] | None = None
        rows: list[list[str | None]] = []
        for row_number, values in iter_sheet_rows(input_path):
            if row_number == 1:
                headers = ["" if value is None else str(value) for value in values]
            else:
                rows.append([None if value is None else str(value) for value in values])
        if headers is None:
            raise ValueError("Workbook does not contain a header row.")
        return headers, rows, "xlsx"
    if input_path.suffix.lower() == ".csv":
        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            headers = next(reader)
            rows = [[None if value == "" else value for value in row] for row in reader]
        return headers, rows, "csv"
    raise ValueError(f"Unsupported input format: {input_path.suffix}")


def validate_headers(headers: list[str]) -> list[int]:
    if len(headers) < 7:
        raise ValueError("Input file has fewer columns than expected.")
    if headers[:6] != META_COLUMNS:
        raise ValueError(
            "Input file metadata columns do not match the expected structure: "
            f"{headers[:6]!r}"
        )
    spectral_headers = headers[6:]
    wavelengths = []
    for header in spectral_headers:
        try:
            wavelengths.append(int(str(header)))
        except ValueError as exc:
            raise ValueError(f"Non-numeric spectral header found: {header!r}") from exc
    if wavelengths != list(EXPECTED_WAVELENGTHS):
        raise ValueError("Spectral bands are not contiguous from 350 to 2500 nm.")
    return wavelengths


def load_and_align_dataset(input_path: Path, metadata_path: Path) -> SpectralDataset:
    LOGGER.info("Loading normalized metadata from %s", metadata_path)
    metadata_rows = load_normalized_metadata(metadata_path)
    headers, rows, source_kind = load_input_rows(input_path)
    wavelengths = np.asarray(validate_headers(headers), dtype=np.int32)
    if len(rows) != len(metadata_rows):
        raise ValueError(
            f"Row count mismatch: input has {len(rows)} samples, metadata has {len(metadata_rows)}."
        )

    n_samples = len(rows)
    n_bands = len(wavelengths)
    x = np.empty((n_samples, n_bands), dtype=np.float64)

    sample_ids: list[str] = []
    row_numbers: list[int] = []
    raw_block: list[str] = []
    raw_genotype: list[str] = []
    raw_condition: list[str] = []
    raw_date: list[str] = []
    raw_turno: list[str] = []
    block: list[str] = []
    genotype: list[str] = []
    condition: list[str] = []
    date_raw: list[str] = []
    date_iso: list[str] = []
    turno: list[str] = []

    for index, (row, meta) in enumerate(zip(rows, metadata_rows, strict=True)):
        if row[0] != meta["nomenclaura"]:
            raise ValueError(
                "Unsafe merge prevented: nomenclaura mismatch at row "
                f"{index + 2}: {row[0]!r} != {meta['nomenclaura']!r}"
            )
        if int(meta["row_number"]) != index + 2:
            raise ValueError(
                "Unsafe merge prevented: row_number mismatch at row "
                f"{index + 2}: metadata reports {meta['row_number']!r}"
            )
        sample_ids.append(row[0])
        row_numbers.append(index + 2)
        raw_block.append(str(row[1]))
        raw_genotype.append(str(row[2]))
        raw_condition.append(str(row[3]))
        raw_date.append(str(row[4]))
        raw_turno.append(str(row[5]))
        block.append(meta["bloco_normalizado"])
        genotype.append(meta["genotipo_normalizado"])
        condition.append(meta["condicao_normalizada"])
        date_raw.append(meta["data_coleta_raw"])
        date_iso.append(meta["data_coleta_iso"])
        turno.append(meta["turno"])
        try:
            x[index, :] = np.asarray([float(value) for value in row[6:]], dtype=np.float64)
        except ValueError as exc:
            raise ValueError(f"Non-numeric spectral value at row {index + 2}") from exc

    return SpectralDataset(
        source_path=input_path,
        source_kind=source_kind,
        sample_ids=sample_ids,
        row_numbers=row_numbers,
        raw_block=raw_block,
        raw_genotype=raw_genotype,
        raw_condition=raw_condition,
        raw_date=raw_date,
        raw_turno=raw_turno,
        block=block,
        genotype=genotype,
        condition=condition,
        date_raw=date_raw,
        date_iso=date_iso,
        turno=turno,
        wavelengths=wavelengths,
        x=x,
        normalized_metadata_path=metadata_path,
    )


def build_group_labels(dataset: SpectralDataset) -> np.ndarray:
    return np.asarray(
        [
            f"{date}|{genotype}|{condition}"
            for date, genotype, condition in zip(
                dataset.date_iso, dataset.genotype, dataset.condition, strict=True
            )
        ],
        dtype=object,
    )


def validate_dataset_structure(dataset: SpectralDataset, validation_dir: Path) -> dict[str, object]:
    LOGGER.info("Running structural validation")
    validation_dir = ensure_dir(validation_dir)
    group_labels = build_group_labels(dataset)
    counts = Counter(group_labels.tolist())
    rows = []
    for group, count in sorted(counts.items()):
        date_iso, genotype, condition = group.split("|")
        rows.append([date_iso, genotype, condition, count])
    write_csv(
        validation_dir / "amostras_por_grupo_v2.csv",
        ["data_coleta_iso", "genotipo_normalizado", "condicao_normalizada", "n_amostras"],
        rows,
    )
    summary_rows = [
        ["input_path", str(dataset.source_path)],
        ["source_kind", dataset.source_kind],
        ["samples", len(dataset.sample_ids)],
        ["bands", len(dataset.wavelengths)],
        ["wavelength_min", int(dataset.wavelengths.min())],
        ["wavelength_max", int(dataset.wavelengths.max())],
        ["missing_spectral_values", int(np.isnan(dataset.x).sum())],
        ["unique_dates", len(set(dataset.date_iso))],
        ["unique_genotypes", len(set(dataset.genotype))],
        ["unique_conditions", len(set(dataset.condition))],
        ["unique_turnos", len(set(dataset.turno))],
        ["groups", len(counts)],
        ["min_group_size", int(min(counts.values()))],
        ["max_group_size", int(max(counts.values()))],
    ]
    write_csv(validation_dir / "validation_summary_v2.csv", ["metric", "value"], summary_rows)
    report = {
        "input_path": str(dataset.source_path),
        "metadata_path": str(dataset.normalized_metadata_path),
        "source_kind": dataset.source_kind,
        "samples": len(dataset.sample_ids),
        "bands": len(dataset.wavelengths),
        "wavelength_min": int(dataset.wavelengths.min()),
        "wavelength_max": int(dataset.wavelengths.max()),
        "groups": len(counts),
        "group_size_min": int(min(counts.values())),
        "group_size_max": int(max(counts.values())),
        "dates": sorted(set(dataset.date_iso)),
        "genotypes": sorted(set(dataset.genotype)),
        "conditions": sorted(set(dataset.condition)),
        "turnos": sorted(set(dataset.turno)),
    }
    write_json(validation_dir / "validation_report_v2.json", report)
    return report


def group_stats(dataset: SpectralDataset) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, key in enumerate(
        zip(dataset.date_iso, dataset.genotype, dataset.condition, strict=True)
    ):
        groups[key].append(index)
    rows: list[dict[str, object]] = []
    for (date_iso, genotype, condition), indices in sorted(groups.items()):
        subset = dataset.x[indices]
        mean = subset.mean(axis=0)
        std = subset.std(axis=0, ddof=1) if subset.shape[0] > 1 else np.zeros_like(mean)
        sem = std / math.sqrt(subset.shape[0]) if subset.shape[0] > 0 else np.zeros_like(mean)
        with np.errstate(divide="ignore", invalid="ignore"):
            cv = np.where(np.isclose(mean, 0.0), np.nan, (std / mean) * 100.0)
        rows.append(
            {
                "data_coleta_iso": date_iso,
                "genotipo_normalizado": genotype,
                "condicao_normalizada": condition,
                "n_amostras": subset.shape[0],
                "mean": mean,
                "std": std,
                "sem": sem,
                "cv": cv,
            }
        )
    return rows


def export_group_statistics(dataset: SpectralDataset, output_dir: Path) -> dict[str, Path]:
    output_dir = ensure_dir(output_dir)
    stats_rows = group_stats(dataset)
    bands = [str(int(w)) for w in dataset.wavelengths]
    mean_rows = []
    std_rows = []
    sem_rows = []
    cv_rows = []
    for row in stats_rows:
        base = [
            row["data_coleta_iso"],
            row["genotipo_normalizado"],
            row["condicao_normalizada"],
            row["n_amostras"],
        ]
        mean_rows.append(base + row["mean"].tolist())
        std_rows.append(base + row["std"].tolist())
        sem_rows.append(base + row["sem"].tolist())
        cv_rows.append(base + row["cv"].tolist())
    header = ["data_coleta_iso", "genotipo_normalizado", "condicao_normalizada", "n_amostras"] + bands
    write_csv(output_dir / "descriptive_mean_by_group_v2.csv", header, mean_rows)
    write_csv(output_dir / "descriptive_std_by_group_v2.csv", header, std_rows)
    write_csv(output_dir / "descriptive_sem_by_group_v2.csv", header, sem_rows)
    write_csv(output_dir / "descriptive_cv_by_group_v2.csv", header, cv_rows)
    write_csv(
        output_dir / "group_counts_v2.csv",
        ["data_coleta_iso", "genotipo_normalizado", "condicao_normalizada", "n_amostras"],
        [
            [
                row["data_coleta_iso"],
                row["genotipo_normalizado"],
                row["condicao_normalizada"],
                row["n_amostras"],
            ]
            for row in stats_rows
        ],
    )
    return {
        "mean": output_dir / "descriptive_mean_by_group_v2.csv",
        "std": output_dir / "descriptive_std_by_group_v2.csv",
        "sem": output_dir / "descriptive_sem_by_group_v2.csv",
        "cv": output_dir / "descriptive_cv_by_group_v2.csv",
        "counts": output_dir / "group_counts_v2.csv",
    }


def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    adjusted = np.full_like(p_values, np.nan, dtype=np.float64)
    finite_mask = np.isfinite(p_values)
    finite_values = p_values[finite_mask]
    if finite_values.size == 0:
        return adjusted
    order = np.argsort(finite_values)
    ordered = finite_values[order]
    ranks = np.arange(1, ordered.size + 1, dtype=np.float64)
    adjusted_sorted = np.minimum.accumulate((ordered[::-1] * ordered.size / ranks[::-1]))[::-1]
    adjusted_sorted = np.clip(adjusted_sorted, 0.0, 1.0)
    restored = np.empty_like(finite_values)
    restored[order] = adjusted_sorted
    adjusted[finite_mask] = restored
    return adjusted


def band_anova(dataset: SpectralDataset, target: np.ndarray) -> tuple[list[dict[str, object]], np.ndarray]:
    classes = sorted(np.unique(target).tolist())
    class_groups = [dataset.x[target == cls] for cls in classes]
    rows: list[dict[str, object]] = []
    p_values = np.empty(dataset.x.shape[1], dtype=np.float64)
    for band_idx, wavelength in enumerate(dataset.wavelengths):
        samples = [group[:, band_idx] for group in class_groups]
        if any(group.size == 0 for group in samples):
            f_stat = np.nan
            p_value = np.nan
            eta_sq = np.nan
        else:
            f_stat, p_value = f_oneway(*samples)
            all_values = np.concatenate(samples)
            grand_mean = np.mean(all_values)
            ss_total = np.sum((all_values - grand_mean) ** 2)
            ss_between = sum(len(sample) * (np.mean(sample) - grand_mean) ** 2 for sample in samples)
            eta_sq = float(ss_between / ss_total) if ss_total > 0 else np.nan
        p_values[band_idx] = p_value
        rows.append(
            {
                "wavelength": int(wavelength),
                "anova_f": float(f_stat) if np.isfinite(f_stat) else np.nan,
                "p_value": float(p_value) if np.isfinite(p_value) else np.nan,
                "eta_squared": eta_sq,
            }
        )
    q_values = benjamini_hochberg(p_values)
    for row, q_value in zip(rows, q_values, strict=True):
        row["q_value"] = float(q_value) if np.isfinite(q_value) else np.nan
    return rows, q_values


def save_band_anova(output_dir: Path, dataset: SpectralDataset, target: np.ndarray) -> list[dict[str, object]]:
    output_dir = ensure_dir(output_dir)
    rows, _ = band_anova(dataset, target)
    rows_sorted = sorted(
        rows,
        key=lambda item: (
            np.nan_to_num(item["q_value"], nan=1.0),
            -np.nan_to_num(item["anova_f"], nan=0.0),
        ),
    )
    write_dict_csv(
        output_dir / "anova_by_band_v2.csv",
        rows_sorted,
        ["wavelength", "anova_f", "p_value", "q_value", "eta_squared"],
    )
    write_dict_csv(
        output_dir / "anova_top_100_v2.csv",
        rows_sorted[:100],
        ["wavelength", "anova_f", "p_value", "q_value", "eta_squared"],
    )
    return rows_sorted


def pca_analysis(dataset: SpectralDataset, output_dir: Path) -> dict[str, object]:
    output_dir = ensure_dir(output_dir)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(dataset.x)
    pca = PCA(n_components=5, random_state=0)
    scores = pca.fit_transform(x_scaled)
    loadings = pca.components_.T

    score_rows = []
    for idx in range(scores.shape[0]):
        score_rows.append(
            {
                "sample_id": dataset.sample_ids[idx],
                "data_coleta_iso": dataset.date_iso[idx],
                "genotipo_normalizado": dataset.genotype[idx],
                "condicao_normalizada": dataset.condition[idx],
                "turno": dataset.turno[idx],
                "PC1": float(scores[idx, 0]),
                "PC2": float(scores[idx, 1]),
                "PC3": float(scores[idx, 2]),
                "PC4": float(scores[idx, 3]),
                "PC5": float(scores[idx, 4]),
            }
        )
    write_dict_csv(
        output_dir / "pca_scores_v2.csv",
        score_rows,
        [
            "sample_id",
            "data_coleta_iso",
            "genotipo_normalizado",
            "condicao_normalizada",
            "turno",
            "PC1",
            "PC2",
            "PC3",
            "PC4",
            "PC5",
        ],
    )

    write_csv(
        output_dir / "pca_loadings_v2.csv",
        ["wavelength", "PC1", "PC2", "PC3", "PC4", "PC5"],
        [
            [int(wavelength)] + [float(loadings[idx, pc]) for pc in range(5)]
            for idx, wavelength in enumerate(dataset.wavelengths)
        ],
    )
    write_csv(
        output_dir / "pca_variance_v2.csv",
        ["component", "explained_variance_ratio", "cumulative_explained_variance"],
        [
            [
                f"PC{index + 1}",
                float(ratio),
                float(np.cumsum(pca.explained_variance_ratio_)[index]),
            ]
            for index, ratio in enumerate(pca.explained_variance_ratio_)
        ],
    )

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.plot(np.arange(1, 6), pca.explained_variance_ratio_[:5], marker="o", color="#0f766e")
    ax.set_xlabel("Component")
    ax.set_ylabel("Explained variance ratio")
    ax.set_title("PCA scree plot")
    ax.grid(alpha=0.2)
    fig.savefig(output_dir / "pca_scree_v2.png", dpi=180)
    plt.close(fig)

    color_map = {
        "condicao_normalizada": {"irrigado": "#0f766e", "nao_irrigado": "#c2410c"},
        "genotipo_normalizado": {"BR16": "#1d4ed8", "CD202": "#9333ea", "EMB48": "#0f766e"},
        "data_coleta_iso": {
            value: color
            for value, color in zip(
                sorted(set(dataset.date_iso)),
                ["#0f766e", "#2563eb", "#7c3aed", "#c2410c", "#b45309", "#111827"],
                strict=False,
            )
        },
    }
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    for ax, key, title in zip(
        axes,
        ["condicao_normalizada", "genotipo_normalizado", "data_coleta_iso"],
        ["Condition", "Genotype", "Collection date"],
        strict=True,
    ):
        labels = getattr(dataset, {
            "condicao_normalizada": "condition",
            "genotipo_normalizado": "genotype",
            "data_coleta_iso": "date_iso",
        }[key])
        palette = color_map[key]
        for label in sorted(set(labels)):
            mask = np.asarray([value == label for value in labels], dtype=bool)
            ax.scatter(
                scores[mask, 0],
                scores[mask, 1],
                s=10,
                alpha=0.65,
                color=palette.get(label, "#111827"),
                label=label,
            )
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.set_title(title)
        ax.grid(alpha=0.2)
        ax.legend(loc="best", fontsize=8, frameon=False)
    fig.savefig(output_dir / "pca_scatter_by_metadata_v2.png", dpi=180)
    plt.close(fig)

    return {
        "pca": pca,
        "scaler": scaler,
        "scores": scores,
        "loadings": loadings,
        "score_path": output_dir / "pca_scores_v2.csv",
        "loading_path": output_dir / "pca_loadings_v2.csv",
    }


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    return numerator / np.where(np.abs(denominator) < eps, np.nan, denominator)


def _eta_squared_by_factor(values: np.ndarray, labels: list[str]) -> float:
    groups = []
    for label in sorted(set(labels)):
        group = values[np.asarray([value == label for value in labels], dtype=bool)]
        if group.size:
            groups.append(group)
    if len(groups) < 2:
        return np.nan
    clean_groups = [group[np.isfinite(group)] for group in groups if np.isfinite(group).any()]
    if len(clean_groups) < 2:
        return np.nan
    all_values = np.concatenate(clean_groups)
    grand_mean = np.mean(all_values)
    ss_total = np.sum((all_values - grand_mean) ** 2)
    if np.isclose(ss_total, 0.0):
        return np.nan
    ss_between = sum(len(group) * (np.mean(group) - grand_mean) ** 2 for group in clean_groups)
    return float(ss_between / ss_total)


def compute_vegetation_indices(dataset: SpectralDataset, output_dir: Path) -> dict[str, object]:
    output_dir = ensure_dir(output_dir)
    w_to_i = {int(w): idx for idx, w in enumerate(dataset.wavelengths)}

    def band(wavelength: int) -> np.ndarray:
        return dataset.x[:, w_to_i[wavelength]]

    blue = band(470)
    green = band(550)
    red = band(670)
    red_edge = band(705)
    nir = band(800)
    swir1 = band(1240)
    swir2 = band(1650)

    indices = {
        "NDVI": _safe_divide(nir - red, nir + red),
        "GNDVI": _safe_divide(nir - green, nir + green),
        "NDRE": _safe_divide(nir - red_edge, nir + red_edge),
        "RVI": _safe_divide(nir, red),
        "DVI": nir - red,
        "SAVI": _safe_divide((nir - red) * 1.5, nir + red + 0.5),
        "OSAVI": _safe_divide((nir - red) * 1.16, nir + red + 0.16),
        "EVI": _safe_divide(2.5 * (nir - red), nir + 6.0 * red - 7.5 * blue + 1.0),
        "PRI": _safe_divide(band(531) - band(570), band(531) + band(570)),
        "CIgreen": _safe_divide(nir, green) - 1.0,
        "CIrededge": _safe_divide(nir, red_edge) - 1.0,
        "MSAVI": (
            2 * nir + 1 - np.sqrt(np.maximum((2 * nir + 1) ** 2 - 8 * (nir - red), 0.0))
        ) / 2,
        "NDSI": _safe_divide(swir1 - swir2, swir1 + swir2),
        "SIPI": _safe_divide(nir - blue, nir - red),
    }

    sample_rows = []
    for idx in range(dataset.x.shape[0]):
        row = {
            "sample_id": dataset.sample_ids[idx],
            "data_coleta_iso": dataset.date_iso[idx],
            "genotipo_normalizado": dataset.genotype[idx],
            "condicao_normalizada": dataset.condition[idx],
            "turno": dataset.turno[idx],
        }
        for col_name, values in indices.items():
            row[col_name] = float(values[idx])
        sample_rows.append(row)

    write_dict_csv(
        output_dir / "vegetation_indices_by_sample_v2.csv",
        sample_rows,
        [
            "sample_id",
            "data_coleta_iso",
            "genotipo_normalizado",
            "condicao_normalizada",
            "turno",
        ]
        + list(indices.keys()),
    )

    y_condition = np.asarray([1 if value == "irrigado" else 0 for value in dataset.condition], dtype=np.int32)
    summary_rows = []
    for index_name, values in indices.items():
        try:
            corr, p_value = pearsonr(np.nan_to_num(values, nan=np.nanmean(values)), y_condition)
        except Exception:
            corr, p_value = np.nan, np.nan
        summary_rows.append(
            {
                "index_name": index_name,
                "mean": float(np.nanmean(values)),
                "std": float(np.nanstd(values)),
                "min": float(np.nanmin(values)),
                "max": float(np.nanmax(values)),
                "corr_condition": float(corr) if np.isfinite(corr) else np.nan,
                "p_condition": float(p_value) if np.isfinite(p_value) else np.nan,
                "eta2_genotype": _eta_squared_by_factor(values, dataset.genotype),
                "eta2_turno": _eta_squared_by_factor(values, dataset.turno),
                "eta2_date": _eta_squared_by_factor(values, dataset.date_iso),
            }
        )

    write_dict_csv(
        output_dir / "vegetation_indices_summary_v2.csv",
        summary_rows,
        [
            "index_name",
            "mean",
            "std",
            "min",
            "max",
            "corr_condition",
            "p_condition",
            "eta2_genotype",
            "eta2_turno",
            "eta2_date",
        ],
    )
    return {
        "sample_path": output_dir / "vegetation_indices_by_sample_v2.csv",
        "summary_path": output_dir / "vegetation_indices_summary_v2.csv",
    }


def group_means_matrix(dataset: SpectralDataset) -> tuple[list[str], np.ndarray]:
    groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, key in enumerate(zip(dataset.date_iso, dataset.genotype, dataset.condition, strict=True)):
        groups[key].append(index)
    labels = []
    means = []
    for (date_iso, genotype, condition), indices in sorted(groups.items()):
        labels.append(f"{date_iso}|{genotype}|{condition}")
        means.append(dataset.x[indices].mean(axis=0))
    return labels, np.asarray(means, dtype=np.float64)


def hierarchical_clustering(dataset: SpectralDataset, output_dir: Path) -> dict[str, object]:
    output_dir = ensure_dir(output_dir)
    labels, means = group_means_matrix(dataset)
    scaler = StandardScaler()
    means_scaled = scaler.fit_transform(means)
    dist = pdist(means_scaled, metric="euclidean")
    linkage_matrix = linkage(dist, method="average")
    dist_matrix = squareform(dist)

    write_csv(
        output_dir / "hierarchical_distance_matrix_v2.csv",
        ["group"] + labels,
        [[labels[i]] + [float(value) for value in dist_matrix[i]] for i in range(len(labels))],
    )

    fig, ax = plt.subplots(figsize=(13, 6), constrained_layout=True)
    dendrogram(linkage_matrix, labels=labels, leaf_rotation=90, ax=ax, color_threshold=None)
    ax.set_title("Hierarchical clustering of group mean spectra")
    ax.set_ylabel("Euclidean distance")
    fig.savefig(output_dir / "hierarchical_dendrogram_v2.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 8), constrained_layout=True)
    image = ax.imshow(dist_matrix, cmap="viridis")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_title("Distance matrix between group mean spectra")
    fig.colorbar(image, ax=ax, shrink=0.8)
    fig.savefig(output_dir / "hierarchical_distance_heatmap_v2.png", dpi=180)
    plt.close(fig)

    return {"labels": labels, "means": means, "distance_matrix": dist_matrix, "linkage_matrix": linkage_matrix}


def build_group_for_target(dataset: SpectralDataset, target_name: str) -> list[str]:
    if target_name == "condition":
        return [
            f"{date}|{genotype}|{turno}"
            for date, genotype, turno in zip(dataset.date_iso, dataset.genotype, dataset.turno, strict=True)
        ]
    if target_name == "turno":
        return [
            f"{date}|{genotype}|{condition}"
            for date, genotype, condition in zip(
                dataset.date_iso, dataset.genotype, dataset.condition, strict=True
            )
        ]
    if target_name == "genotype":
        return [
            f"{date}|{condition}|{turno}"
            for date, condition, turno in zip(dataset.date_iso, dataset.condition, dataset.turno, strict=True)
        ]
    raise ValueError(f"Unsupported classification target: {target_name}")


def target_values(dataset: SpectralDataset, target_name: str) -> list[str]:
    if target_name == "condition":
        return dataset.condition
    if target_name == "turno":
        return dataset.turno
    if target_name == "genotype":
        return dataset.genotype
    raise ValueError(f"Unsupported classification target: {target_name}")


def make_classifier(name: str, seed: int):
    if name == "lr":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=5000,
                        class_weight="balanced",
                        random_state=seed,
                        solver="lbfgs",
                        l1_ratio=0.0,
                    ),
                ),
            ]
        )
    if name == "svm":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("clf", SVC(kernel="rbf", C=3.0, gamma="scale", class_weight="balanced")),
            ]
        )
    if name == "knn":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("clf", KNeighborsClassifier(n_neighbors=7, weights="distance")),
            ]
        )
    if name == "nb":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("clf", GaussianNB()),
            ]
        )
    if name == "dt":
        return DecisionTreeClassifier(random_state=seed, class_weight="balanced", min_samples_leaf=2)
    if name == "rf":
        return RandomForestClassifier(
            n_estimators=300,
            random_state=seed,
            class_weight="balanced_subsample",
            n_jobs=-1,
        )
    if name == "gboost":
        return GradientBoostingClassifier(random_state=seed)
    if name == "mlp":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    MLPClassifier(
                        hidden_layer_sizes=(64, 32),
                        random_state=seed,
                        max_iter=500,
                        early_stopping=True,
                    ),
                ),
            ]
        )
    raise ValueError(f"Unsupported classifier: {name}")


def classify_target(dataset: SpectralDataset, target_name: str, seed: int, cv_splits: int) -> ClassificationResult:
    labels = np.asarray(target_values(dataset, target_name), dtype=object)
    classes = sorted(np.unique(labels).tolist())
    y = np.asarray([classes.index(value) for value in labels], dtype=np.int32)
    groups = np.asarray(build_group_for_target(dataset, target_name), dtype=object)

    class_counts = Counter(labels.tolist())
    group_counts = Counter(groups.tolist())
    min_class = min(class_counts.values())
    effective_splits = max(2, min(cv_splits, min_class, len(group_counts)))

    if effective_splits >= 2 and min(len(set(groups.tolist())), min_class) >= effective_splits:
        splitter = StratifiedGroupKFold(n_splits=effective_splits, shuffle=True, random_state=seed)
        split_iter = list(splitter.split(dataset.x, y, groups))
    else:
        split_iter = list(StratifiedKFold(n_splits=min(cv_splits, min_class), shuffle=True, random_state=seed).split(dataset.x, y))

    model_names = ["lr", "svm", "knn", "nb", "dt", "rf", "gboost", "mlp"]
    metrics_rows: list[dict[str, object]] = []

    for model_name in model_names:
        model = make_classifier(model_name, seed)
        predictions = np.empty_like(y)
        probabilities = np.full((y.shape[0], len(classes)), np.nan, dtype=np.float64)
        for train_idx, test_idx in split_iter:
            fitted = clone(model)
            fitted.fit(dataset.x[train_idx], y[train_idx])
            preds = fitted.predict(dataset.x[test_idx])
            predictions[test_idx] = preds
            if hasattr(fitted, "predict_proba"):
                probs = fitted.predict_proba(dataset.x[test_idx])
                probabilities[test_idx, : probs.shape[1]] = probs

        accuracy = accuracy_score(y, predictions)
        precision_macro = precision_score(y, predictions, average="macro", zero_division=0)
        recall_macro = recall_score(y, predictions, average="macro", zero_division=0)
        f1_macro = f1_score(y, predictions, average="macro", zero_division=0)
        balanced = balanced_accuracy_score(y, predictions)
        try:
            if len(classes) == 2 and np.isfinite(probabilities[:, 1]).any():
                auc = roc_auc_score(y, probabilities[:, 1])
            else:
                auc = np.nan
        except Exception:
            auc = np.nan
        metrics_rows.append(
            {
                "target": target_name,
                "model": model_name,
                "accuracy": float(accuracy),
                "balanced_accuracy": float(balanced),
                "precision_macro": float(precision_macro),
                "recall_macro": float(recall_macro),
                "f1_macro": float(f1_macro),
                "roc_auc": float(auc) if np.isfinite(auc) else np.nan,
                "classes": "|".join(classes),
                "n_samples": int(y.shape[0]),
                "cv_splits": int(len(split_iter)),
            }
        )

    best_name = max(metrics_rows, key=lambda row: row["f1_macro"])["model"]
    best_model = make_classifier(str(best_name), seed)
    best_predictions = np.empty_like(y)
    for train_idx, test_idx in split_iter:
        fitted = clone(best_model)
        fitted.fit(dataset.x[train_idx], y[train_idx])
        best_predictions[test_idx] = fitted.predict(dataset.x[test_idx])

    cm = confusion_matrix(y, best_predictions, labels=np.arange(len(classes)))
    return ClassificationResult(
        target_name=target_name,
        classes=classes,
        metrics_rows=metrics_rows,
        confusion=cm,
        predictions=best_predictions,
        y_true=y,
    )


def export_classification_results(
    dataset: SpectralDataset,
    output_dir: Path,
    targets: list[str],
    seed: int,
    cv_splits: int,
) -> dict[str, object]:
    output_dir = ensure_dir(output_dir)
    all_metrics: list[dict[str, object]] = []
    results: dict[str, ClassificationResult] = {}
    for target in targets:
        LOGGER.info("Running classification target: %s", target)
        result = classify_target(dataset, target, seed, cv_splits)
        results[target] = result
        all_metrics.extend(result.metrics_rows)
        classes = result.classes
        write_csv(
            output_dir / f"confusion_matrix_{target}_v2.csv",
            [target] + classes,
            [[classes[row_idx]] + result.confusion[row_idx].tolist() for row_idx in range(len(classes))],
        )
        fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
        image = ax.imshow(result.confusion, cmap="Blues")
        ax.set_xticks(np.arange(len(classes)))
        ax.set_yticks(np.arange(len(classes)))
        ax.set_xticklabels(classes, rotation=45, ha="right")
        ax.set_yticklabels(classes)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Observed")
        ax.set_title(f"Confusion matrix: {target}")
        for i in range(result.confusion.shape[0]):
            for j in range(result.confusion.shape[1]):
                ax.text(j, i, int(result.confusion[i, j]), ha="center", va="center", color="black")
        fig.colorbar(image, ax=ax, shrink=0.8)
        fig.savefig(output_dir / f"confusion_matrix_{target}_v2.png", dpi=180)
        plt.close(fig)

    write_dict_csv(
        output_dir / "classification_metrics_v2.csv",
        all_metrics,
        [
            "target",
            "model",
            "accuracy",
            "balanced_accuracy",
            "precision_macro",
            "recall_macro",
            "f1_macro",
            "roc_auc",
            "classes",
            "n_samples",
            "cv_splits",
        ],
    )
    return {"metrics": output_dir / "classification_metrics_v2.csv", "results": results}


def calculate_vip_scores(pls: PLSRegression) -> np.ndarray:
    t = pls.x_scores_
    w = pls.x_weights_
    q = pls.y_loadings_
    p = w.shape[0]
    sum_sq = np.sum(t ** 2, axis=0) * np.sum(q ** 2, axis=1)
    total = np.sum(sum_sq)
    if np.isclose(total, 0.0):
        return np.zeros(p, dtype=np.float64)
    weights = (w ** 2) / np.sum(w ** 2, axis=0, keepdims=True)
    return np.sqrt(p * (weights @ sum_sq.reshape(-1, 1)).ravel() / total)


def plsr_binary_target(dataset: SpectralDataset, seed: int, max_components: int, cv_splits: int) -> PLSRResult | None:
    if len(set(dataset.condition)) != 2:
        return None
    y = np.asarray([1 if value == "irrigado" else 0 for value in dataset.condition], dtype=np.float64)
    groups = np.asarray(build_group_for_target(dataset, "condition"), dtype=object)
    class_counts = Counter(y.tolist())
    min_class = int(min(class_counts.values()))
    effective_splits = max(2, min(cv_splits, min_class, len(set(groups.tolist()))))
    if effective_splits < 2:
        return None

    split_iter = list(StratifiedGroupKFold(n_splits=effective_splits, shuffle=True, random_state=seed).split(dataset.x, y, groups))
    upper = min(max_components, dataset.x.shape[0] - 1, dataset.x.shape[1])
    cv_rows: list[dict[str, object]] = []
    best_components = 1
    best_rmse = float("inf")

    for n_components in range(1, upper + 1):
        predictions = np.empty_like(y)
        for train_idx, test_idx in split_iter:
            model = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("pls", PLSRegression(n_components=n_components, scale=False)),
                ]
            )
            model.fit(dataset.x[train_idx], y[train_idx])
            predictions[test_idx] = model.predict(dataset.x[test_idx]).ravel()
        rmse = float(np.sqrt(np.mean((y - predictions) ** 2)))
        ss_res = float(np.sum((y - predictions) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - (ss_res / ss_tot if ss_tot > 0 else np.nan)
        auc = roc_auc_score(y, predictions)
        accuracy = accuracy_score(y, (predictions >= 0.5).astype(int))
        cv_rows.append(
            {
                "n_components": int(n_components),
                "rmsecv": rmse,
                "r2cv": float(r2),
                "auc": float(auc),
                "accuracy": float(accuracy),
            }
        )
        if rmse < best_rmse:
            best_rmse = rmse
            best_components = n_components

    final_model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("pls", PLSRegression(n_components=best_components, scale=False)),
        ]
    )
    final_model.fit(dataset.x, y)
    predictions = final_model.predict(dataset.x).ravel()
    pls = final_model.named_steps["pls"]
    vip = calculate_vip_scores(pls)
    metrics = {
        "best_components": best_components,
        "rmsecv": float(min(row["rmsecv"] for row in cv_rows)),
        "r2cv": float(max(row["r2cv"] for row in cv_rows)),
        "auc": float(max(row["auc"] for row in cv_rows)),
        "accuracy": float(max(row["accuracy"] for row in cv_rows)),
    }
    return PLSRResult(
        best_components=best_components,
        cv_rows=cv_rows,
        metrics=metrics,
        coefficients=pls.coef_.ravel(),
        vip=vip,
        y_pred=predictions,
    )


def export_plsr_results(dataset: SpectralDataset, output_dir: Path, seed: int, max_components: int, cv_splits: int) -> dict[str, object]:
    output_dir = ensure_dir(output_dir)
    result = plsr_binary_target(dataset, seed, max_components, cv_splits)
    if result is None:
        write_text(output_dir / "plsr_skipped_v2.md", "# PLSR\n\nPLSR was skipped.\n")
        return {"skipped": True}

    write_dict_csv(output_dir / "plsr_cv_metrics_v2.csv", result.cv_rows, ["n_components", "rmsecv", "r2cv", "auc", "accuracy"])
    band_rows = []
    for wavelength, coef, vip in zip(dataset.wavelengths, result.coefficients, result.vip, strict=True):
        band_rows.append(
            {
                "wavelength": int(wavelength),
                "coefficient": float(coef),
                "abs_coefficient": float(abs(coef)),
                "vip": float(vip),
                "direction": "irrigado" if coef >= 0 else "nao_irrigado",
            }
        )
    band_rows_sorted = sorted(band_rows, key=lambda item: (item["vip"], item["abs_coefficient"]), reverse=True)
    write_dict_csv(
        output_dir / "plsr_bandas_importantes_v2.csv",
        band_rows_sorted,
        ["wavelength", "coefficient", "abs_coefficient", "vip", "direction"],
    )
    write_dict_csv(
        output_dir / "plsr_predicoes_v2.csv",
        [
            {
                "sample_id": dataset.sample_ids[idx],
                "data_coleta_iso": dataset.date_iso[idx],
                "genotipo_normalizado": dataset.genotype[idx],
                "condicao_normalizada": dataset.condition[idx],
                "y_true": int(dataset.condition[idx] == "irrigado"),
                "y_pred": float(result.y_pred[idx]),
            }
            for idx in range(dataset.x.shape[0])
        ],
        ["sample_id", "data_coleta_iso", "genotipo_normalizado", "condicao_normalizada", "y_true", "y_pred"],
    )
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.plot([row["n_components"] for row in result.cv_rows], [row["rmsecv"] for row in result.cv_rows], marker="o")
    ax.set_xlabel("PLS components")
    ax.set_ylabel("RMSECV")
    ax.set_title("PLSR cross-validation")
    ax.grid(alpha=0.2)
    fig.savefig(output_dir / "plsr_cv_v2.png", dpi=180)
    plt.close(fig)
    return {"result": result, "band_rows": band_rows_sorted}


def zscore(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    mean = np.nanmean(values)
    std = np.nanstd(values)
    if np.isclose(std, 0.0):
        return np.zeros_like(values)
    return (values - mean) / std


def rank_bands(
    dataset: SpectralDataset,
    output_dir: Path,
    candidate_n: int,
    seed: int,
) -> dict[str, object]:
    output_dir = ensure_dir(output_dir)
    labels = np.asarray(dataset.condition, dtype=object)
    y = np.asarray([1 if value == "irrigado" else 0 for value in labels], dtype=np.int32)
    anova_rows, _ = band_anova(dataset, labels)
    anova_map = {int(row["wavelength"]): row for row in anova_rows}
    anova_q = np.asarray([anova_map[int(w)]["q_value"] for w in dataset.wavelengths], dtype=np.float64)
    anova_f = np.asarray([anova_map[int(w)]["anova_f"] for w in dataset.wavelengths], dtype=np.float64)

    mi = mutual_info_classif(dataset.x, y, random_state=seed, n_neighbors=5)
    rf = RandomForestClassifier(
        n_estimators=300,
        random_state=seed,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    rf.fit(dataset.x, y)
    rf_importance = rf.feature_importances_

    lasso = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    solver="saga",
                    l1_ratio=1.0,
                    max_iter=4000,
                    class_weight="balanced",
                    random_state=seed,
                ),
            ),
        ]
    )
    lasso.fit(dataset.x, y)
    lasso_coef = lasso.named_steps["clf"].coef_.ravel()

    candidate_count = min(candidate_n, dataset.x.shape[1])
    candidate_indices = np.argsort(np.nan_to_num(anova_q, nan=1.0))[:candidate_count]
    candidate_x = dataset.x[:, candidate_indices]
    estimator = LogisticRegression(
        solver="lbfgs",
        l1_ratio=0.0,
        max_iter=4000,
        class_weight="balanced",
        random_state=seed,
    )
    rfe = RFE(estimator=estimator, n_features_to_select=max(10, candidate_count // 5), step=0.2)
    rfe.fit(candidate_x, y)
    rfe_rank = np.full(dataset.x.shape[1], np.nan, dtype=np.float64)
    rfe_rank[candidate_indices] = np.where(rfe.support_, 1.0, 2.0)

    pls_result = plsr_binary_target(dataset, seed, max_components=20, cv_splits=5)
    if pls_result is None:
        vip = np.zeros(dataset.x.shape[1], dtype=np.float64)
        pls_coef = np.zeros(dataset.x.shape[1], dtype=np.float64)
    else:
        vip = pls_result.vip
        pls_coef = pls_result.coefficients

    combined = (
        zscore(np.abs(vip))
        + zscore(np.abs(pls_coef))
        + zscore(mi)
        + zscore(rf_importance)
        + zscore(anova_f)
    )

    ranking_rows = []
    for idx, wavelength in enumerate(dataset.wavelengths):
        ranking_rows.append(
            {
                "wavelength": int(wavelength),
                "anova_f": float(anova_map[int(wavelength)]["anova_f"]),
                "anova_p": float(anova_map[int(wavelength)]["p_value"]),
                "anova_q": float(anova_map[int(wavelength)]["q_value"]),
                "mutual_info": float(mi[idx]),
                "rf_importance": float(rf_importance[idx]),
                "lasso_coef": float(lasso_coef[idx]),
                "rfe_rank": float(rfe_rank[idx]) if np.isfinite(rfe_rank[idx]) else np.nan,
                "pls_coef": float(pls_coef[idx]),
                "vip": float(vip[idx]),
                "combined_score": float(combined[idx]),
                "direction": "irrigado" if pls_coef[idx] >= 0 else "nao_irrigado",
            }
        )

    ranking_rows_sorted = sorted(
        ranking_rows,
        key=lambda row: (-row["combined_score"], -row["vip"], -abs(row["pls_coef"])),
    )
    write_dict_csv(
        output_dir / "band_ranking_v2.csv",
        ranking_rows_sorted,
        [
            "wavelength",
            "anova_f",
            "anova_p",
            "anova_q",
            "mutual_info",
            "rf_importance",
            "lasso_coef",
            "rfe_rank",
            "pls_coef",
            "vip",
            "combined_score",
            "direction",
        ],
    )
    write_dict_csv(
        output_dir / "band_ranking_top_100_v2.csv",
        ranking_rows_sorted[:100],
        [
            "wavelength",
            "anova_f",
            "anova_p",
            "anova_q",
            "mutual_info",
            "rf_importance",
            "lasso_coef",
            "rfe_rank",
            "pls_coef",
            "vip",
            "combined_score",
            "direction",
        ],
    )

    fig, ax = plt.subplots(figsize=(10, 8), constrained_layout=True)
    top = ranking_rows_sorted[:25][::-1]
    ax.barh(
        [str(row["wavelength"]) for row in top],
        [row["combined_score"] for row in top],
        color=["#0f766e" if row["direction"] == "irrigado" else "#c2410c" for row in top],
    )
    ax.set_xlabel("Combined score")
    ax.set_title("Top 25 discriminative bands")
    fig.savefig(output_dir / "band_ranking_top_25_v2.png", dpi=180)
    plt.close(fig)

    return {"rows": ranking_rows_sorted, "top_path": output_dir / "band_ranking_top_100_v2.csv"}


def pair_hvi_score(index_values: np.ndarray, labels: np.ndarray) -> float:
    class0 = index_values[labels == 0]
    class1 = index_values[labels == 1]
    if class0.size == 0 or class1.size == 0:
        return np.nan
    mean_diff = abs(np.nanmean(class1) - np.nanmean(class0))
    pooled = math.sqrt(0.5 * (np.nanvar(class0, ddof=1) + np.nanvar(class1, ddof=1)))
    if np.isclose(pooled, 0.0):
        return np.nan
    return float(mean_diff / pooled)


def optimize_hvi(
    dataset: SpectralDataset,
    output_dir: Path,
    candidate_n: int,
    ranking_rows: list[dict[str, object]],
) -> dict[str, object] | None:
    output_dir = ensure_dir(output_dir)
    if len(set(dataset.condition)) != 2:
        write_text(output_dir / "hvi_skipped_v2.md", "# HVI\n\nHVI search was skipped.\n")
        return None

    labels = np.asarray([1 if value == "irrigado" else 0 for value in dataset.condition], dtype=np.int32)
    top_bands = [int(row["wavelength"]) for row in ranking_rows[:candidate_n]]
    w_to_i = {int(w): idx for idx, w in enumerate(dataset.wavelengths)}
    candidate_idx = [w_to_i[w] for w in top_bands if w in w_to_i]
    candidate_w = dataset.wavelengths[candidate_idx]
    n = len(candidate_idx)
    if n < 2:
        return None

    score_matrix = np.full((n, n), np.nan, dtype=np.float64)
    pair_rows = []
    for i in range(n):
        for j in range(i + 1, n):
            x_i = dataset.x[:, candidate_idx[i]]
            x_j = dataset.x[:, candidate_idx[j]]
            index_values = _safe_divide(x_i - x_j, x_i + x_j)
            score = pair_hvi_score(index_values, labels)
            score_matrix[i, j] = score
            score_matrix[j, i] = score
            pair_rows.append(
                {
                    "band_a": int(candidate_w[i]),
                    "band_b": int(candidate_w[j]),
                    "score": float(score) if np.isfinite(score) else np.nan,
                    "mean_condition_diff": float(
                        np.nanmean(index_values[labels == 1]) - np.nanmean(index_values[labels == 0])
                    ),
                }
            )

    pair_rows_sorted = sorted(pair_rows, key=lambda row: np.nan_to_num(row["score"], nan=-np.inf), reverse=True)
    write_dict_csv(output_dir / "hvi_pairs_v2.csv", pair_rows_sorted, ["band_a", "band_b", "score", "mean_condition_diff"])
    write_csv(
        output_dir / "hvi_score_matrix_v2.csv",
        ["band"] + [str(int(w)) for w in candidate_w],
        [
            [int(candidate_w[i])] + [float(value) if np.isfinite(value) else "" for value in score_matrix[i]]
            for i in range(n)
        ],
    )

    fig, ax = plt.subplots(figsize=(9, 8), constrained_layout=True)
    image = ax.imshow(score_matrix, cmap="magma")
    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels([str(int(w)) for w in candidate_w], rotation=90, fontsize=7)
    ax.set_yticklabels([str(int(w)) for w in candidate_w], fontsize=7)
    ax.set_title("HVI pair score matrix")
    fig.colorbar(image, ax=ax, shrink=0.8)
    fig.savefig(output_dir / "hvi_score_matrix_v2.png", dpi=180)
    plt.close(fig)
    return {"pairs": pair_rows_sorted, "top_path": output_dir / "hvi_pairs_v2.csv"}


def build_summary_markdown(run_report: dict[str, object]) -> str:
    lines = [
        "# Pipeline v2 summary",
        "",
        f"- Run timestamp: {run_report['timestamp']}",
        f"- Input: `{run_report['input_path']}`",
        f"- Metadata: `{run_report['metadata_path']}`",
        f"- Output dir: `{run_report['output_dir']}`",
        f"- Samples: {run_report['samples']}",
        f"- Bands: {run_report['bands']}",
        f"- Groups: {run_report['groups']}",
        f"- Genotypes: {', '.join(run_report['genotypes'])}",
        f"- Conditions: {', '.join(run_report['conditions'])}",
        f"- Turnos: {', '.join(run_report['turnos'])}",
        "",
        "## Included analyses",
        "",
        "- Structural validation",
        "- Descriptive statistics by date x genotype x condition",
        "- PCA and scatter plots by metadata",
        "- Vegetation indices and summary correlations",
        "- Hierarchical clustering of group mean spectra",
        "- Supervised classification for selected targets",
        "- Band selection using ANOVA, MI, RF, L1 logistic, RFE, and PLS/VIP",
        "- Optional binary PLSR",
        "- Optional HVI pair search",
        "",
        "## Methodological note",
        "",
        "- The dataset does not contain the laboratory biochemical targets from the original paper.",
        "- Those regression analyses are therefore not reproduced in the base pipeline and remain optional extensions.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    setup_logging(args.output_dir)
    LOGGER.info("Starting pipeline v2")
    timestamp = datetime.now(timezone.utc).isoformat()

    dataset = load_and_align_dataset(args.input, args.metadata_csv)
    validation_report = validate_dataset_structure(dataset, args.output_dir / "01_validation")
    export_group_statistics(dataset, args.output_dir / "02_descriptive_stats")
    pca_result = pca_analysis(dataset, args.output_dir / "03_pca")
    compute_vegetation_indices(dataset, args.output_dir / "04_indices")
    hierarchical_clustering(dataset, args.output_dir / "05_cluster")

    targets = [target.strip() for target in args.classification_targets.split(",") if target.strip()]
    classification_result = export_classification_results(
        dataset,
        args.output_dir / "06_classification",
        targets,
        args.seed,
        args.cv_splits,
    )

    ranking_result = rank_bands(
        dataset,
        args.output_dir / "07_band_selection",
        args.band_selection_candidate_n,
        args.seed,
    )

    plsr_result = None
    if not args.skip_plsr:
        plsr_result = export_plsr_results(
            dataset,
            args.output_dir / "08_plsr",
            args.seed,
            args.max_plsr_components,
            args.cv_splits,
        )

    hvi_result = None
    if not args.skip_hvi:
        hvi_result = optimize_hvi(
            dataset,
            args.output_dir / "09_hvi",
            args.hvi_candidate_bands,
            ranking_result["rows"],
        )

    run_report = {
        "timestamp": timestamp,
        "input_path": str(args.input),
        "metadata_path": str(args.metadata_csv),
        "output_dir": str(args.output_dir),
        "samples": len(dataset.sample_ids),
        "bands": len(dataset.wavelengths),
        "groups": validation_report["groups"],
        "genotypes": validation_report["genotypes"],
        "conditions": validation_report["conditions"],
        "turnos": validation_report["turnos"],
        "classification_targets": targets,
        "pca_variance_pc1": float(pca_result["pca"].explained_variance_ratio_[0]),
        "pca_variance_pc2": float(pca_result["pca"].explained_variance_ratio_[1]),
        "plsr_run": plsr_result is not None and not plsr_result.get("skipped", False),
        "hvi_run": hvi_result is not None,
    }
    write_json(args.output_dir / "run_manifest_v2.json", run_report)
    write_text(args.output_dir / "README_v2.md", build_summary_markdown(run_report))
    LOGGER.info("Pipeline v2 completed")


if __name__ == "__main__":
    main()
