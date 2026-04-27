from __future__ import annotations

import unittest

import numpy as np

from band_significance import run_band_significance_analysis


class BandSignificanceTests(unittest.TestCase):
    def test_binary_ranking_prefers_informative_bands(self) -> None:
        rng = np.random.default_rng(42)
        y = np.array([0] * 40 + [1] * 40, dtype=np.int32)
        band_signal = y.astype(np.float64) + rng.normal(0.0, 0.05, size=y.size)
        band_monotonic = np.square(y.astype(np.float64)) + rng.normal(0.0, 0.05, size=y.size)
        band_noise = rng.normal(0.0, 1.0, size=y.size)
        data = {
            "signal": band_signal,
            "monotonic": band_monotonic,
            "noise": band_noise,
            "target": y,
        }

        result = run_band_significance_analysis(
            data,
            band_columns=["signal", "monotonic", "noise"],
            target_column="target",
            target_type="binary",
            alpha=0.05,
            class_names=("nao_irrigado", "irrigado"),
        )

        top_bands = [row["band"] for row in result.rows[:2]]
        self.assertIn("signal", top_bands)
        self.assertTrue(any(row["band"] == "signal" and row["significant_at_alpha"] for row in result.rows))
        self.assertTrue(any(row["band"] == "monotonic" and row["significant_at_alpha"] for row in result.rows))

    def test_continuous_ranking_uses_correlations(self) -> None:
        rng = np.random.default_rng(7)
        target = np.linspace(-1.0, 1.0, 90, dtype=np.float64)
        band_linear = target + rng.normal(0.0, 0.04, size=target.size)
        band_monotonic = np.tanh(2.5 * target) + rng.normal(0.0, 0.04, size=target.size)
        band_noise = rng.normal(0.0, 1.0, size=target.size)
        data = {
            "linear": band_linear,
            "monotonic": band_monotonic,
            "noise": band_noise,
            "target": target,
        }

        result = run_band_significance_analysis(
            data,
            band_columns=["linear", "monotonic", "noise"],
            target_column="target",
            target_type="continuous",
            alpha=0.05,
        )

        top_bands = [row["band"] for row in result.rows[:2]]
        self.assertIn("linear", top_bands)
        self.assertIn("monotonic", top_bands)
        self.assertTrue(any(row["band"] == "linear" and row["significant_at_alpha"] for row in result.rows))

    def test_multiclass_uses_kruskal(self) -> None:
        rng = np.random.default_rng(11)
        target = np.array([0] * 25 + [1] * 25 + [2] * 25, dtype=np.int32)
        band_separated = np.concatenate(
            [
                rng.normal(0.0, 0.05, 25),
                rng.normal(1.5, 0.05, 25),
                rng.normal(3.0, 0.05, 25),
            ]
        )
        band_noise = rng.normal(0.0, 1.0, size=target.size)
        data = {
            "separated": band_separated,
            "noise": band_noise,
            "target": target,
        }

        result = run_band_significance_analysis(
            data,
            band_columns=["separated", "noise"],
            target_column="target",
            target_type="multiclass",
            alpha=0.05,
            class_names=("class0", "class1", "class2"),
        )

        self.assertEqual(result.rows[0]["band"], "separated")
        self.assertTrue(result.rows[0]["significant_at_alpha"])
        self.assertTrue(np.isnan(result.rows[0]["pearson_r"]))
        self.assertTrue(np.isnan(result.rows[0]["spearman_rho"]))


if __name__ == "__main__":
    unittest.main()
