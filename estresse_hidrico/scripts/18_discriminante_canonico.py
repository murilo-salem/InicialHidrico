#!/usr/bin/env python3
"""Discriminant Canonical Analysis (LDA/RDA) with clusters for irrigation classification."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, dendrogram

OUTPUT_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/tabelas/discriminante_canonico")
FIGURE_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/figuras/discriminante_canonico")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = ["band_1200", "band_1451", "band_1951", "band_970", "band_670", "NDRE"]
DIAS = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9"]
CULTIVARES = ["BR16", "CD202", "EMB48"]
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


def prepare_subset(df: pd.DataFrame, dia: str | None = None, cultivar: str | None = None) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list]:
    mask = pd.Series([True] * len(df))
    if dia is not None:
        mask &= df["dia"] == dia
    if cultivar is not None:
        mask &= df["cultivar"] == cultivar
    subset = df[mask].copy()
    X = subset[FEATURES].values
    y = (subset["condicao"] == IRR_LABEL).astype(int).values
    groups = (subset["cultivar"].astype(str) + "_" + subset["condicao"].astype(str) + "_" + subset["replicata"].astype(str)).tolist()
    return subset, X, y, groups


def plot_ldaProjection(X_lda: np.ndarray, y: np.ndarray, title: str, path: Path, labels: dict = None) -> None:
    plt.figure(figsize=(10, 8))
    colors = {0: "#e74c3c", 1: "#2ecc71"}
    markers = {0: "o", 1: "s"}
    for class_val in [0, 1]:
        mask = y == class_val
        label = labels[class_val] if labels and class_val in labels else ("NIRR" if class_val == 0 else "IRR")
        plt.scatter(X_lda[mask, 0], X_lda[mask, 1],
                    c=colors[class_val], marker=markers[class_val],
                    s=100, alpha=0.7, edgecolors="black", linewidth=0.5,
                    label=label)
    plt.xlabel("LD1", fontsize=12)
    plt.ylabel("LD2", fontsize=12)
    plt.title(title, fontsize=14, fontweight="bold")
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_means_in_lda(df: pd.DataFrame, dia: str, output_dir: Path, figure_dir: Path) -> None:
    subset = df[df["dia"] == dia].copy()
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle(f"Discriminante Canonico - {dia} - Medios por Genotipo e Condicao", fontsize=14, fontweight="bold")

    for idx, cultivar in enumerate(CULTIVARES):
        ax = axes[idx]
        sub = subset[subset["cultivar"] == cultivar]
        means = sub.groupby("condicao")[FEATURES].mean()

        if len(means) < 2:
            ax.text(0.5, 0.5, f"{cultivar}\nDados insuficientes", ha="center", va="center")
            ax.set_title(f"{cultivar}", fontsize=12, fontweight="bold")
            continue

        X_mean = means.values
        y_mean = np.array([0 if idx == 0 else 1 for idx in range(len(means))])

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_mean)

        lda = LinearDiscriminantAnalysis()
        try:
            lda.fit(X_scaled, y_mean)
            X_lda = lda.transform(X_scaled)
            n_components = X_lda.shape[1]
        except:
            ax.text(0.5, 0.5, f"{cultivar}\nLDA falhou", ha="center", va="center")
            ax.set_title(f"{cultivar}", fontsize=12, fontweight="bold")
            continue

        colors = {"IRR": "#2ecc71", "NIRR": "#e74c3c"}
        for i, (cond, row) in enumerate(means.iterrows()):
            x_val = X_lda[i, 0] if n_components > 0 else 0
            y_val = X_lda[i, 1] if n_components > 1 else 0
            ax.scatter(x_val, y_val,
                      c=colors.get(cond, "blue"), s=200, marker="s" if cond == "IRR" else "o",
                      edgecolors="black", linewidth=1.5, label=cond, alpha=0.8)
            ax.annotate(cond, (x_val, y_val),
                        textcoords="offset points", xytext=(10, 5), fontsize=10)

        ax.set_xlabel("LD1", fontsize=10)
        ax.set_ylabel("LD2" if n_components > 1 else "", fontsize=10)
        ax.set_title(f"{cultivar}", fontsize=12, fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(figure_dir / f"lda_means_{dia}.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_global_lda(df: pd.DataFrame, dia: str, output_dir: Path, figure_dir: Path) -> None:
    subset, X, y, _ = prepare_subset(df, dia=dia)
    if len(np.unique(y)) < 2:
        return

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    lda = LinearDiscriminantAnalysis()
    X_lda = lda.fit_transform(X_scaled, y)

    n_components = X_lda.shape[1]

    plt.figure(figsize=(12, 10))
    colors = {0: "#e74c3c", 1: "#2ecc71"}
    markers = {0: "o", 1: "s"}

    for class_val in [0, 1]:
        mask = y == class_val
        label = "Nao irrigado" if class_val == 0 else "Irrigado"
        if n_components > 1:
            plt.scatter(X_lda[mask, 0], X_lda[mask, 1],
                       c=colors[class_val], marker=markers[class_val],
                       s=120, alpha=0.7, edgecolors="black", linewidth=0.5,
                       label=label)
        else:
            plt.scatter(X_lda[mask, 0], np.zeros(sum(mask)),
                       c=colors[class_val], marker=markers[class_val],
                       s=120, alpha=0.7, edgecolors="black", linewidth=0.5,
                       label=label)

    plt.xlabel("LD1", fontsize=12)
    if n_components > 1:
        plt.ylabel("LD2", fontsize=12)
    plt.title(f"Analise Discriminante Canonica - {dia}\nIRR vs NIRR (Todos Genotipos)", fontsize=14, fontweight="bold")
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)

    var_explained = lda.explained_variance_ratio_
    if n_components > 1:
        plt.text(0.02, 0.98, f"LD1: {var_explained[0]*100:.1f}%\nLD2: {var_explained[1]*100:.1f}%",
                 transform=plt.gca().transAxes, fontsize=10, verticalalignment="top",
                 bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))
    else:
        plt.text(0.02, 0.98, f"LD1: {var_explained[0]*100:.1f}%",
                 transform=plt.gca().transAxes, fontsize=10, verticalalignment="top",
                 bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    plt.tight_layout()
    plt.savefig(figure_dir / f"lda_global_{dia}.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_lda_per_genotype(df: pd.DataFrame, dia: str, output_dir: Path, figure_dir: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle(f"Analise Discriminante Canonica - {dia} - Por Genotipo", fontsize=14, fontweight="bold")

    for idx, cultivar in enumerate(CULTIVARES):
        ax = axes[idx]
        subset, X, y, _ = prepare_subset(df, dia=dia, cultivar=cultivar)

        if len(np.unique(y)) < 2 or len(y) < 4:
            ax.text(0.5, 0.5, f"{cultivar}\nDados insuficientes", ha="center", va="center")
            ax.set_title(f"{cultivar}", fontsize=12, fontweight="bold")
            continue

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        lda = LinearDiscriminantAnalysis()
        X_lda = lda.fit_transform(X_scaled, y)
        n_components = X_lda.shape[1]

        colors = {0: "#e74c3c", 1: "#2ecc71"}
        markers = {0: "o", 1: "s"}

        for class_val in [0, 1]:
            mask = y == class_val
            label = "Nao irrigado" if class_val == 0 else "Irrigado"
            if n_components > 1:
                ax.scatter(X_lda[mask, 0], X_lda[mask, 1],
                           c=colors[class_val], marker=markers[class_val],
                           s=100, alpha=0.7, edgecolors="black", linewidth=0.5,
                           label=label)
            else:
                ax.scatter(X_lda[mask, 0], np.zeros(sum(mask)),
                           c=colors[class_val], marker=markers[class_val],
                           s=100, alpha=0.7, edgecolors="black", linewidth=0.5,
                           label=label)

        ax.set_xlabel("LD1", fontsize=10)
        ax.set_ylabel("LD2" if n_components > 1 else "", fontsize=10)
        ax.set_title(f"{cultivar}", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(figure_dir / f"lda_per_genotype_{dia}.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_heatmap_means(df: pd.DataFrame, output_dir: Path, figure_dir: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(20, 14))
    fig.suptitle("Medias das Variaveis por Genotipo e Condicao", fontsize=16, fontweight="bold")

    for idx_dia, dia in enumerate(DIAS):
        row = idx_dia // 3
        col = idx_dia % 3
        ax = axes[row, col]

        subset = df[df["dia"] == dia]
        means = subset.groupby(["cultivar", "condicao"])[FEATURES].mean()
        means = means.unstack(level="condicao")

        data_matrix = []
        index_labels = []
        for cult in CULTIVARES:
            if (cult, "IRR") in means.index and (cult, "NIRR") in means.index:
                irr_vals = means.loc[(cult, "IRR")].values
                nirr_vals = means.loc[(cult, "NIRR")].values
                data_matrix.append(irr_vals)
                data_matrix.append(nirr_vals)
                index_labels.append(f"{cult}_IRR")
                index_labels.append(f"{cult}_NIRR")

        if data_matrix:
            data_matrix = np.array(data_matrix)
            im = ax.imshow(data_matrix, cmap="RdYlGn", aspect="auto")
            ax.set_xticks(range(len(FEATURES)))
            ax.set_xticklabels([f.replace("band_", "") for f in FEATURES], fontsize=9)
            ax.set_yticks(range(len(index_labels)))
            ax.set_yticklabels(index_labels, fontsize=9)
            ax.set_title(f"{dia}", fontsize=12, fontweight="bold")
            plt.colorbar(im, ax=ax, shrink=0.6)

    plt.tight_layout()
    fig.savefig(figure_dir / "heatmap_means.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_lda_by_genotype_all_days(df: pd.DataFrame, cultivar: str, output_dir: Path, figure_dir: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f"Analise Discriminante Canonica - {cultivar}\nIRR vs NIRR por Dia", fontsize=14, fontweight="bold")

    for idx_dia, dia in enumerate(DIAS):
        row = idx_dia // 3
        col = idx_dia % 3
        ax = axes[row, col]

        subset, X, y, _ = prepare_subset(df, dia=dia, cultivar=cultivar)

        if len(np.unique(y)) < 2 or len(y) < 4:
            ax.text(0.5, 0.5, f"{dia}\nDados insuficientes", ha="center", va="center")
            ax.set_title(f"{dia}", fontsize=11, fontweight="bold")
            continue

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        lda = LinearDiscriminantAnalysis()
        X_lda = lda.fit_transform(X_scaled, y)
        n_components = X_lda.shape[1]

        colors = {0: "#e74c3c", 1: "#2ecc71"}
        markers = {0: "o", 1: "s"}

        for class_val in [0, 1]:
            mask = y == class_val
            label = "NIRR" if class_val == 0 else "IRR"
            if n_components > 1:
                ax.scatter(X_lda[mask, 0], X_lda[mask, 1],
                           c=colors[class_val], marker=markers[class_val],
                           s=80, alpha=0.7, edgecolors="black", linewidth=0.5,
                           label=label)
            else:
                ax.scatter(X_lda[mask, 0], np.zeros(sum(mask)),
                           c=colors[class_val], marker=markers[class_val],
                           s=80, alpha=0.7, edgecolors="black", linewidth=0.5,
                           label=label)

        ax.set_xlabel("LD1", fontsize=9)
        ax.set_ylabel("LD2" if n_components > 1 else "", fontsize=9)
        ax.set_title(f"{dia}", fontsize=11, fontweight="bold")
        ax.legend(fontsize=8, loc="best")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(figure_dir / f"lda_{cultivar}_all_days.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    input_path = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/dados/processados/replicatas_bloco_dia.csv")
    df = load_and_prepare_data(input_path)

    print("="*60)
    print("ANALISE DISCRIMINANTE CANONICA (LDA/RDA)")
    print("="*60)

    for dia in DIAS:
        print(f"\n{dia}...")

        plot_global_lda(df, dia, OUTPUT_DIR, FIGURE_DIR)
        plot_lda_per_genotype(df, dia, OUTPUT_DIR, FIGURE_DIR)
        plot_means_in_lda(df, dia, OUTPUT_DIR, FIGURE_DIR)

    for cultivar in CULTIVARES:
        plot_lda_by_genotype_all_days(df, cultivar, OUTPUT_DIR, FIGURE_DIR)

    plot_heatmap_means(df, OUTPUT_DIR, FIGURE_DIR)

    results = []
    for dia in DIAS:
        for cultivar in CULTIVARES:
            subset, X, y, _ = prepare_subset(df, dia=dia, cultivar=cultivar)
            if len(np.unique(y)) < 2 or len(y) < 4:
                continue

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            lda = LinearDiscriminantAnalysis()
            lda.fit(X_scaled, y)
            accuracy = lda.score(X_scaled, y)

            results.append({
                "dia": dia,
                "cultivar": cultivar,
                "n_amostras": len(y),
                "lda_accuracy": accuracy,
                "ld1_variance": lda.explained_variance_ratio_[0] if len(lda.explained_variance_ratio_) > 0 else 0,
            })

    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "lda_results.csv", index=False, encoding="utf-8-sig")

    print("\n" + "="*60)
    print("RESULTADOS LDA por Dia e Genotipo")
    print("="*60)
    print(results_df.to_string(index=False))

    print(f"\nOutput: {OUTPUT_DIR}")
    print(f"Figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()