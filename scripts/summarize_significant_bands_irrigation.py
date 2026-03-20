#!/usr/bin/env python3
"""Summarize the most significant bands for irrigated vs non-irrigated classes."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import ttest_ind

from run_plsr_pca_irrigation import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a top-20 candidate-band table combining PLS importance and "
            "univariate significance for irrigated vs non-irrigated classes."
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
        "--plsr-bands-csv",
        type=Path,
        default=Path("dados_processados_soft/plsr_pca_irrigacao/plsr_bandas_importantes.csv"),
        help="PLSR band-importance table.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft/plsr_pca_irrigacao"),
        help="Directory where the summary outputs will be written.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of candidate bands to keep in the final table.",
    )
    return parser.parse_args()


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
    adjusted_values = np.empty_like(finite_values)
    adjusted_values[order] = adjusted_sorted
    adjusted[finite_mask] = adjusted_values
    return adjusted


def safe_neg_log10(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 1e-300, 1.0)
    return -np.log10(clipped)


def robust_zscore(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    mean = np.nanmean(values)
    std = np.nanstd(values)
    if np.isclose(std, 0.0):
        return np.zeros_like(values)
    return (values - mean) / std


def load_plsr_band_metrics(path: Path) -> dict[int, dict[str, float | str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            int(row["wavelength"]): {
                "coefficient": float(row["coefficient"]),
                "abs_coefficient": float(row["abs_coefficient"]),
                "vip": float(row["vip"]),
                "direction": row["direction"],
            }
            for row in reader
        }


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def plot_volcano(table: np.ndarray, top_wavelengths: set[int], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.5), constrained_layout=True)
    positive = table["mean_diff"] >= 0
    negative = ~positive
    significance = safe_neg_log10(table["q_value"])

    ax.scatter(
        table["mean_diff"][negative],
        significance[negative],
        s=12,
        alpha=0.45,
        color="#c2410c",
        label="mais associado a nao_irrigado",
    )
    ax.scatter(
        table["mean_diff"][positive],
        significance[positive],
        s=12,
        alpha=0.45,
        color="#0f766e",
        label="mais associado a irrigado",
    )

    top_mask = np.asarray([int(w) in top_wavelengths for w in table["wavelength"]])
    ax.scatter(
        table["mean_diff"][top_mask],
        significance[top_mask],
        s=38,
        facecolors="none",
        edgecolors="#111827",
        linewidths=1.0,
        label="top 20 candidatas",
    )

    for row in table[top_mask]:
        ax.annotate(
            str(int(row["wavelength"])),
            (row["mean_diff"], -np.log10(max(row["q_value"], 1e-300))),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
            color="#111827",
        )

    ax.set_xlabel("Diferenca de media processada (irrigado - nao_irrigado)")
    ax.set_ylabel("-log10(q-value FDR)")
    ax.set_title("Significancia univariada por banda")
    ax.grid(alpha=0.18)
    ax.legend(loc="best")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_top20(top_table: np.ndarray, output_path: Path) -> None:
    order = np.arange(top_table.shape[0])[::-1]
    labels = [str(int(value)) for value in top_table["wavelength"][order]]
    colors = ["#0f766e" if value >= 0 else "#c2410c" for value in top_table["mean_diff"][order]]
    fig, ax = plt.subplots(figsize=(10.5, 8), constrained_layout=True)
    ax.barh(labels, top_table["combined_score"][order], color=colors)
    ax.set_xlabel("Score combinado (VIP + |Cohen's d| + significancia)")
    ax.set_title("Top 20 bandas candidatas para diferenciar irrigado vs nao_irrigado")
    ax.grid(alpha=0.18, axis="x")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def write_summary_markdown(
    path: Path,
    *,
    top_table: np.ndarray,
    region_table: np.ndarray,
    total_significant: int,
    vip_significant: int,
) -> None:
    lines = [
        "# Bandas mais significativas: irrigado vs nao_irrigado",
        "",
        "- Criterios usados:",
        "  - significancia univariada por banda: Welch t-test com correcao FDR (Benjamini-Hochberg)",
        "  - tamanho de efeito: Cohen's d",
        "  - relevancia multivariada: VIP e coeficientes do PLSR",
        "- Score combinado da tabela final: z(VIP) + z(|Cohen's d|) + z(-log10(q-value))",
        f"- Bandas com q-value < 0.05: {total_significant}",
        f"- Bandas com q-value < 0.05 e VIP >= 1.0: {vip_significant}",
        "",
        "## Top 20 bandas candidatas",
        "",
        "| rank | banda | direcao | VIP | Cohen's d | q-value | score combinado |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]

    for row in top_table:
        lines.append(
            f"| {int(row['rank'])} | {int(row['wavelength'])} | {row['direction_label']} | "
            f"{row['vip']:.4f} | {row['cohen_d']:.4f} | {row['q_value']:.3e} | {row['combined_score']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Regioes espectrais dominantes",
            "",
            "| regiao | n bandas | banda pico | direcao dominante | VIP medio | |d| medio | menor q-value |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
        ]
    )

    for row in region_table[:15]:
        lines.append(
            f"| {int(row['start_wavelength'])}-{int(row['end_wavelength'])} | {int(row['band_count'])} | "
            f"{int(row['peak_wavelength'])} | {row['dominant_direction']} | {row['mean_vip']:.4f} | "
            f"{row['mean_abs_d']:.4f} | {row['min_q_value']:.3e} |"
        )

    lines.extend(
        [
            "",
            "## Leitura da analise",
            "",
            "- No dataset processado, a separacao irrigado vs nao_irrigado aparece tanto em bandas isoladas quanto em blocos contiguos de comprimentos de onda.",
            "- As regioes mais fortes combinando significancia univariada e relevancia no PLSR se concentram principalmente em 2270-2280 nm, 1660-1666 nm e 1420-1439 nm.",
            "- Direcao positiva do sinal processado indica maior associacao com irrigado; direcao negativa indica maior associacao com nao_irrigado.",
            "- Como os dados estao em SNV + Savitzky-Golay + 1a derivada, a interpretacao e sobre o sinal processado, nao sobre reflectancia bruta.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(args.processed_csv.resolve(), args.metadata_csv.resolve())
    plsr_metrics = load_plsr_band_metrics(args.plsr_bands_csv.resolve())

    irrigated = dataset.x[dataset.y == 1]
    non_irrigated = dataset.x[dataset.y == 0]

    mean_irrigated = irrigated.mean(axis=0)
    mean_non_irrigated = non_irrigated.mean(axis=0)
    mean_diff = mean_irrigated - mean_non_irrigated

    variance_irrigated = irrigated.var(axis=0, ddof=1)
    variance_non_irrigated = non_irrigated.var(axis=0, ddof=1)
    pooled_std = np.sqrt(
        (
            ((irrigated.shape[0] - 1) * variance_irrigated)
            + ((non_irrigated.shape[0] - 1) * variance_non_irrigated)
        )
        / (irrigated.shape[0] + non_irrigated.shape[0] - 2)
    )
    cohen_d = np.divide(
        mean_diff,
        pooled_std,
        out=np.zeros_like(mean_diff),
        where=pooled_std > 0,
    )

    test_result = ttest_ind(
        irrigated,
        non_irrigated,
        axis=0,
        equal_var=False,
        nan_policy="omit",
    )
    p_values = np.asarray(test_result.pvalue, dtype=np.float64)
    q_values = benjamini_hochberg(p_values)

    dtype = np.dtype(
        [
            ("wavelength", np.float64),
            ("vip", np.float64),
            ("coefficient", np.float64),
            ("abs_coefficient", np.float64),
            ("mean_irrigated", np.float64),
            ("mean_non_irrigated", np.float64),
            ("mean_diff", np.float64),
            ("cohen_d", np.float64),
            ("abs_cohen_d", np.float64),
            ("p_value", np.float64),
            ("q_value", np.float64),
            ("neg_log10_q", np.float64),
            ("combined_score", np.float64),
            ("rank", np.int32),
            ("direction_label", "U20"),
        ]
    )

    table = np.empty(dataset.wavelengths.shape[0], dtype=dtype)
    table["wavelength"] = dataset.wavelengths
    table["vip"] = np.asarray([plsr_metrics[int(w)]["vip"] for w in dataset.wavelengths], dtype=np.float64)
    table["coefficient"] = np.asarray(
        [plsr_metrics[int(w)]["coefficient"] for w in dataset.wavelengths], dtype=np.float64
    )
    table["abs_coefficient"] = np.abs(table["coefficient"])
    table["mean_irrigated"] = mean_irrigated
    table["mean_non_irrigated"] = mean_non_irrigated
    table["mean_diff"] = mean_diff
    table["cohen_d"] = cohen_d
    table["abs_cohen_d"] = np.abs(cohen_d)
    table["p_value"] = p_values
    table["q_value"] = q_values
    table["neg_log10_q"] = safe_neg_log10(q_values)
    table["direction_label"] = np.where(mean_diff >= 0, "irrigado", "nao_irrigado")

    finite_mask = np.isfinite(table["q_value"])
    significant_mask = finite_mask & (table["q_value"] < 0.05)
    vip_significant_mask = significant_mask & (table["vip"] >= 1.0)

    combined_score = (
        robust_zscore(table["vip"])
        + robust_zscore(table["abs_cohen_d"])
        + robust_zscore(table["neg_log10_q"])
    )
    table["combined_score"] = combined_score

    candidate_table = np.sort(table[vip_significant_mask], order="combined_score")[::-1]
    top_table = candidate_table[: args.top_k].copy()
    top_table["rank"] = np.arange(1, top_table.shape[0] + 1)

    full_table_path = output_dir / "bandas_significativas_completo.csv"
    top_table_path = output_dir / "top_20_bandas_candidatas_irrigacao.csv"
    region_table_path = output_dir / "regioes_espectrais_significativas.csv"
    summary_path = output_dir / "resumo_bandas_significativas.md"
    volcano_path = output_dir / "volcano_bandas_irrigacao.png"
    top_plot_path = output_dir / "top_20_bandas_candidatas.png"

    write_csv(
        full_table_path,
        [
            "wavelength",
            "vip",
            "coefficient",
            "abs_coefficient",
            "mean_irrigated",
            "mean_non_irrigated",
            "mean_diff",
            "cohen_d",
            "abs_cohen_d",
            "p_value",
            "q_value",
            "neg_log10_q",
            "combined_score",
            "direction_label",
        ],
        [
            [
                int(row["wavelength"]),
                f"{row['vip']:.10f}",
                f"{row['coefficient']:.10f}",
                f"{row['abs_coefficient']:.10f}",
                f"{row['mean_irrigated']:.10f}",
                f"{row['mean_non_irrigated']:.10f}",
                f"{row['mean_diff']:.10f}",
                f"{row['cohen_d']:.10f}",
                f"{row['abs_cohen_d']:.10f}",
                f"{row['p_value']:.10e}" if np.isfinite(row["p_value"]) else "",
                f"{row['q_value']:.10e}" if np.isfinite(row["q_value"]) else "",
                f"{row['neg_log10_q']:.10f}" if np.isfinite(row["neg_log10_q"]) else "",
                f"{row['combined_score']:.10f}",
                row["direction_label"],
            ]
            for row in np.sort(table, order="wavelength")
        ],
    )

    write_csv(
        top_table_path,
        [
            "rank",
            "wavelength",
            "direction_label",
            "vip",
            "coefficient",
            "mean_irrigated",
            "mean_non_irrigated",
            "mean_diff",
            "cohen_d",
            "p_value",
            "q_value",
            "combined_score",
        ],
        [
            [
                int(row["rank"]),
                int(row["wavelength"]),
                row["direction_label"],
                f"{row['vip']:.10f}",
                f"{row['coefficient']:.10f}",
                f"{row['mean_irrigated']:.10f}",
                f"{row['mean_non_irrigated']:.10f}",
                f"{row['mean_diff']:.10f}",
                f"{row['cohen_d']:.10f}",
                f"{row['p_value']:.10e}" if np.isfinite(row["p_value"]) else "",
                f"{row['q_value']:.10e}" if np.isfinite(row["q_value"]) else "",
                f"{row['combined_score']:.10f}",
            ]
            for row in top_table
        ],
    )

    significant_regions = []
    selected = np.sort(table[vip_significant_mask], order="wavelength")
    if selected.size > 0:
        start = selected[0]["wavelength"]
        end = start
        bucket = [selected[0]]
        for row in selected[1:]:
            wavelength = row["wavelength"]
            if wavelength == end + 1:
                bucket.append(row)
                end = wavelength
            else:
                significant_regions.append(bucket)
                bucket = [row]
                start = wavelength
                end = wavelength
        significant_regions.append(bucket)

    region_dtype = np.dtype(
        [
            ("start_wavelength", np.float64),
            ("end_wavelength", np.float64),
            ("band_count", np.int32),
            ("peak_wavelength", np.float64),
            ("peak_score", np.float64),
            ("dominant_direction", "U20"),
            ("mean_vip", np.float64),
            ("mean_abs_d", np.float64),
            ("min_q_value", np.float64),
        ]
    )
    region_table = np.empty(len(significant_regions), dtype=region_dtype)
    for index, bucket in enumerate(significant_regions):
        bucket_array = np.array(bucket, dtype=table.dtype)
        peak = bucket_array[np.argmax(bucket_array["combined_score"])]
        positive_count = np.sum(bucket_array["mean_diff"] >= 0)
        dominant_direction = (
            "irrigado" if positive_count >= (bucket_array.shape[0] / 2) else "nao_irrigado"
        )
        region_table[index] = (
            bucket_array["wavelength"][0],
            bucket_array["wavelength"][-1],
            bucket_array.shape[0],
            peak["wavelength"],
            peak["combined_score"],
            dominant_direction,
            float(np.mean(bucket_array["vip"])),
            float(np.mean(bucket_array["abs_cohen_d"])),
            float(np.min(bucket_array["q_value"])),
        )
    region_table = np.sort(region_table, order="peak_score")[::-1]

    write_csv(
        region_table_path,
        [
            "start_wavelength",
            "end_wavelength",
            "band_count",
            "peak_wavelength",
            "peak_score",
            "dominant_direction",
            "mean_vip",
            "mean_abs_d",
            "min_q_value",
        ],
        [
            [
                int(row["start_wavelength"]),
                int(row["end_wavelength"]),
                int(row["band_count"]),
                int(row["peak_wavelength"]),
                f"{row['peak_score']:.10f}",
                row["dominant_direction"],
                f"{row['mean_vip']:.10f}",
                f"{row['mean_abs_d']:.10f}",
                f"{row['min_q_value']:.10e}",
            ]
            for row in region_table
        ],
    )

    plot_volcano(table, {int(value) for value in top_table["wavelength"]}, volcano_path)
    plot_top20(top_table, top_plot_path)
    write_summary_markdown(
        summary_path,
        top_table=top_table,
        region_table=region_table,
        total_significant=int(np.sum(significant_mask)),
        vip_significant=int(np.sum(vip_significant_mask)),
    )

    print(f"Output directory: {output_dir}")
    print(f"Significant bands (q < 0.05): {int(np.sum(significant_mask))}")
    print(f"Significant bands with VIP >= 1.0: {int(np.sum(vip_significant_mask))}")
    print(f"Top table: {top_table_path}")
    print(f"Regions table: {region_table_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
