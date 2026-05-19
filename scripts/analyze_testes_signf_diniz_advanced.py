from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_TOP5_COLS = {
    "data_coleta",
    "turno",
    "analysis",
    "rank",
    "wavelength_nm",
    "p_value",
    "q_FDR_BH",
}


@dataclass(frozen=True)
class DatasetPack:
    name: str
    top5: pd.DataFrame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analise avancada de consenso robusto para TestesSignfDiniz.")
    parser.add_argument("--base-dir", type=Path, default=Path("TestesSignfDiniz"))
    parser.add_argument("--out-dir", type=Path, default=Path("outputs") / "testes_signf_diniz_advanced")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--n-permutations", type=int, default=5000)
    return parser.parse_args()


def _bh_fdr(p_values: pd.Series) -> pd.Series:
    p = pd.to_numeric(p_values, errors="coerce").values.astype(float)
    out = np.full_like(p, np.nan, dtype=float)
    valid = np.isfinite(p)
    pv = p[valid]
    if pv.size == 0:
        return pd.Series(out, index=p_values.index)
    order = np.argsort(pv)
    ranked = pv[order]
    m = float(len(ranked))
    q = ranked * m / (np.arange(1, len(ranked) + 1))
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    tmp = np.empty_like(q)
    tmp[order] = q
    out[valid] = tmp
    return pd.Series(out, index=p_values.index)


