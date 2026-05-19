#!/usr/bin/env python3
"""Generate comprehensive summary of Discriminant Canonical Analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler

OUTPUT_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/tabelas/discriminante_canonico")
FIGURE_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/figuras/discriminante_canonico")

FEATURES = ["band_1200", "band_1451", "band_1951", "band_970", "band_670", "NDRE"]
DIAS = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9"]
CULTIVARES = ["BR16", "CD202", "EMB48"]
IRR_LABEL = "IRR"
NIRR_LABEL = "NIRR"


def calculate_ndre(df: pd.DataFrame) -> pd.Series:
    nir = df["band_800"].values
    rededge = df["band_720"].values
    return pd.Series((nir - rededge) / (nir + rededge), index=df.index)


def main():
    input_path = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/dados/processados/replicatas_bloco_dia.csv")
    df = pd.read_csv(input_path)
    df["NDRE"] = calculate_ndre(df)

    fig3, axes3 = plt.subplots(3, 6, figsize=(36, 18))
    fig3.suptitle("LDA - Por Dia e Genotipo (todos os pontos)", fontsize=16, fontweight="bold")

    for idx_cult, cultivar in enumerate(CULTIVARES):
        for idx_dia, dia in enumerate(DIAS):
            ax = axes3[idx_cult, idx_dia]
            sub = df[(df["dia"] == dia) & (df["cultivar"] == cultivar)]

            if len(sub) < 4:
                ax.text(0.5, 0.5, "N/A", ha="center", va="center")
                ax.set_title(f"{dia} - {cultivar}", fontsize=10, fontweight="bold")
                continue

            X = sub[FEATURES].values
            y = (sub["condicao"] == IRR_LABEL).astype(int).values

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            lda = LinearDiscriminantAnalysis()
            X_lda = lda.fit_transform(X_scaled, y)
            n_comp = X_lda.shape[1]

            colors_p = ["#e74c3c" if v == 0 else "#2ecc71" for v in y]
            markers_p = ["o" if v == 0 else "s" for v in y]

            x_vals = X_lda[:, 0]
            y_vals = X_lda[:, 1] if n_comp > 1 else np.zeros(len(X_lda))

            for i in range(len(x_vals)):
                ax.scatter(x_vals[i], y_vals[i], c=colors_p[i], marker=markers_p[i],
                          s=60, alpha=0.7, edgecolors="black", linewidth=0.3)

            ax.set_xlabel("LD1", fontsize=8)
            if n_comp > 1:
                ax.set_ylabel("LD2", fontsize=8)
            ax.set_title(f"{dia} - {cultivar}", fontsize=9, fontweight="bold")
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig3.savefig(FIGURE_DIR / "lda_all_days_all_genotypes.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {FIGURE_DIR / 'lda_all_days_all_genotypes.png'}")

    fig2, axes2 = plt.subplots(3, 1, figsize=(18, 24))
    fig2.suptitle("LDA - Por Genotipo (media IRR vs NIRR por dia)", fontsize=16, fontweight="bold")

    for idx_cult, cultivar in enumerate(CULTIVARES):
        ax = axes2[idx_cult]
        all_means = []
        all_labels = []

        for dia in DIAS:
            sub = df[(df["dia"] == dia) & (df["cultivar"] == cultivar)]
            irr_m = sub[sub["condicao"] == "IRR"][FEATURES].mean().values
            nirr_m = sub[sub["condicao"] == "NIRR"][FEATURES].mean().values
            if len(irr_m) > 0 and len(nirr_m) > 0:
                all_means.append(irr_m)
                all_means.append(nirr_m)
                all_labels.append(f"{dia}_IRR")
                all_labels.append(f"{dia}_NIRR")

        if len(all_means) >= 2:
            arr_c = np.array(all_means)
            scaler = StandardScaler()
            arr_c_scaled = scaler.fit_transform(arr_c)

            n_classes = 2
            lda_c = LinearDiscriminantAnalysis(n_components=min(1, n_classes - 1))
            y_labels = [0 if "NIRR" in l else 1 for l in all_labels]
            lda_c.fit(arr_c_scaled, y_labels)
            arr_c_lda = lda_c.transform(arr_c_scaled)

            colors_c = ["#e74c3c" if "NIRR" in l else "#2ecc71" for l in all_labels]
            x_vals = arr_c_lda[:, 0]
            y_vals = arr_c_lda[:, 1] if arr_c_lda.shape[1] > 1 else np.zeros(len(arr_c_lda))

            for i, (x, y) in enumerate(zip(x_vals, y_vals)):
                ax.scatter(x, y, c=colors_c[i], s=150, alpha=0.8, edgecolors="black", linewidth=1, label=all_labels[i])
                ax.annotate(all_labels[i], (x, y), textcoords="offset points", xytext=(5, 5), fontsize=8)

        ax.set_xlabel("LD1", fontsize=11)
        ax.set_ylabel("LD2" if len(all_means) >= 2 and arr_c_lda.shape[1] > 1 else "", fontsize=11)
        ax.set_title(f"{cultivar}", fontsize=13, fontweight="bold")
        ax.legend(fontsize=8, loc="best", ncol=3)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig2.savefig(FIGURE_DIR / "lda_cultivar_means_all_days.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {FIGURE_DIR / 'lda_cultivar_means_all_days.png'}")

    fig1, axes1 = plt.subplots(2, 3, figsize=(24, 16))
    fig1.suptitle("LDA - Por Dia (todos genotipos)", fontsize=16, fontweight="bold")

    for idx_dia, dia in enumerate(DIAS):
        ax = axes1[idx_dia // 3, idx_dia % 3]
        sub = df[df["dia"] == dia]

        X = sub[FEATURES].values
        y = (sub["condicao"] == IRR_LABEL).astype(int).values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        lda = LinearDiscriminantAnalysis()
        X_lda = lda.fit_transform(X_scaled, y)
        n_comp = X_lda.shape[1]

        colors_p = ["#e74c3c" if v == 0 else "#2ecc71" for v in y]
        markers_p = ["o" if v == 0 else "s" for v in y]

        x_vals = X_lda[:, 0]
        y_vals = X_lda[:, 1] if n_comp > 1 else np.zeros(len(X_lda))

        for i in range(len(x_vals)):
            ax.scatter(x_vals[i], y_vals[i], c=colors_p[i], marker=markers_p[i],
                      s=80, alpha=0.7, edgecolors="black", linewidth=0.5)

        ax.set_xlabel("LD1", fontsize=10)
        if n_comp > 1:
            ax.set_ylabel("LD2", fontsize=10)
        ax.set_title(f"{dia}", fontsize=12, fontweight="bold")
        ax.legend(["NIRR", "IRR"], fontsize=9)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig1.savefig(FIGURE_DIR / "lda_per_day_all_genotypes.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {FIGURE_DIR / 'lda_per_day_all_genotypes.png'}")

    fig4, axes4 = plt.subplots(1, 3, figsize=(24, 8))
    fig4.suptitle("Heatmap - Media IRR vs NIRR por Genotipo (dia2)", fontsize=14, fontweight="bold")

    for idx_cult, cultivar in enumerate(CULTIVARES):
        ax = axes4[idx_cult]
        sub = df[(df["dia"] == "dia2") & (df["cultivar"] == cultivar)]
        means = sub.groupby("condicao")[FEATURES].mean()

        data_h = []
        labels_h = []
        for cond in ["NIRR", "IRR"]:
            if cond in means.index:
                data_h.append(means.loc[cond].values)
                labels_h.append(f"{cultivar}_{cond}")

        if data_h:
            arr_h = np.array(data_h)
            im = ax.imshow(arr_h, cmap="RdYlGn", aspect="auto")
            ax.set_xticks(range(len(FEATURES)))
            ax.set_xticklabels([f.replace("band_", "") for f in FEATURES], fontsize=10)
            ax.set_yticks(range(len(labels_h)))
            ax.set_yticklabels(labels_h, fontsize=10)
            ax.set_title(f"{cultivar}", fontsize=12, fontweight="bold")
            plt.colorbar(im, ax=ax, shrink=0.6)

    plt.tight_layout()
    fig4.savefig(FIGURE_DIR / "heatmap_dia2_means.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {FIGURE_DIR / 'heatmap_dia2_means.png'}")

    print("\nDone! All figures saved to:")
    print(f"  {FIGURE_DIR}")