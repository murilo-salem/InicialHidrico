#!/usr/bin/env python3
"""Run PLSR and PCA for irrigated vs non-irrigated samples."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Ellipse
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.metrics import mean_squared_error, r2_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CLASS_LABELS = {0: "nao_irrigado", 1: "irrigado"}
CLASS_COLORS = {"nao_irrigado": "#c2410c", "irrigado": "#0f766e"}
GENOTYPE_COLORS = {"BR16": "#1d4ed8", "CD202": "#c2410c", "EMB48": "#0f766e"}


@dataclass
class Dataset:
    sample_names: list[str]
    dates: list[str]
    shifts: list[str]
    genotypes: list[str]
    conditions: list[str]
    wavelengths: np.ndarray
    x: np.ndarray
    y: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run PLSR and PCA on the processed irrigation dataset."
    )
    parser.add_argument(
        "--processed-csv",
        type=Path,
        default=Path("dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv"),
        help="Processed spectral dataset.",
    )
    parser.add_argument(
        "--metadata-csv",
        type=Path,
        default=Path("dados_processados_soft/metadados_normalizados_soft.csv"),
        help="Normalized metadata file aligned with the processed dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft/plsr_pca_irrigacao"),
        help="Directory where analysis outputs will be written.",
    )
    parser.add_argument(
        "--max-components",
        type=int,
        default=15,
        help="Maximum number of PLS components to evaluate.",
    )
    parser.add_argument(
        "--cv-splits",
        type=int,
        default=5,
        help="Number of stratified folds for cross-validation.",
    )
    return parser.parse_args()


def load_dataset(processed_csv_path: Path, metadata_csv_path: Path) -> Dataset:
    with metadata_csv_path.open("r", encoding="utf-8", newline="") as metadata_handle:
        metadata_reader = csv.DictReader(metadata_handle)
        metadata_rows = list(metadata_reader)

    with processed_csv_path.open("r", encoding="utf-8", newline="") as processed_handle:
        processed_reader = csv.reader(processed_handle)
        header = next(processed_reader)
        wavelengths = np.asarray([float(value) for value in header[6:]], dtype=np.float64)
        n_samples = len(metadata_rows)
        x = np.empty((n_samples, len(wavelengths)), dtype=np.float64)

        sample_names: list[str] = []
        dates: list[str] = []
        shifts: list[str] = []
        genotypes: list[str] = []
        conditions: list[str] = []

        for row_index, row in enumerate(processed_reader):
            if row_index >= n_samples:
                raise ValueError(
                    "Processed CSV contains more rows than the normalized metadata file."
                )

            metadata = metadata_rows[row_index]
            if row[0] != metadata["nomenclaura"]:
                raise ValueError(
                    "Processed CSV and normalized metadata file are misaligned at "
                    f"row {row_index + 2}: {row[0]!r} != {metadata['nomenclaura']!r}"
                )

            sample_names.append(row[0])
            dates.append(metadata["data_coleta_iso"])
            shifts.append(metadata["turno"])
            genotypes.append(metadata["genotipo_normalizado"])
            conditions.append(metadata["condicao_normalizada"])
            x[row_index, :] = np.asarray(row[6:], dtype=np.float64)

        if row_index + 1 != n_samples:
            raise ValueError(
                "Normalized metadata file contains more rows than the processed CSV."
            )

    y = np.asarray([1 if condition == "irrigado" else 0 for condition in conditions], dtype=np.float64)
    return Dataset(
        sample_names=sample_names,
        dates=dates,
        shifts=shifts,
        genotypes=genotypes,
        conditions=conditions,
        wavelengths=wavelengths,
        x=x,
        y=y,
    )


def subset_dataset(dataset: Dataset, mask: np.ndarray) -> Dataset:
    bool_mask = np.asarray(mask, dtype=bool)
    return Dataset(
        sample_names=[value for value, keep in zip(dataset.sample_names, bool_mask, strict=False) if keep],
        dates=[value for value, keep in zip(dataset.dates, bool_mask, strict=False) if keep],
        shifts=[value for value, keep in zip(dataset.shifts, bool_mask, strict=False) if keep],
        genotypes=[value for value, keep in zip(dataset.genotypes, bool_mask, strict=False) if keep],
        conditions=[value for value, keep in zip(dataset.conditions, bool_mask, strict=False) if keep],
        wavelengths=dataset.wavelengths.copy(),
        x=dataset.x[bool_mask].copy(),
        y=dataset.y[bool_mask].copy(),
    )


def evaluate_pls_components(
    x: np.ndarray,
    y: np.ndarray,
    max_components: int,
    cv_splits: int,
) -> tuple[list[dict[str, float]], int]:
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    results: list[dict[str, float]] = []
    upper = min(max_components, x.shape[0] - 1, x.shape[1])

    for n_components in range(1, upper + 1):
        pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("pls", PLSRegression(n_components=n_components, scale=False)),
            ]
        )
        y_pred = cross_val_predict(pipeline, x, y, cv=cv, n_jobs=-1).ravel()
        rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
        r2 = float(r2_score(y, y_pred))
        auc = float(roc_auc_score(y, y_pred))
        accuracy = float(np.mean((y_pred >= 0.5) == y))
        results.append(
            {
                "n_components": float(n_components),
                "rmsecv": rmse,
                "r2cv": r2,
                "auc": auc,
                "accuracy": accuracy,
            }
        )

    best_result = min(results, key=lambda item: (item["rmsecv"], item["n_components"]))
    return results, int(best_result["n_components"])


def fit_final_pls(
    x: np.ndarray,
    y: np.ndarray,
    n_components: int,
) -> tuple[StandardScaler, PLSRegression, np.ndarray]:
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    pls = PLSRegression(n_components=n_components, scale=False)
    pls.fit(x_scaled, y)
    return scaler, pls, x_scaled


def calculate_vip_scores(pls: PLSRegression) -> np.ndarray:
    t = pls.x_scores_
    w = pls.x_weights_
    q = pls.y_loadings_
    p = w.shape[0]
    sum_sq = np.sum(t ** 2, axis=0) * np.sum(q ** 2, axis=1)
    total = np.sum(sum_sq)
    weights = (w ** 2) / np.sum(w ** 2, axis=0, keepdims=True)
    vip = np.sqrt(p * (weights @ sum_sq.reshape(-1, 1)).ravel() / total)
    return vip


def confidence_ellipse(points: np.ndarray, ax: plt.Axes, color: str, label: str) -> None:
    if points.shape[0] < 3:
        return
    covariance = np.cov(points, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
    width, height = 2 * 2.0 * np.sqrt(np.maximum(eigenvalues, 0.0))
    center = points.mean(axis=0)
    ellipse = Ellipse(
        xy=center,
        width=width,
        height=height,
        angle=angle,
        facecolor=color,
        edgecolor=color,
        alpha=0.12,
        linewidth=2.0,
        label=label,
    )
    ax.add_patch(ellipse)


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def plot_pls_cv(results: list[dict[str, float]], output_path: Path) -> None:
    components = [int(item["n_components"]) for item in results]
    rmsecv = [item["rmsecv"] for item in results]
    auc = [item["auc"] for item in results]
    fig, ax1 = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    ax1.plot(components, rmsecv, marker="o", color="#0f766e", linewidth=2.2)
    ax1.set_xlabel("Numero de componentes PLS")
    ax1.set_ylabel("RMSECV", color="#0f766e")
    ax1.tick_params(axis="y", labelcolor="#0f766e")
    ax1.grid(alpha=0.24)
    ax2 = ax1.twinx()
    ax2.plot(components, auc, marker="s", color="#c2410c", linewidth=2.0)
    ax2.set_ylabel("AUC", color="#c2410c")
    ax2.tick_params(axis="y", labelcolor="#c2410c")
    ax1.set_title("Selecao do numero de componentes do PLSR")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_pls_band_curves(
    wavelengths: np.ndarray,
    coefficients: np.ndarray,
    vip_scores: np.ndarray,
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True, constrained_layout=True)
    axes[0].plot(wavelengths, coefficients, color="#1d4ed8", linewidth=1.6)
    axes[0].axhline(0.0, color="#111827", linewidth=0.9, alpha=0.6)
    axes[0].set_ylabel("Coeficiente PLSR")
    axes[0].set_title("Coeficientes do PLSR por banda")
    axes[0].grid(alpha=0.2)

    axes[1].plot(wavelengths, vip_scores, color="#c2410c", linewidth=1.6)
    axes[1].axhline(1.0, color="#111827", linewidth=1.0, linestyle="--", alpha=0.7)
    axes[1].set_ylabel("VIP")
    axes[1].set_xlabel("Comprimento de onda (nm)")
    axes[1].set_title("VIP por banda")
    axes[1].grid(alpha=0.2)

    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_top_coeff_bands(top_positive: np.ndarray, top_negative: np.ndarray, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), constrained_layout=True)

    axes[0].barh(
        [str(int(item["wavelength"])) for item in top_positive],
        [item["coefficient"] for item in top_positive],
        color="#0f766e",
    )
    axes[0].set_title("Bandas mais associadas a irrigado")
    axes[0].set_xlabel("Coeficiente PLSR")

    axes[1].barh(
        [str(int(item["wavelength"])) for item in top_negative],
        [item["coefficient"] for item in top_negative],
        color="#c2410c",
    )
    axes[1].set_title("Bandas mais associadas a nao_irrigado")
    axes[1].set_xlabel("Coeficiente PLSR")

    for ax in axes:
        ax.grid(alpha=0.18, axis="x")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_pca_scores(
    scores: np.ndarray,
    conditions: list[str],
    explained_variance: np.ndarray,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 7), constrained_layout=True)
    for condition in ["irrigado", "nao_irrigado"]:
        mask = np.asarray([value == condition for value in conditions])
        class_scores = scores[mask]
        ax.scatter(
            class_scores[:, 0],
            class_scores[:, 1],
            s=24,
            alpha=0.6,
            color=CLASS_COLORS[condition],
            edgecolor="none",
            label=condition,
        )
        confidence_ellipse(class_scores[:, :2], ax, CLASS_COLORS[condition], f"{condition} dispersao")
        centroid = class_scores[:, :2].mean(axis=0)
        ax.scatter(
            centroid[0],
            centroid[1],
            s=120,
            marker="X",
            color=CLASS_COLORS[condition],
            edgecolor="#111827",
            linewidth=0.6,
        )

    ax.axhline(0.0, color="#111827", linewidth=0.8, alpha=0.45)
    ax.axvline(0.0, color="#111827", linewidth=0.8, alpha=0.45)
    ax.set_xlabel(f"PC1 ({explained_variance[0] * 100:.2f}% var.)")
    ax.set_ylabel(f"PC2 ({explained_variance[1] * 100:.2f}% var.)")
    ax.set_title("PCA das classes irrigado vs nao_irrigado")
    ax.grid(alpha=0.18)
    ax.legend(loc="best")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_pca_scores_by_genotype(
    scores: np.ndarray,
    genotypes: list[str],
    explained_variance: np.ndarray,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 7), constrained_layout=True)
    for genotype in ["BR16", "CD202", "EMB48"]:
        mask = np.asarray([value == genotype for value in genotypes])
        geno_scores = scores[mask]
        ax.scatter(
            geno_scores[:, 0],
            geno_scores[:, 1],
            s=24,
            alpha=0.6,
            color=GENOTYPE_COLORS[genotype],
            edgecolor="none",
            label=genotype,
        )
        confidence_ellipse(geno_scores[:, :2], ax, GENOTYPE_COLORS[genotype], f"{genotype} dispersao")
        centroid = geno_scores[:, :2].mean(axis=0)
        ax.scatter(
            centroid[0],
            centroid[1],
            s=120,
            marker="X",
            color=GENOTYPE_COLORS[genotype],
            edgecolor="#111827",
            linewidth=0.6,
        )

    ax.axhline(0.0, color="#111827", linewidth=0.8, alpha=0.45)
    ax.axvline(0.0, color="#111827", linewidth=0.8, alpha=0.45)
    ax.set_xlabel(f"PC1 ({explained_variance[0] * 100:.2f}% var.)")
    ax.set_ylabel(f"PC2 ({explained_variance[1] * 100:.2f}% var.)")
    ax.set_title("PCA por genotipo")
    ax.grid(alpha=0.18)
    ax.legend(loc="best")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_spectral_signatures_by_genotype(
    wavelengths: np.ndarray,
    x: np.ndarray,
    genotypes: list[str],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
    for genotype in ["BR16", "CD202", "EMB48"]:
        mask = np.asarray([value == genotype for value in genotypes])
        mean_spec = x[mask].mean(axis=0)
        std_spec = x[mask].std(axis=0)
        ax.plot(wavelengths, mean_spec, color=GENOTYPE_COLORS[genotype], linewidth=1.6, label=genotype)
        ax.fill_between(wavelengths, mean_spec - std_spec, mean_spec + std_spec, color=GENOTYPE_COLORS[genotype], alpha=0.15)

    ax.set_xlabel("Comprimento de onda (nm)")
    ax.set_ylabel("Reflectancia")
    ax.set_title("Assinaturas espectrais medias por genotipo")
    ax.grid(alpha=0.18)
    ax.legend(loc="best")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_pca_loadings(
    wavelengths: np.ndarray,
    components: np.ndarray,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 5.5), constrained_layout=True)
    ax.plot(wavelengths, components[0], color="#1d4ed8", linewidth=1.5, label="PC1")
    ax.plot(wavelengths, components[1], color="#c2410c", linewidth=1.5, label="PC2")
    ax.axhline(0.0, color="#111827", linewidth=0.8, alpha=0.5)
    ax.set_title("Loadings da PCA por banda")
    ax.set_xlabel("Comprimento de onda (nm)")
    ax.set_ylabel("Loading")
    ax.grid(alpha=0.18)
    ax.legend()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def write_summary_markdown(
    path: Path,
    *,
    dataset: Dataset,
    best_components: int,
    best_result: dict[str, float],
    explained_variance: np.ndarray,
    top_positive: np.ndarray,
    top_negative: np.ndarray,
    top_vip: np.ndarray,
) -> None:
    lines = [
        "# PLSR e PCA: irrigado vs nao_irrigado",
        "",
        f"- Dataset analisado: `{dataset.x.shape[0]}` amostras x `{dataset.x.shape[1]}` bandas",
        "- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`)",
        f"- Classes: irrigado = {int(np.sum(dataset.y == 1))}, nao_irrigado = {int(np.sum(dataset.y == 0))}",
        f"- Melhor numero de componentes PLSR: {best_components}",
        f"- RMSECV: {best_result['rmsecv']:.6f}",
        f"- R2CV: {best_result['r2cv']:.6f}",
        f"- AUC: {best_result['auc']:.6f}",
        f"- Accuracy com corte 0.5: {best_result['accuracy']:.6f}",
        f"- PCA: PC1 = {explained_variance[0] * 100:.2f}% da variancia, PC2 = {explained_variance[1] * 100:.2f}%",
        "",
        "## Bandas com coeficiente mais positivo",
        "",
        "| banda | coeficiente | VIP | interpretacao |",
        "| ---: | ---: | ---: | --- |",
    ]
    for item in top_positive:
        lines.append(
            f"| {int(item['wavelength'])} | {item['coefficient']:.6f} | {item['vip']:.6f} | mais associado a irrigado |"
        )

    lines.extend(
        [
            "",
            "## Bandas com coeficiente mais negativo",
            "",
            "| banda | coeficiente | VIP | interpretacao |",
            "| ---: | ---: | ---: | --- |",
        ]
    )
    for item in top_negative:
        lines.append(
            f"| {int(item['wavelength'])} | {item['coefficient']:.6f} | {item['vip']:.6f} | mais associado a nao_irrigado |"
        )

    lines.extend(
        [
            "",
            "## Bandas com maior VIP",
            "",
            "| banda | VIP | coeficiente | direcao |",
            "| ---: | ---: | ---: | --- |",
        ]
    )
    for item in top_vip:
        direction = "irrigado" if item["coefficient"] >= 0 else "nao_irrigado"
        lines.append(
            f"| {int(item['wavelength'])} | {item['vip']:.6f} | {item['coefficient']:.6f} | {direction} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    processed_csv_path = args.processed_csv.resolve()
    metadata_csv_path = args.metadata_csv.resolve()
    output_dir = args.output_dir.resolve()

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_dataset(processed_csv_path, metadata_csv_path)

    cv_results, best_components = evaluate_pls_components(
        dataset.x,
        dataset.y,
        max_components=args.max_components,
        cv_splits=args.cv_splits,
    )
    best_result = next(item for item in cv_results if int(item["n_components"]) == best_components)

    scaler, pls, x_scaled = fit_final_pls(dataset.x, dataset.y, best_components)
    vip_scores = calculate_vip_scores(pls)
    coefficients = pls.coef_.ravel()
    y_fitted = pls.predict(x_scaled).ravel()

    band_dtype = np.dtype(
        [
            ("wavelength", np.float64),
            ("coefficient", np.float64),
            ("abs_coefficient", np.float64),
            ("vip", np.float64),
        ]
    )
    band_table = np.empty(dataset.wavelengths.shape[0], dtype=band_dtype)
    band_table["wavelength"] = dataset.wavelengths
    band_table["coefficient"] = coefficients
    band_table["abs_coefficient"] = np.abs(coefficients)
    band_table["vip"] = vip_scores

    top_positive = np.sort(band_table, order="coefficient")[-15:][::-1]
    top_negative = np.sort(band_table, order="coefficient")[:15]
    top_vip = np.sort(band_table, order="vip")[-20:][::-1]
    bands_by_relevance = np.sort(band_table, order=["vip", "abs_coefficient"])[::-1]

    pca = PCA(n_components=2, svd_solver="randomized", random_state=42)
    scores = pca.fit_transform(dataset.x)

    plsr_cv_csv = output_dir / "plsr_cv_metricas.csv"
    plsr_bands_csv = output_dir / "plsr_bandas_importantes.csv"
    plsr_predictions_csv = output_dir / "plsr_predicoes_ajuste.csv"
    pca_scores_csv = output_dir / "pca_scores.csv"
    pca_loadings_csv = output_dir / "pca_loadings.csv"

    write_csv(
        plsr_cv_csv,
        ["n_components", "rmsecv", "r2cv", "auc", "accuracy"],
        [
            [
                int(item["n_components"]),
                f"{item['rmsecv']:.10f}",
                f"{item['r2cv']:.10f}",
                f"{item['auc']:.10f}",
                f"{item['accuracy']:.10f}",
            ]
            for item in cv_results
        ],
    )
    write_csv(
        plsr_bands_csv,
        ["wavelength", "coefficient", "abs_coefficient", "vip", "direction"],
        [
            [
                int(item["wavelength"]),
                f"{item['coefficient']:.10f}",
                f"{item['abs_coefficient']:.10f}",
                f"{item['vip']:.10f}",
                "irrigado" if item["coefficient"] >= 0 else "nao_irrigado",
            ]
            for item in bands_by_relevance
        ],
    )
    write_csv(
        plsr_predictions_csv,
        ["sample_name", "data_coleta", "genotipo", "condicao", "y_true", "y_pred_fit"],
        [
            [
                dataset.sample_names[index],
                dataset.dates[index],
                dataset.genotypes[index],
                dataset.conditions[index],
                int(dataset.y[index]),
                f"{y_fitted[index]:.10f}",
            ]
            for index in range(dataset.x.shape[0])
        ],
    )
    write_csv(
        pca_scores_csv,
        ["sample_name", "data_coleta", "genotipo", "condicao", "PC1", "PC2"],
        [
            [
                dataset.sample_names[index],
                dataset.dates[index],
                dataset.genotypes[index],
                dataset.conditions[index],
                f"{scores[index, 0]:.10f}",
                f"{scores[index, 1]:.10f}",
            ]
            for index in range(dataset.x.shape[0])
        ],
    )
    write_csv(
        pca_loadings_csv,
        ["wavelength", "PC1_loading", "PC2_loading"],
        [
            [
                int(dataset.wavelengths[index]),
                f"{pca.components_[0, index]:.10f}",
                f"{pca.components_[1, index]:.10f}",
            ]
            for index in range(dataset.wavelengths.shape[0])
        ],
    )

    plot_pls_cv(cv_results, output_dir / "plsr_cv.svg")
    plot_pls_band_curves(
        dataset.wavelengths,
        coefficients,
        vip_scores,
        output_dir / "plsr_coeficientes_vip.svg",
    )
    plot_top_coeff_bands(
        top_positive,
        top_negative,
        output_dir / "plsr_top_bandas.svg",
    )
    plot_pca_scores(
        scores,
        dataset.conditions,
        pca.explained_variance_ratio_,
        output_dir / "pca_scores_classes.svg",
    )
    plot_pca_scores_by_genotype(
        scores,
        dataset.genotypes,
        pca.explained_variance_ratio_,
        output_dir / "pca_scores_genotipo.svg",
    )
    plot_spectral_signatures_by_genotype(
        dataset.wavelengths,
        dataset.x,
        dataset.genotypes,
        output_dir / "assinatura_espectral_genotipo.svg",
    )
    plot_pca_loadings(
        dataset.wavelengths,
        pca.components_,
        output_dir / "pca_loadings.svg",
    )

    write_summary_markdown(
        output_dir / "resumo_plsr_pca.md",
        dataset=dataset,
        best_components=best_components,
        best_result=best_result,
        explained_variance=pca.explained_variance_ratio_,
        top_positive=top_positive,
        top_negative=top_negative,
        top_vip=top_vip,
    )

    print(f"Output directory: {output_dir}")
    print(f"Samples: {dataset.x.shape[0]} | Bands: {dataset.x.shape[1]}")
    print(f"Best PLS components: {best_components}")
    print(f"RMSECV: {best_result['rmsecv']:.6f}")
    print(f"R2CV: {best_result['r2cv']:.6f}")
    print(f"AUC: {best_result['auc']:.6f}")
    print(f"PC1 variance: {pca.explained_variance_ratio_[0] * 100:.2f}%")
    print(f"PC2 variance: {pca.explained_variance_ratio_[1] * 100:.2f}%")


if __name__ == "__main__":
    main()
