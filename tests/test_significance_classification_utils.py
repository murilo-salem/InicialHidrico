from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "estresse_hidrico" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from significance_classification_utils import (  # noqa: E402
    build_group_labels,
    evaluate_model_holdout,
    prepare_targets,
    resolve_class_order,
    select_recurrent_bands,
)


def test_prepare_targets_builds_expected_global_labels() -> None:
    frame = pd.DataFrame(
        {
            "cultivar": ["BR16", "CD202"],
            "condicao": ["IRR", "NIRR"],
            "replicata": [1, 2],
            "turnos_disponiveis": ["manha + tarde", "unico"],
        }
    )

    prepared = prepare_targets(frame)

    assert prepared["target_condicao"].tolist() == ["IRR", "NIRR"]
    assert prepared["target_condicao_genotipo"].tolist() == ["IRR|BR16", "NIRR|CD202"]
    assert prepared["target_condicao_genotipo_turno"].tolist() == [
        "IRR|BR16|manha + tarde",
        "NIRR|CD202|unico",
    ]


def test_build_group_labels_uses_target_and_replicate() -> None:
    labels = pd.Series(["IRR|BR16", "IRR|BR16", "NIRR|BR16"], dtype="object")
    replicates = pd.Series([1, 2, 1], dtype="int64")

    groups = build_group_labels(labels, replicates)

    assert groups.tolist() == ["IRR|BR16_B1", "IRR|BR16_B2", "NIRR|BR16_B1"]


def test_resolve_class_order_keeps_binary_condition_as_nirr_then_irr() -> None:
    order = resolve_class_order("condicao", ["IRR", "NIRR", "IRR"])

    assert order == ["NIRR", "IRR"]


def test_select_recurrent_bands_prefers_frequency_then_rank(tmp_path: Path) -> None:
    significance_dir = tmp_path / "TOP5"
    significance_dir.mkdir()
    pd.DataFrame(
        [
            {"analysis": "cond", "rank": 1, "wavelength_nm": 400.0, "q_FDR_BH": 1e-6},
            {"analysis": "cond", "rank": 2, "wavelength_nm": 530.0, "q_FDR_BH": 1e-5},
            {"analysis": "cond", "rank": 1, "wavelength_nm": 400.0, "q_FDR_BH": 1e-7},
            {"analysis": "cond", "rank": 3, "wavelength_nm": 579.0, "q_FDR_BH": 1e-4},
            {"analysis": "cond", "rank": 2, "wavelength_nm": 579.0, "q_FDR_BH": 1e-5},
            {"analysis": "cond", "rank": 1, "wavelength_nm": 739.0, "q_FDR_BH": 1e-8},
        ]
    ).to_csv(significance_dir / "TOP5_TODOS_DIAS_TURNOS_CONSOLIDADO.csv", index=False)

    selected = select_recurrent_bands(
        significance_dir=significance_dir,
        analysis_source="cond",
        top_n=3,
        band_columns=["band_400", "band_530", "band_579", "band_739"],
    )

    assert selected["wavelength_nm"].tolist() == [400, 579, 739]
    assert selected["band_column"].tolist() == ["band_400", "band_579", "band_739"]
    assert selected["frequency"].tolist() == [2, 2, 1]


def test_select_recurrent_bands_falls_back_to_nearest_available_band(tmp_path: Path) -> None:
    significance_dir = tmp_path / "TOP5"
    significance_dir.mkdir()
    pd.DataFrame(
        [
            {"analysis": "gen_cond", "rank": 1, "wavelength_nm": 1386.0, "q_FDR_BH": 1e-6},
            {"analysis": "gen_cond", "rank": 2, "wavelength_nm": 400.0, "q_FDR_BH": 1e-5},
        ]
    ).to_csv(significance_dir / "TOP5_TODOS_DIAS_TURNOS_CONSOLIDADO.csv", index=False)

    selected = select_recurrent_bands(
        significance_dir=significance_dir,
        analysis_source="gen_cond",
        top_n=2,
        band_columns=["band_400", "band_1349", "band_1451"],
    )

    assert selected.iloc[0]["band_column"] == "band_1349"
    assert bool(selected.iloc[0]["resolved_exact_match"]) is False


def test_evaluate_model_holdout_uses_grouped_80_20_split_without_group_leakage() -> None:
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rows = []
    for condicao in ["NIRR", "IRR"]:
        for rep in [1, 2, 3, 4]:
            for sample_idx in range(3):
                base = 0.2 if condicao == "NIRR" else 0.8
                rows.append(
                    {
                        "condicao": condicao,
                        "cultivar": "BR16",
                        "replicata": rep,
                        "band_400": base + 0.01 * sample_idx,
                        "band_530": base + 0.02 * sample_idx,
                    }
                )
    frame = pd.DataFrame(rows)
    frame = prepare_targets(frame)
    groups = build_group_labels(frame["target_condicao"], frame["replicata"])
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        ]
    )

    artifacts = evaluate_model_holdout(
        model_name="LDA",
        model=model,
        frame=frame,
        feature_columns=["band_400", "band_530"],
        label_column="target_condicao",
        target_name="condicao",
        class_names=["NIRR", "IRR"],
        groups=groups,
        test_size=0.2,
        random_state=42,
    )

    predictions = artifacts.predictions_df
    test_mask = predictions["in_test_split"].astype(bool).to_numpy()
    assert test_mask.sum() > 0
    test_ratio = test_mask.mean()
    assert 0.15 <= test_ratio <= 0.35

    train_groups = set(groups[~test_mask])
    test_groups = set(groups[test_mask])
    assert train_groups.isdisjoint(test_groups)
