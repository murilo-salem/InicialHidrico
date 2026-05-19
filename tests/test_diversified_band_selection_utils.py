from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "estresse_hidrico" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from diversified_band_selection_utils import (  # noqa: E402
    build_absolute_correlation,
    cluster_bands,
    select_ranked_bands_by_cluster_policy,
    summarize_band_subset,
)


def test_cluster_bands_groups_highly_correlated_pairs() -> None:
    abs_corr = pd.DataFrame(
        [
            [1.0, 0.96, 0.20, 0.18],
            [0.96, 1.0, 0.19, 0.17],
            [0.20, 0.19, 1.0, 0.97],
            [0.18, 0.17, 0.97, 1.0],
        ],
        index=["band_350", "band_351", "band_700", "band_701"],
        columns=["band_350", "band_351", "band_700", "band_701"],
    )

    mapping = cluster_bands(abs_corr, threshold=0.95)

    assert mapping["band_350"] == mapping["band_351"]
    assert mapping["band_700"] == mapping["band_701"]
    assert mapping["band_350"] != mapping["band_700"]


def test_soft_policy_waits_for_other_clusters_before_reusing_one() -> None:
    ranked_bands = ["band_350", "band_351", "band_500", "band_501", "band_700"]
    band_to_cluster = {
        "band_350": 1,
        "band_351": 1,
        "band_500": 2,
        "band_501": 2,
        "band_700": 3,
    }

    hard_records = select_ranked_bands_by_cluster_policy(ranked_bands, band_to_cluster, k=5, policy="hard")
    soft_records = select_ranked_bands_by_cluster_policy(ranked_bands, band_to_cluster, k=5, policy="soft")

    assert [record.band for record in hard_records] == ["band_350", "band_500", "band_700"]
    assert [record.band for record in soft_records] == ["band_350", "band_500", "band_700", "band_351", "band_501"]
    assert [record.selection_round for record in soft_records] == [1, 1, 1, 2, 2]


def test_summarize_band_subset_reports_spacing_and_regions() -> None:
    data = pd.DataFrame(
        {
            "band_350": [0.1, 0.2, 0.3, 0.4],
            "band_351": [0.1, 0.2, 0.3, 0.39],
            "band_700": [0.4, 0.3, 0.2, 0.1],
            "band_710": [0.41, 0.31, 0.21, 0.09],
        }
    )
    abs_corr = build_absolute_correlation(data)
    band_to_cluster = {
        "band_350": 1,
        "band_351": 1,
        "band_700": 2,
        "band_710": 3,
    }

    summary = summarize_band_subset(["band_350", "band_351", "band_700", "band_710"], abs_corr, band_to_cluster)

    assert summary["n_clusters_represented"] == 3
    assert summary["max_bands_in_same_cluster"] == 2
    assert summary["min_nm"] == 350
    assert summary["max_nm"] == 710
    assert summary["largest_contiguous_run_nm"] == 2
    assert summary["n_distinct_spectral_regions"] == 2
    assert summary["spectral_regions"] == "350-499|700-999"

