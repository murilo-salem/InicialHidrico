#!/usr/bin/env python3
"""Generate a single figure with all confusion matrices and metrics tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

OUTPUT_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/tabelas/classificacao_irrigacao_por_dia_genotipo")
FIGURE_DIR = Path("C:/Users/muril/OneDrive/Documentos/AgroSATHidrico/estresse_hidrico/outputs/figuras")
MODELOS = ["Random_Forest", "SVM_RBF", "LDA", "k-NN_k5", "XGBoost"]
MODEL_NAMES = ["Random Forest", "SVM (RBF)", "LDA", "k-NN (k=5)", "XGBoost"]
DIAS = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9"]
CULTIVARES = ["BR16", "CD202", "EMB48"]
LABELS_CM = ["Nao irrigado", "Irrigado"]


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


def load_metrics(dia: str, cultivar: str, modelo_clean: str) -> pd.DataFrame | None:
    path = OUTPUT_DIR / dia / cultivar / f"metricas_{modelo_clean}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df


def main():
    n_rows = len(DIAS) * len(CULTIVARES)
    n_cols = len(MODELOS)

    fig = plt.figure(figsize=(50, 140))

    gs = gridspec.GridSpec(n_rows, n_cols * 2, figure=fig, wspace=0.3, hspace=0.5)

    fig.suptitle("Classificacao IRR vs NIRR - Por Dia e Genotipo\nBandas: band_1200, band_1451, band_1951, band_970, band_670, NDRE", fontsize=24, y=0.98)

    for row_idx, (dia, cultivar) in enumerate([(d, c) for d in DIAS for c in CULTIVARES]):
        for col_idx, (modelo_clean, modelo_name) in enumerate(zip(MODELOS, MODEL_NAMES)):
            cm_ax = fig.add_subplot(gs[row_idx, col_idx * 2])
            metrics_ax = fig.add_subplot(gs[row_idx, col_idx * 2 + 1])

            cm = load_confusion(dia, cultivar, modelo_clean)
            metrics_df = load_metrics(dia, cultivar, modelo_clean)

            if cm is not None and metrics_df is not None:
                im = cm_ax.imshow(cm, cmap="Blues", vmin=0, vmax=4)
                for i in range(2):
                    for j in range(2):
                        color = "white" if cm[i, j] > 1.5 else "black"
                        cm_ax.text(j, i, str(int(cm[i, j])), ha="center", va="center", fontsize=11, color=color)
                cm_ax.set_xticks([0, 1])
                cm_ax.set_yticks([0, 1])
                cm_ax.set_xticklabels(["NIRR", "IRR"], fontsize=9)
                cm_ax.set_yticklabels(["NIRR", "IRR"], fontsize=9)
                cm_ax.set_xlabel("Predito", fontsize=9)
                cm_ax.set_ylabel("Real", fontsize=9)

                title = f"{dia} - {cultivar}\n{modelo_name}"
                cm_ax.set_title(title, fontsize=10, fontweight="bold")

                metrics_ax.axis("off")
                row = metrics_df.iloc[0]
                table_data = [
                    ["ACC", f"{row['accuracy_media']:.4f}"],
                    ["BAC", f"{row['balanced_accuracy_media']:.4f}"],
                    ["F1_IRR", f"{row['f1_irrigado_media']:.4f}"],
                    ["F1_MACRO", f"{row['f1_macro_media']:.4f}"],
                    ["AUC", f"{row['roc_auc_media']:.4f}"],
                    ["KAPPA", f"{row['kappa_media']:.4f}"],
                ]

                table = metrics_ax.table(
                    cellText=table_data,
                    colLabels=["Metrica", "Valor"],
                    loc="center",
                    cellLoc="center",
                )
                table.auto_set_font_size(False)
                table.set_fontsize(9)
                table.scale(1.2, 1.5)
                metrics_ax.set_title("Metricas", fontsize=10, fontweight="bold", pad=5)
            else:
                cm_ax.text(0.5, 0.5, "N/A", ha="center", va="center", fontsize=12)
                cm_ax.set_title(f"{dia} - {cultivar}\n{modelo_name}", fontsize=10)

    out_path = FIGURE_DIR / "todas_matrizes_confusao_com_metricas.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()