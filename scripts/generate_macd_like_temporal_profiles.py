#!/usr/bin/env python3
"""Generate NDVI+MACD-like temporal charts for top-5 reflectance bands."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGETS = ["condicao", "condicao_genotipo", "condicao_genotipo_turno"]
TARGET_LABELS = {
    "condicao": "Condicao",
    "condicao_genotipo": "Condicao + Genotipo",
    "condicao_genotipo_turno": "Condicao + Genotipo + Turno",
}

COLORS = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate MACD-like temporal charts from reflectance top-5 outputs."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("outputs/testes_signf_diniz/perfil_temporal_reflectancia_top5"),
        help="Directory with perfil_temporal_reflectancia_<target>.csv files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/testes_signf_diniz/perfil_temporal_reflectancia_top5"),
        help="Output directory for MACD-like charts.",
    )
    parser.add_argument("--dpi", type=int, default=300)
    return parser.parse_args()


def _read_target_csv(input_dir: Path, target: str) -> pd.DataFrame:
    path = input_dir / f"perfil_temporal_reflectancia_{target}.csv"
    df = pd.read_csv(path)
    df["dia"] = df["dia"].astype(str).str.strip()
    if "tempo" in df.columns:
        df["tempo"] = df["tempo"].astype(str).str.strip()
    df["banda_nm"] = pd.to_numeric(df["banda_nm"], errors="coerce")
    df["reflectancia_media"] = pd.to_numeric(df["reflectancia_media"], errors="coerce")
    df["n_amostras_efetivo"] = pd.to_numeric(df["n_amostras_efetivo"], errors="coerce").fillna(0)
    df = df.dropna(subset=["banda_nm", "reflectancia_media"]).copy()
    return df


def _turno_tag(value: object) -> str:
    s = str(value).strip().upper()
    if s.startswith("M"):
        return "m"
    if s.startswith("T"):
        return "t"
    return s.lower()[:1] if s else "?"


def _weighted_band_series(df: pd.DataFrame, target: str) -> pd.DataFrame:
    rows: list[dict[str, float | pd.Timestamp]] = []
    time_key = "tempo" if target == "condicao_genotipo_turno" and "tempo" in df.columns else "dia"
    for (tempo, banda), grp in df.groupby([time_key, "banda_nm"], dropna=False):
        w = grp["n_amostras_efetivo"].to_numpy(dtype=float)
        x = grp["reflectancia_media"].to_numpy(dtype=float)
        valid = np.isfinite(w) & np.isfinite(x) & (w > 0)
        if not valid.any():
            continue
        if time_key == "tempo":
            day_raw, turno_raw = str(tempo).split("|", 1)
            day_num = pd.to_numeric(pd.Series([day_raw]).str.extract(r"D(\d+)", expand=False), errors="coerce").iloc[0]
            turno_rank = 0 if turno_raw.upper().startswith("M") else 1 if turno_raw.upper().startswith("T") else 9
            tick_label = f"dia {{}}{_turno_tag(turno_raw)}"
        else:
            day_raw = str(tempo)
            day_num = pd.to_numeric(pd.Series([day_raw]).str.extract(r"D(\d+)", expand=False), errors="coerce").iloc[0]
            turno_rank = -1
            tick_label = "dia {}"
        rows.append(
            {
                "tempo": str(tempo),
                "day_raw": day_raw,
                "day_num": day_num,
                "turno_rank": turno_rank,
                "banda_nm": float(banda),
                "reflectancia": float(np.average(x[valid], weights=w[valid])),
                "tick_label_tpl": tick_label,
            }
        )
    out = pd.DataFrame(rows).sort_values(["day_num", "day_raw", "turno_rank", "tempo", "banda_nm"]).reset_index(drop=True)
    unique_days = out["day_raw"].drop_duplicates().tolist()
    day_map = {d: i for i, d in enumerate(unique_days)}
    out["time_idx"] = out["day_raw"].map(day_map).astype(int)
    out["tick_label"] = out.apply(lambda r: str(r["tick_label_tpl"]).format(int(r["time_idx"])), axis=1)
    return out


def _compute_index_and_macd(band_daily: pd.DataFrame) -> pd.DataFrame:
    idx = (
        band_daily.groupby(["tempo", "time_idx", "tick_label"], as_index=False)["reflectancia"]
        .mean()
        .sort_values(["time_idx", "tempo"])
        .reset_index(drop=True)
        .rename(columns={"reflectancia": "observado"})
    )
    idx["suavizado_ema"] = idx["observado"].ewm(span=3, adjust=False).mean()
    idx["tendencia"] = idx["observado"].rolling(window=3, min_periods=1).mean()

    ema_fast = idx["observado"].ewm(span=3, adjust=False).mean()
    ema_slow = idx["observado"].ewm(span=6, adjust=False).mean()
    idx["macd"] = ema_fast - ema_slow
    idx["signal"] = idx["macd"].ewm(span=3, adjust=False).mean()
    idx["hist"] = idx["macd"] - idx["signal"]

    # inflections on MACD-signal crossing
    diff = idx["macd"] - idx["signal"]
    sign = np.sign(diff.fillna(0))
    idx["cross"] = (sign != sign.shift(1)) & (sign != 0) & (sign.shift(1) != 0)
    return idx


def _plot_target(target: str, band_daily: pd.DataFrame, idx: pd.DataFrame, out_file: Path, dpi: int) -> None:
    bands = sorted(band_daily["banda_nm"].unique().tolist())
    band_colors = {b: COLORS[i % len(COLORS)] for i, b in enumerate(bands)}

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(13.5, 8.0),
        sharex=True,
        gridspec_kw={"height_ratios": [3.0, 1.4]},
        constrained_layout=True,
    )
    ax_top, ax_bot = axes

    # Top panel: each line = one band + observed/smoothed/trend
    for b in bands:
        sub = band_daily[band_daily["banda_nm"] == b].sort_values(["time_idx", "tempo"])
        ax_top.plot(
            sub["time_idx"],
            sub["reflectancia"],
            linewidth=1.2,
            marker="o",
            markersize=3.0,
            color=band_colors[b],
            alpha=0.85,
            label=f"Banda {int(round(b))} nm",
        )
    ax_top.plot(idx["time_idx"], idx["observado"], color="#2166ac", linewidth=2.0, label="Indice observado (media top-5)")
    ax_top.plot(idx["time_idx"], idx["suavizado_ema"], color="#e6ab02", linewidth=2.0, label="Suavizado EMA")
    ax_top.plot(idx["time_idx"], idx["tendencia"], color="#666666", linewidth=2.2, label="Tendencia")

    inflection_dates = idx.loc[idx["cross"], "tempo"].tolist()
    for d in inflection_dates:
        d_idx = float(idx.loc[idx["tempo"] == d, "time_idx"].iloc[0])
        ax_top.axvline(d_idx, color="black", linestyle="--", linewidth=1.0, alpha=0.65)

    ax_top.set_ylabel("Reflectancia")
    ax_top.set_title(f"Perfil Temporal + MACD-like ({TARGET_LABELS[target]})", fontsize=13, fontweight="bold")
    ax_top.grid(True, alpha=0.25)
    band_handles = []
    band_labels = []
    extra_handles = []
    extra_labels = []
    for h, l in zip(*ax_top.get_legend_handles_labels()):
        if l.startswith("Banda "):
            band_handles.append(h)
            band_labels.append(l)
        else:
            extra_handles.append(h)
            extra_labels.append(l)
    ax_top.legend(extra_handles, extra_labels, loc="upper left", ncol=2, fontsize=8, frameon=False)
    fig.legend(band_handles, band_labels, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.01))

    # Bottom panel: MACD and signal
    ax_bot.plot(idx["time_idx"], idx["macd"], color="#222222", linewidth=1.8, label="MACD")
    ax_bot.plot(idx["time_idx"], idx["signal"], color="#d73027", linewidth=1.8, label="Sinal")
    ax_bot.bar(idx["time_idx"], idx["hist"], color="#a6bddb", alpha=0.6, width=0.6, label="Hist")
    ax_bot.axhline(0.0, color="black", linewidth=1.0, alpha=0.8)
    for d in inflection_dates:
        d_idx = float(idx.loc[idx["tempo"] == d, "time_idx"].iloc[0])
        ax_bot.axvline(d_idx, color="black", linestyle="--", linewidth=1.0, alpha=0.65)
    ax_bot.set_ylabel("MACD")
    ax_bot.set_xlabel("Dia")
    ax_bot.grid(True, alpha=0.25)
    ax_bot.legend(loc="upper left", ncol=3, fontsize=8, frameon=False)
    ticks_df = idx[["time_idx", "tick_label"]].drop_duplicates().sort_values("time_idx")
    ax_bot.set_xticks(ticks_df["time_idx"].to_numpy())
    ax_bot.set_xticklabels(ticks_df["tick_label"].tolist(), rotation=0, ha="center")

    if inflection_dates:
        text_dates = ", ".join(
            idx.loc[idx["tempo"] == d, "tick_label"].iloc[0] for d in inflection_dates
        )
        fig.text(
            0.01,
            0.01,
            f"Inflexoes detectadas (cruz. MACD x sinal): {text_dates}",
            fontsize=8,
        )

    out_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_file, dpi=dpi)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for target in TARGETS:
        df = _read_target_csv(args.input_dir, target)
        if df.empty:
            print(f"SKIP {target}: no rows.")
            continue
        band_daily = _weighted_band_series(df, target)
        if band_daily.empty:
            print(f"SKIP {target}: no weighted band series.")
            continue
        idx = _compute_index_and_macd(band_daily)
        out_file = args.output_dir / f"perfil_temporal_macd_like_{target}.png"
        _plot_target(target, band_daily, idx, out_file, dpi=args.dpi)
        print(f"OK: {out_file}")


if __name__ == "__main__":
    main()
