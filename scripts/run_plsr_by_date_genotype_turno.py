#!/usr/bin/env python3
"""Run irrigation PLSR for every date x genotype x shift subset."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from run_plsr_pca_irrigation import (
    calculate_vip_scores,
    evaluate_pls_components,
    fit_final_pls,
    load_dataset,
    subset_dataset,
)


SHIFT_ORDER = {"manha": 0, "tarde": 1}
GENOTYPE_ORDER = {"BR16": 0, "CD202": 1, "EMB48": 2}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run PLSR for every date x genotype x turno subset to discriminate "
            "irrigado vs nao_irrigado."
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
        help="Normalized metadata aligned with the processed dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft/plsr_data_genotipo_turno"),
        help="Directory where consolidated outputs will be written.",
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
        default=5,
        help="Number of top bands to export per subset.",
    )
    return parser.parse_args()


def write_dict_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def robust_zscore(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    mean = np.nanmean(values)
    std = np.nanstd(values)
    if np.isclose(std, 0.0):
        return np.zeros_like(values)
    return (values - mean) / std


def build_top_band_rows(
    *,
    data_coleta_iso: str,
    genotipo: str,
    turno: str,
    wavelengths: np.ndarray,
    coefficients: np.ndarray,
    vip_scores: np.ndarray,
    top_k: int,
) -> list[dict[str, object]]:
    scores = robust_zscore(vip_scores) + robust_zscore(np.abs(coefficients))
    order = np.lexsort((-np.abs(coefficients), -vip_scores, -scores))
    top_indices = order[:top_k]
    rows: list[dict[str, object]] = []
    for rank, idx in enumerate(top_indices, start=1):
        coefficient = float(coefficients[idx])
        rows.append(
            {
                "data_coleta_iso": data_coleta_iso,
                "genotipo": genotipo,
                "turno": turno,
                "rank": rank,
                "wavelength": int(wavelengths[idx]),
                "vip": float(vip_scores[idx]),
                "coefficient": coefficient,
                "abs_coefficient": float(abs(coefficient)),
                "score": float(scores[idx]),
                "direction": "irrigado" if coefficient >= 0 else "nao_irrigado",
            }
        )
    return rows


def write_summary_markdown(
    path: Path,
    rows: list[dict[str, object]],
    top_band_rows: list[dict[str, object]],
) -> None:
    sorted_rows = sorted(
        rows,
        key=lambda item: (
            str(item["data_coleta_iso"]),
            GENOTYPE_ORDER.get(str(item["genotipo"]), 99),
            SHIFT_ORDER.get(str(item["turno"]), 99),
        ),
    )
    best_row = max(rows, key=lambda item: float(item["r2cv"]))
    worst_row = min(rows, key=lambda item: float(item["r2cv"]))

    lines = [
        "# PLSR por data x genotipo x turno",
        "",
        f"- Subconjuntos avaliados: `{len(rows)}`",
        "",
        "## Melhor R2CV",
        "",
        (
            f"- `{best_row['data_coleta_iso']} | {best_row['genotipo']} | {best_row['turno']}` | "
            f"R2CV `{float(best_row['r2cv']):.6f}` | RMSECV `{float(best_row['rmsecv']):.6f}` | "
            f"AUC `{float(best_row['auc']):.6f}` | Accuracy `{float(best_row['accuracy']):.6f}`"
        ),
        "",
        "## Pior R2CV",
        "",
        (
            f"- `{worst_row['data_coleta_iso']} | {worst_row['genotipo']} | {worst_row['turno']}` | "
            f"R2CV `{float(worst_row['r2cv']):.6f}` | RMSECV `{float(worst_row['rmsecv']):.6f}` | "
            f"AUC `{float(worst_row['auc']):.6f}` | Accuracy `{float(worst_row['accuracy']):.6f}`"
        ),
        "",
        "## Tabela consolidada",
        "",
        "| data | genotipo | turno | n | irrigado | nao_irrigado | folds | comp. | R2CV | RMSECV | AUC | accuracy |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted_rows:
        lines.append(
            "| "
            f"{row['data_coleta_iso']} | "
            f"{row['genotipo']} | "
            f"{row['turno']} | "
            f"{row['n_samples']} | "
            f"{row['irrigated_count']} | "
            f"{row['non_irrigated_count']} | "
            f"{row['effective_cv_splits']} | "
            f"{row['best_components']} | "
            f"{float(row['r2cv']):.6f} | "
            f"{float(row['rmsecv']):.6f} | "
            f"{float(row['auc']):.6f} | "
            f"{float(row['accuracy']):.6f} |"
        )

    lines.extend(
        [
            "",
            "## Top 5 bandas por subconjunto",
            "",
            "| data | genotipo | turno | top 5 bandas (nm) |",
            "| --- | --- | --- | --- |",
        ]
    )
    grouped_top_rows: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in top_band_rows:
        key = (
            str(row["data_coleta_iso"]),
            str(row["genotipo"]),
            str(row["turno"]),
        )
        grouped_top_rows.setdefault(key, []).append(row)
    for key in sorted(
        grouped_top_rows,
        key=lambda item: (
            item[0],
            GENOTYPE_ORDER.get(item[1], 99),
            SHIFT_ORDER.get(item[2], 99),
        ),
    ):
        subset_rows = sorted(grouped_top_rows[key], key=lambda item: int(item["rank"]))
        top_bands = ", ".join(str(row["wavelength"]) for row in subset_rows)
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {top_bands} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(args.processed_csv.resolve(), args.metadata_csv.resolve())
    dates = sorted(set(dataset.dates))
    genotypes = sorted(set(dataset.genotypes), key=lambda value: (GENOTYPE_ORDER.get(value, 99), value))
    shifts = sorted(set(dataset.shifts), key=lambda value: (SHIFT_ORDER.get(value, 99), value))

    metric_rows: list[dict[str, object]] = []
    curve_rows: list[dict[str, object]] = []
    top_band_rows: list[dict[str, object]] = []

    for date_value in dates:
        for genotype_value in genotypes:
            for shift_value in shifts:
                mask = np.asarray(
                    [
                        row_date == date_value
                        and row_genotype == genotype_value
                        and row_shift == shift_value
                        for row_date, row_genotype, row_shift in zip(
                            dataset.dates,
                            dataset.genotypes,
                            dataset.shifts,
                            strict=True,
                        )
                    ],
                    dtype=bool,
                )
                subset = subset_dataset(dataset, mask)
                irrigated_count = int(np.sum(subset.y == 1))
                non_irrigated_count = int(np.sum(subset.y == 0))
                min_class_count = min(irrigated_count, non_irrigated_count)
                if subset.x.shape[0] == 0 or min_class_count < 2:
                    continue

                effective_cv_splits = min(args.cv_splits, min_class_count)
                cv_results, best_components = evaluate_pls_components(
                    subset.x,
                    subset.y,
                    max_components=args.max_components,
                    cv_splits=effective_cv_splits,
                )
                best_result = next(
                    item for item in cv_results if int(item["n_components"]) == best_components
                )
                scaler, pls, x_scaled = fit_final_pls(subset.x, subset.y, best_components)
                del scaler, x_scaled
                vip_scores = calculate_vip_scores(pls)
                coefficients = pls.coef_.ravel()

                metric_row = {
                    "data_coleta_iso": date_value,
                    "genotipo": genotype_value,
                    "turno": shift_value,
                    "n_samples": int(subset.x.shape[0]),
                    "irrigated_count": irrigated_count,
                    "non_irrigated_count": non_irrigated_count,
                    "effective_cv_splits": int(effective_cv_splits),
                    "best_components": int(best_components),
                    "rmsecv": float(best_result["rmsecv"]),
                    "r2cv": float(best_result["r2cv"]),
                    "auc": float(best_result["auc"]),
                    "accuracy": float(best_result["accuracy"]),
                }
                metric_rows.append(metric_row)
                top_band_rows.extend(
                    build_top_band_rows(
                        data_coleta_iso=date_value,
                        genotipo=genotype_value,
                        turno=shift_value,
                        wavelengths=subset.wavelengths,
                        coefficients=coefficients,
                        vip_scores=vip_scores,
                        top_k=args.top_k,
                    )
                )

                for item in cv_results:
                    curve_rows.append(
                        {
                            "data_coleta_iso": date_value,
                            "genotipo": genotype_value,
                            "turno": shift_value,
                            "n_components": int(item["n_components"]),
                            "rmsecv": float(item["rmsecv"]),
                            "r2cv": float(item["r2cv"]),
                            "auc": float(item["auc"]),
                            "accuracy": float(item["accuracy"]),
                        }
                    )

                print(
                    f"{date_value} | {genotype_value} | {shift_value} | "
                    f"R2CV={float(best_result['r2cv']):.6f} | "
                    f"RMSECV={float(best_result['rmsecv']):.6f} | "
                    f"AUC={float(best_result['auc']):.6f}"
                )

    metric_rows.sort(
        key=lambda item: (
            str(item["data_coleta_iso"]),
            GENOTYPE_ORDER.get(str(item["genotipo"]), 99),
            SHIFT_ORDER.get(str(item["turno"]), 99),
        )
    )

    write_dict_csv(
        output_dir / "metricas_plsr_data_genotipo_turno.csv",
        [
            "data_coleta_iso",
            "genotipo",
            "turno",
            "n_samples",
            "irrigated_count",
            "non_irrigated_count",
            "effective_cv_splits",
            "best_components",
            "rmsecv",
            "r2cv",
            "auc",
            "accuracy",
        ],
        metric_rows,
    )
    write_dict_csv(
        output_dir / "curvas_componentes_plsr_data_genotipo_turno.csv",
        [
            "data_coleta_iso",
            "genotipo",
            "turno",
            "n_components",
            "rmsecv",
            "r2cv",
            "auc",
            "accuracy",
        ],
        curve_rows,
    )
    write_dict_csv(
        output_dir / "top_bandas_plsr_data_genotipo_turno.csv",
        [
            "data_coleta_iso",
            "genotipo",
            "turno",
            "rank",
            "wavelength",
            "vip",
            "coefficient",
            "abs_coefficient",
            "score",
            "direction",
        ],
        top_band_rows,
    )
    write_summary_markdown(
        output_dir / "resumo_plsr_data_genotipo_turno.md",
        metric_rows,
        top_band_rows,
    )

    print(f"Output directory: {output_dir}")
    print(f"Subsets evaluated: {len(metric_rows)}")


if __name__ == "__main__":
    main()
