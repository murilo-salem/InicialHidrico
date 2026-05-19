from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera dashboard executivo avancado (3x3) para TestesSignfDiniz.")
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=Path("outputs") / "testes_signf_diniz_advanced",
    )
    parser.add_argument(
        "--focus-analysis",
        type=str,
        default="gen_cond",
    )
    parser.add_argument(
        "--out-file",
        type=Path,
        default=Path("outputs") / "testes_signf_diniz_advanced" / "dashboard_executivo_avancado.png",
    )
    return parser.parse_args()


def _slot_sort_key(slot: str) -> tuple[int, int]:
    parts = slot.split("_")
    d = parts[0] if parts else ""
    t = parts[1] if len(parts) > 1 else ""
    day = 999
    if d.startswith("D"):
        try:
            day = int(d[1:].replace("M", "").replace("T", ""))
        except ValueError:
            day = 999
    turno = 0 if t == "MANHA" else 1 if t == "TARDE" else 9
    return day, turno


def main() -> None:
    args = parse_args()
    base = args.analysis_dir
    band = pd.read_csv(base / "consenso_bandas_core.csv")
    fam = pd.read_csv(base / "consenso_familias_core.csv")
    boot = pd.read_csv(base / "bootstrap_ic_consenso.csv")
    perm = pd.read_csv(base / "teste_permutacao_consenso.csv")
    net = pd.read_csv(base / "rede_coocorrencia_metricas.csv")
    div = pd.read_csv(base / "divergencia_temporal_turno.csv")
    master = pd.read_csv(base / "master_unificado.csv")

    fa = args.focus_analysis
    band_f = band[band["analysis"] == fa].copy()
    fam_f = fam[fam["analysis"] == fa].copy()
    boot_f = boot[boot["analysis"] == fa].copy()
    perm_f = perm[perm["analysis"] == fa].copy()
    net_f = net[net["analysis"] == fa].copy()
    div_f = div[div["analysis"] == fa].copy()
    master_f = master[master["analysis"] == fa].copy()

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(3, 3, figsize=(24, 16), constrained_layout=True)
    fig.suptitle(f"Dashboard Executivo Avancado - TestesSignfDiniz ({fa})", fontsize=20, fontweight="bold")

    # 1 consenso top bandas
    ax = axes[0, 0]
    t1 = band_f.sort_values("consensus_score", ascending=False).head(12)
    ax.barh(t1["wavelength_nm"].astype(str), t1["consensus_score"], color="#1b9e77")
    ax.invert_yaxis()
    ax.set_title("Top Bandas por Score de Consenso")
    ax.set_xlabel("Consensus Score")
    ax.set_ylabel("Wavelength (nm)")

    # 2 cobertura slot vs dataset
    ax = axes[0, 1]
    ax.scatter(
        band_f["slot_coverage"], band_f["dataset_coverage"], c=band_f["consensus_score"], cmap="viridis", alpha=0.8
    )
    ax.set_title("Cobertura Temporal vs Cobertura de Datasets")
    ax.set_xlabel("Slot Coverage")
    ax.set_ylabel("Dataset Coverage")

    # 3 familias top
    ax = axes[0, 2]
    t3 = fam_f.sort_values("mean_consensus_score", ascending=False).head(12)
    ax.bar(t3["family_nm"].astype(int).astype(str), t3["mean_consensus_score"], color="#d95f02")
    ax.set_title("Top Familias por Consenso Medio")
    ax.set_xlabel("Familia 10nm")
    ax.set_ylabel("Mean Consensus")
    ax.tick_params(axis="x", rotation=50)

    # 4 bootstrap CI
    ax = axes[1, 0]
    t4 = boot_f.sort_values("consensus_mean_boot", ascending=False).head(10).copy()
    ypos = np.arange(len(t4))
    err_low = t4["consensus_mean_boot"] - t4["consensus_ci_low"]
    err_high = t4["consensus_ci_high"] - t4["consensus_mean_boot"]
    ax.errorbar(t4["consensus_mean_boot"], ypos, xerr=[err_low, err_high], fmt="o", color="#7570b3", ecolor="#7570b3")
    ax.set_yticks(ypos, labels=t4["wavelength_nm"].astype(str))
    ax.invert_yaxis()
    ax.set_title("Bootstrap IC95% do Consenso (Top 10)")
    ax.set_xlabel("Consensus Mean (boot)")
    ax.set_ylabel("Wavelength (nm)")

    # 5 permutacao obs score
    ax = axes[1, 1]
    t5 = perm_f.sort_values("obs_score", ascending=False).head(15).copy()
    colors = np.where(t5["q_fdr_bh_perm"] < 0.05, "#66a61e", "#e6ab02")
    ax.bar(t5["wavelength_nm"].astype(str), t5["obs_score"], color=colors)
    ax.set_title("Score Observado + Significancia (FDR)")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Obs Score")
    ax.tick_params(axis="x", rotation=70)

    # 6 rede grau
    ax = axes[1, 2]
    t6 = net_f.sort_values("weighted_degree", ascending=False).head(12)
    ax.barh(t6["node_id"].astype(str), t6["weighted_degree"], color="#e7298a")
    ax.invert_yaxis()
    ax.set_title("Hubs de Coocorrencia Espectral")
    ax.set_xlabel("Weighted Degree")
    ax.set_ylabel("Wavelength (nm)")

    # 7 divergencia por dia
    ax = axes[2, 0]
    if not div_f.empty:
        d7 = div_f.sort_values("data_coleta")
        ax.bar(d7["data_coleta"], d7["js_divergence_manha_vs_tarde"], color="#a6761d")
        ax.set_title("Divergencia Manha vs Tarde por Dia (JS)")
        ax.set_xlabel("Dia")
        ax.set_ylabel("JS Divergence")
    else:
        ax.text(0.5, 0.5, "Sem pares MANHA/TARDE suficientes", ha="center", va="center")
        ax.set_title("Divergencia Manha vs Tarde por Dia (JS)")
        ax.axis("off")

    # 8 heatmap top bandas x slot
    ax = axes[2, 1]
    top_bands = band_f.sort_values("consensus_score", ascending=False).head(12)["wavelength_nm"].tolist()
    tmp = master_f[master_f["wavelength_nm"].isin(top_bands)].copy()
    tmp["present"] = 1
    pivot = tmp.pivot_table(index="wavelength_nm", columns="slot", values="present", aggfunc="max", fill_value=0)
    slot_cols = sorted(pivot.columns.tolist(), key=_slot_sort_key)
    pivot = pivot[slot_cols]
    ax.imshow(pivot.values, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_title("Heatmap Presenca Top Bandas por Slot")
    ax.set_xlabel("Slot")
    ax.set_ylabel("Wavelength (nm)")
    ax.set_xticks(np.arange(len(slot_cols)))
    ax.set_xticklabels(slot_cols, rotation=70, fontsize=8)
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([str(x) for x in pivot.index], fontsize=8)

    # 9 resumo KPI
    ax = axes[2, 2]
    core_n = int(band_f["is_core"].sum())
    sig_n = int((perm_f["q_fdr_bh_perm"] < 0.05).sum()) if not perm_f.empty else 0
    mean_js = float(div_f["js_divergence_manha_vs_tarde"].mean()) if not div_f.empty else np.nan
    text = (
        f"KPI ({fa})\n\n"
        f"Bandas avaliadas: {band_f['wavelength_nm'].nunique()}\n"
        f"Bandas core: {core_n}\n"
        f"Bandas sig. perm/FDR<0.05: {sig_n}\n"
        f"Familias: {fam_f['family_nm'].nunique()}\n"
        f"JS medio MxT: {mean_js:.3f}" if np.isfinite(mean_js) else
        f"KPI ({fa})\n\n"
        f"Bandas avaliadas: {band_f['wavelength_nm'].nunique()}\n"
        f"Bandas core: {core_n}\n"
        f"Bandas sig. perm/FDR<0.05: {sig_n}\n"
        f"Familias: {fam_f['family_nm'].nunique()}\n"
        f"JS medio MxT: n/a"
    )
    ax.text(0.05, 0.95, text, va="top", ha="left", fontsize=12, family="monospace")
    ax.set_title("Resumo Executivo")
    ax.axis("off")

    args.out_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out_file, dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
