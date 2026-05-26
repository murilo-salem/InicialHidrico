#!/usr/bin/env python3
"""Compute band importance (Gini and VIP) for significance-based results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.cross_decomposition import PLSRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from significance_classification_utils import (
    TARGET_SPECS,
    build_group_labels,
    prepare_targets,
    resolve_class_order,
    select_recurrent_bands,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    workspace_dir = project_dir.parent
    parser = argparse.ArgumentParser(
        description="Calcula importancia de bandas (Gini e VIP) para os alvos com bandas significativas."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
    )
    parser.add_argument(
        "--significance-dir",
        type=Path,
        default=workspace_dir / "TestesSignfDiniz" / "TOP5_POR_DIA_TURNO",
    )
    parser.add_argument(
        "--best-optuna-csv",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "optuna_significancia_melhores_modelos_2026-05-19" / "optuna_resumo_geral.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "importancia_bandas_significativas_2026-05-19",
    )
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def build_pipeline_from_optuna_row(row: pd.Series) -> Pipeline:
    model_name = str(row["model"])
    params = json.loads(str(row["best_params"]))

    if model_name == "Random Forest":
        model = RandomForestClassifier(
            n_estimators=int(params["rf_n_estimators"]),
            max_depth=int(params["rf_max_depth"]),
            min_samples_split=int(params["rf_min_samples_split"]),
            min_samples_leaf=int(params["rf_min_samples_leaf"]),
            max_features=params["rf_max_features"],
            class_weight=params["rf_class_weight"],
            random_state=42,
            n_jobs=-1,
        )
        return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", model)])

    if model_name == "LDA":
        shrinkage = params["lda_shrinkage"] if params["lda_shrinkage_mode"] == "float" else "auto"
        model = LinearDiscriminantAnalysis(solver=params["lda_solver"], shrinkage=shrinkage)
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", model),
            ]
        )

    raise ValueError(f"Modelo nao suportado: {model_name}")


def compute_vip_scores(x: np.ndarray, y: np.ndarray, n_components: int) -> np.ndarray:
    pls = PLSRegression(n_components=n_components)
    pls.fit(x, y)
    t = pls.x_scores_
    w = pls.x_weights_
    q = pls.y_loadings_
    p = w.shape[0]
    h = w.shape[1]

    ssy = np.array(
        [
            np.sum(t[:, a] ** 2) * np.sum(q[:, a] ** 2)
            for a in range(h)
        ],
        dtype=float,
    )
    denominator = np.sum(ssy)
    if denominator <= 0:
        return np.zeros(p, dtype=float)

    vip = np.zeros(p, dtype=float)
    for j in range(p):
        numerator = 0.0
        for a in range(h):
            w_norm = np.sum(w[:, a] ** 2)
            if w_norm > 0:
                numerator += ssy[a] * (w[j, a] ** 2) / w_norm
        vip[j] = np.sqrt(p * numerator / denominator)
    return vip


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = prepare_targets(pd.read_csv(args.input.resolve()))
    best_df = pd.read_csv(args.best_optuna_csv.resolve())
    band_columns = [column for column in frame.columns if str(column).startswith("band_")]

    all_vip_rows: list[dict[str, object]] = []
    all_gini_rows: list[dict[str, object]] = []
    all_permutation_rows: list[dict[str, object]] = []
    summary_lines = [
        "# Importancia das bandas significativas",
        "",
        "| alvo | melhor_modelo | banda_mais_importante_gini | banda_mais_importante_vip | banda_mais_importante_permutacao |",
        "| --- | --- | --- | --- | --- |",
    ]

    for target_name, spec in TARGET_SPECS.items():
        label_column = spec["label_column"]
        analysis_source = spec["analysis_source"]
        target_dir = output_dir / target_name
        target_dir.mkdir(parents=True, exist_ok=True)

        selected_bands_df = select_recurrent_bands(
            significance_dir=args.significance_dir.resolve(),
            analysis_source=analysis_source,
            top_n=args.top_n,
            band_columns=band_columns,
        )
        features = selected_bands_df["band_column"].tolist()
        write_csv(selected_bands_df, target_dir / "bandas_selecionadas.csv")

        row = best_df.loc[best_df["target"] == target_name]
        if row.empty:
            raise ValueError(f"Alvo ausente no CSV de melhor Optuna: {target_name}")
        row = row.iloc[0]
        model_name = str(row["model"])
        pipeline = build_pipeline_from_optuna_row(row)

        class_names = resolve_class_order(target_name, frame[label_column].tolist())
        label_to_index = {label: idx for idx, label in enumerate(class_names)}
        x_df = frame[features].copy()
        y = frame[label_column].map(label_to_index).to_numpy(dtype=int)
        groups = build_group_labels(frame[label_column], frame["replicata"])
        min_groups = int(pd.Series(groups).groupby(frame[label_column]).nunique().min())
        n_splits = min(5, max(2, min_groups))
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=args.seed)
        splits = list(splitter.split(x_df, y, groups))

        top_gini_band = "-"
        if model_name == "Random Forest":
            fold_importances: list[np.ndarray] = []
            for train_idx, _ in splits:
                fitted = clone(pipeline)
                fitted.fit(x_df.iloc[train_idx], y[train_idx])
                model = fitted.named_steps["model"]
                fold_importances.append(np.asarray(model.feature_importances_, dtype=float))
            matrix = np.vstack(fold_importances)
            gini_mean = matrix.mean(axis=0)
            gini_std = matrix.std(axis=0, ddof=1) if matrix.shape[0] > 1 else np.zeros_like(gini_mean)
            gini_df = pd.DataFrame(
                {
                    "target": target_name,
                    "model": model_name,
                    "feature": features,
                    "gini_mean": gini_mean,
                    "gini_std": gini_std,
                }
            ).sort_values("gini_mean", ascending=False)
            write_csv(gini_df, target_dir / "gini_importance.csv")
            top_gini_band = str(gini_df.iloc[0]["feature"])
            all_gini_rows.extend(gini_df.to_dict(orient="records"))

        # Permutation importance over full data with the tuned best pipeline.
        fitted_full = clone(pipeline)
        fitted_full.fit(x_df, y)
        permutation = permutation_importance(
            fitted_full,
            x_df,
            y,
            scoring="f1_macro",
            n_repeats=30,
            random_state=args.seed,
            n_jobs=-1,
        )
        permutation_df = pd.DataFrame(
            {
                "target": target_name,
                "model": model_name,
                "feature": features,
                "permutation_mean": permutation.importances_mean,
                "permutation_std": permutation.importances_std,
            }
        ).sort_values("permutation_mean", ascending=False)
        write_csv(permutation_df, target_dir / "permutation_importance.csv")
        all_permutation_rows.extend(permutation_df.to_dict(orient="records"))
        top_permutation_band = str(permutation_df.iloc[0]["feature"])

        x_values = x_df.to_numpy(dtype=float)
        x_scaled = StandardScaler().fit_transform(x_values)
        n_classes = len(class_names)
        y_onehot = np.eye(n_classes, dtype=float)[y]
        n_components = max(1, min(x_scaled.shape[1] - 1, n_classes - 1, 3))
        vip_scores = compute_vip_scores(x_scaled, y_onehot, n_components=n_components)
        vip_df = pd.DataFrame(
            {
                "target": target_name,
                "model": model_name,
                "feature": features,
                "vip_score": vip_scores,
            }
        ).sort_values("vip_score", ascending=False)
        write_csv(vip_df, target_dir / "vip_scores.csv")
        all_vip_rows.extend(vip_df.to_dict(orient="records"))
        top_vip_band = str(vip_df.iloc[0]["feature"])

        summary_lines.append(
            f"| {target_name} | {model_name} | {top_gini_band} | {top_vip_band} | {top_permutation_band} |"
        )

    if all_gini_rows:
        write_csv(pd.DataFrame(all_gini_rows), output_dir / "gini_importance_all_targets.csv")
    write_csv(pd.DataFrame(all_vip_rows), output_dir / "vip_scores_all_targets.csv")
    write_csv(pd.DataFrame(all_permutation_rows), output_dir / "permutation_importance_all_targets.csv")
    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
