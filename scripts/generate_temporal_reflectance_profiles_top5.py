#!/usr/bin/env python3
"""Generate temporal reflectance profiles for fixed top-5 bands per target."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TOP5_BANDS_BY_TARGET: dict[str, list[int]] = {
    "condicao": [1580, 400, 739, 579, 530],
    "condicao_genotipo": [720, 401, 400, 550, 530],
    "condicao_genotipo_turno": [720, 401, 400, 550, 530],
}

TARGET_LABELS: dict[str, str] = {
    "condicao": "Condicao",
    "condicao_genotipo": "Condicao + Genotipo",
    "condicao_genotipo_turno": "Condicao + Genotipo + Turno",
}


@dataclass(frozen=True)
class Inputs:
    by_day_turno_gen_cond: Path
    by_day_gen_cond: Path
    output_dir: Path
    dpi: int


def parse_args() -> Inputs:
    parser = argparse.ArgumentParser(
        description=(
            "Generate temporal reflectance profiles (X=day, Y=reflectance) "
            "for fixed top-5 bands by target."
        )
    )
    parser.add_argument(
        "--by-day-turno-gen-cond-csv",
        type=Path,
        default=Path(
            "outputs/reflectancia_bruta_genotipos/tabelas/"
            "reflectancia_bruta_media_por_data_turno_genotipo_condicao.csv"
        ),
        help="Aggregated reflectance by day/turno/genotype/condition.",
    )
    parser.add_argument(
        "--by-day-gen-cond-csv",
        type=Path,
        default=Path(
            "outputs/reflectancia_bruta_genotipos/tabelas/"
            "reflectancia_bruta_media_por_data_genotipo_condicao.csv"
        ),
        help="Aggregated reflectance by day/genotype/condition.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/testes_signf_diniz/perfil_temporal_reflectancia_top5"),
        help="Directory to write PNG and CSV outputs.",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Output PNG DPI.")
    ns = parser.parse_args()
    return Inputs(
        by_day_turno_gen_cond=ns.by_day_turno_gen_cond_csv,
        by_day_gen_cond=ns.by_day_gen_cond_csv,
        output_dir=ns.output_dir,
        dpi=ns.dpi,
    )


def _normalize_base_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["data_coleta"] = out["data_coleta"].astype(str).str.strip()
    out["condicao"] = out["condicao"].astype(str).str.strip()
    out["genotipo"] = out["genotipo"].astype(str).str.strip()
    if "turno" in out.columns:
        out["turno"] = out["turno"].astype(str).str.strip().str.upper()
    out["n_amostras"] = pd.to_numeric(out["n_amostras"], errors="coerce").fillna(0)
    out = out[out["n_amostras"] > 0].copy()
    return out


def _validate_band_columns(df: pd.DataFrame, bands: list[int], source_name: str) -> None:
    missing = [str(b) for b in bands if str(b) not in df.columns]
    if missing:
        raise ValueError(
            f"{source_name}: missing band columns: {', '.join(missing)}"
        )


def _day_order(values: pd.Series) -> list[str]:
    tmp = values.astype(str).str.extract(r"D(\d+)", expand=False)
    day_num = pd.to_numeric(tmp, errors="coerce")
    ordered = (
        pd.DataFrame({"day": values.astype(str), "day_num": day_num})
        .drop_duplicates("day")
        .sort_values(["day_num", "day"], na_position="last")
    )
    return ordered["day"].tolist()


def _build_day_label_map(day_order: list[str]) -> dict[str, str]:
    return {day: f"dia {idx}" for idx, day in enumerate(day_order)}


def _turno_tag(value: object) -> str:
    s = str(value).strip().upper()
    if s.startswith("M"):
        return "m"
    if s.startswith("T"):
        return "t"
    return s.lower()[:1] if s else "?"


def _tempo_order_and_labels(values: pd.Series) -> tuple[list[str], dict[str, str]]:
    tmp = values.astype(str).str.extract(r"^(.*?)\|([A-Za-z]+)$", expand=True)
    day_raw = tmp[0].fillna(values.astype(str))
    turno_raw = tmp[1].fillna("")
    day_num = pd.to_numeric(day_raw.str.extract(r"D(\d+)", expand=False), errors="coerce")
    turno_rank = turno_raw.str.upper().map({"MANHA": 0, "M": 0, "TARDE": 1, "T": 1}).fillna(9)
    order_df = (
        pd.DataFrame(
            {
                "tempo": values.astype(str),
                "day_raw": day_raw.astype(str),
                "day_num": day_num,
                "turno_raw": turno_raw.astype(str),
                "turno_rank": turno_rank,
            }
        )
        .drop_duplicates("tempo")
        .sort_values(["day_num", "day_raw", "turno_rank", "turno_raw", "tempo"], na_position="last")
    )
    tempo_order = order_df["tempo"].tolist()
    day_map = {d: i for i, d in enumerate(order_df["day_raw"].drop_duplicates().tolist())}
    label_map = {
        row["tempo"]: f"dia {day_map[row['day_raw']]}{_turno_tag(row['turno_raw'])}"
        for _, row in order_df.iterrows()
    }
    return tempo_order, label_map


def build_target_frames(
    by_day_turno_gen_cond: pd.DataFrame, by_day_gen_cond: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}

    # condicao: weighted aggregation over genotypes for each day + condition
    cond_rows: list[dict[str, object]] = []
    bands_cond = TOP5_BANDS_BY_TARGET["condicao"]
    for (day, cond), grp in by_day_gen_cond.groupby(["data_coleta", "condicao"], dropna=False):
        weights = grp["n_amostras"].to_numpy(dtype=float)
        for band in bands_cond:
            col = str(band)
            vals = pd.to_numeric(grp[col], errors="coerce").to_numpy(dtype=float)
            valid = np.isfinite(vals) & np.isfinite(weights) & (weights > 0)
            if not valid.any():
                continue
            mean_val = float(np.average(vals[valid], weights=weights[valid]))
            n_eff = int(weights[valid].sum())
            cond_rows.append(
                {
                    "target": "condicao",
                    "classe": cond,
                    "dia": day,
                    "banda_nm": band,
                    "reflectancia_media": mean_val,
                    "n_amostras_efetivo": n_eff,
                }
            )
    frames["condicao"] = pd.DataFrame(cond_rows)

    # condicao_genotipo: class = condicao|genotipo, from day/genotype/condition table
    cgen_rows: list[dict[str, object]] = []
    bands_cgen = TOP5_BANDS_BY_TARGET["condicao_genotipo"]
    for _, row in by_day_gen_cond.iterrows():
        cls = f"{row['condicao']}|{row['genotipo']}"
        for band in bands_cgen:
            val = pd.to_numeric(row[str(band)], errors="coerce")
            if not np.isfinite(val):
                continue
            cgen_rows.append(
                {
                    "target": "condicao_genotipo",
                    "classe": cls,
                    "dia": row["data_coleta"],
                    "banda_nm": band,
                    "reflectancia_media": float(val),
                    "n_amostras_efetivo": int(row["n_amostras"]),
                }
            )
    frames["condicao_genotipo"] = pd.DataFrame(cgen_rows)

    # condicao_genotipo_turno: class = condicao|genotipo|turno, from day/turno/genotype/condition table
    cgent_rows: list[dict[str, object]] = []
    bands_cgent = TOP5_BANDS_BY_TARGET["condicao_genotipo_turno"]
    for _, row in by_day_turno_gen_cond.iterrows():
        cls = f"{row['condicao']}|{row['genotipo']}|{row['turno']}"
        for band in bands_cgent:
            val = pd.to_numeric(row[str(band)], errors="coerce")
            if not np.isfinite(val):
                continue
            cgent_rows.append(
                {
                    "target": "condicao_genotipo_turno",
                    "classe": cls,
                    "dia": row["data_coleta"],
                    "tempo": f"{row['data_coleta']}|{row['turno']}",
                    "banda_nm": band,
                    "reflectancia_media": float(val),
                    "n_amostras_efetivo": int(row["n_amostras"]),
                }
            )
    frames["condicao_genotipo_turno"] = pd.DataFrame(cgent_rows)

    return frames


def plot_target(df: pd.DataFrame, target: str, out_file: Path, dpi: int) -> None:
    if df.empty:
        raise ValueError(f"No data rows available for target={target}")

    bands = TOP5_BANDS_BY_TARGET[target]
    classes = sorted(df["classe"].unique().tolist())
    if target == "condicao_genotipo_turno" and "tempo" in df.columns:
        x_key = "tempo"
        x_order, x_label_map = _tempo_order_and_labels(df["tempo"])
    else:
        x_key = "dia"
        x_order = _day_order(df["dia"])
        x_label_map = _build_day_label_map(x_order)
    band_colors = {
        bands[0]: "#1b9e77",
        bands[1]: "#d95f02",
        bands[2]: "#7570b3",
        bands[3]: "#e7298a",
        bands[4]: "#66a61e",
    }

    n_classes = len(classes)
    n_cols = 3 if n_classes > 4 else 2 if n_classes > 1 else 1
    n_rows = int(np.ceil(n_classes / n_cols))
    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(7.0 * n_cols, 3.8 * n_rows),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )
    if not isinstance(axes, np.ndarray):
        axes_arr = np.array([axes], dtype=object)
    else:
        axes_arr = axes.ravel()

    legend_handles = []
    legend_labels = []
    x_vals = np.arange(len(x_order))

    for i, cls in enumerate(classes):
        ax = axes_arr[i]
        sub = df[df["classe"] == cls].copy()
        sub[x_key] = pd.Categorical(sub[x_key], categories=x_order, ordered=True)
        sub = sub.sort_values([x_key, "banda_nm"])

        for band in bands:
            band_sub = sub[sub["banda_nm"] == band]
            y_map = {d: np.nan for d in x_order}
            for _, r in band_sub.iterrows():
                y_map[str(r[x_key])] = float(r["reflectancia_media"])
            y_vals = np.array([y_map[d] for d in x_order], dtype=float)
            (line,) = ax.plot(
                x_vals,
                y_vals,
                marker="o",
                linewidth=1.8,
                markersize=4.5,
                color=band_colors[band],
                label=f"{band} nm",
            )
            if i == 0:
                legend_handles.append(line)
                legend_labels.append(f"{band} nm")

        ax.set_title(str(cls), fontsize=10)
        ax.grid(True, alpha=0.25, linewidth=0.8)
        ax.set_xticks(x_vals)
        ax.set_xticklabels([x_label_map[d] for d in x_order], rotation=0, ha="center")
        ax.set_ylabel("Reflectancia")
        ax.set_xlabel("Dia")

    for j in range(n_classes, len(axes_arr)):
        fig.delaxes(axes_arr[j])

    fig.suptitle(
        f"Perfil Temporal de Reflectancia - {TARGET_LABELS[target]}",
        fontsize=14,
        fontweight="bold",
    )
    fig.legend(
        legend_handles,
        legend_labels,
        loc="lower center",
        ncol=5,
        frameon=False,
        bbox_to_anchor=(0.5, -0.02),
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_file, dpi=dpi)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df_day_turno_gen_cond = _normalize_base_frame(pd.read_csv(args.by_day_turno_gen_cond))
    df_day_gen_cond = _normalize_base_frame(pd.read_csv(args.by_day_gen_cond))

    # Validate required band columns in sources.
    _validate_band_columns(
        df_day_gen_cond,
        TOP5_BANDS_BY_TARGET["condicao"],
        "reflectancia_bruta_media_por_data_genotipo_condicao.csv",
    )
    _validate_band_columns(
        df_day_gen_cond,
        TOP5_BANDS_BY_TARGET["condicao_genotipo"],
        "reflectancia_bruta_media_por_data_genotipo_condicao.csv",
    )
    _validate_band_columns(
        df_day_turno_gen_cond,
        TOP5_BANDS_BY_TARGET["condicao_genotipo_turno"],
        "reflectancia_bruta_media_por_data_turno_genotipo_condicao.csv",
    )

    target_frames = build_target_frames(df_day_turno_gen_cond, df_day_gen_cond)

    for target, df_target in target_frames.items():
        csv_out = args.output_dir / f"perfil_temporal_reflectancia_{target}.csv"
        png_out = args.output_dir / f"perfil_temporal_reflectancia_{target}.png"
        df_target.to_csv(csv_out, index=False, encoding="utf-8-sig")
        plot_target(df_target, target, png_out, dpi=args.dpi)

    print(f"OK: temporal profiles written to: {args.output_dir}")


if __name__ == "__main__":
    main()
