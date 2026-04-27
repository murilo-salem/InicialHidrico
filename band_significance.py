from __future__ import annotations

"""Statistical band-significance analysis for spectral datasets.

The module is intentionally dependency-light. It uses NumPy and SciPy for the
statistics and falls back to an internal Benjamini-Hochberg implementation when
statsmodels is unavailable.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import csv
import math

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import kruskal, pearsonr, spearmanr, ttest_ind

try:  # pragma: no cover - optional dependency
    from statsmodels.stats.multitest import multipletests as _multipletests
except Exception:  # pragma: no cover - optional dependency
    _multipletests = None


@dataclass(frozen=True)
class BandSignificanceResult:
    rows: list[dict[str, Any]]
    metadata: dict[str, Any]


def _as_array(values: Any) -> np.ndarray:
    if hasattr(values, "to_numpy"):
        values = values.to_numpy()
    return np.asarray(values)


def _get_column(data: Any, column: str) -> np.ndarray:
    try:
        values = data[column]
    except Exception as exc:  # pragma: no cover - defensive
        raise KeyError(f"Column {column!r} not found in dataset-like object.") from exc
    return _as_array(values)


def _finite_mask(*arrays: np.ndarray) -> np.ndarray:
    mask = np.ones(arrays[0].shape[0], dtype=bool)
    for array in arrays:
        if np.issubdtype(np.asarray(array).dtype, np.number):
            mask &= np.isfinite(np.asarray(array, dtype=np.float64))
        else:
            mask &= np.asarray(array) == np.asarray(array)
    return mask


def robust_zscore(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(values)
    if not np.any(finite):
        return np.zeros_like(values)
    center = np.nanmedian(values[finite])
    mad = np.nanmedian(np.abs(values[finite] - center))
    if np.isclose(mad, 0.0):
        std = np.nanstd(values[finite])
        if np.isclose(std, 0.0):
            return np.zeros_like(values)
        return (values - np.nanmean(values[finite])) / std
    return 0.6744897501960817 * (values - center) / mad


def adjust_pvalues(pvalues: np.ndarray, method: str = "fdr_bh") -> np.ndarray:
    """Adjust p-values for multiple testing.

    Supports Benjamini-Hochberg (`fdr_bh`) and Bonferroni. If statsmodels is
    installed it is used; otherwise a local BH implementation is applied.
    """

    pvalues = np.asarray(pvalues, dtype=np.float64)
    adjusted = np.full_like(pvalues, np.nan, dtype=np.float64)
    finite_mask = np.isfinite(pvalues)
    finite_values = pvalues[finite_mask]
    if finite_values.size == 0:
        return adjusted

    method = method.lower()
    if method in {"bonferroni", "bonf"}:
        adjusted[finite_mask] = np.clip(finite_values * finite_values.size, 0.0, 1.0)
        return adjusted

    if method not in {"fdr_bh", "bh", "benjamini-hochberg"}:
        raise ValueError(f"Unsupported p-value adjustment method: {method}")

    if _multipletests is not None:  # pragma: no cover - optional dependency path
        adjusted_values = _multipletests(finite_values, alpha=0.05, method="fdr_bh")[1]
        adjusted[finite_mask] = adjusted_values
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


def _numeric_target(target: np.ndarray, target_type: str, class_names: Sequence[Any] | None) -> tuple[np.ndarray, list[Any]]:
    if target_type == "continuous":
        if not np.issubdtype(target.dtype, np.number):
            raise ValueError("Continuous targets must be numeric.")
        return target.astype(np.float64, copy=False), []

    if np.issubdtype(target.dtype, np.number):
        raw_classes = list(np.unique(target[np.isfinite(target)]))
    else:
        raw_classes = list(dict.fromkeys(target.tolist()))

    output_classes = list(class_names) if class_names is not None else raw_classes
    mapping = {label: index for index, label in enumerate(raw_classes)}
    numeric = np.asarray([mapping.get(value, np.nan) for value in target], dtype=np.float64)
    return numeric, output_classes


def apply_ttest_per_band(x: np.ndarray, target_numeric: np.ndarray, class_order: Sequence[Any]) -> tuple[np.ndarray, np.ndarray]:
    t_stat = np.full(x.shape[1], np.nan, dtype=np.float64)
    p_value = np.full(x.shape[1], np.nan, dtype=np.float64)
    if len(class_order) != 2:
        return t_stat, p_value

    class_a, class_b = class_order
    mask_a = target_numeric == 0
    mask_b = target_numeric == 1

    for idx in range(x.shape[1]):
        col = x[:, idx]
        valid = np.isfinite(col) & np.isfinite(target_numeric)
        group_a = col[valid & mask_a]
        group_b = col[valid & mask_b]
        if group_a.size < 3 or group_b.size < 3:
            continue
        if np.isclose(np.nanstd(group_a), 0.0) and np.isclose(np.nanstd(group_b), 0.0):
            continue
        stat, p = ttest_ind(group_a, group_b, equal_var=False, nan_policy="omit")
        t_stat[idx] = float(stat)
        p_value[idx] = float(p)
    return t_stat, p_value


def apply_kruskal_per_band(x: np.ndarray, target_numeric: np.ndarray, class_order: Sequence[Any]) -> tuple[np.ndarray, np.ndarray]:
    h_stat = np.full(x.shape[1], np.nan, dtype=np.float64)
    p_value = np.full(x.shape[1], np.nan, dtype=np.float64)
    if len(class_order) < 2:
        return h_stat, p_value

    groups = [np.where(target_numeric == idx)[0] for idx in range(len(class_order))]
    for band_idx in range(x.shape[1]):
        col = x[:, band_idx]
        valid = np.isfinite(col) & np.isfinite(target_numeric)
        band_groups = [col[valid & (target_numeric == idx)] for idx in range(len(class_order))]
        if any(group.size < 3 for group in band_groups):
            continue
        try:
            stat, p = kruskal(*band_groups, nan_policy="omit")
        except Exception:
            continue
        h_stat[band_idx] = float(stat)
        p_value[band_idx] = float(p)
    return h_stat, p_value


def apply_pearson_per_band(x: np.ndarray, target_numeric: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    correlation = np.full(x.shape[1], np.nan, dtype=np.float64)
    p_value = np.full(x.shape[1], np.nan, dtype=np.float64)
    for idx in range(x.shape[1]):
        col = x[:, idx]
        valid = np.isfinite(col) & np.isfinite(target_numeric)
        if np.count_nonzero(valid) < 3:
            continue
        band = col[valid]
        target = target_numeric[valid]
        if np.isclose(np.nanstd(band), 0.0) or np.isclose(np.nanstd(target), 0.0):
            continue
        stat, p = pearsonr(band, target)
        correlation[idx] = float(stat)
        p_value[idx] = float(p)
    return correlation, p_value


def apply_spearman_per_band(x: np.ndarray, target_numeric: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    correlation = np.full(x.shape[1], np.nan, dtype=np.float64)
    p_value = np.full(x.shape[1], np.nan, dtype=np.float64)
    for idx in range(x.shape[1]):
        col = x[:, idx]
        valid = np.isfinite(col) & np.isfinite(target_numeric)
        if np.count_nonzero(valid) < 3:
            continue
        band = col[valid]
        target = target_numeric[valid]
        if np.isclose(np.nanstd(band), 0.0) or np.isclose(np.nanstd(target), 0.0):
            continue
        stat, p = spearmanr(band, target)
        correlation[idx] = float(stat)
        p_value[idx] = float(p)
    return correlation, p_value


def _class_labels_for_target(target_type: str, class_names: Sequence[Any] | None, target: np.ndarray) -> list[Any]:
    if class_names is not None:
        return list(class_names)
    if target_type == "continuous":
        return []
    if np.issubdtype(target.dtype, np.number):
        return list(np.unique(target))
    return list(dict.fromkeys(target.tolist()))


def _safe_band_label(band_name: Any) -> Any:
    try:
        text = str(band_name)
        if text.isdigit():
            return int(text)
        return float(text)
    except Exception:
        return band_name


def _consistency_score(t_stat: np.ndarray, pearson_r: np.ndarray, spearman_rho: np.ndarray) -> np.ndarray:
    scores = np.zeros(t_stat.shape[0], dtype=np.float64)
    for idx in range(t_stat.shape[0]):
        signs = []
        for value in (t_stat[idx], pearson_r[idx], spearman_rho[idx]):
            if np.isfinite(value) and not np.isclose(value, 0.0):
                signs.append(np.sign(value))
        if len(signs) < 2:
            scores[idx] = 0.0
            continue
        majority = max(np.sum(np.asarray(signs) > 0), np.sum(np.asarray(signs) < 0))
        scores[idx] = majority / len(signs)
    return scores


def _rowwise_nanmean(arrays: Sequence[np.ndarray]) -> np.ndarray:
    stacked = np.vstack(arrays).astype(np.float64, copy=False)
    valid = np.isfinite(stacked)
    counts = np.sum(valid, axis=0)
    sums = np.nansum(stacked, axis=0)
    return np.divide(sums, counts, out=np.zeros(stacked.shape[1], dtype=np.float64), where=counts > 0)


def build_ranking(
    *,
    band_names: Sequence[Any],
    kruskal_stat: np.ndarray,
    kruskal_pvalue: np.ndarray,
    kruskal_pvalue_adj: np.ndarray,
    ttest_stat: np.ndarray,
    ttest_pvalue: np.ndarray,
    ttest_pvalue_adj: np.ndarray,
    pearson_r: np.ndarray,
    pearson_pvalue: np.ndarray,
    pearson_pvalue_adj: np.ndarray,
    spearman_rho: np.ndarray,
    spearman_pvalue: np.ndarray,
    spearman_pvalue_adj: np.ndarray,
    target_type: str,
    class_names: Sequence[Any] | None,
    alpha: float,
    weights: tuple[float, float, float] = (0.45, 0.45, 0.10),
) -> list[dict[str, Any]]:
    band_names = list(band_names)
    n_bands = len(band_names)

    pvalue_sources = np.vstack(
        [
            kruskal_pvalue_adj,
            ttest_pvalue_adj,
            pearson_pvalue_adj,
            spearman_pvalue_adj,
        ]
    )
    pvalue_adjusted = np.full(n_bands, np.nan, dtype=np.float64)
    pvalue_adjusted_source = np.full(n_bands, "", dtype=object)
    for idx in range(n_bands):
        finite = np.isfinite(pvalue_sources[:, idx])
        if not np.any(finite):
            continue
        best_idx = np.argmin(pvalue_sources[finite, idx])
        source_indices = np.flatnonzero(finite)
        chosen = source_indices[best_idx]
        pvalue_adjusted[idx] = pvalue_sources[chosen, idx]
        pvalue_adjusted_source[idx] = ["kruskal", "ttest", "pearson", "spearman"][chosen]

    effect_terms = []
    for values in (np.abs(kruskal_stat), np.abs(ttest_stat), np.abs(pearson_r), np.abs(spearman_rho)):
        if np.any(np.isfinite(values)):
            effect_terms.append(robust_zscore(values))
    if effect_terms:
        effect_score = _rowwise_nanmean(effect_terms)
    else:
        effect_score = np.zeros(n_bands, dtype=np.float64)

    sig_terms = []
    for values in (kruskal_pvalue_adj, ttest_pvalue_adj, pearson_pvalue_adj, spearman_pvalue_adj):
        if np.any(np.isfinite(values)):
            sig_terms.append(robust_zscore(-np.log10(np.clip(values, 1e-300, 1.0))))
    if sig_terms:
        significance_score = _rowwise_nanmean(sig_terms)
    else:
        significance_score = np.zeros(n_bands, dtype=np.float64)

    consistency_score = _consistency_score(ttest_stat, pearson_r, spearman_rho)

    ranking_score = weights[0] * effect_score + weights[1] * significance_score + weights[2] * consistency_score

    rows: list[dict[str, Any]] = []
    for idx, band_name in enumerate(band_names):
        direction: str
        if target_type == "continuous":
            if np.isfinite(pearson_r[idx]) and pearson_r[idx] < 0:
                direction = "negative"
            else:
                direction = "positive"
        else:
            class_labels = list(class_names) if class_names is not None else []
            if len(class_labels) >= 2 and np.isfinite(kruskal_stat[idx]):
                direction = str(class_labels[1]) if np.isfinite(pearson_r[idx]) and pearson_r[idx] >= 0 else str(class_labels[0])
            else:
                direction = "positive" if np.isfinite(pearson_r[idx]) and pearson_r[idx] >= 0 else "negative"

        rows.append(
            {
                "band": _safe_band_label(band_name),
                "kruskal_stat": float(kruskal_stat[idx]) if np.isfinite(kruskal_stat[idx]) else np.nan,
                "kruskal_pvalue": float(kruskal_pvalue[idx]) if np.isfinite(kruskal_pvalue[idx]) else np.nan,
                "kruskal_pvalue_adj": float(kruskal_pvalue_adj[idx]) if np.isfinite(kruskal_pvalue_adj[idx]) else np.nan,
                "ttest_stat": float(ttest_stat[idx]) if np.isfinite(ttest_stat[idx]) else np.nan,
                "ttest_pvalue": float(ttest_pvalue[idx]) if np.isfinite(ttest_pvalue[idx]) else np.nan,
                "ttest_pvalue_adj": float(ttest_pvalue_adj[idx]) if np.isfinite(ttest_pvalue_adj[idx]) else np.nan,
                "pearson_r": float(pearson_r[idx]) if np.isfinite(pearson_r[idx]) else np.nan,
                "pearson_pvalue": float(pearson_pvalue[idx]) if np.isfinite(pearson_pvalue[idx]) else np.nan,
                "pearson_pvalue_adj": float(pearson_pvalue_adj[idx]) if np.isfinite(pearson_pvalue_adj[idx]) else np.nan,
                "spearman_rho": float(spearman_rho[idx]) if np.isfinite(spearman_rho[idx]) else np.nan,
                "spearman_pvalue": float(spearman_pvalue[idx]) if np.isfinite(spearman_pvalue[idx]) else np.nan,
                "spearman_pvalue_adj": float(spearman_pvalue_adj[idx]) if np.isfinite(spearman_pvalue_adj[idx]) else np.nan,
                "pvalue_adjusted": float(pvalue_adjusted[idx]) if np.isfinite(pvalue_adjusted[idx]) else np.nan,
                "pvalue_adjusted_source": str(pvalue_adjusted_source[idx]),
                "significant_at_alpha": bool(np.isfinite(pvalue_adjusted[idx]) and pvalue_adjusted[idx] < alpha),
                "effect_score": float(effect_score[idx]) if np.isfinite(effect_score[idx]) else np.nan,
                "significance_score": float(significance_score[idx]) if np.isfinite(significance_score[idx]) else np.nan,
                "consistency_score": float(consistency_score[idx]) if np.isfinite(consistency_score[idx]) else np.nan,
                "ranking_score": float(ranking_score[idx]) if np.isfinite(ranking_score[idx]) else -np.inf,
                "direction_label": direction,
            }
        )

    rows.sort(key=lambda item: (item["ranking_score"], -abs(item["pvalue_adjusted"]) if np.isfinite(item["pvalue_adjusted"]) else math.inf), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def run_band_significance_analysis(
    data: Any,
    band_columns: Sequence[str],
    target_column: str,
    target_type: str,
    alpha: float = 0.05,
    *,
    class_names: Sequence[Any] | None = None,
    p_adjust_method: str = "fdr_bh",
    min_group_size: int = 3,
    ranking_weights: tuple[float, float, float] = (0.45, 0.45, 0.10),
) -> BandSignificanceResult:
    target_type = target_type.lower()
    if target_type not in {"binary", "multiclass", "continuous"}:
        raise ValueError("target_type must be one of: binary, multiclass, continuous")

    target_raw = _as_array(data[target_column])
    band_columns = list(band_columns)
    x = np.column_stack([_as_array(data[column]).astype(np.float64, copy=False) for column in band_columns])

    target_numeric, class_order = _numeric_target(target_raw, target_type, class_names)
    valid_target = np.isfinite(target_numeric)
    target_numeric = target_numeric.astype(np.float64, copy=False)

    kruskal_stat = np.full(x.shape[1], np.nan, dtype=np.float64)
    kruskal_pvalue = np.full(x.shape[1], np.nan, dtype=np.float64)
    ttest_stat = np.full(x.shape[1], np.nan, dtype=np.float64)
    ttest_pvalue = np.full(x.shape[1], np.nan, dtype=np.float64)
    pearson_r = np.full(x.shape[1], np.nan, dtype=np.float64)
    pearson_pvalue = np.full(x.shape[1], np.nan, dtype=np.float64)
    spearman_rho = np.full(x.shape[1], np.nan, dtype=np.float64)
    spearman_pvalue = np.full(x.shape[1], np.nan, dtype=np.float64)
    n_valid = np.zeros(x.shape[1], dtype=np.int32)
    discard_reason = np.full(x.shape[1], "", dtype=object)
    class_means_min = np.full(x.shape[1], np.nan, dtype=np.float64)
    class_means_max = np.full(x.shape[1], np.nan, dtype=np.float64)
    class_medians_min = np.full(x.shape[1], np.nan, dtype=np.float64)
    class_medians_max = np.full(x.shape[1], np.nan, dtype=np.float64)
    class_std_mean = np.full(x.shape[1], np.nan, dtype=np.float64)
    n_groups = np.full(x.shape[1], 0, dtype=np.int32)

    for idx in range(x.shape[1]):
        col = x[:, idx]
        valid = np.isfinite(col) & valid_target
        x_valid = col[valid]
        y_valid = target_numeric[valid]
        n_valid[idx] = int(x_valid.size)

        if x_valid.size < min_group_size * max(1, len(class_order) if target_type != "continuous" else 1):
            discard_reason[idx] = "insufficient_valid_samples"
            continue

        if np.isclose(np.nanstd(x_valid), 0.0):
            discard_reason[idx] = "zero_variance"
            continue

        if target_type == "continuous":
            if np.isclose(np.nanstd(y_valid), 0.0):
                discard_reason[idx] = "zero_target_variance"
                continue
            pr, pp = pearsonr(x_valid, y_valid)
            sr, sp = spearmanr(x_valid, y_valid)
            pearson_r[idx] = float(pr)
            pearson_pvalue[idx] = float(pp)
            spearman_rho[idx] = float(sr)
            spearman_pvalue[idx] = float(sp)
            continue

        class_values = list(range(len(class_order)))
        groups = [x_valid[y_valid == value] for value in class_values]
        n_groups[idx] = len(groups)
        if any(group.size < min_group_size for group in groups):
            discard_reason[idx] = "insufficient_group_samples"
            continue

        means = np.array([np.nanmean(group) for group in groups], dtype=np.float64)
        medians = np.array([np.nanmedian(group) for group in groups], dtype=np.float64)
        stds = np.array([np.nanstd(group, ddof=1) for group in groups], dtype=np.float64)
        class_means_min[idx] = float(np.nanmin(means))
        class_means_max[idx] = float(np.nanmax(means))
        class_medians_min[idx] = float(np.nanmin(medians))
        class_medians_max[idx] = float(np.nanmax(medians))
        class_std_mean[idx] = float(np.nanmean(stds))

        if len(class_order) >= 2:
            try:
                h, hp = kruskal(*groups, nan_policy="omit")
                kruskal_stat[idx] = float(h)
                kruskal_pvalue[idx] = float(hp)
            except Exception:
                pass

        if len(class_order) == 2:
            try:
                t, tp = ttest_ind(groups[0], groups[1], equal_var=False, nan_policy="omit")
                ttest_stat[idx] = float(t)
                ttest_pvalue[idx] = float(tp)
            except Exception:
                pass
            try:
                pr, pp = pearsonr(x_valid, y_valid)
                sr, sp = spearmanr(x_valid, y_valid)
                pearson_r[idx] = float(pr)
                pearson_pvalue[idx] = float(pp)
                spearman_rho[idx] = float(sr)
                spearman_pvalue[idx] = float(sp)
            except Exception:
                pass

    kruskal_pvalue_adj = adjust_pvalues(kruskal_pvalue, method=p_adjust_method)
    ttest_pvalue_adj = adjust_pvalues(ttest_pvalue, method=p_adjust_method)
    pearson_pvalue_adj = adjust_pvalues(pearson_pvalue, method=p_adjust_method)
    spearman_pvalue_adj = adjust_pvalues(spearman_pvalue, method=p_adjust_method)

    rows = build_ranking(
        band_names=band_columns,
        kruskal_stat=kruskal_stat,
        kruskal_pvalue=kruskal_pvalue,
        kruskal_pvalue_adj=kruskal_pvalue_adj,
        ttest_stat=ttest_stat,
        ttest_pvalue=ttest_pvalue,
        ttest_pvalue_adj=ttest_pvalue_adj,
        pearson_r=pearson_r,
        pearson_pvalue=pearson_pvalue,
        pearson_pvalue_adj=pearson_pvalue_adj,
        spearman_rho=spearman_rho,
        spearman_pvalue=spearman_pvalue,
        spearman_pvalue_adj=spearman_pvalue_adj,
        target_type=target_type,
        class_names=class_names if class_names is not None else class_order,
        alpha=alpha,
        weights=ranking_weights,
    )

    metadata = {
        "target_type": target_type,
        "alpha": alpha,
        "band_count": len(band_columns),
        "valid_bands": int(np.sum(np.array([reason == "" for reason in discard_reason], dtype=bool))),
        "discard_reasons": dict(zip(*np.unique(discard_reason[discard_reason != ""], return_counts=True))) if np.any(discard_reason != "") else {},
        "class_names": list(class_names) if class_names is not None else class_order,
        "p_adjust_method": p_adjust_method,
    }
    return BandSignificanceResult(rows=rows, metadata=metadata)


def write_rows_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Cannot write an empty table.")
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot_top_bands(rows: Sequence[dict[str, Any]], output_path: Path, top_n: int = 20) -> None:
    top = list(rows[:top_n])
    if not top:
        raise ValueError("No rows available for plotting.")
    labels = [str(row["band"]) for row in top][::-1]
    scores = [float(row["ranking_score"]) for row in top][::-1]
    colors = ["#0f766e" if row.get("direction_label") in {"irrigado", "positive"} else "#c2410c" for row in top][::-1]

    fig, ax = plt.subplots(figsize=(11, 7), constrained_layout=True)
    ax.barh(labels, scores, color=colors)
    ax.set_xlabel("Ranking score")
    ax.set_title(f"Top {len(top)} bandas por significância estatística")
    ax.grid(alpha=0.18, axis="x")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def write_summary_markdown(
    path: Path,
    *,
    result: BandSignificanceResult,
    top_n: int = 20,
    alpha: float = 0.05,
) -> None:
    rows = result.rows
    significant = [row for row in rows if row["significant_at_alpha"]]
    lines = [
        "# Band significance analysis",
        "",
        f"- Target type: `{result.metadata['target_type']}`",
        f"- Bands analyzed: `{result.metadata['band_count']}`",
        f"- Significant bands at alpha={alpha:.3f}: `{len(significant)}`",
        f"- p-value adjustment: `{result.metadata['p_adjust_method']}`",
        "",
        "## Score definition",
        "",
        "- `effect_score`: robust z-score average of the available effect metrics.",
        "- `significance_score`: robust z-score average of `-log10(pvalue_adjusted)` across available tests.",
        "- `consistency_score`: agreement among signed metrics when available.",
        "- `ranking_score = 0.45 * effect_score + 0.45 * significance_score + 0.10 * consistency_score`.",
        "",
        "## Top bands",
        "",
        "| rank | band | direction | ranking_score | p_adj | source | significant |",
        "| ---: | ---: | --- | ---: | ---: | --- | --- |",
    ]
    for row in rows[:top_n]:
        p_adj = row["pvalue_adjusted"]
        lines.append(
            f"| {row['rank']} | {row['band']} | {row['direction_label']} | {row['ranking_score']:.4f} | "
            f"{p_adj:.3e} | {row['pvalue_adjusted_source']} | {'yes' if row['significant_at_alpha'] else 'no'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
