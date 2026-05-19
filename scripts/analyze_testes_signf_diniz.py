from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
    path: Path
    top5: pd.DataFrame
    pq: pd.DataFrame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analisa resultados de significancia espectral em TestesSignfDiniz "
            "(estabilidade, familias, evidencias, concordancia e comparacao de configuracoes)."
        )
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("TestesSignfDiniz"),
        help="Diretorio base com subpastas TOP5_*.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs") / "testes_signf_diniz",
        help="Diretorio de saida para tabelas consolidadas.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed para testes de permutacao.",
    )
    parser.add_argument(
        "--n-permutations",
        type=int,
        default=5000,
        help="Numero de permutacoes para testes nao parametricos.",
    )
    return parser.parse_args()


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _normalize_top5(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_TOP5_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no TOP5 consolidado: {sorted(missing)}")

    out = df.copy()
    out["data_coleta"] = out["data_coleta"].astype(str).str.strip()
    out["turno"] = out["turno"].astype(str).str.strip()
    out["analysis"] = out["analysis"].astype(str).str.strip()
    out["rank"] = pd.to_numeric(out["rank"], errors="coerce")
    out["wavelength_nm"] = pd.to_numeric(out["wavelength_nm"], errors="coerce")
    out["p_value"] = pd.to_numeric(out["p_value"], errors="coerce")
    out["q_FDR_BH"] = pd.to_numeric(out["q_FDR_BH"], errors="coerce")
    out = out.dropna(subset=["data_coleta", "turno", "analysis", "rank", "wavelength_nm"])
    out["rank"] = out["rank"].astype(int)
    out["wavelength_nm"] = out["wavelength_nm"].round(1)
    out["slot"] = out["data_coleta"] + "_" + out["turno"]
    return out


def _load_pq_files(folder: Path) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for pq_file in sorted(folder.glob("p_q_*.csv")):
        stem = pq_file.stem.replace("p_q_", "")
        parts = stem.split("_")
        if len(parts) < 3:
            continue
        analysis = "_".join(parts[:-2])
        data_coleta, turno = parts[-2], parts[-1]
        df = pd.read_csv(pq_file)
        if not {"wavelength_nm", "p_value", "q_FDR_BH"}.issubset(df.columns):
            continue
        df = df[["wavelength_nm", "p_value", "q_FDR_BH"]].copy()
        df["analysis"] = analysis
        df["data_coleta"] = data_coleta
        df["turno"] = turno
        rows.append(df)
    if not rows:
        return pd.DataFrame(
            columns=["wavelength_nm", "p_value", "q_FDR_BH", "analysis", "data_coleta", "turno", "slot"]
        )
    out = pd.concat(rows, ignore_index=True)
    out["wavelength_nm"] = pd.to_numeric(out["wavelength_nm"], errors="coerce").round(1)
    out["p_value"] = pd.to_numeric(out["p_value"], errors="coerce")
    out["q_FDR_BH"] = pd.to_numeric(out["q_FDR_BH"], errors="coerce")
    out["analysis"] = out["analysis"].astype(str).str.strip()
    out["data_coleta"] = out["data_coleta"].astype(str).str.strip()
    out["turno"] = out["turno"].astype(str).str.strip()
    out = out.dropna(subset=["wavelength_nm", "q_FDR_BH"])
    out["slot"] = out["data_coleta"] + "_" + out["turno"]
    return out


def discover_datasets(base_dir: Path) -> list[DatasetPack]:
    packs: list[DatasetPack] = []
    for folder in sorted(base_dir.glob("TOP5*")):
        if not folder.is_dir():
            continue
        top5_file = folder / "TOP5_TODOS_DIAS_TURNOS_CONSOLIDADO.csv"
        if not top5_file.exists():
            continue
        top5 = _normalize_top5(pd.read_csv(top5_file))
        pq = _load_pq_files(folder)
        packs.append(DatasetPack(name=folder.name, path=folder, top5=top5, pq=pq))
    if not packs:
        raise FileNotFoundError(f"Nenhuma subpasta TOP5* valida encontrada em {base_dir}")
    return packs


def stability_metrics(top5: pd.DataFrame) -> pd.DataFrame:
    slots_total = top5[["analysis", "slot"]].drop_duplicates().groupby("analysis").size().rename("n_slots")
    grouped = (
        top5.groupby(["analysis", "wavelength_nm"], as_index=False)
        .agg(
            count_top5=("rank", "size"),
            n_slots_present=("slot", "nunique"),
            best_rank=("rank", "min"),
            mean_rank=("rank", "mean"),
            min_q=("q_FDR_BH", "min"),
        )
        .merge(slots_total, on="analysis", how="left")
    )
    grouped["freq_rel"] = grouped["count_top5"] / grouped["n_slots"].replace(0, np.nan)
    grouped["persistencia"] = grouped["n_slots_present"] / grouped["n_slots"].replace(0, np.nan)
    return grouped.sort_values(["analysis", "persistencia", "freq_rel", "min_q"], ascending=[True, False, False, True])


def family_metrics(stability_df: pd.DataFrame) -> pd.DataFrame:
    fam = stability_df.copy()
    fam["family_nm"] = (fam["wavelength_nm"] // 10) * 10
    out = (
        fam.groupby(["analysis", "family_nm"], as_index=False)
        .agg(
            count_top5=("count_top5", "sum"),
            wavelengths_distintas=("wavelength_nm", "nunique"),
            mean_persistencia=("persistencia", "mean"),
            min_q=("min_q", "min"),
        )
        .sort_values(["analysis", "count_top5", "min_q"], ascending=[True, False, True])
    )
    return out


def evidence_metrics(pq: pd.DataFrame) -> pd.DataFrame:
    if pq.empty:
        return pd.DataFrame(
            columns=[
                "analysis",
                "data_coleta",
                "turno",
                "n_bandas",
                "median_neglog10_q",
                "prop_q_lt_0_05",
                "prop_q_lt_0_01",
                "prop_q_lt_1e_3",
            ]
        )
    safe_q = pq["q_FDR_BH"].clip(lower=1e-300)
    pq = pq.copy()
    pq["neglog10_q"] = -np.log10(safe_q)
    out = (
        pq.groupby(["analysis", "data_coleta", "turno"], as_index=False)
        .agg(
            n_bandas=("q_FDR_BH", "size"),
            median_neglog10_q=("neglog10_q", "median"),
            prop_q_lt_0_05=("q_FDR_BH", lambda s: float((s < 0.05).mean())),
            prop_q_lt_0_01=("q_FDR_BH", lambda s: float((s < 0.01).mean())),
            prop_q_lt_1e_3=("q_FDR_BH", lambda s: float((s < 1e-3).mean())),
        )
        .sort_values(["analysis", "data_coleta", "turno"])
    )
    return out


def _jaccard(a: set[float], b: set[float]) -> float:
    union = a | b
    if not union:
        return float("nan")
    return len(a & b) / len(union)


def _overlap(a: set[float], b: set[float]) -> float:
    denom = min(len(a), len(b))
    if denom == 0:
        return float("nan")
    return len(a & b) / denom


def _perm_test_overlap(
    a: set[float],
    b: set[float],
    universe: np.ndarray,
    rng: np.random.Generator,
    n_permutations: int,
) -> float:
    k1 = len(a)
    k2 = len(b)
    if k1 == 0 or k2 == 0 or len(universe) < max(k1, k2):
        return float("nan")
    obs = len(a & b)
    ge = 0
    for _ in range(n_permutations):
        ra = set(rng.choice(universe, size=k1, replace=False).tolist())
        rb = set(rng.choice(universe, size=k2, replace=False).tolist())
        if len(ra & rb) >= obs:
            ge += 1
    return (ge + 1) / (n_permutations + 1)


def agreement_metrics(top5: pd.DataFrame, seed: int, n_permutations: int) -> pd.DataFrame:
    slots = sorted(top5["slot"].dropna().unique().tolist())
    analyses = sorted(top5["analysis"].dropna().unique().tolist())
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for slot in slots:
        slot_df = top5[top5["slot"] == slot]
        universe = np.array(sorted(slot_df["wavelength_nm"].dropna().unique().tolist()), dtype=float)
        for i, a1 in enumerate(analyses):
            set1 = set(slot_df.loc[slot_df["analysis"] == a1, "wavelength_nm"].dropna().tolist())
            for a2 in analyses[i + 1 :]:
                set2 = set(slot_df.loc[slot_df["analysis"] == a2, "wavelength_nm"].dropna().tolist())
                rows.append(
                    {
                        "slot": slot,
                        "analysis_a": a1,
                        "analysis_b": a2,
                        "n_a": len(set1),
                        "n_b": len(set2),
                        "intersection": len(set1 & set2),
                        "jaccard": _jaccard(set1, set2),
                        "overlap_coef": _overlap(set1, set2),
                        "p_perm_intersection_ge_obs": _perm_test_overlap(
                            set1, set2, universe, rng=rng, n_permutations=n_permutations
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _chi_square_gof(counts: Iterable[float]) -> tuple[float, float]:
    obs = np.asarray(list(counts), dtype=float)
    obs = obs[~np.isnan(obs)]
    if obs.size <= 1:
        return float("nan"), float("nan")
    total = obs.sum()
    if total <= 0:
        return float("nan"), float("nan")
    exp = total / obs.size
    chi2 = float(np.sum((obs - exp) ** 2 / exp))
    # p-value por aproximacao Monte Carlo para evitar dependencia de scipy
    rng = np.random.default_rng(42)
    draws = rng.multinomial(int(total), [1 / obs.size] * obs.size, size=3000)
    sim_chi2 = np.sum((draws - exp) ** 2 / exp, axis=1)
    pval = float((np.sum(sim_chi2 >= chi2) + 1) / (sim_chi2.size + 1))
    return chi2, pval


def comparison_metrics(packs: list[DatasetPack]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for pack in packs:
        stab = stability_metrics(pack.top5)
        fam = family_metrics(stab)
        evid = evidence_metrics(pack.pq)
        qvals = pack.pq["q_FDR_BH"].dropna() if not pack.pq.empty else pd.Series([], dtype=float)
        rows.append(
            {
                "dataset": pack.name,
                "n_registros_top5": int(len(pack.top5)),
                "n_slots": int(pack.top5["slot"].nunique()),
                "n_bandas_distintas": int(pack.top5["wavelength_nm"].nunique()),
                "persistencia_media": _safe_float(stab["persistencia"].mean()),
                "persistencia_p90": _safe_float(stab["persistencia"].quantile(0.90)),
                "familias_distintas": int(fam["family_nm"].nunique()),
                "mediana_min_q_por_banda": _safe_float(stab["min_q"].median()),
                "prop_q_lt_0_05_global": _safe_float((qvals < 0.05).mean() if len(qvals) else np.nan),
                "mediana_neglog10_q_slot": _safe_float(evid["median_neglog10_q"].median()) if not evid.empty else np.nan,
            }
        )
    out = pd.DataFrame(rows).sort_values(
        ["persistencia_media", "familias_distintas", "prop_q_lt_0_05_global"],
        ascending=[False, False, False],
    )
    out["rank_robustez"] = np.arange(1, len(out) + 1)
    return out


def run_for_dataset(
    pack: DatasetPack,
    out_dir: Path,
    seed: int,
    n_permutations: int,
) -> None:
    ds_dir = out_dir / pack.name
    ds_dir.mkdir(parents=True, exist_ok=True)

    stab = stability_metrics(pack.top5)
    fam = family_metrics(stab)
    evid = evidence_metrics(pack.pq)
    agree = agreement_metrics(pack.top5, seed=seed, n_permutations=n_permutations)

    chi_rows: list[dict[str, object]] = []
    for analysis, grp in fam.groupby("analysis"):
        chi2, pval = _chi_square_gof(grp["count_top5"].values)
        chi_rows.append(
            {
                "analysis": analysis,
                "n_familias": int(grp["family_nm"].nunique()),
                "chi2_gof_uniforme": chi2,
                "pvalue_mc": pval,
            }
        )
    family_test = pd.DataFrame(chi_rows)

    stab.to_csv(ds_dir / "01_estabilidade_bandas.csv", index=False)
    fam.to_csv(ds_dir / "02_frequencia_familias.csv", index=False)
    family_test.to_csv(ds_dir / "03_teste_familias_gof.csv", index=False)
    evid.to_csv(ds_dir / "04_forca_evidencia_temporal.csv", index=False)
    agree.to_csv(ds_dir / "05_concordancia_analises.csv", index=False)


def main() -> None:
    args = parse_args()
    packs = discover_datasets(args.base_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for pack in packs:
        run_for_dataset(
            pack=pack,
            out_dir=args.out_dir,
            seed=args.seed,
            n_permutations=args.n_permutations,
        )

    cmp_df = comparison_metrics(packs)
    cmp_df.to_csv(args.out_dir / "comparacao_configuracoes_robustez.csv", index=False)

    summary_lines = [
        "# Resumo TestesSignfDiniz",
        "",
        f"- Data de execucao: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Configuracoes avaliadas: {len(packs)}",
        f"- Saida principal: `{args.out_dir.as_posix()}`",
        "",
        "## Ranking de robustez (global)",
    ]
    preview = cmp_df.head(5)
    for _, row in preview.iterrows():
        summary_lines.append(
            f"- #{int(row['rank_robustez'])} `{row['dataset']}` | "
            f"persistencia_media={row['persistencia_media']:.3f} | "
            f"familias={int(row['familias_distintas'])} | "
            f"prop_q<0.05={row['prop_q_lt_0_05_global']:.3f}"
        )
    (args.out_dir / "README_analise.md").write_text("\n".join(summary_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
