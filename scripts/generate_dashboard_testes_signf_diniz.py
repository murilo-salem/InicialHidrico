from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera dashboard (imagem) dos estudos estatisticos de TestesSignfDiniz.")
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=Path("outputs") / "testes_signf_diniz",
        help="Diretorio com as saidas do script analyze_testes_signf_diniz.py",
    )
    parser.add_argument(
        "--focus-dataset",
        type=str,
        default="TOP5_POR_DIA_TURNO",
        help="Subpasta TOP5_* para paineis detalhados.",
    )
    parser.add_argument(
        "--out-file",
        type=Path,
        default=Path("outputs") / "testes_signf_diniz" / "dashboard_estudos_estatisticos.png",
        help="Arquivo PNG de saida.",
    )
    return parser.parse_args()


def _slot_order(df: pd.DataFrame) -> list[str]:
    frame = df.copy()
    frame["dia_num"] = frame["data_coleta"].astype(str).str.extract(r"D(\d+)").astype(float)
    frame["turno_ord"] = frame["turno"].map({"MANHA": 0, "TARDE": 1}).fillna(99)
    frame = frame.sort_values(["dia_num", "turno_ord"])
    return (frame["data_coleta"] + "_" + frame["turno"]).drop_duplicates().tolist()


def main() -> None:
    args = parse_args()
    base = args.analysis_dir
    focus = base / args.focus_dataset

    rank_df = pd.read_csv(base / "comparacao_configuracoes_robustez.csv")
    stab_df = pd.read_csv(focus / "01_estabilidade_bandas.csv")
    fam_df = pd.read_csv(focus / "02_frequencia_familias.csv")
    ev_df = pd.read_csv(focus / "04_forca_evidencia_temporal.csv")
    agr_df = pd.read_csv(focus / "05_concordancia_analises.csv")

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 3, figsize=(22, 12), constrained_layout=True)
    fig.suptitle("Dashboard Estatistico - TestesSignfDiniz", fontsize=18, fontweight="bold")

    # 1) Ranking global de robustez
    ax = axes[0, 0]
    rank_df = rank_df.sort_values("rank_robustez")
    ax.barh(rank_df["dataset"], rank_df["persistencia_media"], color="#2E86AB")
    ax.invert_yaxis()
    ax.set_title("Ranking de Robustez (Persistencia Media)")
    ax.set_xlabel("Persistencia Media")
    ax.set_ylabel("Configuracao")

    # 2) Top bandas mais persistentes (dataset foco)
    ax = axes[0, 1]
    top_stab = stab_df.sort_values(["persistencia", "count_top5"], ascending=[False, False]).head(12).copy()
    labels = top_stab["analysis"] + " | " + top_stab["wavelength_nm"].round(1).astype(str)
    ax.barh(labels, top_stab["persistencia"], color="#F18F01")
    ax.invert_yaxis()
    ax.set_title(f"Top 12 Bandas Mais Persistentes ({args.focus_dataset})")
    ax.set_xlabel("Persistencia")
    ax.set_ylabel("Analise | Wavelength (nm)")

    # 3) Familias mais recorrentes
    ax = axes[0, 2]
    top_fam = fam_df.groupby("family_nm", as_index=False)["count_top5"].sum().sort_values("count_top5", ascending=False).head(15)
    ax.bar(top_fam["family_nm"].astype(int).astype(str), top_fam["count_top5"], color="#A23B72")
    ax.set_title("Top 15 Familias Espectrais Recorrentes")
    ax.set_xlabel("Familia (nm, bins de 10nm)")
    ax.set_ylabel("Contagem TOP5")
    ax.tick_params(axis="x", rotation=60)

    # 4) Forca de evidencia temporal (mediana -log10(q))
    ax = axes[1, 0]
    slot_ord = _slot_order(ev_df)
    for analysis in sorted(ev_df["analysis"].unique()):
        sub = ev_df[ev_df["analysis"] == analysis].copy()
        sub["slot"] = sub["data_coleta"] + "_" + sub["turno"]
        sub["slot"] = pd.Categorical(sub["slot"], categories=slot_ord, ordered=True)
        sub = sub.sort_values("slot")
        ax.plot(sub["slot"].astype(str), sub["median_neglog10_q"], marker="o", linewidth=2, label=analysis)
    ax.set_title("Intensidade de Significancia Temporal")
    ax.set_xlabel("Dia_Turno")
    ax.set_ylabel("Mediana de -log10(q_FDR_BH)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(title="Analise")

    # 5) Proporcao q<0.05 por analise
    ax = axes[1, 1]
    prop_df = ev_df.groupby("analysis", as_index=False)["prop_q_lt_0_05"].mean().sort_values("prop_q_lt_0_05", ascending=False)
    ax.bar(prop_df["analysis"], prop_df["prop_q_lt_0_05"], color=["#6A994E", "#386641", "#A7C957"])
    ax.set_title("Proporcao Media de Bandas com q < 0.05")
    ax.set_xlabel("Analise")
    ax.set_ylabel("Proporcao")
    ax.set_ylim(0, 1)

    # 6) Concordancia entre analises (Jaccard medio)
    ax = axes[1, 2]
    agr_df["pair"] = agr_df["analysis_a"] + " vs " + agr_df["analysis_b"]
    pair_df = agr_df.groupby("pair", as_index=False)["jaccard"].mean().sort_values("jaccard", ascending=False)
    ax.bar(pair_df["pair"], pair_df["jaccard"], color="#3D405B")
    ax.set_title("Concordancia Media Entre Analises (Jaccard)")
    ax.set_xlabel("Pares de analise")
    ax.set_ylabel("Jaccard medio")
    ax.set_ylim(0, max(0.05, pair_df["jaccard"].max() * 1.2))
    ax.tick_params(axis="x", rotation=20)

    args.out_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out_file, dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
