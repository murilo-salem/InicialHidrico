#!/usr/bin/env python3
"""Generate a single figure with all confusion matrices."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUTPUT_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/tabelas/classificacao_irrigacao_por_dia_genotipo")
FIGURE_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/figuras")
MODELOS = ["Random_Forest", "SVM_RBF", "LDA", "k-NN_k5", "XGBoost"]
MODEL_NAMES = ["Random Forest", "SVM (RBF)", "LDA", "k-NN (k=5)", "XGBoost"]
DIAS = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9"]
CULTIVARES = ["BR16", "CD202", "EMB48"]
LABELS = ["Nao irrigado", "Irrigado"]


def load_confusion(dia: str, cultivar: str, modelo_clean: str) -> np.ndarray | None:
    path = OUTPUT_DIR / dia / cultivar / f"matriz_confusao_{modelo_clean}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, encoding="utf-8-sig")
    cols = [c for c in df.columns if c not in ["analysis_id", "analysis_label", "dia", "cultivar", "modelo", "real"]]
    if len(cols) < 2:
        return None
    vals = df[cols].values
    if vals.shape[0] == 2 and vals.shape[1] == 2:
        return vals
    return None


def main():
    fig, axes = plt.subplots(18, 5, figsize=(25, 90))
    fig.suptitle("Matrizes de Confusao - IRR vs NIRR por Dia e Genotipo\nBandas: band_1200, band_1451, band_1951, band_970, band_670, NDRE", fontsize=20, y=0.995)

    for row_idx, (dia, cultivar) in enumerate([(d, c) for d in DIAS for c in CULTIVARES]):
        for col_idx, (modelo_clean, modelo_name) in enumerate(zip(MODELOS, MODEL_NAMES)):
            ax = axes[row_idx, col_idx]
            cm = load_confusion(dia, cultivar, modelo_clean)

            if cm is not None:
                im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=4)
                for i in range(2):
                    for j in range(2):
                        ax.text(j, i, str(int(cm[i, j])), ha="center", va="center", fontsize=12, color="white" if cm[i, j] > 1 else "black")
            else:
                ax.text(0.5, 0.5, "N/A", ha="center", va="center", fontsize=12)
                ax.set_facecolor("#f0f0f0")

            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
            ax.set_xticklabels(LABELS, fontsize=9)
            ax.set_yticklabels(LABELS, fontsize=9)

            if row_idx == 0:
                ax.set_title(modelo_name, fontsize=12, fontweight="bold")
            if col_idx == 0:
                ax.set_ylabel(f"{dia} - {cultivar}", fontsize=11, fontweight="bold")
            if row_idx == 17:
                ax.set_xlabel("Predito", fontsize=10)
            ax.set_yticklabels(LABELS, fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.98])
    out_path = FIGURE_DIR / "todas_matrizes_confusao.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()