#!/usr/bin/env python3
"""Utilities for diversified spectral band selection."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform


SPECTRAL_REGION_BINS: list[tuple[str, int, int]] = [
    ("350-499", 350, 499),
    ("500-699", 500, 699),
    ("700-999", 700, 999),
    ("1000-1399", 1000, 1399),
    ("1400-1799", 1400, 1799),
    ("1800-2500", 1800, 2500),
]


@dataclass(frozen=True)
class SelectionRecord:
    band: str
    wavelength_nm: int
    cluster_id: int
    rank_position: int
    selection_round: int


def band_to_wavelength(band_name: str) -> int:
    return int(str(band_name).replace("band_", "", 1))


def format_threshold_token(threshold: float) -> str:
    return f"{threshold:.2f}".replace(".", "p")


def build_absolute_correlation(data: pd.DataFrame) -> pd.DataFrame:
    corr = data.astype(float).corr(method="pearson").abs().fillna(0.0).copy()
    corr_values = corr.to_numpy(copy=True)
    np.fill_diagonal(corr_values, 1.0)
    corr.iloc[:, :] = corr_values
    ordered = sorted(corr.columns, key=band_to_wavelength)
    return corr.loc[ordered, ordered]


def cluster_bands(abs_corr: pd.DataFrame, threshold: float) -> dict[str, int]:
    if abs_corr.empty:
        return {}
    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must be in the interval (0, 1].")
    if abs_corr.shape[0] == 1:
        band_name = str(abs_corr.index[0])
        return {band_name: 1}

    distances = 1.0 - abs_corr.to_numpy(dtype=float)
    distances = np.clip(distances, 0.0, 1.0)
    np.fill_diagonal(distances, 0.0)
    condensed = squareform(distances, checks=False)
    linkage_matrix = linkage(condensed, method="average")
    labels = fcluster(linkage_matrix, t=1.0 - threshold, criterion="distance")
    return {str(band): int(cluster_id) for band, cluster_id in zip(abs_corr.index.tolist(), labels.tolist(), strict=True)}


def spectral_region_label(wavelength_nm: int) -> str:
    for label, start_nm, end_nm in SPECTRAL_REGION_BINS:
        if start_nm <= wavelength_nm <= end_nm:
            return label
    return "out_of_range"


def filter_ranked_bands(ranked_bands: list[str], allowed_bands: set[str]) -> list[str]:
    seen: set[str] = set()
    filtered: list[str] = []
    for band in ranked_bands:
        band_name = str(band)
        if band_name not in allowed_bands or band_name in seen:
            continue
        seen.add(band_name)
        filtered.append(band_name)
    return filtered


def select_ranked_bands_by_cluster_policy(
    ranked_bands: list[str],
    band_to_cluster: dict[str, int],
    k: int,
    policy: str,
) -> list[SelectionRecord]:
    if k < 0:
        raise ValueError("k must be non-negative.")
    if policy not in {"hard", "soft"}:
        raise ValueError("policy must be 'hard' or 'soft'.")

    ranked = [band for band in ranked_bands if band in band_to_cluster]
    rank_position = {band: idx + 1 for idx, band in enumerate(ranked)}

    if policy == "hard":
        selected: list[SelectionRecord] = []
        seen_clusters: set[int] = set()
        for band in ranked:
            cluster_id = int(band_to_cluster[band])
            if cluster_id in seen_clusters:
                continue
            selected.append(
                SelectionRecord(
                    band=band,
                    wavelength_nm=band_to_wavelength(band),
                    cluster_id=cluster_id,
                    rank_position=rank_position[band],
                    selection_round=1,
                )
            )
            seen_clusters.add(cluster_id)
            if len(selected) == k:
                break
        return selected

    cluster_bands_map: dict[int, list[str]] = defaultdict(list)
    for band in ranked:
        cluster_bands_map[int(band_to_cluster[band])].append(band)

    selected = []
    round_index = 0
    while len(selected) < k:
        round_candidates: list[tuple[int, int, str]] = []
        for cluster_id, cluster_bands_list in cluster_bands_map.items():
            if len(cluster_bands_list) <= round_index:
                continue
            band = cluster_bands_list[round_index]
            round_candidates.append((rank_position[band], cluster_id, band))
        if not round_candidates:
            break
        round_candidates.sort()
        for _, cluster_id, band in round_candidates:
            selected.append(
                SelectionRecord(
                    band=band,
                    wavelength_nm=band_to_wavelength(band),
                    cluster_id=cluster_id,
                    rank_position=rank_position[band],
                    selection_round=round_index + 1,
                )
            )
            if len(selected) == k:
                break
        round_index += 1

    return selected


def summarize_band_subset(
    selected_bands: list[str],
    abs_corr: pd.DataFrame,
    band_to_cluster: dict[str, int],
) -> dict[str, object]:
    if not selected_bands:
        return {
            "n_clusters_represented": 0,
            "max_bands_in_same_cluster": 0,
            "median_abs_corr_within_subset": np.nan,
            "mean_abs_corr_within_subset": np.nan,
            "min_nm": np.nan,
            "max_nm": np.nan,
            "median_gap_nm": np.nan,
            "mean_gap_nm": np.nan,
            "largest_contiguous_run_nm": 0,
            "n_distinct_spectral_regions": 0,
            "spectral_regions": "",
        }

    wavelengths = sorted(band_to_wavelength(band) for band in selected_bands)
    cluster_counts = Counter(int(band_to_cluster[band]) for band in selected_bands if band in band_to_cluster)
    gaps = np.diff(wavelengths).astype(float) if len(wavelengths) >= 2 else np.asarray([], dtype=float)

    pairwise_abs_corr = np.asarray([], dtype=float)
    if len(selected_bands) >= 2:
        subset_corr = abs_corr.loc[selected_bands, selected_bands].to_numpy(dtype=float)
        upper_indices = np.triu_indices_from(subset_corr, k=1)
        pairwise_abs_corr = subset_corr[upper_indices]

    regions = sorted({spectral_region_label(wavelength) for wavelength in wavelengths})

    largest_run = 1
    current_run = 1
    for previous_nm, current_nm in zip(wavelengths, wavelengths[1:]):
        if current_nm == previous_nm + 1:
            current_run += 1
        else:
            largest_run = max(largest_run, current_run)
            current_run = 1
    largest_run = max(largest_run, current_run)

    return {
        "n_clusters_represented": int(len(cluster_counts)),
        "max_bands_in_same_cluster": int(max(cluster_counts.values())) if cluster_counts else 0,
        "median_abs_corr_within_subset": float(np.nanmedian(pairwise_abs_corr)) if pairwise_abs_corr.size else np.nan,
        "mean_abs_corr_within_subset": float(np.nanmean(pairwise_abs_corr)) if pairwise_abs_corr.size else np.nan,
        "min_nm": int(wavelengths[0]),
        "max_nm": int(wavelengths[-1]),
        "median_gap_nm": float(np.median(gaps)) if gaps.size else np.nan,
        "mean_gap_nm": float(np.mean(gaps)) if gaps.size else np.nan,
        "largest_contiguous_run_nm": int(largest_run),
        "n_distinct_spectral_regions": int(len(regions)),
        "spectral_regions": "|".join(regions),
    }
