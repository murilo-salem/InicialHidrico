from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "estresse_hidrico" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from significance_classification_utils import evaluate_model_cv  # noqa: E402
from significance_augmentation_utils import (  # noqa: E402
    augment_spectral_mixup,
    prune_correlated_features,
)


def load_augmentation_module():
    script_path = SCRIPT_DIR / "23_classificacao_significancia_augmentation.py"
    spec = importlib.util.spec_from_file_location("classification_augmentation", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_augment_spectral_training_data_adds_clipped_copies() -> None:
    module = load_augmentation_module()
    x_train = pd.DataFrame({"band_400": [0.10, 0.20], "band_530": [0.40, 0.60]})
    y_train = np.array([0, 1])

    x_augmented, y_augmented = module.augment_spectral_training_data(
        x_train,
        y_train,
        fold_index=1,
        copies_per_sample=2,
        noise_std_fraction=0.10,
        scale_range=0.05,
        offset_std_fraction=0.01,
        clip_to_train_range=True,
        random_state=42,
    )

    assert x_augmented.shape == (6, 2)
    assert y_augmented.tolist() == [0, 1, 0, 1, 0, 1]
    assert x_augmented["band_400"].between(0.10, 0.20).all()
    assert x_augmented["band_530"].between(0.40, 0.60).all()
    pd.testing.assert_frame_equal(x_augmented.iloc[:2].reset_index(drop=True), x_train)


def test_evaluate_model_cv_invokes_train_augmenter_per_fold() -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    frame = pd.DataFrame(
        {
            "cultivar": ["BR16"] * 8,
            "condicao": ["NIRR", "NIRR", "NIRR", "NIRR", "IRR", "IRR", "IRR", "IRR"],
            "replicata": [1, 2, 3, 4, 1, 2, 3, 4],
            "band_400": [0.10, 0.11, 0.12, 0.13, 0.90, 0.91, 0.92, 0.93],
        }
    )
    frame["target_condicao"] = frame["condicao"]
    groups = (frame["target_condicao"] + "_B" + frame["replicata"].astype(str)).to_numpy()
    calls: list[int] = []

    def augmenter(x_train: pd.DataFrame, y_train: np.ndarray, fold_index: int):
        calls.append(fold_index)
        return pd.concat([x_train, x_train], ignore_index=True), np.concatenate([y_train, y_train])

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(random_state=42)),
        ]
    )

    artifacts = evaluate_model_cv(
        model_name="LogReg",
        model=model,
        frame=frame,
        feature_columns=["band_400"],
        label_column="target_condicao",
        target_name="condicao",
        class_names=["NIRR", "IRR"],
        groups=groups,
        n_splits=2,
        train_augmenter=augmenter,
    )

    assert calls == [1, 2]
    assert artifacts.metrics_row["n_samples"] == 8
    assert artifacts.confusion_matrix.shape == (2, 2)


def test_augment_spectral_mixup_only_interpolates_within_class() -> None:
    x_train = pd.DataFrame({"band_400": [0.0, 0.2, 0.8, 1.0]})
    y_train = np.array([0, 0, 1, 1])

    x_augmented, y_augmented = augment_spectral_mixup(
        x_train,
        y_train,
        fold_index=1,
        copies_per_sample=1,
        alpha=0.4,
        clip_to_train_range=True,
        random_state=42,
    )

    assert x_augmented.shape == (8, 1)
    assert y_augmented.tolist() == [0, 0, 1, 1, 0, 0, 1, 1]
    assert x_augmented.iloc[4:6, 0].between(0.0, 0.2).all()
    assert x_augmented.iloc[6:8, 0].between(0.8, 1.0).all()


def test_prune_correlated_features_keeps_ordered_nonredundant_bands() -> None:
    frame = pd.DataFrame(
        {
            "band_400": [1.0, 2.0, 3.0, 4.0],
            "band_401": [1.1, 2.1, 3.1, 4.1],
            "band_720": [4.0, 1.0, 3.0, 2.0],
        }
    )

    selected = prune_correlated_features(
        frame,
        ["band_400", "band_401", "band_720"],
        max_features=3,
        correlation_threshold=0.95,
    )

    assert selected == ["band_400", "band_720"]
