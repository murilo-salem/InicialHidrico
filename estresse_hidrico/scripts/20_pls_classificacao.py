#!/usr/bin/env python3
"""PLS classification for irrigation (IRR vs NIRR) per day with band importance."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    make_scorer,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict, cross_validate
from sklearn.preprocessing import StandardScaler

OUTPUT_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/tabelas/pls_irrigacao_por_dia")
FIGURE_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/figuras/pls_irrigacao_por_dia")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = ["band_1200", "band_1451", "band_1951", "band_970", "band_670", "NDRE"]
FEATURE_LABELS = ["1200nm", "1451nm", "1951nm", "970nm", "670nm (Clorofila)", "NDRE"]
DIAS = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9"]
IRR_LABEL = "IRR"
NIRR_LABEL = "NIRR"


def calculate_ndre(df: pd.DataFrame) -> pd.Series:
    nir = df["band_800"].values
    rededge = df["band_720"].values
    return pd.Series((nir - rededge) / (nir + rededge), index=df.index)


def load_and_prepare_data(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    for col in ["band_800", "band_720"]:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")
    df["NDRE"] = calculate_ndre(df)
    return df


def prepare_subset(df: pd.DataFrame, dia: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    subset = df[df["dia"] == dia].copy()
    X = subset[FEATURES].values
    y = (subset["condicao"] == IRR_LABEL).astype(int).values
    groups = (subset["cultivar"].astype(str) + "_" + subset["condicao"].astype(str) + "_" + subset["replicata"].astype(str)).values
    return subset, X, y, groups


def calculate_vip(pls: PLSRegression, X: np.ndarray) -> np.ndarray:
    t = pls.x_scores_
    w = pls.x_weights_
    q = pls.y_loadings_

    n_features = X.shape[1]
    n_components = pls.n_components

    vip = np.zeros(n_features)
    s = np.zeros(n_features)

    for a in range(n_components):
        s += (w[:, a] ** 2) * (q[:, a] ** 2)

    t_norm = np.sum(t ** 2, axis=0)
    for a in range(n_components):
        for j in range(n_features):
            vip[j] += (w[j, a] ** 2) * (t_norm[a]) * (q[0, a] ** 2) / s[j] if s[j] != 0 else 0

    vip = np.sqrt(vip / n_components)
    return vip


def run_pls(X: np.ndarray, y: np.ndarray, groups: np.ndarray, dia: str, n_components: int = 2):
    n_splits = min(5, max(2, len(np.unique(groups)) // 2))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    splits = list(splitter.split(X, y, groups))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pls = PLSRegression(n_components=n_components)
    pls.fit(X_scaled, y)

    vip = calculate_vip(pls, X_scaled)

    y_pred = cross_val_predict(pls, X_scaled, y, cv=splits, n_jobs=-1)
    y_pred_binary = (y_pred > 0.5).astype(int).ravel()
    y_prob = y_pred.ravel()

    cm = confusion_matrix(y, y_pred_binary, labels=[0, 1])
    precision, recall, f1_values, support = precision_recall_fscore_support(y, y_pred_binary, labels=[0, 1], zero_division=0)

    metrics = {
        "dia": dia,
        "n_components": n_components,
        "n_amostras": int(len(y)),
        "accuracy_media": float(accuracy_score(y, y_pred_binary)),
        "balanced_accuracy_media": float(balanced_accuracy_score(y, y_pred_binary)),
        "f1_irrigado": float(f1_score(y, y_pred_binary, pos_label=1)),
        "f1_macro": float(f1_score(y, y_pred_binary, average="macro")),
        "roc_auc": float(roc_auc_score(y, y_prob)),
        "kappa": float(cohen_kappa_score(y, y_pred_binary)),
        "precision_irrigado": float(precision[1]),
        "recall_irrigado": float(recall[1]),
    }

    vip_df = pd.DataFrame({
        "feature": FEATURES,
        "feature_label": FEATURE_LABELS,
        "vip_score": vip,
    }).sort_values("vip_score", ascending=False)

    return metrics, vip_df, cm, pls, X_scaled, y, y_pred_binary


def plot_vip_importance(vip_df: pd.DataFrame, dia: str, output_dir: Path, figure_dir: Path) -> None:
    vip_sorted = vip_df.sort_values("vip_score", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(vip_sorted)))[::-1]
    bars = ax.barh(vip_sorted["feature_label"], vip_sorted["vip_score"], color=colors, edgecolor="black", linewidth=0.5)

    for bar, score in zip(bars, vip_sorted["vip_score"]):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
                f"{score:.4f}", va="center", fontsize=10)

    ax.set_xlabel("VIP Score (Variable Importance in Projection)", fontsize=12)
    ax.set_ylabel("Feature", fontsize=12)
    ax.set_title(f"PLS Band Importance - {dia}", fontsize=14, fontweight="bold")
    ax.set_xlim(0, vip_sorted["vip_score"].max() * 1.15)
    ax.grid(True, axis="x", alpha=0.3)

    plt.tight_layout()
    fig.savefig(figure_dir / f"pls_vip_{dia}.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_confusion_matrix(cm: np.ndarray, dia: str, output_dir: Path, figure_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap="Blues", vmin=0)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["NIRR", "IRR"])
    ax.set_yticklabels(["NIRR", "IRR"])
    ax.set_xlabel("Predito")
    ax.set_ylabel("Real")
    ax.set_title(f"PLS Confusion Matrix - {dia}")

    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=14, color="white" if cm[i, j] > 2 else "black")

    fig.savefig(figure_dir / f"pls_cm_{dia}.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_pls_projection(X_lda: np.ndarray, y: np.ndarray, dia: str, figure_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["#e74c3c" if v == 0 else "#2ecc71" for v in y]
    markers = ["o" if v == 0 else "s" for v in y]

    for i in range(len(y)):
        ax.scatter(X_lda[i, 0] if X_lda.ndim > 1 else X_lda[i], 0, c=colors[i], marker=markers[i],
                   s=100, alpha=0.7, edgecolors="black", linewidth=0.5)

    ax.set_xlabel("Component 1", fontsize=11)
    ax.set_ylabel("Component 2" if X_lda.ndim > 1 else "", fontsize=11)
    ax.set_title(f"PLS Projection - {dia}", fontsize=13, fontweight="bold")
    ax.legend(["NIRR", "IRR"], fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(figure_dir / f"pls_projection_{dia}.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_all_vip_comparison(all_results: list, output_dir: Path, figure_dir: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle("PLS Band Importance - All Days", fontsize=16, fontweight="bold")

    for idx, result in enumerate(all_results):
        row = idx // 3
        col = idx % 3
        ax = axes[row, col]
        vip_df = result["vip_df"].sort_values("vip_score", ascending=True)

        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(vip_df)))[::-1]
        ax.barh(vip_df["feature_label"], vip_df["vip_score"], color=colors, edgecolor="black", linewidth=0.3)
        ax.set_title(result["dia"], fontsize=11, fontweight="bold")
        ax.set_xlim(0, vip_df["vip_score"].max() * 1.2)
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(True, axis="x", alpha=0.3)

    plt.tight_layout()
    fig.savefig(figure_dir / "pls_vip_all_days.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    input_path = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/dados/processados/replicatas_bloco_dia.csv")
    df = load_and_prepare_data(input_path)

    all_results = []
    metrics_list = []

    print("="*70)
    print("PLS CLASSIFICATION - IRR vs NIRR por Dia")
    print("Features:", FEATURES)
    print("="*70)

    for dia in DIAS:
        subset, X, y, groups = prepare_subset(df, dia)

        if len(np.unique(y)) < 2 or len(y) < 4:
            print(f"[{dia}] Pulando - dados insuficientes")
            continue

        metrics, vip_df, cm, pls, X_scaled, y_true, y_pred = run_pls(X, y, groups, dia, n_components=2)

        metrics["dia"] = dia
        metrics_list.append(metrics)

        result = {
            "dia": dia,
            "metrics": metrics,
            "vip_df": vip_df,
            "cm": cm,
        }
        all_results.append(result)

        print(f"\n[{dia}]")
        print(f"   Accuracy: {metrics['accuracy_media']:.4f}")
        print(f"   Balanced Accuracy: {metrics['balanced_accuracy_media']:.4f}")
        print(f"   F1 Macro: {metrics['f1_macro']:.4f}")
        print(f"   ROC AUC: {metrics['roc_auc']:.4f}")
        print(f"   Kappa: {metrics['kappa']:.4f}")
        print(f"   VIP (most to least important):")
        for _, row in vip_df.iterrows():
            print(f"      {row['feature_label']}: {row['vip_score']:.4f}")

        plot_vip_importance(vip_df, dia, OUTPUT_DIR, FIGURE_DIR)
        plot_confusion_matrix(cm, dia, OUTPUT_DIR, FIGURE_DIR)

        X_pls = pls.transform(X_scaled)
        plot_pls_projection(X_pls, y_true, dia, FIGURE_DIR)

    plot_all_vip_comparison(all_results, OUTPUT_DIR, FIGURE_DIR)

    metrics_df = pd.DataFrame(metrics_list)
    metrics_df.to_csv(OUTPUT_DIR / "pls_metrics_all_days.csv", index=False, encoding="utf-8-sig")

    vip_combined = []
    for result in all_results:
        vip_copy = result["vip_df"].copy()
        vip_copy["dia"] = result["dia"]
        vip_combined.append(vip_copy)

    vip_all_df = pd.concat(vip_combined, ignore_index=True)
    vip_all_df.to_csv(OUTPUT_DIR / "pls_vip_all_days.csv", index=False, encoding="utf-8-sig")

    vip_ranking = vip_all_df.groupby("feature").agg({"vip_score": ["mean", "std"]}).reset_index()
    vip_ranking.columns = ["feature", "vip_mean", "vip_std"]
    vip_ranking = vip_ranking.sort_values("vip_mean", ascending=False)
    vip_ranking["rank"] = range(1, len(vip_ranking) + 1)
    vip_ranking.to_csv(OUTPUT_DIR / "pls_vip_ranking.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(10, 6))
    vip_ranking_sorted = vip_ranking.sort_values("vip_mean", ascending=True)
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(vip_ranking_sorted)))

    bars = ax.barh(vip_ranking_sorted["feature"], vip_ranking_sorted["vip_mean"],
                   xerr=vip_ranking_sorted["vip_std"], color=colors, edgecolor="black",
                   linewidth=0.5, capsize=3)

    for bar, mean_val in zip(bars, vip_ranking_sorted["vip_mean"]):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                f"{mean_val:.4f}", va="center", fontsize=10)

    ax.set_xlabel("Mean VIP Score", fontsize=12)
    ax.set_ylabel("Feature", fontsize=12)
    ax.set_title("PLS Band Importance Ranking (Mean across all days)", fontsize=14, fontweight="bold")
    ax.set_xlim(0, vip_ranking_sorted["vip_mean"].max() * 1.2)
    ax.grid(True, axis="x", alpha=0.3)

    plt.tight_layout()
    fig.savefig(FIGURE_DIR / "pls_vip_ranking_global.png", dpi=150, bbox_inches="tight")
    plt.close()

    lines = [
        "# PLS Classification - IRR vs NIRR por Dia\n",
        "## Features: " + ", ".join(FEATURE_LABELS) + "\n",
        "## Band Importance Ranking (Mean VIP across days):\n",
        "| Rank | Feature | VIP Mean | VIP Std |",
        "| --- | --- | ---: | ---: |",
    ]
    for _, row in vip_ranking.iterrows():
        feat_label = FEATURE_LABELS[FEATURES.index(row["feature"])]
        lines.append(f"| {int(row['rank'])} | {feat_label} | {row['vip_mean']:.4f} | {row['vip_std']:.4f} |")

    lines.append("\n## Metrics by Day:\n")
    lines.append("| Dia | Accuracy | Balanced Acc | F1 Macro | ROC AUC | Kappa |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for m in metrics_list:
        lines.append(f"| {m['dia']} | {m['accuracy_media']:.4f} | {m['balanced_accuracy_media']:.4f} | {m['f1_macro']:.4f} | {m['roc_auc']:.4f} | {m['kappa']:.4f} |")

    summary_path = OUTPUT_DIR / "pls_summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n" + "="*70)
    print("OUTPUT:", OUTPUT_DIR)
    print("FIGURES:", FIGURE_DIR)
    print("="*70)
    print("\nBand Importance Ranking (Mean VIP across all days):")
    for _, row in vip_ranking.iterrows():
        feat_label = FEATURE_LABELS[FEATURES.index(row["feature"])]
        print(f"  {int(row['rank'])}. {feat_label}: {row['vip_mean']:.4f} (+/- {row['vip_std']:.4f})")


if __name__ == "__main__":
    main()