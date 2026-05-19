#!/usr/bin/env python3
"""Benchmark diversified spectral subsets using correlation-based clustering."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.impute import SimpleImputer
from sklearn.metrics import cohen_kappa_score, f1_score, make_scorer
from sklearn.model_selection import StratifiedGroupKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from diversified_band_selection_utils import (
    SelectionRecord,
    band_to_wavelength,
    build_absolute_correlation,
    cluster_bands,
    filter_ranked_bands,
    format_threshold_token,
    select_ranked_bands_by_cluster_policy,
    summarize_band_subset,
)


CLASS_ORDER = ["A", "B", "C", "D", "E", "F"]
INDEX_COLUMNS = ["NDVI", "EVI", "WBI", "PRI", "SIPI", "REP"]
CLASS_LABELS = {
    ("EMB48", "IRR"): ("A", "A (EMB48 IRR)"),
    ("EMB48", "NIRR"): ("B", "B (EMB48 NIRR)"),
    ("BR16", "IRR"): ("C", "C (BR16 IRR)"),
    ("BR16", "NIRR"): ("D", "D (BR16 NIRR)"),
    ("CD202", "IRR"): ("E", "E (CD202 IRR)"),
    ("CD202", "NIRR"): ("F", "F (CD202 NIRR)"),
}


@dataclass(frozen=True)
class SubsetSpec:
    subset_name: str
    subset_kind: str
    ranking_source: str
    selection_policy: str
    cluster_threshold: float | None
    requested_k: int
    selected_bands: list[str]
    selection_records: list[SelectionRecord]


def set_plot_style() -> None:
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 300
    plt.rcParams["axes.titlesize"] = 13
    plt.rcParams["axes.labelsize"] = 11
    plt.rcParams["legend.fontsize"] = 10


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    default_reduction_dir = project_dir / "outputs" / "tabelas" / "reducao_bandas_p_teste"
    parser = argparse.ArgumentParser(
        description="Compara subconjuntos de bandas diversificados por clusters de correlacao."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
        help="CSV base da classificacao 6x6.",
    )
    parser.add_argument(
        "--features-csv",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "features_classificacao.csv",
        help="Manifesto das bandas da classificacao atual.",
    )
    parser.add_argument(
        "--ttest-csv",
        type=Path,
        default=default_reduction_dir / "welch_ttest_selected_classification_bands.csv",
        help="Ranking Welch t-test exportado pela reducao atual.",
    )
    parser.add_argument(
        "--kruskal-csv",
        type=Path,
        default=default_reduction_dir / "kruskal_selected_classification_bands.csv",
        help="Ranking Kruskal exportado pela reducao atual.",
    )
    parser.add_argument(
        "--joint-csv",
        type=Path,
        default=default_reduction_dir / "joint_ranking_selected_classification_bands.csv",
        help="Ranking combinado exportado pela reducao atual.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "diversificacao_bandas_correlacao",
        help="Diretorio para tabelas e resumos.",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=project_dir / "outputs" / "figuras" / "diversificacao_bandas_correlacao",
        help="Diretorio para figuras.",
    )
    parser.add_argument(
        "--correlation-thresholds",
        type=str,
        default="0.95,0.90,0.85",
        help="Lista separada por virgula de thresholds de correlacao absoluta.",
    )
    parser.add_argument(
        "--top-k-values",
        type=str,
        default="10,15,20,30",
        help="Lista separada por virgula dos tamanhos de subset a testar.",
    )
    parser.add_argument(
        "--baseline-cluster-threshold",
        type=float,
        default=0.90,
        help="Threshold de cluster usado para medir redundancia nos baselines.",
    )
    parser.add_argument(
        "--f1-tolerance",
        type=float,
        default=0.02,
        help="Tolerancia maxima de F1 em relacao ao melhor subset para a recomendacao.",
    )
    return parser.parse_args()


def parse_float_list(raw_value: str) -> list[float]:
    values: list[float] = []
    for token in raw_value.split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        values.append(float(cleaned))
    if not values:
        raise ValueError("Nenhum threshold foi informado.")
    return values


def parse_int_list(raw_value: str) -> list[int]:
    values: list[int] = []
    for token in raw_value.split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        values.append(int(cleaned))
    if not values:
        raise ValueError("Nenhum valor de top-k foi informado.")
    return values


def assign_class_labels(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    labels = frame.apply(lambda row: CLASS_LABELS[(row["cultivar"], row["condicao"])], axis=1)
    frame["classe"] = [item[0] for item in labels]
    frame["classe_legenda"] = [item[1] for item in labels]
    frame["grupo_cv"] = frame["classe"] + "_B" + frame["replicata"].astype(str)
    return frame


def lda_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        ]
    )


def load_selected_bands(features_csv: Path) -> list[str]:
    features_df = pd.read_csv(features_csv, encoding="utf-8-sig")
    return features_df.loc[features_df["tipo"] == "banda", "feature"].tolist()


def load_rankings(
    *,
    ttest_csv: Path,
    kruskal_csv: Path,
    joint_csv: Path,
    allowed_bands: set[str],
) -> dict[str, list[str]]:
    ttest_df = pd.read_csv(ttest_csv, encoding="utf-8-sig").sort_values(
        ["rank_ttest", "q_value", "p_value", "abs_cohen_d", "wavelength_nm"],
        ascending=[True, True, True, False, True],
    )
    kruskal_df = pd.read_csv(kruskal_csv, encoding="utf-8-sig").sort_values(
        ["rank_kruskal", "q_value", "p_value", "h_stat", "wavelength_nm"],
        ascending=[True, True, True, False, True],
    )
    joint_df = pd.read_csv(joint_csv, encoding="utf-8-sig").sort_values(
        ["joint_rank", "joint_rank_score", "ttest_q_value", "kruskal_q_value", "abs_cohen_d", "h_stat"],
        ascending=[True, True, True, True, False, False],
    )
    return {
        "ttest": filter_ranked_bands(ttest_df["band"].tolist(), allowed_bands),
        "kruskal": filter_ranked_bands(kruskal_df["band"].tolist(), allowed_bands),
        "joint": filter_ranked_bands(joint_df["band"].tolist(), allowed_bands),
    }


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
        "subset_name": subset_name,
        "n_bands": int(len(band_columns)),
        "n_features_total": int(len(feature_columns)),
        "n_splits_cv": int(n_splits),
        "accuracy_media": float(scores["test_accuracy"].mean()),
        "accuracy_std": float(scores["test_accuracy"].std(ddof=1)),
        "f1_macro_media": float(scores["test_f1_macro"].mean()),
        "f1_macro_std": float(scores["test_f1_macro"].std(ddof=1)),
        "kappa_media": float(scores["test_kappa"].mean()),
        "kappa_std": float(scores["test_kappa"].std(ddof=1)),
    }


def save_subset_file(path: Path, subset_name: str, bands: list[str]) -> None:
    subset_df = pd.DataFrame(
        {
            "subset": [subset_name] * len(bands),
            "band": bands,
            "wavelength_nm": [band_to_wavelength(band) for band in bands],
        }
    )
    write_csv(subset_df, path)


def build_cluster_artifacts(
    selected_bands: list[str],
    abs_corr: pd.DataFrame,
    thresholds: list[float],
) -> tuple[dict[float, dict[str, int]], pd.DataFrame, pd.DataFrame]:
    cluster_mappings: dict[float, dict[str, int]] = {}
    mapping_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for threshold in thresholds:
        mapping = cluster_bands(abs_corr, threshold)
        cluster_mappings[threshold] = mapping
        cluster_counts = pd.Series(mapping).value_counts().sort_index()
        for band in selected_bands:
            cluster_id = int(mapping[band])
            mapping_rows.append(
                {
                    "cluster_threshold": threshold,
                    "band": band,
                    "wavelength_nm": band_to_wavelength(band),
                    "cluster_id": cluster_id,
                    "cluster_size": int(cluster_counts.loc[cluster_id]),
                }
            )
        summary_rows.append(
            {
                "cluster_threshold": threshold,
                "n_clusters": int(cluster_counts.shape[0]),
                "largest_cluster_size": int(cluster_counts.max()),
                "median_cluster_size": float(cluster_counts.median()),
                "mean_cluster_size": float(cluster_counts.mean()),
                "singleton_clusters": int((cluster_counts == 1).sum()),
            }
        )

    return cluster_mappings, pd.DataFrame(mapping_rows), pd.DataFrame(summary_rows)


def build_subset_specs(
    *,
    selected_bands: list[str],
    rankings: dict[str, list[str]],
    cluster_mappings: dict[float, dict[str, int]],
    thresholds: list[float],
    top_k_values: list[int],
) -> list[SubsetSpec]:
    specs: list[SubsetSpec] = [
        SubsetSpec(
            subset_name="indices_only",
            subset_kind="baseline",
            ranking_source="indices_only",
            selection_policy="baseline",
            cluster_threshold=None,
            requested_k=0,
            selected_bands=[],
            selection_records=[],
        ),
        SubsetSpec(
            subset_name="original_bands",
            subset_kind="baseline",
            ranking_source="original_bands",
            selection_policy="baseline",
            cluster_threshold=None,
            requested_k=len(selected_bands),
            selected_bands=list(selected_bands),
            selection_records=[],
        ),
    ]

    for ranking_source, ranked_bands in rankings.items():
        for k in top_k_values:
            baseline_bands = ranked_bands[:k]
            specs.append(
                SubsetSpec(
                    subset_name=f"{ranking_source}_top_{k}",
                    subset_kind="baseline",
                    ranking_source=ranking_source,
                    selection_policy="baseline",
                    cluster_threshold=None,
                    requested_k=k,
                    selected_bands=baseline_bands,
                    selection_records=[],
                )
            )
        for threshold in thresholds:
            mapping = cluster_mappings[threshold]
            for policy in ("hard", "soft"):
                for k in top_k_values:
                    records = select_ranked_bands_by_cluster_policy(ranked_bands, mapping, k, policy=policy)
                    subset_name = f"{ranking_source}_cluster_{policy}_corr_{format_threshold_token(threshold)}_top_{k}"
                    specs.append(
                        SubsetSpec(
                            subset_name=subset_name,
                            subset_kind="diversified",
                            ranking_source=ranking_source,
                            selection_policy=policy,
                            cluster_threshold=threshold,
                            requested_k=k,
                            selected_bands=[record.band for record in records],
                            selection_records=records,
                        )
                    )
    return specs


def safe_sort_values(frame: pd.DataFrame) -> pd.DataFrame:
    sortable = frame.copy()
    sortable["median_abs_corr_within_subset_sort"] = sortable["median_abs_corr_within_subset"].fillna(np.inf)
    sortable["largest_contiguous_run_nm_sort"] = sortable["largest_contiguous_run_nm"].fillna(np.inf)
    return sortable.sort_values(
        [
            "median_abs_corr_within_subset_sort",
            "n_distinct_spectral_regions",
            "largest_contiguous_run_nm_sort",
            "f1_macro_media",
            "accuracy_media",
        ],
        ascending=[True, False, True, False, False],
    )


def choose_recommended_subset(benchmark_df: pd.DataFrame, f1_tolerance: float) -> pd.Series:
    diversified_df = benchmark_df[benchmark_df["subset_kind"] == "diversified"].copy()
    if diversified_df.empty:
        raise ValueError("Nenhum subset diversificado foi gerado.")
    best_f1 = float(benchmark_df["f1_macro_media"].max())
    within_tolerance = diversified_df[diversified_df["f1_macro_media"] >= best_f1 - f1_tolerance].copy()
    if within_tolerance.empty:
        within_tolerance = diversified_df.copy()
    return safe_sort_values(within_tolerance).iloc[0]


def build_composition_rows(
    spec: SubsetSpec,
    *,
    evaluation_cluster_threshold: float,
    evaluation_cluster_mapping: dict[str, int],
) -> list[dict[str, object]]:
    record_lookup = {record.band: record for record in spec.selection_records}
    rows: list[dict[str, object]] = []
    for order_index, band in enumerate(spec.selected_bands, start=1):
        record = record_lookup.get(band)
        rows.append(
            {
                "subset_name": spec.subset_name,
                "subset_kind": spec.subset_kind,
                "ranking_source": spec.ranking_source,
                "selection_policy": spec.selection_policy,
                "selection_cluster_threshold": spec.cluster_threshold,
                "evaluation_cluster_threshold": evaluation_cluster_threshold,
                "requested_k": spec.requested_k,
                "selection_order": order_index,
                "selection_round": int(record.selection_round) if record is not None else 1,
                "band": band,
                "wavelength_nm": band_to_wavelength(band),
                "cluster_id": int(evaluation_cluster_mapping[band]),
            }
        )
    return rows


def plot_correlation_heatmap(abs_corr: pd.DataFrame, output_path: Path) -> None:
    set_plot_style()
    fig, ax = plt.subplots(figsize=(10, 8))
    image = ax.imshow(abs_corr.to_numpy(dtype=float), cmap="viridis", vmin=0.0, vmax=1.0, aspect="auto")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="|corr|")
    ax.set_title("Correlacao absoluta entre as 148 bandas da classificacao atual")
    ax.set_xlabel("Bandas ordenadas por comprimento de onda")
    ax.set_ylabel("Bandas ordenadas por comprimento de onda")
    ax.set_xticks([])
    ax.set_yticks([])
    save_figure(fig, output_path)


def plot_performance_vs_redundancy(benchmark_df: pd.DataFrame, output_path: Path, recommended_subset: str) -> None:
    set_plot_style()
    plot_df = benchmark_df[(benchmark_df["n_bands"] > 0) & benchmark_df["median_abs_corr_within_subset"].notna()].copy()
    ranking_colors = {
        "original_bands": "#374151",
        "indices_only": "#6b7280",
        "ttest": "#1d4ed8",
        "kruskal": "#b45309",
        "joint": "#0f766e",
    }
    policy_markers = {"baseline": "o", "hard": "s", "soft": "^"}

    fig, ax = plt.subplots(figsize=(10, 7))
    for _, row in plot_df.iterrows():
        ax.scatter(
            float(row["median_abs_corr_within_subset"]),
            float(row["f1_macro_media"]),
            color=ranking_colors.get(str(row["ranking_source"]), "#111827"),
            marker=policy_markers.get(str(row["selection_policy"]), "o"),
            s=70 if row["subset_name"] == recommended_subset else 42,
            alpha=0.9 if row["subset_name"] == recommended_subset else 0.72,
            edgecolors="#111827" if row["subset_name"] == recommended_subset else "none",
            linewidths=1.0 if row["subset_name"] == recommended_subset else 0.0,
        )

    labels_to_annotate = {
        "original_bands",
        "ttest_top_20",
        "kruskal_top_20",
        "joint_top_20",
        recommended_subset,
    }
    for _, row in plot_df[plot_df["subset_name"].isin(labels_to_annotate)].iterrows():
        ax.annotate(
            str(row["subset_name"]),
            (float(row["median_abs_corr_within_subset"]), float(row["f1_macro_media"])),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_xlabel("Mediana de |corr| dentro do subset")
    ax.set_ylabel("F1-macro medio")
    ax.set_title("Desempenho vs redundancia espectral")
    ax.grid(alpha=0.2)
    save_figure(fig, output_path)


def plot_subset_coverage(
    subset_composition_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    output_path: Path,
    recommended_subset: str,
    best_diversified_subset: str,
) -> None:
    set_plot_style()
    key_subsets = [
        "original_bands",
        "ttest_top_20",
        "kruskal_top_20",
        "joint_top_20",
        best_diversified_subset,
        recommended_subset,
    ]
    ordered_unique_subsets: list[str] = []
    for subset_name in key_subsets:
        if subset_name in subset_composition_df["subset_name"].values and subset_name not in ordered_unique_subsets:
            ordered_unique_subsets.append(subset_name)
    if not ordered_unique_subsets:
        return

    plot_df = subset_composition_df[subset_composition_df["subset_name"].isin(ordered_unique_subsets)].copy()
    fig, ax = plt.subplots(figsize=(12, max(4.0, 0.75 * len(ordered_unique_subsets))))
    y_positions = {subset_name: idx for idx, subset_name in enumerate(reversed(ordered_unique_subsets), start=1)}

    for subset_name, group_df in plot_df.groupby("subset_name", sort=False):
        y_value = y_positions[subset_name]
        color = "#0f766e" if subset_name == recommended_subset else "#1d4ed8" if subset_name == best_diversified_subset else "#6b7280"
        ax.scatter(group_df["wavelength_nm"], [y_value] * len(group_df), s=48, color=color, alpha=0.9)

    ax.set_yticks(list(y_positions.values()))
    ax.set_yticklabels(list(y_positions.keys()))
    ax.set_xlabel("Comprimento de onda (nm)")
    ax.set_ylabel("Subset")
    ax.set_title("Cobertura espectral dos subsets-chave")
    ax.grid(alpha=0.15, axis="x")
    save_figure(fig, output_path)


def write_summary(
    path: Path,
    *,
    thresholds: list[float],
    top_k_values: list[int],
    baseline_cluster_threshold: float,
    f1_tolerance: float,
    cluster_summary_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    best_overall_row: pd.Series,
    best_diversified_row: pd.Series,
    recommended_row: pd.Series,
) -> None:
    baseline_map = benchmark_df.set_index("subset_name")
    diversified_df = benchmark_df[benchmark_df["subset_kind"] == "diversified"].copy()
    diversified_within_tolerance = diversified_df[diversified_df["within_f1_tolerance"]].copy()
    used_recommendation_fallback = diversified_within_tolerance.empty
    recommended_baseline_name = (
        f"{recommended_row['ranking_source']}_top_{int(recommended_row['requested_k'])}"
        if recommended_row["subset_kind"] == "diversified"
        else str(recommended_row["subset_name"])
    )
    baseline_row = baseline_map.loc[recommended_baseline_name] if recommended_baseline_name in baseline_map.index else None

    lines = [
        "# Benchmark de bandas diversificadas por correlacao",
        "",
        "## Configuracao",
        "",
        f"- thresholds de cluster: `{', '.join(f'{value:.2f}' for value in thresholds)}`",
        f"- tamanhos de subset: `{', '.join(str(value) for value in top_k_values)}`",
        f"- threshold de referencia para metricas dos baselines: `{baseline_cluster_threshold:.2f}`",
        f"- tolerancia de F1 para recomendacao: `{f1_tolerance:.3f}`",
        f"- subsets diversificados dentro da tolerancia: `{len(diversified_within_tolerance)}`",
        "",
        "## Resumo de clusters",
        "",
        "| threshold | n clusters | maior cluster | mediana tam. | media tam. | singletons |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in cluster_summary_df.itertuples(index=False):
        lines.append(
            f"| {row.cluster_threshold:.2f} | {row.n_clusters} | {row.largest_cluster_size} | {row.median_cluster_size:.2f} | {row.mean_cluster_size:.2f} | {row.singleton_clusters} |"
        )

    lines.extend(
        [
            "",
            "## Melhor subset geral",
            "",
            f"- subset: `{best_overall_row['subset_name']}`",
            f"- tipo: `{best_overall_row['subset_kind']}`",
            f"- F1-macro: `{best_overall_row['f1_macro_media']:.6f}`",
            f"- accuracy: `{best_overall_row['accuracy_media']:.6f}`",
            f"- mediana |corr|: `{best_overall_row['median_abs_corr_within_subset']:.6f}`",
            "",
            "## Melhor subset diversificado por desempenho",
            "",
            f"- subset: `{best_diversified_row['subset_name']}`",
            f"- ranking: `{best_diversified_row['ranking_source']}`",
            f"- politica: `{best_diversified_row['selection_policy']}`",
            f"- threshold: `{float(best_diversified_row['cluster_threshold']):.2f}`",
            f"- F1-macro: `{best_diversified_row['f1_macro_media']:.6f}`",
            f"- accuracy: `{best_diversified_row['accuracy_media']:.6f}`",
            "",
            "## Subset recomendado para tradeoff",
            "",
            f"- subset: `{recommended_row['subset_name']}`",
            f"- ranking: `{recommended_row['ranking_source']}`",
            f"- politica: `{recommended_row['selection_policy']}`",
            f"- threshold: `{float(recommended_row['cluster_threshold']):.2f}`",
            f"- k solicitado: `{int(recommended_row['requested_k'])}`",
            f"- bandas selecionadas: `{int(recommended_row['n_bands'])}`",
            f"- F1-macro: `{recommended_row['f1_macro_media']:.6f}`",
            f"- accuracy: `{recommended_row['accuracy_media']:.6f}`",
            f"- kappa: `{recommended_row['kappa_media']:.6f}`",
            f"- mediana |corr|: `{recommended_row['median_abs_corr_within_subset']:.6f}`",
            f"- maior bloco contiguo: `{int(recommended_row['largest_contiguous_run_nm'])}`",
            f"- regioes espectrais: `{recommended_row['spectral_regions']}`",
        ]
    )

    if used_recommendation_fallback:
        lines.extend(
            [
                f"- observacao: nenhum subset diversificado ficou dentro da tolerancia de F1 de `{f1_tolerance:.3f}` em relacao ao melhor subset geral.",
                "- regra aplicada: fallback para o melhor tradeoff de redundancia/diversidade entre os subsets diversificados disponiveis.",
            ]
        )

    if baseline_row is not None:
        lines.extend(
            [
                "",
                "## Comparacao com baseline pareado",
                "",
                f"- baseline: `{recommended_baseline_name}`",
                f"- delta F1-macro: `{float(recommended_row['f1_macro_media']) - float(baseline_row['f1_macro_media']):+.6f}`",
                f"- delta accuracy: `{float(recommended_row['accuracy_media']) - float(baseline_row['accuracy_media']):+.6f}`",
                f"- delta mediana |corr|: `{float(recommended_row['median_abs_corr_within_subset']) - float(baseline_row['median_abs_corr_within_subset']):+.6f}`",
                f"- delta maior bloco contiguo: `{int(recommended_row['largest_contiguous_run_nm']) - int(baseline_row['largest_contiguous_run_nm'])}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Top 10 subsets diversificados pelo criterio de recomendacao",
            "",
            "| subset | ranking | politica | threshold | n bandas | F1 | accuracy | mediana |corr| | regioes | bloco contiguo |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    top_diversified_source = diversified_within_tolerance if not used_recommendation_fallback else diversified_df
    top_diversified = safe_sort_values(top_diversified_source.copy()).head(10)
    for row in top_diversified.itertuples(index=False):
        lines.append(
            f"| {row.subset_name} | {row.ranking_source} | {row.selection_policy} | {row.cluster_threshold:.2f} | {row.n_bands} | {row.f1_macro_media:.4f} | {row.accuracy_media:.4f} | {row.median_abs_corr_within_subset:.4f} | {row.n_distinct_spectral_regions} | {row.largest_contiguous_run_nm} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    thresholds = parse_float_list(args.correlation_thresholds)
    top_k_values = parse_int_list(args.top_k_values)
    output_dir = args.output_dir.resolve()
    figure_dir = args.figure_dir.resolve()
    subsets_dir = output_dir / "subsets"
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    subsets_dir.mkdir(parents=True, exist_ok=True)

    df = assign_class_labels(pd.read_csv(args.input))
    selected_bands = load_selected_bands(args.features_csv)
    allowed_bands = set(selected_bands)
    rankings = load_rankings(
        ttest_csv=args.ttest_csv,
        kruskal_csv=args.kruskal_csv,
        joint_csv=args.joint_csv,
        allowed_bands=allowed_bands,
    )

    abs_corr = build_absolute_correlation(df[selected_bands])
    unique_thresholds = sorted(set(thresholds + [float(args.baseline_cluster_threshold)]), reverse=True)
    cluster_mappings, cluster_mapping_df, cluster_summary_df = build_cluster_artifacts(selected_bands, abs_corr, unique_thresholds)
    subset_specs = build_subset_specs(
        selected_bands=selected_bands,
        rankings=rankings,
        cluster_mappings=cluster_mappings,
        thresholds=thresholds,
        top_k_values=top_k_values,
    )

    benchmark_rows: list[dict[str, object]] = []
    composition_rows: list[dict[str, object]] = []
    baseline_cluster_mapping = cluster_mappings[float(args.baseline_cluster_threshold)]

    for spec in subset_specs:
        if spec.cluster_threshold is None:
            evaluation_threshold = float(args.baseline_cluster_threshold)
            evaluation_cluster_mapping = baseline_cluster_mapping
        else:
            evaluation_threshold = float(spec.cluster_threshold)
            evaluation_cluster_mapping = cluster_mappings[evaluation_threshold]

        metrics_row = evaluate_subset(df, spec.selected_bands, spec.subset_name)
        diversity_row = summarize_band_subset(spec.selected_bands, abs_corr, evaluation_cluster_mapping)
        metrics_row.update(diversity_row)
        metrics_row.update(
            {
                "subset_kind": spec.subset_kind,
                "ranking_source": spec.ranking_source,
                "selection_policy": spec.selection_policy,
                "cluster_threshold": spec.cluster_threshold,
                "evaluation_cluster_threshold": evaluation_threshold,
                "requested_k": int(spec.requested_k),
            }
        )
        benchmark_rows.append(metrics_row)
        composition_rows.extend(
            build_composition_rows(
                spec,
                evaluation_cluster_threshold=evaluation_threshold,
                evaluation_cluster_mapping=evaluation_cluster_mapping,
            )
        )
        save_subset_file(subsets_dir / f"{spec.subset_name}.csv", spec.subset_name, spec.selected_bands)

    benchmark_df = pd.DataFrame(benchmark_rows).sort_values(
        ["f1_macro_media", "accuracy_media", "kappa_media", "median_abs_corr_within_subset"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    benchmark_df["f1_from_best"] = float(benchmark_df["f1_macro_media"].max()) - benchmark_df["f1_macro_media"]
    benchmark_df["within_f1_tolerance"] = benchmark_df["f1_from_best"] <= float(args.f1_tolerance)
    benchmark_df["is_recommended"] = False

    best_overall_row = benchmark_df.iloc[0]
    best_diversified_row = benchmark_df[benchmark_df["subset_kind"] == "diversified"].sort_values(
        ["f1_macro_media", "accuracy_media", "median_abs_corr_within_subset"],
        ascending=[False, False, True],
    ).iloc[0]
    recommended_row = choose_recommended_subset(benchmark_df, float(args.f1_tolerance))
    benchmark_df.loc[benchmark_df["subset_name"] == recommended_row["subset_name"], "is_recommended"] = True

    subset_composition_df = pd.DataFrame(composition_rows).sort_values(
        ["subset_name", "selection_order"],
        ascending=[True, True],
    ).reset_index(drop=True)

    write_csv(abs_corr.reset_index().rename(columns={"index": "band"}), output_dir / "matriz_correlacao_absoluta_bandas.csv")
    write_csv(cluster_mapping_df, output_dir / "mapeamento_clusters_por_threshold.csv")
    write_csv(cluster_summary_df, output_dir / "resumo_clusters_por_threshold.csv")
    write_csv(subset_composition_df, output_dir / "composicao_subsets_diversificados.csv")
    write_csv(benchmark_df, output_dir / "benchmark_diversificacao_bandas.csv")
    write_csv(
        benchmark_df[benchmark_df["subset_name"] == recommended_row["subset_name"]],
        output_dir / "subset_recomendado_metricas.csv",
    )
    write_csv(
        subset_composition_df[subset_composition_df["subset_name"] == recommended_row["subset_name"]],
        output_dir / "subset_recomendado_bandas.csv",
    )

    plot_correlation_heatmap(abs_corr, figure_dir / "heatmap_correlacao_bandas_classificacao.png")
    plot_performance_vs_redundancy(
        benchmark_df,
        figure_dir / "desempenho_vs_redundancia.png",
        str(recommended_row["subset_name"]),
    )
    plot_subset_coverage(
        subset_composition_df,
        benchmark_df,
        figure_dir / "cobertura_espectral_subsets_chave.png",
        str(recommended_row["subset_name"]),
        str(best_diversified_row["subset_name"]),
    )
    write_summary(
        output_dir / "resumo_benchmark_diversificacao_bandas.md",
        thresholds=thresholds,
        top_k_values=top_k_values,
        baseline_cluster_threshold=float(args.baseline_cluster_threshold),
        f1_tolerance=float(args.f1_tolerance),
        cluster_summary_df=cluster_summary_df.sort_values("cluster_threshold", ascending=False).reset_index(drop=True),
        benchmark_df=benchmark_df,
        best_overall_row=best_overall_row,
        best_diversified_row=best_diversified_row,
        recommended_row=recommended_row,
    )

    print(f"Output directory: {output_dir}")
    print(f"Figure directory: {figure_dir}")
    print(f"Candidate bands: {len(selected_bands)}")
    print(f"Total subsets benchmarked: {len(benchmark_df)}")
    print(
        "Best overall subset: "
        f"{best_overall_row['subset_name']} | F1={best_overall_row['f1_macro_media']:.6f} | "
        f"ACC={best_overall_row['accuracy_media']:.6f}"
    )
    print(
        "Recommended diversified subset: "
        f"{recommended_row['subset_name']} | F1={recommended_row['f1_macro_media']:.6f} | "
        f"ACC={recommended_row['accuracy_media']:.6f} | "
        f"median|corr|={recommended_row['median_abs_corr_within_subset']:.6f}"
    )


if __name__ == "__main__":
    main()
