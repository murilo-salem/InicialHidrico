#!/usr/bin/env python3
"""Run the band-significance pipeline for irrigated vs non-irrigated samples."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from band_significance import (
    BandSignificanceResult,
    plot_top_bands,
    run_band_significance_analysis,
    write_rows_csv,
    write_summary_markdown,
)
from run_plsr_pca_irrigation import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run band significance analysis using Kruskal-Wallis, Pearson, Spearman and t-test."
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
        default=Path("dados_processados_soft/plsr_pca_irrigacao/band_significance"),
        help="Directory where the outputs will be written.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level.",
    )
    parser.add_argument(
        "--p-adjust-method",
        type=str,
        default="fdr_bh",
        help="Multiple-testing correction method: fdr_bh or bonferroni.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(args.processed_csv.resolve(), args.metadata_csv.resolve())
    band_columns = [str(int(wavelength)) for wavelength in dataset.wavelengths]
    data = {column: dataset.x[:, index] for index, column in enumerate(band_columns)}
    data["target"] = dataset.y.astype(np.int32)

    result: BandSignificanceResult = run_band_significance_analysis(
        data,
        band_columns=band_columns,
        target_column="target",
        target_type="binary",
        alpha=args.alpha,
        class_names=("nao_irrigado", "irrigado"),
        p_adjust_method=args.p_adjust_method,
    )

    all_csv = output_dir / "band_significance_ranking.csv"
    significant_csv = output_dir / f"band_significance_significant_alpha_{str(args.alpha).replace('.', '_')}.csv"
    top_csv = output_dir / "band_significance_top20.csv"
    summary_md = output_dir / "resumo_band_significance.md"
    plot_path = output_dir / "band_significance_top20.png"

    write_rows_csv(all_csv, result.rows)
    write_rows_csv(significant_csv, [row for row in result.rows if row["significant_at_alpha"]])
    write_rows_csv(top_csv, result.rows[:20])
    write_summary_markdown(summary_md, result=result, top_n=20, alpha=args.alpha)
    plot_top_bands(result.rows, plot_path, top_n=20)

    sig_count = sum(1 for row in result.rows if row["significant_at_alpha"])
    print(f"Output directory: {output_dir}")
    print(f"Samples: {dataset.x.shape[0]} | Bands: {dataset.x.shape[1]}")
    print(f"Significant bands at alpha={args.alpha:.3f}: {sig_count}")
    print(f"Top band: {result.rows[0]['band']} | score={result.rows[0]['ranking_score']:.4f} | p_adj={result.rows[0]['pvalue_adjusted']:.3e}")
    print(f"CSV: {all_csv}")
    print(f"Summary: {summary_md}")
    print(f"Plot: {plot_path}")


if __name__ == "__main__":
    main()
