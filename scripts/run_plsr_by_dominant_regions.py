#!/usr/bin/env python3
"""Run PLSR for the dominant spectral regions defined by significance thresholds."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from run_plsr_pca_irrigation import (
    calculate_vip_scores,
    evaluate_pls_components,
    fit_final_pls,
    load_dataset,
)


@dataclass(frozen=True)
class RegionSpec:
    threshold: str
    rank: int
    region_start: int
    region_end: int
    n_bands: int

    @property
    def label(self) -> str:
        threshold_token = (
            self.threshold.replace(".", "p").replace("-", "m").replace("+", "")
        )
        return (
            f"thr_{threshold_token}_rank_{self.rank:02d}_"
            f"{self.region_start}_{self.region_end}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run PLSR for each interval listed in "
            "regioes_dominantes_por_threshold.csv."
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
        "--regions-csv",
        type=Path,
        default=Path("dados_processados_soft/plsr_pca_irrigacao/regioes_dominantes_por_threshold.csv"),
        help="CSV with dominant regions by threshold.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft/plsr_intervalos_regioes_threshold"),
        help="Directory where PLSR-by-interval outputs will be written.",
    )
    parser.add_argument(
        "--max-components",
        type=int,
        default=15,
        help="Maximum number of PLS components to evaluate for each interval.",
    )
    parser.add_argument(
        "--cv-splits",
        type=int,
        default=5,
        help="Number of stratified folds for cross-validation.",
    )
    return parser.parse_args()


def read_region_specs(path: Path) -> list[RegionSpec]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        raise ValueError(f"Region CSV is empty: {path}")
    specs: list[RegionSpec] = []
    for row in rows:
        specs.append(
            RegionSpec(
                threshold=row["threshold"],
                rank=int(row["rank"]),
                region_start=int(row["region_start"]),
                region_end=int(row["region_end"]),
                n_bands=int(row["n_bands"]),
            )
        )
    return specs


def write_dict_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def evaluate_region(
    *,
    x: np.ndarray,
    y: np.ndarray,
    wavelengths: np.ndarray,
    spec: RegionSpec,
    max_components: int,
    cv_splits: int,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    mask = (wavelengths >= spec.region_start) & (wavelengths <= spec.region_end)
    selected_wavelengths = wavelengths[mask]
    x_region = x[:, mask]
    if x_region.shape[1] == 0:
        raise ValueError(
            f"Region {spec.label} has no wavelengths in the processed dataset."
        )

    cv_results, best_components = evaluate_pls_components(
        x_region,
        y,
        max_components=max_components,
        cv_splits=cv_splits,
    )
    best_result = next(
        item for item in cv_results if int(item["n_components"]) == best_components
    )

    scaler, pls, x_scaled = fit_final_pls(x_region, y, best_components)
    _ = scaler
    vip_scores = calculate_vip_scores(pls)
    coefficients = pls.coef_.ravel()
    y_fit = pls.predict(x_scaled).ravel()

    top_vip_idx = int(np.nanargmax(vip_scores))
    top_abs_coef_idx = int(np.nanargmax(np.abs(coefficients)))
    top_positive_idx = int(np.nanargmax(coefficients))
    top_negative_idx = int(np.nanargmin(coefficients))

    metric_row = {
        "interval_label": spec.label,
        "threshold": spec.threshold,
        "rank": spec.rank,
        "region_start": spec.region_start,
        "region_end": spec.region_end,
        "n_bands_csv": spec.n_bands,
        "n_bands_used": int(x_region.shape[1]),
        "best_components": int(best_components),
        "rmsecv": float(best_result["rmsecv"]),
        "r2cv": float(best_result["r2cv"]),
        "auc": float(best_result["auc"]),
        "accuracy": float(best_result["accuracy"]),
        "top_vip_band": int(selected_wavelengths[top_vip_idx]),
        "top_vip": float(vip_scores[top_vip_idx]),
        "top_abs_coef_band": int(selected_wavelengths[top_abs_coef_idx]),
        "top_abs_coef": float(np.abs(coefficients[top_abs_coef_idx])),
        "top_positive_band": int(selected_wavelengths[top_positive_idx]),
        "top_positive_coef": float(coefficients[top_positive_idx]),
        "top_negative_band": int(selected_wavelengths[top_negative_idx]),
        "top_negative_coef": float(coefficients[top_negative_idx]),
        "fit_mean_pred": float(np.mean(y_fit)),
    }

    cv_rows: list[dict[str, object]] = []
    for item in cv_results:
        cv_rows.append(
            {
                "interval_label": spec.label,
                "threshold": spec.threshold,
                "rank": spec.rank,
                "region_start": spec.region_start,
                "region_end": spec.region_end,
                "n_components": int(item["n_components"]),
                "rmsecv": float(item["rmsecv"]),
                "r2cv": float(item["r2cv"]),
                "auc": float(item["auc"]),
                "accuracy": float(item["accuracy"]),
            }
        )

    band_rows: list[dict[str, object]] = []
    for wavelength, coefficient, vip_score in zip(
        selected_wavelengths,
        coefficients,
        vip_scores,
        strict=True,
    ):
        band_rows.append(
            {
                "interval_label": spec.label,
                "threshold": spec.threshold,
                "rank": spec.rank,
                "region_start": spec.region_start,
                "region_end": spec.region_end,
                "wavelength": int(wavelength),
                "coefficient": float(coefficient),
                "abs_coefficient": float(abs(coefficient)),
                "vip": float(vip_score),
                "direction": "irrigado" if coefficient >= 0 else "nao_irrigado",
            }
        )

    return metric_row, cv_rows, band_rows


def write_summary_markdown(
    path: Path,
    *,
    processed_csv: Path,
    metadata_csv: Path,
    regions_csv: Path,
    metric_rows: list[dict[str, object]],
) -> None:
    sorted_by_auc = sorted(metric_rows, key=lambda item: (-float(item["auc"]), float(item["rmsecv"])))
    sorted_by_rmse = sorted(metric_rows, key=lambda item: (float(item["rmsecv"]), -float(item["auc"])))
    best_auc = sorted_by_auc[0]
    best_rmse = sorted_by_rmse[0]

    best_per_threshold: list[dict[str, object]] = []
    seen_thresholds: set[str] = set()
    for row in sorted_by_auc:
        threshold = str(row["threshold"])
        if threshold in seen_thresholds:
            continue
        seen_thresholds.add(threshold)
        best_per_threshold.append(row)

    lines = [
        "# PLSR por intervalos de regioes dominantes",
        "",
        f"- Dataset processado: `{processed_csv}`",
        f"- Metadados: `{metadata_csv}`",
        f"- Intervalos de entrada: `{regions_csv}`",
        f"- Total de intervalos avaliados: `{len(metric_rows)}`",
        "",
        "## Melhor intervalo por AUC",
        "",
        (
            f"- `{best_auc['interval_label']}` | threshold `{best_auc['threshold']}` | "
            f"faixa `{best_auc['region_start']}-{best_auc['region_end']} nm` | "
            f"AUC `{float(best_auc['auc']):.6f}` | RMSECV `{float(best_auc['rmsecv']):.6f}` | "
            f"R2CV `{float(best_auc['r2cv']):.6f}` | Accuracy `{float(best_auc['accuracy']):.6f}`"
        ),
        "",
        "## Melhor intervalo por RMSECV",
        "",
        (
            f"- `{best_rmse['interval_label']}` | threshold `{best_rmse['threshold']}` | "
            f"faixa `{best_rmse['region_start']}-{best_rmse['region_end']} nm` | "
            f"RMSECV `{float(best_rmse['rmsecv']):.6f}` | AUC `{float(best_rmse['auc']):.6f}` | "
            f"R2CV `{float(best_rmse['r2cv']):.6f}` | Accuracy `{float(best_rmse['accuracy']):.6f}`"
        ),
        "",
        "## Melhores por threshold",
        "",
        "| threshold | faixa (nm) | bandas | comp. | AUC | RMSECV | R2CV | accuracy | top VIP | top abs coef |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in best_per_threshold:
        lines.append(
            "| "
            f"{row['threshold']} | "
            f"{row['region_start']}-{row['region_end']} | "
            f"{row['n_bands_used']} | "
            f"{row['best_components']} | "
            f"{float(row['auc']):.6f} | "
            f"{float(row['rmsecv']):.6f} | "
            f"{float(row['r2cv']):.6f} | "
            f"{float(row['accuracy']):.6f} | "
            f"{row['top_vip_band']} | "
            f"{row['top_abs_coef_band']} |"
        )

    lines.extend(
        [
            "",
            "## Top 15 intervalos por AUC",
            "",
            "| rank AUC | threshold | rank regiao | faixa (nm) | comp. | AUC | RMSECV | R2CV | accuracy |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for position, row in enumerate(sorted_by_auc[:15], start=1):
        lines.append(
            "| "
            f"{position} | "
            f"{row['threshold']} | "
            f"{row['rank']} | "
            f"{row['region_start']}-{row['region_end']} | "
            f"{row['best_components']} | "
            f"{float(row['auc']):.6f} | "
            f"{float(row['rmsecv']):.6f} | "
            f"{float(row['r2cv']):.6f} | "
            f"{float(row['accuracy']):.6f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    processed_csv = args.processed_csv.resolve()
    metadata_csv = args.metadata_csv.resolve()
    regions_csv = args.regions_csv.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(processed_csv, metadata_csv)
    specs = read_region_specs(regions_csv)

    metric_rows: list[dict[str, object]] = []
    cv_rows: list[dict[str, object]] = []
    band_rows: list[dict[str, object]] = []

    for spec in specs:
        metric_row, region_cv_rows, region_band_rows = evaluate_region(
            x=dataset.x,
            y=dataset.y,
            wavelengths=dataset.wavelengths,
            spec=spec,
            max_components=args.max_components,
            cv_splits=args.cv_splits,
        )
        metric_rows.append(metric_row)
        cv_rows.extend(region_cv_rows)
        band_rows.extend(region_band_rows)
        print(
            f"[{spec.threshold} | rank {spec.rank:02d}] "
            f"{spec.region_start}-{spec.region_end} nm | "
            f"AUC={float(metric_row['auc']):.6f} | "
            f"RMSECV={float(metric_row['rmsecv']):.6f}"
        )

    metric_rows_sorted = sorted(
        metric_rows,
        key=lambda item: (-float(item["auc"]), float(item["rmsecv"]), int(item["rank"])),
    )

    write_dict_csv(
        output_dir / "metricas_plsr_por_intervalo.csv",
        [
            "interval_label",
            "threshold",
            "rank",
            "region_start",
            "region_end",
            "n_bands_csv",
            "n_bands_used",
            "best_components",
            "rmsecv",
            "r2cv",
            "auc",
            "accuracy",
            "top_vip_band",
            "top_vip",
            "top_abs_coef_band",
            "top_abs_coef",
            "top_positive_band",
            "top_positive_coef",
            "top_negative_band",
            "top_negative_coef",
            "fit_mean_pred",
        ],
        metric_rows_sorted,
    )
    write_dict_csv(
        output_dir / "curva_componentes_plsr_por_intervalo.csv",
        [
            "interval_label",
            "threshold",
            "rank",
            "region_start",
            "region_end",
            "n_components",
            "rmsecv",
            "r2cv",
            "auc",
            "accuracy",
        ],
        cv_rows,
    )
    write_dict_csv(
        output_dir / "bandas_plsr_por_intervalo.csv",
        [
            "interval_label",
            "threshold",
            "rank",
            "region_start",
            "region_end",
            "wavelength",
            "coefficient",
            "abs_coefficient",
            "vip",
            "direction",
        ],
        band_rows,
    )
    write_summary_markdown(
        output_dir / "resumo_plsr_intervalos.md",
        processed_csv=processed_csv,
        metadata_csv=metadata_csv,
        regions_csv=regions_csv,
        metric_rows=metric_rows_sorted,
    )

    print(f"Output directory: {output_dir}")
    print(f"Intervals evaluated: {len(metric_rows_sorted)}")
    print(f"Best interval by AUC: {metric_rows_sorted[0]['interval_label']}")


if __name__ == "__main__":
    main()
