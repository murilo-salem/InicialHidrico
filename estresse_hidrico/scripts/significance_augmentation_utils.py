#!/usr/bin/env python3
"""Augmentation and feature helpers for significance-driven classification."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _feature_std(values: np.ndarray) -> np.ndarray:
    feature_std = np.nanstd(values, axis=0, ddof=1)
    positive = feature_std[np.isfinite(feature_std) & (feature_std > 0)]
    fallback_std = float(np.nanmedian(positive)) if len(positive) else 1.0
    if not np.isfinite(fallback_std) or fallback_std <= 0:
        fallback_std = 1.0
    return np.where(np.isfinite(feature_std) & (feature_std > 0), feature_std, fallback_std)


def augment_spectral_jitter(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    fold_index: int,
    *,
    copies_per_sample: int = 3,
    noise_std_fraction: float = 0.015,
    scale_range: float = 0.02,
    offset_std_fraction: float = 0.005,
    clip_to_train_range: bool = True,
    random_state: int = 42,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Create conservative spectral jitter copies using training-fold statistics only."""
    if copies_per_sample <= 0:
        return x_train.copy(), y_train.copy()

    values = x_train.to_numpy(dtype=np.float64, copy=True)
    rng = np.random.default_rng(random_state + fold_index * 1009)
    feature_std = _feature_std(values)
    train_min = np.nanmin(values, axis=0)
    train_max = np.nanmax(values, axis=0)

    synthetic_blocks: list[np.ndarray] = []
    for _ in range(copies_per_sample):
        scale = rng.uniform(1.0 - scale_range, 1.0 + scale_range, size=(len(values), 1))
        noise = rng.normal(0.0, feature_std * noise_std_fraction, size=values.shape)
        offset = rng.normal(0.0, feature_std * offset_std_fraction, size=values.shape)
        synthetic = values * scale + noise + offset
        if clip_to_train_range:
            synthetic = np.clip(synthetic, train_min, train_max)
        synthetic_blocks.append(synthetic)

    synthetic_values = np.vstack(synthetic_blocks)
    x_augmented = pd.concat(
        [x_train.reset_index(drop=True), pd.DataFrame(synthetic_values, columns=x_train.columns)],
        ignore_index=True,
    )
    y_augmented = np.concatenate([y_train, np.tile(y_train, copies_per_sample)])
    return x_augmented, y_augmented


def augment_spectral_mixup(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    fold_index: int,
    *,
    copies_per_sample: int = 3,
    alpha: float = 0.4,
    clip_to_train_range: bool = True,
    random_state: int = 42,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Interpolate spectra within the same class using training-fold samples only."""
    if copies_per_sample <= 0:
        return x_train.copy(), y_train.copy()

    values = x_train.to_numpy(dtype=np.float64, copy=True)
    rng = np.random.default_rng(random_state + fold_index * 2003)
    train_min = np.nanmin(values, axis=0)
    train_max = np.nanmax(values, axis=0)
    synthetic_blocks: list[np.ndarray] = []
    synthetic_labels: list[np.ndarray] = []

    for class_value in np.unique(y_train):
        class_idx = np.flatnonzero(y_train == class_value)
        if len(class_idx) == 0:
            continue
        n_synthetic = len(class_idx) * copies_per_sample
        left = rng.choice(class_idx, size=n_synthetic, replace=True)
        right = rng.choice(class_idx, size=n_synthetic, replace=True)
        lam = rng.beta(alpha, alpha, size=(n_synthetic, 1))
        synthetic = lam * values[left] + (1.0 - lam) * values[right]
        if clip_to_train_range:
            synthetic = np.clip(synthetic, train_min, train_max)
        synthetic_blocks.append(synthetic)
        synthetic_labels.append(np.full(n_synthetic, class_value, dtype=y_train.dtype))

    if not synthetic_blocks:
        return x_train.copy(), y_train.copy()

    synthetic_values = np.vstack(synthetic_blocks)
    x_augmented = pd.concat(
        [x_train.reset_index(drop=True), pd.DataFrame(synthetic_values, columns=x_train.columns)],
        ignore_index=True,
    )
    y_augmented = np.concatenate([y_train, *synthetic_labels])
    return x_augmented, y_augmented


def prune_correlated_features(
    frame: pd.DataFrame,
    ordered_features: list[str],
    *,
    max_features: int,
    correlation_threshold: float = 0.95,
) -> list[str]:
    """Keep the ordered features while dropping bands highly correlated to earlier picks."""
    if max_features <= 0:
        raise ValueError("max_features must be positive.")
    if not ordered_features:
        return []

    candidates = [feature for feature in ordered_features if feature in frame.columns]
    if not candidates:
        return []

    corr = frame[candidates].corr(method="pearson").abs().fillna(0.0)
    selected: list[str] = []
    for feature in candidates:
        if len(selected) >= max_features:
            break
        if not selected:
            selected.append(feature)
            continue
        max_corr = float(corr.loc[feature, selected].max())
        if max_corr < correlation_threshold:
            selected.append(feature)
    return selected
