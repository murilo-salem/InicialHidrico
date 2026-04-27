#!/usr/bin/env python3
"""Reduce the classification band set with univariate statistical tests.

This script restricts the analysis to the exact spectral bands already used by
the 6-class classifier, then computes:

- Welch t-test for IRR vs NIRR
- Kruskal-Wallis for classes A-F
- LDA benchmarks for reduced subsets
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kruskal, ttest_ind
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.impute import SimpleImputer
from sklearn.metrics import cohen_kappa_score, f1_score, make_scorer
from sklearn.model_selection import StratifiedGroupKFold, cross_validate
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
CLASS_ORDER = ["A", "B", "C", "D", "E", "F"]


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    parser = argparse.ArgumentParser(
        description="Aplica p-test nas bandas da classificacao e avalia subconjuntos reduzidos."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
        help="CSV usado na classificacao 6x6.",
    )
    parser.add_argument(
        "--features-csv",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "features_classificacao.csv",
        help="Manifesto de features da classificacao atual.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "reducao_bandas_p_teste",
        help="Diretorio para salvar a analise.",
    )
    return parser.parse_args()


def ensure_class_columns(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    if "classe" not in frame.columns or "classe_legenda" not in frame.columns:
        labels = frame.apply(lambda row: CLASS_LABELS[(row["cultivar"], row["condicao"])], axis=1)
        frame["classe"] = [item[0] for item in labels]
        frame["classe_legenda"] = [item[1] for item in labels]
    if "grupo_cv" not in frame.columns:
        frame["grupo_cv"] = frame["classe"] + "_B" + frame["replicata"].astype(str)
    return frame


def adjust_pvalues_bh(pvalues: np.ndarray) -> np.ndarray:
    adjusted = np.full_like(pvalues, np.nan, dtype=np.float64)
    finite_mask = np.isfinite(pvalues)
    finite_values = pvalues[finite_mask]
    if finite_values.size == 0:
        return adjusted

    order = np.argsort(finite_values)
    ordered = finite_values[order]
    n = ordered.size
    ranks = np.arange(1, n + 1, dtype=np.float64)
    bh = ordered * n / ranks
    bh = np.minimum.accumulate(bh[::-1])[::-1]
    bh = np.clip(bh, 0.0, 1.0)
    restored = np.empty_like(ordered)
    restored[order] = bh
    adjusted[finite_mask] = restored
    return adjusted


def cohen_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    valid_a = group_a[np.isfinite(group_a)]
    valid_b = group_b[np.isfinite(group_b)]
    if valid_a.size < 2 or valid_b.size < 2:
        return np.nan
    var_a = float(np.var(valid_a, ddof=1))
    var_b = float(np.var(valid_b, ddof=1))
    pooled_num = (valid_a.size - 1) * var_a + (valid_b.size - 1) * var_b
    pooled_den = valid_a.size + valid_b.size - 2
    if pooled_den <= 0:
        return np.nan
    pooled_std = np.sqrt(max(pooled_num / pooled_den, 0.0))
    if np.isclose(pooled_std, 0.0):
        return np.nan
    return float((np.mean(valid_b) - np.mean(valid_a)) / pooled_std)


def load_selected_bands(features_csv: Path) -> list[str]:
    features_df = pd.read_csv(features_csv, encoding="utf-8-sig")
    return features_df.loc[features_df["tipo"] == "banda", "feature"].tolist()


def build_ttest_table(df: pd.DataFrame, band_columns: list[str]) -> pd.DataFrame:
    non_irr = df.loc[df["condicao"] == "NIRR", band_columns]
    irr = df.loc[df["condicao"] == "IRR", band_columns]
    rows: list[dict[str, object]] = []

    for band in band_columns:
        group_a = non_irr[band].to_numpy(dtype=np.float64)
        group_b = irr[band].to_numpy(dtype=np.float64)
        stat, p_value = ttest_ind(group_a, group_b, equal_var=False, nan_policy="omit")
        mean_non_irr = float(np.nanmean(group_a))
        mean_irr = float(np.nanmean(group_b))
        mean_diff = mean_irr - mean_non_irr
        effect = cohen_d(group_a, group_b)
        rows.append(
            {
                "band": band,
                "wavelength_nm": int(band.replace("band_", "")),
                "t_stat": float(stat),
                "p_value": float(p_value),
                "mean_non_irrigated": mean_non_irr,
                "mean_irrigated": mean_irr,
                "mean_diff_irrigated_minus_non_irrigated": mean_diff,
                "cohen_d": effect,
                "abs_cohen_d": float(abs(effect)) if np.isfinite(effect) else np.nan,
                "direction": "irrigado" if mean_diff >= 0 else "nao_irrigado",
            }
        )

    result = pd.DataFrame(rows)
    result["q_value"] = adjust_pvalues_bh(result["p_value"].to_numpy(dtype=np.float64))
    result = result.sort_values(
        ["q_value", "p_value", "abs_cohen_d", "wavelength_nm"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)
    result["rank_ttest"] = np.arange(1, len(result) + 1)
    return result


def build_kruskal_table(df: pd.DataFrame, band_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    class_means = df.groupby("classe")[band_columns].mean()
    class_support = df["classe"].value_counts()
    n_total = int(df.shape[0])
    k = len(CLASS_ORDER)

    for band in band_columns:
        groups = [
            df.loc[df["classe"] == class_name, band].to_numpy(dtype=np.float64)
            for class_name in CLASS_ORDER
        ]
        stat, p_value = kruskal(*groups, nan_policy="omit")
        band_means = class_means[band].dropna()
        top_class = str(band_means.idxmax()) if not band_means.empty else ""
        bottom_class = str(band_means.idxmin()) if not band_means.empty else ""
        eta2 = np.nan
        if np.isfinite(stat) and n_total > k:
            eta2 = max((float(stat) - k + 1) / (n_total - k), 0.0)
        rows.append(
            {
                "band": band,
                "wavelength_nm": int(band.replace("band_", "")),
                "h_stat": float(stat),
                "p_value": float(p_value),
                "class_mean_min": float(band_means.min()) if not band_means.empty else np.nan,
                "class_mean_max": float(band_means.max()) if not band_means.empty else np.nan,
                "class_mean_range": float(band_means.max() - band_means.min()) if not band_means.empty else np.nan,
                "eta2_h": eta2,
                "top_class_mean": top_class,
                "bottom_class_mean": bottom_class,
                "min_class_support": int(class_support.min()),
            }
        )

    result = pd.DataFrame(rows)
    result["q_value"] = adjust_pvalues_bh(result["p_value"].to_numpy(dtype=np.float64))
    result = result.sort_values(
        ["q_value", "p_value", "h_stat", "wavelength_nm"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)
    result["rank_kruskal"] = np.arange(1, len(result) + 1)
    return result


def lda_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        ]
    )


def evaluate_subset(df: pd.DataFrame, band_columns: list[str], subset_name: str) -> dict[str, object]:
    feature_columns = list(band_columns) + INDEX_COLUMNS
    X = df[feature_columns].copy()
    y = pd.Categorical(df["classe"], categories=CLASS_ORDER, ordered=True).codes
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
    return {
        "subset": subset_name,
        "n_bands": int(len(band_columns)),
        "n_features_total": int(len(feature_columns)),
        "accuracy_media": float(scores["test_accuracy"].mean()),
        "accuracy_std": float(scores["test_accuracy"].std(ddof=1)),
        "f1_macro_media": float(scores["test_f1_macro"].mean()),
        "f1_macro_std": float(scores["test_f1_macro"].std(ddof=1)),
        "kappa_media": float(scores["test_kappa"].mean()),
        "kappa_std": float(scores["test_kappa"].std(ddof=1)),
    }


def save_subset(path: Path, subset_name: str, bands: list[str]) -> None:
    subset_df = pd.DataFrame(
        {
            "subset": [subset_name] * len(bands),
            "band": bands,
            "wavelength_nm": [int(band.replace("band_", "")) for band in bands],
        }
    )
    subset_df.to_csv(path, index=False, encoding="utf-8-sig")


def build_joint_ranking(ttest_df: pd.DataFrame, kruskal_df: pd.DataFrame) -> pd.DataFrame:
    merged = ttest_df[
        ["band", "wavelength_nm", "rank_ttest", "q_value", "abs_cohen_d"]
    ].rename(columns={"q_value": "ttest_q_value"})
    merged = merged.merge(
        kruskal_df[["band", "rank_kruskal", "q_value", "h_stat", "eta2_h"]],
        on="band",
        how="inner",
    ).rename(columns={"q_value": "kruskal_q_value"})
    merged["joint_rank_score"] = merged["rank_ttest"] + merged["rank_kruskal"]
    merged = merged.sort_values(
        ["joint_rank_score", "ttest_q_value", "kruskal_q_value", "abs_cohen_d", "h_stat"],
        ascending=[True, True, True, False, False],
    ).reset_index(drop=True)
    merged["joint_rank"] = np.arange(1, len(merged) + 1)
    return merged


def write_summary(
    path: Path,
    *,
    total_bands: int,
    ttest_df: pd.DataFrame,
    kruskal_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
) -> None:
    lines = [
        "# Reducao de bandas por p-teste",
        "",
        f"- Bandas testadas: `{total_bands}`",
        f"- Welch t-test com FDR-BH (`IRR vs NIRR`): `q < 0.05 -> {(ttest_df['q_value'] < 0.05).sum()}` bandas; `q < 0.01 -> {(ttest_df['q_value'] < 0.01).sum()}` bandas.",
        f"- Kruskal-Wallis com FDR-BH (`A-F`): `q < 0.05 -> {(kruskal_df['q_value'] < 0.05).sum()}` bandas; `q < 0.01 -> {(kruskal_df['q_value'] < 0.01).sum()}` bandas.",
        "",
        "## Top 10 Welch t-test",
        "",
        "| rank | banda | q-value | |d| | direcao |",
        "| ---: | ---: | ---: | ---: | --- |",
    ]

    for row in ttest_df.head(10).itertuples(index=False):
        lines.append(
            f"| {row.rank_ttest} | {row.wavelength_nm} | {row.q_value:.3e} | {row.abs_cohen_d:.4f} | {row.direction} |"
        )

    lines.extend(
        [
            "",
            "## Top 10 Kruskal-Wallis",
            "",
            "| rank | banda | q-value | H | eta2(H) |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for row in kruskal_df.head(10).itertuples(index=False):
        lines.append(
            f"| {row.rank_kruskal} | {row.wavelength_nm} | {row.q_value:.3e} | {row.h_stat:.4f} | {row.eta2_h:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Benchmark LDA",
            "",
            "| subset | n bandas | accuracy | f1_macro | kappa |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )

    for row in benchmark_df.itertuples(index=False):
        lines.append(
            f"| {row.subset} | {row.n_bands} | {row.accuracy_media:.4f} | {row.f1_macro_media:.4f} | {row.kappa_media:.4f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = ensure_class_columns(pd.read_csv(args.input))
    selected_bands = load_selected_bands(args.features_csv)

    ttest_df = build_ttest_table(df, selected_bands)
    kruskal_df = build_kruskal_table(df, selected_bands)
    joint_df = build_joint_ranking(ttest_df, kruskal_df)

    subsets: list[tuple[str, list[str]]] = [
        ("indices_only", []),
        ("original_bands", selected_bands),
        ("ttest_q_lt_0_05", ttest_df.loc[ttest_df["q_value"] < 0.05, "band"].tolist()),
        ("ttest_q_lt_0_01", ttest_df.loc[ttest_df["q_value"] < 0.01, "band"].tolist()),
        ("kruskal_q_lt_0_05", kruskal_df.loc[kruskal_df["q_value"] < 0.05, "band"].tolist()),
        ("kruskal_q_lt_0_01", kruskal_df.loc[kruskal_df["q_value"] < 0.01, "band"].tolist()),
        (
            "intersection_q_lt_0_05",
            sorted(
                set(ttest_df.loc[ttest_df["q_value"] < 0.05, "band"]).intersection(
                    kruskal_df.loc[kruskal_df["q_value"] < 0.05, "band"]
                )
            ),
        ),
        (
            "intersection_q_lt_0_01",
            sorted(
                set(ttest_df.loc[ttest_df["q_value"] < 0.01, "band"]).intersection(
                    kruskal_df.loc[kruskal_df["q_value"] < 0.01, "band"]
                )
            ),
        ),
        ("joint_top_10", joint_df.head(10)["band"].tolist()),
        ("joint_top_15", joint_df.head(15)["band"].tolist()),
        ("joint_top_20", joint_df.head(20)["band"].tolist()),
        ("joint_top_30", joint_df.head(30)["band"].tolist()),
        ("ttest_top_10", ttest_df.head(10)["band"].tolist()),
        ("ttest_top_15", ttest_df.head(15)["band"].tolist()),
        ("ttest_top_20", ttest_df.head(20)["band"].tolist()),
        ("ttest_top_30", ttest_df.head(30)["band"].tolist()),
        ("kruskal_top_10", kruskal_df.head(10)["band"].tolist()),
        ("kruskal_top_15", kruskal_df.head(15)["band"].tolist()),
        ("kruskal_top_20", kruskal_df.head(20)["band"].tolist()),
        ("kruskal_top_30", kruskal_df.head(30)["band"].tolist()),
    ]

    benchmark_rows: list[dict[str, object]] = []
    for subset_name, subset_bands in subsets:
        benchmark_rows.append(evaluate_subset(df, subset_bands, subset_name))
        save_subset(output_dir / f"{subset_name}.csv", subset_name, subset_bands)

    benchmark_df = pd.DataFrame(benchmark_rows).sort_values(
        ["f1_macro_media", "accuracy_media", "kappa_media", "n_bands"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    ttest_df.to_csv(output_dir / "welch_ttest_selected_classification_bands.csv", index=False, encoding="utf-8-sig")
    kruskal_df.to_csv(output_dir / "kruskal_selected_classification_bands.csv", index=False, encoding="utf-8-sig")
    joint_df.to_csv(output_dir / "joint_ranking_selected_classification_bands.csv", index=False, encoding="utf-8-sig")
    benchmark_df.to_csv(output_dir / "lda_benchmark_reduced_band_subsets.csv", index=False, encoding="utf-8-sig")
    write_summary(
        output_dir / "resumo_reducao_bandas_p_teste.md",
        total_bands=len(selected_bands),
        ttest_df=ttest_df,
        kruskal_df=kruskal_df,
        benchmark_df=benchmark_df,
    )

    print(f"Output directory: {output_dir}")
    print(f"Selected classification bands: {len(selected_bands)}")
    print(f"Welch q<0.05: {(ttest_df['q_value'] < 0.05).sum()} | q<0.01: {(ttest_df['q_value'] < 0.01).sum()}")
    print(f"Kruskal q<0.05: {(kruskal_df['q_value'] < 0.05).sum()} | q<0.01: {(kruskal_df['q_value'] < 0.01).sum()}")
    best_row = benchmark_df.iloc[0]
    print(
        "Best LDA subset: "
        f"{best_row['subset']} | n_bands={int(best_row['n_bands'])} | "
        f"accuracy={best_row['accuracy_media']:.4f} | f1={best_row['f1_macro_media']:.4f}"
    )


if __name__ == "__main__":
    main()
