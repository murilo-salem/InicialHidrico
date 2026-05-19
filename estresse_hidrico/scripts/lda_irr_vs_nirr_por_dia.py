#!/usr/bin/env python3
"""Discriminant Canonical Analysis (LDA) IRR vs NIRR per day - all genotypes aggregated."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler

OUTPUT_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/tabelas/discriminante_canonico")
FIGURE_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/figuras/discriminante_canonico")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = ["band_1200", "band_1451", "band_1951", "band_970", "band_670", "NDRE"]
DIAS = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9"]
IRR_LABEL = "IRR"
NIRR_LABEL = "NIRR"
COLORS = {"IRR": "#2ecc71", "NIRR": "#e74c3c"}
MARKERS = {"IRR": "s", "NIRR": "o"}


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


def prepare_day_data(df: pd.DataFrame, dia: str) -> tuple[np.ndarray, np.ndarray, dict]:
    subset = df[df["dia"] == dia].copy()
    X = subset[FEATURES].values
    y = (subset["condicao"] == IRR_LABEL).astype(int).values
    counts = {"total": len(y), "irr": int(np.sum(y)), "nirr": int(np.sum(y == 0))}
    return X, y, counts


def confidence_ellipse(x, y, ax, n_std=2.0, facecolor='none', **kwargs):
    if x.size != y.size:
        raise ValueError("x and y must be the same size")
    cov = np.cov(x, y)
    pearson = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
                       facecolor=facecolor, **kwargs)
    scale_x = np.sqrt(cov[0, 0]) * n_std
    scale_y = np.sqrt(cov[1, 1]) * n_std
    transf = transforms.Affine2D().rotate_deg(45).scale(scale_x, scale_y).translate(np.mean(x), np.mean(y))
    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)


def plot_lda_with_ellipses(X_lda: np.ndarray, y: np.ndarray, dia: str,
                            lda: LinearDiscriminantAnalysis, accuracy: float,
                            figure_dir: Path) -> None:
    plt.figure(figsize=(10, 8))
    ax = plt.gca()

    n_components = X_lda.shape[1]

    for class_val, label in [(0, "Nao Irrigado"), (1, "Irrigado")]:
        mask = y == class_val
        color = COLORS["NIRR"] if class_val == 0 else COLORS["IRR"]
        marker = MARKERS["NIRR"] if class_val == 0 else MARKERS["IRR"]

        if n_components > 1:
            ax.scatter(X_lda[mask, 0], X_lda[mask, 1],
                       c=color, marker=marker, s=100, alpha=0.7,
                       edgecolors="black", linewidth=0.5, label=label)
            if np.sum(mask) > 1:
                confidence_ellipse(X_lda[mask, 0], X_lda[mask, 1], ax,
                                   n_std=2, edgecolor=color, linewidth=2, linestyle='--')
        else:
            y_offset = 0.1 * (class_val - 0.5)
            ax.scatter(X_lda[mask, 0], np.full(np.sum(mask), y_offset),
                       c=color, marker=marker, s=100, alpha=0.7,
                       edgecolors="black", linewidth=0.5, label=label)

    var_exp = lda.explained_variance_ratio_
    var_text = f"LD1: {var_exp[0]*100:.1f}%"
    if n_components > 1:
        var_text += f"\nLD2: {var_exp[1]*100:.1f}%"

    plt.xlabel("LD1", fontsize=12)
    if n_components > 1:
        plt.ylabel("LD2", fontsize=12)
    plt.title(f"Analise Discriminante Canonica - {dia}\nIRR vs NIRR (Todos Genotipos)", fontsize=14, fontweight="bold")
    plt.legend(fontsize=11, loc="best")
    plt.grid(True, alpha=0.3)
    plt.text(0.02, 0.98, f"Acuracia: {accuracy*100:.1f}%\n{var_text}",
             transform=ax.transAxes, fontsize=10, verticalalignment="top",
             bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))
    plt.tight_layout()
    plt.savefig(figure_dir / f"lda_irr_vs_nirr_{dia}.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_overall_lda(all_results: dict, figure_dir: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle("Analise Discriminante Canonica - Visão Geral (Todos os Dias)\nIRR vs NIRR", fontsize=14, fontweight="bold")

    day_colors = {
        "dia2": "#1f77b4", "dia3": "#ff7f0e", "dia4": "#2ca02c",
        "dia5": "#d62728", "dia6": "#9467bd", "dia9": "#8c564b"
    }

    for idx, dia in enumerate(DIAS):
        row = idx // 3
        col = idx % 3
        ax = axes[row, col]

        if dia not in all_results:
            ax.text(0.5, 0.5, f"{dia}\nSem dados", ha="center", va="center")
            ax.set_title(f"{dia}", fontsize=12, fontweight="bold")
            continue

        X_lda = all_results[dia]["X_lda"]
        y = all_results[dia]["y"]
        n_components = X_lda.shape[1]

        for class_val, label in [(0, "NIRR"), (1, "IRR")]:
            mask = y == class_val
            color = day_colors[dia]
            marker = MARKERS["NIRR"] if class_val == 0 else MARKERS["IRR"]
            fill_color = color if class_val == 1 else "white"

            if n_components > 1:
                ax.scatter(X_lda[mask, 0], X_lda[mask, 1],
                           c=fill_color, marker=marker, s=80, alpha=0.8,
                           edgecolors=color, linewidth=1, label=label)
                if np.sum(mask) > 1:
                    confidence_ellipse(X_lda[mask, 0], X_lda[mask, 1], ax,
                                       n_std=2, edgecolor=color, linewidth=1.5, linestyle='--')
            else:
                y_offset = 0.1 * (class_val - 0.5)
                ax.scatter(X_lda[mask, 0], np.full(np.sum(mask), y_offset),
                           c=fill_color, marker=marker, s=80, alpha=0.8,
                           edgecolors=color, linewidth=1, label=label)

        ax.set_xlabel("LD1", fontsize=10)
        ax.set_ylabel("LD2" if n_components > 1 else "", fontsize=10)
        ax.set_title(f"{dia}", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=11, bbox_to_anchor=(0.99, 0.99))
    plt.tight_layout()
    plt.savefig(figure_dir / "lda_irr_vs_nirr_all_days.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    input_path = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/dados/processados/replicatas_bloco_dia.csv")
    df = load_and_prepare_data(input_path)

    print("=" * 60)
    print("ANALISE DISCRIMINANTE CANONICA - IRR vs NIRR POR DIA")
    print("=" * 60)

    results = []
    all_results = {}

    for dia in DIAS:
        print(f"\n{dia}...")

        X, y, counts = prepare_day_data(df, dia)

        if len(np.unique(y)) < 2:
            print(f"  {dia}: Dados insuficientes (menos de 2 classes)")
            continue

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        lda = LinearDiscriminantAnalysis()
        X_lda = lda.fit_transform(X_scaled, y)
        accuracy = lda.score(X_scaled, y)

        plot_lda_with_ellipses(X_lda, y, dia, lda, accuracy, FIGURE_DIR)

        var_exp = lda.explained_variance_ratio_
        n_comp = X_lda.shape[1]

        results.append({
            "dia": dia,
            "n_total": counts["total"],
            "n_irr": counts["irr"],
            "n_nirr": counts["nirr"],
            "lda_accuracy": accuracy,
            "ld1_variance_pct": var_exp[0] * 100 if n_comp >= 1 else 0,
            "ld2_variance_pct": var_exp[1] * 100 if n_comp >= 2 else 0,
        })

        all_results[dia] = {"X_lda": X_lda, "y": y}

        print(f"  Amostras: {counts['total']} (IRR: {counts['irr']}, NIRR: {counts['nirr']})")
        print(f"  Acuracia: {accuracy*100:.1f}%")

    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "lda_results_summary.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print("RESULTADOS LDA por Dia")
    print("=" * 60)
    print(results_df.to_string(index=False))

    plot_overall_lda(all_results, FIGURE_DIR)

    print(f"\nFiguras: {FIGURE_DIR}")
    print(f"Tabela: {OUTPUT_DIR / 'lda_results_summary.csv'}")


if __name__ == "__main__":
    main()