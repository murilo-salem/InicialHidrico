#!/usr/bin/env python3
"""Build PLSR + Pearson + Welch t-test tables for irrigation subsets."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, ttest_ind

from run_plsr_pca_irrigation import (
    calculate_vip_scores,
    evaluate_pls_components,
    fit_final_pls,
    load_dataset,
    subset_dataset,
    write_csv,
)


SHIFT_ORDER = {"manha": 0, "tarde": 1}
GENOTYPE_ORDER = {"BR16": 0, "CD202": 1, "EMB48": 2}
FAMILY_ORDER = {"data": 0, "turno": 1, "genotipo": 2, "turno_genotipo": 3}
P_THRESHOLD = 0.005


@dataclass(frozen=True)
class SubsetSpec:
    family: str
    name: str
    label: str
    dates: tuple[str, ...]
    shift: str | None = None
    genotype: str | None = None


@dataclass(frozen=True)
class SubsetResult:
    spec: SubsetSpec
    n_samples: int
    irrigated_count: int
    non_irrigated_count: int
    effective_cv_splits: int
    best_components: int
    best_result: dict[str, float]
    top_table: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create tables of the most important bands for irrigated vs non-irrigated "
            "using PLSR, Pearson correlation and Welch t-test on the current subsets."
        )
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
        default=Path("dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao"),
        help="Directory where the tables will be written.",
    )
    parser.add_argument(
        "--max-components",
        type=int,
        default=15,
        help="Maximum number of PLS components to evaluate per subset.",
    )
    parser.add_argument(
        "--cv-splits",
        type=int,
        default=5,
        help="Maximum number of stratified folds per subset.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of top bands to keep per subset.",
    )
    return parser.parse_args()


def robust_zscore(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    mean = np.nanmean(values)
    std = np.nanstd(values)
    if np.isclose(std, 0.0):
        return np.zeros_like(values)
    return (values - mean) / std


def find_matched_dates(dates: list[str], shifts: list[str]) -> list[str]:
    shifts_by_date: dict[str, set[str]] = {}
    for date_value, shift_value in zip(dates, shifts, strict=False):
        shifts_by_date.setdefault(date_value, set()).add(shift_value)
    return sorted(
        date_value
        for date_value, date_shifts in shifts_by_date.items()
        if {"manha", "tarde"}.issubset(date_shifts)
    )


def format_date_label(date_iso: str) -> str:
    year, month, day = date_iso.split("-")
    return f"{day}/{month}/{year}"


def build_subset_specs(matched_dates: list[str], genotypes: list[str]) -> list[SubsetSpec]:
    specs: list[SubsetSpec] = []

    for date_iso in matched_dates:
        specs.append(
            SubsetSpec(
                family="data",
                name=date_iso,
                label=f"Data {format_date_label(date_iso)}",
                dates=(date_iso,),
            )
        )

    for shift in ["manha", "tarde"]:
        specs.append(
            SubsetSpec(
                family="turno",
                name=shift,
                label=f"Turno {shift}",
                dates=tuple(matched_dates),
                shift=shift,
            )
        )

    for genotype in genotypes:
        specs.append(
            SubsetSpec(
                family="genotipo",
                name=genotype,
                label=f"Genotipo {genotype}",
                dates=tuple(matched_dates),
                genotype=genotype,
            )
        )

    for shift in ["manha", "tarde"]:
        for genotype in genotypes:
            specs.append(
                SubsetSpec(
                    family="turno_genotipo",
                    name=f"{shift}_{genotype}",
                    label=f"{shift} / {genotype}",
                    dates=tuple(matched_dates),
                    shift=shift,
                    genotype=genotype,
                )
            )

    return specs


def build_subset_mask(
    *,
    dataset,
    spec: SubsetSpec,
) -> np.ndarray:
    mask = np.asarray([date_value in spec.dates for date_value in dataset.dates], dtype=bool)
    if spec.shift is not None:
        mask &= np.asarray([value == spec.shift for value in dataset.shifts], dtype=bool)
    if spec.genotype is not None:
        mask &= np.asarray([value == spec.genotype for value in dataset.genotypes], dtype=bool)
    return mask


def calculate_pearson_metrics(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    correlation = np.empty(x.shape[1], dtype=np.float64)
    p_values = np.empty(x.shape[1], dtype=np.float64)
    for column_index in range(x.shape[1]):
        column = x[:, column_index]
        if np.isclose(np.nanstd(column), 0.0):
            correlation[column_index] = np.nan
            p_values[column_index] = np.nan
            continue
        corr_value, p_value = pearsonr(column, y)
        correlation[column_index] = corr_value
        p_values[column_index] = p_value
    return correlation, p_values


def build_band_table(
    *,
    wavelengths: np.ndarray,
    coefficients: np.ndarray,
    vip_scores: np.ndarray,
    pearson_r: np.ndarray,
    pearson_p_value: np.ndarray,
    welch_p_value: np.ndarray,
    top_k: int,
) -> tuple[np.ndarray, np.ndarray]:
    dtype = np.dtype(
        [
            ("wavelength", np.float64),
            ("coefficient", np.float64),
            ("abs_coefficient", np.float64),
            ("vip", np.float64),
            ("optimal_score", np.float64),
            ("pearson_r", np.float64),
            ("pearson_p_value", np.float64),
            ("welch_p_value", np.float64),
            ("rank", np.int32),
            ("direction_label", "U20"),
        ]
    )
    table = np.empty(wavelengths.shape[0], dtype=dtype)
    table["wavelength"] = wavelengths
    table["coefficient"] = coefficients
    table["abs_coefficient"] = np.abs(coefficients)
    table["vip"] = vip_scores
    table["optimal_score"] = robust_zscore(vip_scores) + robust_zscore(np.abs(coefficients))
    table["pearson_r"] = pearson_r
    table["pearson_p_value"] = pearson_p_value
    table["welch_p_value"] = welch_p_value
    table["rank"] = 0
    table["direction_label"] = np.where(coefficients >= 0, "irrigado", "nao_irrigado")

    significant_mask = np.isfinite(table["welch_p_value"]) & (table["welch_p_value"] < P_THRESHOLD)
    filtered = table[significant_mask]
    if filtered.size == 0:
        filtered = table

    top_table = np.sort(filtered, order=["optimal_score", "vip", "abs_coefficient"])[::-1][:top_k].copy()
    top_table["rank"] = np.arange(1, top_table.shape[0] + 1)
    return table, top_table


def analyze_subset(
    dataset,
    spec: SubsetSpec,
    *,
    max_components: int,
    cv_splits: int,
    top_k: int,
) -> tuple[SubsetResult, np.ndarray]:
    mask = build_subset_mask(dataset=dataset, spec=spec)
    subset = subset_dataset(dataset, mask)
    irrigated_count = int(np.sum(subset.y == 1))
    non_irrigated_count = int(np.sum(subset.y == 0))
    min_class_count = min(irrigated_count, non_irrigated_count)
    if min_class_count < 2:
        raise ValueError(f"Subset {spec.label!r} does not have enough samples per class.")

    effective_cv_splits = min(cv_splits, min_class_count)
    cv_results, best_components = evaluate_pls_components(
        subset.x,
        subset.y,
        max_components=max_components,
        cv_splits=effective_cv_splits,
    )
    best_result = next(item for item in cv_results if int(item["n_components"]) == best_components)
    scaler, pls, x_scaled = fit_final_pls(subset.x, subset.y, best_components)
    del scaler, x_scaled

    vip_scores = calculate_vip_scores(pls)
    coefficients = pls.coef_.ravel()
    pearson_r, pearson_p_value = calculate_pearson_metrics(subset.x, subset.y)

    irrigated = subset.x[subset.y == 1]
    non_irrigated = subset.x[subset.y == 0]
    welch_result = ttest_ind(
        irrigated,
        non_irrigated,
        axis=0,
        equal_var=False,
        nan_policy="omit",
    )
    welch_p_value = np.asarray(welch_result.pvalue, dtype=np.float64)

    band_table, top_table = build_band_table(
        wavelengths=subset.wavelengths,
        coefficients=coefficients,
        vip_scores=vip_scores,
        pearson_r=pearson_r,
        pearson_p_value=pearson_p_value,
        welch_p_value=welch_p_value,
        top_k=top_k,
    )

    result = SubsetResult(
        spec=spec,
        n_samples=subset.x.shape[0],
        irrigated_count=irrigated_count,
        non_irrigated_count=non_irrigated_count,
        effective_cv_splits=effective_cv_splits,
        best_components=best_components,
        best_result=best_result,
        top_table=top_table,
    )
    return result, band_table


def write_summary_markdown(path: Path, *, results: list[SubsetResult]) -> None:
    sections = [
        ("data", "Datas"),
        ("turno", "Turnos"),
        ("genotipo", "Genotipos"),
        ("turno_genotipo", "Turno x Genotipo"),
    ]
    lines = [
        "# Tabelas PLSR + Pearson + Welch t-test",
        "",
        "- Bandas ordenadas por relevancia PLSR: z(VIP) + z(|coeficiente|).",
        f"- Limite de significancia aplicado no Welch t-test: p < {P_THRESHOLD:.3f}.",
        "- Pearson foi calculado entre cada banda e a classe binaria (`irrigado`=1, `nao_irrigado`=0).",
        "",
    ]

    for family_key, family_title in sections:
        family_results = [item for item in results if item.spec.family == family_key]
        if not family_results:
            continue

        lines.extend(
            [
                f"## {family_title}",
                "",
                "| subconjunto | rank | banda | direcao | VIP | coef. PLSR | Pearson r | p Pearson | p Welch | p Welch < 0.005 |",
                "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for result in family_results:
            for row in result.top_table[:5]:
                lines.append(
                    f"| {result.spec.label} | {int(row['rank'])} | {int(row['wavelength'])} | {row['direction_label']} | "
                    f"{row['vip']:.4f} | {row['coefficient']:.6f} | {row['pearson_r']:.4f} | "
                    f"{row['pearson_p_value']:.3e} | {row['welch_p_value']:.3e} | "
                    f"{'sim' if row['welch_p_value'] < P_THRESHOLD else 'nao'} |"
                )
            lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(args.processed_csv.resolve(), args.metadata_csv.resolve())
    matched_dates = find_matched_dates(dataset.dates, dataset.shifts)
    genotypes = sorted(set(dataset.genotypes), key=lambda value: (GENOTYPE_ORDER.get(value, 999), value))
    subset_specs = build_subset_specs(matched_dates, genotypes)

    results: list[SubsetResult] = []
    full_rows: list[list[object]] = []
    top_rows: list[list[object]] = []

    for spec in subset_specs:
        result, band_table = analyze_subset(
            dataset,
            spec,
            max_components=args.max_components,
            cv_splits=args.cv_splits,
            top_k=args.top_k,
        )
        results.append(result)

        for row in np.sort(band_table, order="wavelength"):
            full_rows.append(
                [
                    spec.family,
                    spec.name,
                    spec.label,
                    ",".join(spec.dates),
                    spec.shift or "",
                    spec.genotype or "",
                    result.n_samples,
                    result.irrigated_count,
                    result.non_irrigated_count,
                    result.best_components,
                    f"{result.best_result['rmsecv']:.10f}",
                    f"{result.best_result['auc']:.10f}",
                    int(row["wavelength"]),
                    row["direction_label"],
                    f"{row['vip']:.10f}",
                    f"{row['coefficient']:.10f}",
                    f"{row['abs_coefficient']:.10f}",
                    f"{row['optimal_score']:.10f}",
                    f"{row['pearson_r']:.10f}",
                    f"{row['pearson_p_value']:.10e}",
                    f"{row['welch_p_value']:.10e}" if np.isfinite(row["welch_p_value"]) else "",
                    "1" if row["pearson_p_value"] < P_THRESHOLD else "0",
                    "1" if np.isfinite(row["welch_p_value"]) and row["welch_p_value"] < P_THRESHOLD else "0",
                ]
            )

        for row in result.top_table:
            top_rows.append(
                [
                    spec.family,
                    spec.name,
                    spec.label,
                    ",".join(spec.dates),
                    spec.shift or "",
                    spec.genotype or "",
                    result.n_samples,
                    result.irrigated_count,
                    result.non_irrigated_count,
                    result.best_components,
                    f"{result.best_result['rmsecv']:.10f}",
                    f"{result.best_result['auc']:.10f}",
                    int(row["rank"]),
                    int(row["wavelength"]),
                    row["direction_label"],
                    f"{row['vip']:.10f}",
                    f"{row['coefficient']:.10f}",
                    f"{row['optimal_score']:.10f}",
                    f"{row['pearson_r']:.10f}",
                    f"{row['pearson_p_value']:.10e}",
                    f"{row['welch_p_value']:.10e}" if np.isfinite(row["welch_p_value"]) else "",
                    "1" if row["pearson_p_value"] < P_THRESHOLD else "0",
                    "1" if np.isfinite(row["welch_p_value"]) and row["welch_p_value"] < P_THRESHOLD else "0",
                ]
            )

    results.sort(
        key=lambda item: (
            FAMILY_ORDER.get(item.spec.family, 99),
            item.spec.dates[0],
            SHIFT_ORDER.get(item.spec.shift or "", 99),
            GENOTYPE_ORDER.get(item.spec.genotype or "", 99),
            item.spec.name,
        )
    )

    write_csv(
        output_dir / "bandas_plsr_pearson_ttest_completo.csv",
        [
            "subset_family",
            "subset_name",
            "subset_label",
            "dates",
            "shift",
            "genotype",
            "n_samples",
            "irrigated_count",
            "non_irrigated_count",
            "best_components",
            "rmsecv",
            "auc",
            "wavelength",
            "direction_label",
            "vip",
            "coefficient",
            "abs_coefficient",
            "optimal_score",
            "pearson_r",
            "pearson_p_value",
            "welch_p_value",
            "pearson_p_lt_0_005",
            "welch_p_lt_0_005",
        ],
        full_rows,
    )
    write_csv(
        output_dir / "top_bandas_plsr_pearson_ttest.csv",
        [
            "subset_family",
            "subset_name",
            "subset_label",
            "dates",
            "shift",
            "genotype",
            "n_samples",
            "irrigated_count",
            "non_irrigated_count",
            "best_components",
            "rmsecv",
            "auc",
            "rank",
            "wavelength",
            "direction_label",
            "vip",
            "coefficient",
            "optimal_score",
            "pearson_r",
            "pearson_p_value",
            "welch_p_value",
            "pearson_p_lt_0_005",
            "welch_p_lt_0_005",
        ],
        top_rows,
    )
    write_summary_markdown(output_dir / "resumo_top_bandas_plsr_pearson_ttest.md", results=results)

    print(f"Output directory: {output_dir}")
    print(f"Matched dates: {', '.join(matched_dates)}")
    print(f"Subsets analyzed: {len(results)}")
    print("Outputs:")
    print(f"  - {output_dir / 'top_bandas_plsr_pearson_ttest.csv'}")
    print(f"  - {output_dir / 'bandas_plsr_pearson_ttest_completo.csv'}")
    print(f"  - {output_dir / 'resumo_top_bandas_plsr_pearson_ttest.md'}")


if __name__ == "__main__":
    main()