def _normalize_top5(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_TOP5_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    out = df.copy()
    out["data_coleta"] = out["data_coleta"].astype(str).str.strip()
    out["turno"] = out["turno"].astype(str).str.strip()
    out["analysis"] = out["analysis"].astype(str).str.strip()
    out["rank"] = pd.to_numeric(out["rank"], errors="coerce")
    out["wavelength_nm"] = pd.to_numeric(out["wavelength_nm"], errors="coerce").round(1)
    out["q_FDR_BH"] = pd.to_numeric(out["q_FDR_BH"], errors="coerce")
    out = out.dropna(subset=["data_coleta", "turno", "analysis", "rank", "wavelength_nm", "q_FDR_BH"])
    out["rank"] = out["rank"].astype(int)
    out["slot"] = out["data_coleta"] + "_" + out["turno"]
    out["family_nm"] = (out["wavelength_nm"] // 10) * 10
    return out


def discover(base_dir: Path) -> list[DatasetPack]:
    packs: list[DatasetPack] = []
    for folder in sorted(base_dir.glob("TOP5*")):
        top5_file = folder / "TOP5_TODOS_DIAS_TURNOS_CONSOLIDADO.csv"
        if folder.is_dir() and top5_file.exists():
            df = _normalize_top5(pd.read_csv(top5_file))
            packs.append(DatasetPack(name=folder.name, top5=df))
    if not packs:
        raise FileNotFoundError(f"Nenhuma pasta TOP5* valida em {base_dir}")
    return packs


def build_master(packs: list[DatasetPack]) -> pd.DataFrame:
    rows = []
    for p in packs:
        df = p.top5.copy()
        df["dataset"] = p.name
        rows.append(df)
    out = pd.concat(rows, ignore_index=True)
    out["neglog10_q"] = -np.log10(out["q_FDR_BH"].clip(lower=1e-300))
    out["inv_rank"] = 1.0 / out["rank"].replace(0, np.nan)
    return out


def compute_consensus(master: pd.DataFrame, n_datasets: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    slot_count = master["slot"].nunique()
    band = (
        master.groupby(["analysis", "wavelength_nm"], as_index=False)
        .agg(
            n_obs=("wavelength_nm", "size"),
            n_slots=("slot", "nunique"),
            n_datasets=("dataset", "nunique"),
            mean_inv_rank=("inv_rank", "mean"),
            mean_neglog10_q=("neglog10_q", "mean"),
            std_rank=("rank", "std"),
        )
    )
    band["slot_coverage"] = band["n_slots"] / max(slot_count, 1)
    band["dataset_coverage"] = band["n_datasets"] / max(n_datasets, 1)
    band["rank_stability"] = 1 / (1 + band["std_rank"].fillna(0))
    band["consensus_score"] = (
        0.35 * band["slot_coverage"]
        + 0.25 * band["dataset_coverage"]
        + 0.20 * band["mean_inv_rank"]
        + 0.15 * (band["mean_neglog10_q"] / (band["mean_neglog10_q"].max() or 1))
        + 0.05 * band["rank_stability"]
    )
    band = band.sort_values(["analysis", "consensus_score"], ascending=[True, False])
    band["is_core"] = (band["slot_coverage"] >= 0.5) & (band["n_datasets"] >= min(4, n_datasets))

    fam = band.copy()
    fam["family_nm"] = (fam["wavelength_nm"] // 10) * 10
    fam = (
        fam.groupby(["analysis", "family_nm"], as_index=False)
        .agg(
            mean_consensus_score=("consensus_score", "mean"),
            max_consensus_score=("consensus_score", "max"),
            n_bandas=("wavelength_nm", "nunique"),
            slot_coverage_mean=("slot_coverage", "mean"),
            dataset_coverage_mean=("dataset_coverage", "mean"),
        )
        .sort_values(["analysis", "mean_consensus_score"], ascending=[True, False])
    )
    return band, fam


def bootstrap_consensus(master: pd.DataFrame, n_datasets: int, n_bootstrap: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    slots = sorted(master["slot"].unique().tolist())
    analyses = sorted(master["analysis"].unique().tolist())
    results: list[dict[str, float | str]] = []

    for analysis in analyses:
        base = master[master["analysis"] == analysis].copy()
        slot_to_df = {s: base[base["slot"] == s] for s in slots}
        unique_bands = sorted(base["wavelength_nm"].unique().tolist())
        scores = {w: [] for w in unique_bands}
        for _ in range(n_bootstrap):
            sampled_slots = rng.choice(slots, size=len(slots), replace=True)
            boot = pd.concat([slot_to_df[s] for s in sampled_slots], ignore_index=True)
            b, _ = compute_consensus(boot, n_datasets=n_datasets)
            for _, r in b.iterrows():
                scores[r["wavelength_nm"]].append(float(r["consensus_score"]))
        for w, arr in scores.items():
            if len(arr) == 0:
                continue
            vals = np.array(arr, dtype=float)
            results.append(
                {
                    "analysis": analysis,
                    "wavelength_nm": w,
                    "consensus_mean_boot": float(np.mean(vals)),
                    "consensus_ci_low": float(np.quantile(vals, 0.025)),
                    "consensus_ci_high": float(np.quantile(vals, 0.975)),
                }
            )
    return pd.DataFrame(results).sort_values(["analysis", "consensus_mean_boot"], ascending=[True, False])


def permutation_consensus_test(master: pd.DataFrame, n_datasets: int, n_permutations: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    obs_band, _ = compute_consensus(master, n_datasets=n_datasets)
    obs = obs_band[["analysis", "wavelength_nm", "consensus_score"]].copy()
    obs = obs.rename(columns={"consensus_score": "obs_score"})

    # nulo: aleatoriza labels de wavelength dentro de cada slot/analysis/dataset
    null_scores: dict[tuple[str, float], list[float]] = {}
    grouped = master.groupby(["slot", "analysis", "dataset"], sort=False)
    for _ in range(n_permutations):
        perm_chunks = []
        for _, g in grouped:
            gp = g.copy()
            perm_w = gp["wavelength_nm"].values.copy()
            rng.shuffle(perm_w)
            gp["wavelength_nm"] = perm_w
            gp["family_nm"] = (gp["wavelength_nm"] // 10) * 10
            perm_chunks.append(gp)
        perm = pd.concat(perm_chunks, ignore_index=True)
        b_perm, _ = compute_consensus(perm, n_datasets=n_datasets)
        for _, r in b_perm.iterrows():
            key = (str(r["analysis"]), float(r["wavelength_nm"]))
            null_scores.setdefault(key, []).append(float(r["consensus_score"]))

    pvals = []
    for _, r in obs.iterrows():
        key = (str(r["analysis"]), float(r["wavelength_nm"]))
        null = np.array(null_scores.get(key, []), dtype=float)
        if null.size == 0:
            p = np.nan
        else:
            p = float((np.sum(null >= float(r["obs_score"])) + 1) / (null.size + 1))
        pvals.append(p)
    obs["p_perm"] = pvals
    obs["q_fdr_bh_perm"] = _bh_fdr(obs["p_perm"])
    obs["significativo_perm_fdr_0_05"] = obs["q_fdr_bh_perm"] < 0.05
    return obs.sort_values(["analysis", "obs_score"], ascending=[True, False])


def cooccurrence_network(master: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for analysis, ga in master.groupby("analysis"):
        slots = sorted(ga["slot"].unique().tolist())
        edge_counts: dict[tuple[float, float], int] = {}
        node_degree: dict[float, int] = {}
        for s in slots:
            bands = sorted(set(ga.loc[ga["slot"] == s, "wavelength_nm"].tolist()))
            for i, a in enumerate(bands):
                node_degree.setdefault(a, 0)
                for b in bands[i + 1 :]:
                    key = (a, b)
                    edge_counts[key] = edge_counts.get(key, 0) + 1
                    node_degree[a] = node_degree.get(a, 0) + 1
                    node_degree[b] = node_degree.get(b, 0) + 1
        for w, deg in node_degree.items():
            rows.append(
                {
                    "analysis": analysis,
                    "node_type": "band",
                    "node_id": w,
                    "weighted_degree": deg,
                    "normalized_degree": deg / max(len(slots), 1),
                }
            )
    out = pd.DataFrame(rows).sort_values(["analysis", "weighted_degree"], ascending=[True, False])
    return out


def _js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    p = p / max(p.sum(), 1e-12)
    q = q / max(q.sum(), 1e-12)
    m = 0.5 * (p + q)
    def _kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = (a > 0) & (b > 0)
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


def temporal_turno_divergence(master: pd.DataFrame, n_permutations: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for analysis, ga in master.groupby("analysis"):
        fams = sorted(ga["family_nm"].unique().tolist())
        fam_idx = {f: i for i, f in enumerate(fams)}
        for day, gd in ga.groupby("data_coleta"):
            m = gd[gd["turno"] == "MANHA"]
            t = gd[gd["turno"] == "TARDE"]
            if m.empty or t.empty:
                continue
            vm = np.zeros(len(fams), dtype=float)
            vt = np.zeros(len(fams), dtype=float)
            for f, c in m["family_nm"].value_counts().items():
                vm[fam_idx[f]] = c
            for f, c in t["family_nm"].value_counts().items():
                vt[fam_idx[f]] = c
            obs = _js_divergence(vm, vt)

            comb = pd.concat([m.assign(_lbl="M"), t.assign(_lbl="T")], ignore_index=True)
            ge = 0
            for _ in range(n_permutations):
                perm_lbl = comb["_lbl"].values.copy()
                rng.shuffle(perm_lbl)
                cp = comb.copy()
                cp["_perm"] = perm_lbl
                pm = cp[cp["_perm"] == "M"]
                pt = cp[cp["_perm"] == "T"]
                vm_p = np.zeros(len(fams), dtype=float)
                vt_p = np.zeros(len(fams), dtype=float)
                for f, c in pm["family_nm"].value_counts().items():
                    vm_p[fam_idx[f]] = c
                for f, c in pt["family_nm"].value_counts().items():
                    vt_p[fam_idx[f]] = c
                if _js_divergence(vm_p, vt_p) >= obs:
                    ge += 1
            p = (ge + 1) / (n_permutations + 1)
            rows.append({"analysis": analysis, "data_coleta": day, "js_divergence_manha_vs_tarde": obs, "p_perm": p})
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["analysis", "data_coleta", "js_divergence_manha_vs_tarde", "p_perm", "q_fdr_bh"])
    out["q_fdr_bh"] = _bh_fdr(out["p_perm"])
    return out.sort_values(["analysis", "js_divergence_manha_vs_tarde"], ascending=[True, False])


def write_readme(out_dir: Path, band: pd.DataFrame, fam: pd.DataFrame, cmp_perm: pd.DataFrame) -> None:
    lines = [
        "# Metodologia Avancada - TestesSignfDiniz",
        "",
        "- Objetivo: consenso robusto entre configuracoes, dias e turnos.",
        "- Criterio core: cobertura de slot >= 0.5 e presenca em >=4 datasets.",
        "",
        "## Resumo rapido",
        f"- Bandas avaliadas: {band['wavelength_nm'].nunique()}",
        f"- Familias avaliadas: {fam['family_nm'].nunique()}",
    ]
    if not cmp_perm.empty:
        sig = int((cmp_perm["q_fdr_bh_perm"] < 0.05).sum())
        lines.append(f"- Bandas com consenso significativo por permutacao (FDR<0.05): {sig}")
    (out_dir / "README_metodologia_avancada.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    packs = discover(args.base_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    master = build_master(packs)
    n_datasets = len(packs)

    band, fam = compute_consensus(master, n_datasets=n_datasets)
    boot = bootstrap_consensus(master, n_datasets=n_datasets, n_bootstrap=args.n_bootstrap, seed=args.seed)
    perm = permutation_consensus_test(
        master, n_datasets=n_datasets, n_permutations=args.n_permutations, seed=args.seed
    )
    net = cooccurrence_network(master)
    div = temporal_turno_divergence(master, n_permutations=args.n_permutations, seed=args.seed)

    band.to_csv(args.out_dir / "consenso_bandas_core.csv", index=False)
    fam.to_csv(args.out_dir / "consenso_familias_core.csv", index=False)
    boot.to_csv(args.out_dir / "bootstrap_ic_consenso.csv", index=False)
    perm.to_csv(args.out_dir / "teste_permutacao_consenso.csv", index=False)
    net.to_csv(args.out_dir / "rede_coocorrencia_metricas.csv", index=False)
    div.to_csv(args.out_dir / "divergencia_temporal_turno.csv", index=False)
    master.to_csv(args.out_dir / "master_unificado.csv", index=False)

    write_readme(args.out_dir, band, fam, perm)


if __name__ == "__main__":
    main()
