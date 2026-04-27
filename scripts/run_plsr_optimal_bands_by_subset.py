#!/usr/bin/env python3
"""Run PLSR on subgroup slices to identify optimal bands for water stress."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from run_plsr_pca_irrigation import (
    calculate_vip_scores,
    evaluate_pls_components,
    fit_final_pls,
    load_dataset,
    plot_pls_band_curves,
    subset_dataset,
    write_csv,
)


SHIFT_ORDER = {"manha": 0, "tarde": 1}
GENOTYPE_ORDER = {"BR16": 0, "CD202": 1, "EMB48": 2}
DIRECTION_COLORS = {"irrigado": "#0f766e", "nao_irrigado": "#c2410c"}


@dataclass(frozen=True)
class SubsetSpec:
    subset_type: str
    subset_name: str
    subset_label: str
    shift: str | None = None
    genotype: str | None = None


@dataclass(frozen=True)
class SubsetResult:
    spec: SubsetSpec
    matched_dates: list[str]
    n_samples: int
    irrigated_count: int
    non_irrigated_count: int
    effective_cv_splits: int
    best_components: int
    best_result: dict[str, float]
    top_table: np.ndarray
    positive_table: np.ndarray
    negative_table: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run PLSR on turno/genotipo subsets of the processed irrigation dataset "
            "to identify optimal bands for water-stress discrimination."
        )
    )
    parser.add_argument(
        "--processed-csv",
        type=Path,
        default=Path("dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv"),
        help="Processed spectral dataset.",
    )
    parser.add_argument(
        "--metadata-csv",
        type=Path,
        default=Path("dados_processados_soft/metadados_normalizados_soft.csv"),
        help="Normalized metadata file aligned with the processed dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft/plsr_subconjuntos_irrigacao"),
        help="Directory where subgroup PLSR outputs will be written.",
    )
    parser.add_argument(
        "--max-components",
        type=int,
        default=15,
        help="Maximum number of PLS components to evaluate per subset.",
    )
    parser.add_argument(
        "--cv-splits",
        type=int,
        default=5,
        help="Maximum number of stratified folds per subset.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of optimal bands to keep for each subset.",
    )
    return parser.parse_args()


def robust_zscore(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    mean = np.nanmean(values)
    std = np.nanstd(values)
    if np.isclose(std, 0.0):
        return np.zeros_like(values)
    return (values - mean) / std


def find_matched_dates(dates: list[str], shifts: list[str]) -> list[str]:
    shifts_by_date: dict[str, set[str]] = {}
    for date_value, shift_value in zip(dates, shifts, strict=False):
        shifts_by_date.setdefault(date_value, set()).add(shift_value)
    return sorted(
        date_value
        for date_value, date_shifts in shifts_by_date.items()
        if {"manha", "tarde"}.issubset(date_shifts)
    )


def build_subset_specs(genotypes: list[str]) -> list[SubsetSpec]:
    specs = [
        SubsetSpec("turno", "manha", "Turno manha", shift="manha"),
        SubsetSpec("turno", "tarde", "Turno tarde", shift="tarde"),
    ]

    for genotype in genotypes:
        specs.append(
            SubsetSpec(
                "genotipo",
                genotype,
                f"Genotipo {genotype}",
                genotype=genotype,
            )
        )

    for shift in ["manha", "tarde"]:
        for genotype in genotypes:
            specs.append(
                SubsetSpec(
                    "turno_genotipo",
                    f"{shift}_{genotype}",
                    f"{shift} / {genotype}",
                    shift=shift,
                    genotype=genotype,
                )
            )

    return specs


def build_subset_mask(
    *,
    dates: list[str],
    shifts: list[str],
    genotypes: list[str],
    matched_dates: set[str],
    shift: str | None,
    genotype: str | None,
) -> np.ndarray:
    mask = np.asarray([date_value in matched_dates for date_value in dates], dtype=bool)
    if shift is not None:
        mask &= np.asarray([value == shift for value in shifts], dtype=bool)
    if genotype is not None:
        mask &= np.asarray([value == genotype for value in genotypes], dtype=bool)
    return mask


def build_band_table(
    wavelengths: np.ndarray,
    coefficients: np.ndarray,
    vip_scores: np.ndarray,
    *,
    top_k: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dtype = np.dtype(
        [
            ("wavelength", np.float64),
            ("coefficient", np.float64),
            ("abs_coefficient", np.float64),
            ("vip", np.float64),
            ("optimal_score", np.float64),
            ("rank", np.int32),
            ("direction_label", "U20"),
        ]
    )
    band_table = np.empty(wavelengths.shape[0], dtype=dtype)
    band_table["wavelength"] = wavelengths
    band_table["coefficient"] = coefficients
    band_table["abs_coefficient"] = np.abs(coefficients)
    band_table["vip"] = vip_scores
    band_table["optimal_score"] = robust_zscore(vip_scores) + robust_zscore(np.abs(coefficients))
    band_table["rank"] = 0
    band_table["direction_label"] = np.where(coefficients >= 0, "irrigado", "nao_irrigado")

    top_table = np.sort(band_table, order=["optimal_score", "vip", "abs_coefficient"])[::-1][:top_k].copy()
    top_table["rank"] = np.arange(1, top_table.shape[0] + 1)
    positive_table = np.sort(band_table, order="coefficient")[-10:][::-1].copy()
    negative_table = np.sort(band_table, order="coefficient")[:10].copy()
    return band_table, top_table, positive_table, negative_table


def write_subset_summary_markdown(path: Path, result: SubsetResult) -> None:
    lines = [
        f"# PLSR: {result.spec.subset_label}",
        "",
        "- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.",
        "- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).",
        f"- Datas usadas: {', '.join(result.matched_dates)}",
        f"- Amostras totais: {result.n_samples}",
        f"- Classes: irrigado = {result.irrigated_count}, nao_irrigado = {result.non_irrigated_count}",
        f"- Folds efetivos: {result.effective_cv_splits}",
        f"- Melhor numero de componentes PLSR: {result.best_components}",
        f"- RMSECV: {result.best_result['rmsecv']:.6f}",
        f"- R2CV: {result.best_result['r2cv']:.6f}",
        f"- AUC: {result.best_result['auc']:.6f}",
        f"- Accuracy: {result.best_result['accuracy']:.6f}",
        "- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).",
        "",
        "## Top bandas otimas",
        "",
        "| rank | banda | direcao | VIP | coeficiente | score otimo |",
        "| ---: | ---: | --- | ---: | ---: | ---: |",
    ]

    for row in result.top_table:
        lines.append(
            f"| {int(row['rank'])} | {int(row['wavelength'])} | {row['direction_label']} | "
            f"{row['vip']:.4f} | {row['coefficient']:.6f} | {row['optimal_score']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Coeficientes mais positivos",
            "",
            "| banda | coeficiente | VIP |",
            "| ---: | ---: | ---: |",
        ]
    )
    for row in result.positive_table[:5]:
        lines.append(
            f"| {int(row['wavelength'])} | {row['coefficient']:.6f} | {row['vip']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Coeficientes mais negativos",
            "",
            "| banda | coeficiente | VIP |",
            "| ---: | ---: | ---: |",
        ]
    )
    for row in result.negative_table[:5]:
        lines.append(
            f"| {int(row['wavelength'])} | {row['coefficient']:.6f} | {row['vip']:.4f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_master_summary_markdown(
    path: Path,
    *,
    matched_dates: list[str],
    results: list[SubsetResult],
) -> None:
    lines = [
        "# PLSR por turno e genotipo",
        "",
        "- Objetivo: identificar bandas otimas para diferenciar `irrigado` vs `nao_irrigado` em subconjuntos de turno e genotipo.",
        "- Base usada: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).",
        f"- Datas usadas em todos os subconjuntos: {', '.join(matched_dates)}",
        "- Score de banda otima: z(VIP) + z(|coeficiente PLSR|).",
        "",
        "## Resumo dos subconjuntos",
        "",
        "| subconjunto | n | irrigado | nao_irrigado | folds | comp. | RMSECV | AUC | banda #1 | direcao | VIP | coeficiente |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]

    for result in results:
        top_band = result.top_table[0]
        lines.append(
            f"| {result.spec.subset_label} | {result.n_samples} | {result.irrigated_count} | "
            f"{result.non_irrigated_count} | {result.effective_cv_splits} | {result.best_components} | "
            f"{result.best_result['rmsecv']:.6f} | {result.best_result['auc']:.6f} | "
            f"{int(top_band['wavelength'])} | {top_band['direction_label']} | "
            f"{top_band['vip']:.4f} | {top_band['coefficient']:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Top 5 bandas por subconjunto",
            "",
        ]
    )

    for result in results:
        lines.extend(
            [
                f"### {result.spec.subset_label}",
                "",
                "| rank | banda | direcao | VIP | coeficiente | score otimo |",
                "| ---: | ---: | --- | ---: | ---: | ---: |",
            ]
        )
        for row in result.top_table[:5]:
            lines.append(
                f"| {int(row['rank'])} | {int(row['wavelength'])} | {row['direction_label']} | "
                f"{row['vip']:.4f} | {row['coefficient']:.6f} | {row['optimal_score']:.4f} |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index_html(output_dir: Path, matched_dates: list[str], results: list[SubsetResult]) -> None:
    sections = [
        ("turno", "Turno"),
        ("genotipo", "Genotipo"),
        ("turno_genotipo", "Turno x Genotipo"),
    ]
    section_html: list[str] = []

    for section_key, section_title in sections:
        section_results = [result for result in results if result.spec.subset_type == section_key]
        if not section_results:
            continue

        cards: list[str] = []
        for result in section_results:
            subset_dir = f"{result.spec.subset_type}/{result.spec.subset_name}"
            top_band = result.top_table[0]
            cards.append(
                (
                    '<article class="subset-card">'
                    f'<div class="subset-header"><h3>{escape(result.spec.subset_label)}</h3>'
                    f'<span class="badge">{result.n_samples} amostras</span></div>'
                    f'<p class="meta">PLSR para diferenciar irrigado vs nao_irrigado nas datas '
                    f'{escape(", ".join(result.matched_dates))}.</p>'
                    '<div class="stats">'
                    f'<span>RMSECV {result.best_result["rmsecv"]:.4f}</span>'
                    f'<span>AUC {result.best_result["auc"]:.4f}</span>'
                    f'<span>Banda #1 {int(top_band["wavelength"])}</span>'
                    '</div>'
                    '<div class="links">'
                    f'<a href="{escape(subset_dir)}/resumo_plsr_subconjunto.md">resumo</a>'
                    f'<a href="{escape(subset_dir)}/top_20_bandas_otimas.csv">top 20 csv</a>'
                    f'<a href="{escape(subset_dir)}/plsr_bandas_importantes.csv">bandas completas</a>'
                    '</div>'
                    '<div class="figure-grid">'
                    f'<figure><figcaption>Top bandas otimas</figcaption>'
                    f'<a href="{escape(subset_dir)}/top_20_bandas_otimas.svg">'
                    f'<img src="{escape(subset_dir)}/top_20_bandas_otimas.svg" '
                    f'alt="Top bandas otimas - {escape(result.spec.subset_label)}"/></a></figure>'
                    f'<figure><figcaption>Coeficientes e VIP</figcaption>'
                    f'<a href="{escape(subset_dir)}/plsr_coeficientes_vip.svg">'
                    f'<img src="{escape(subset_dir)}/plsr_coeficientes_vip.svg" '
                    f'alt="Coeficientes e VIP - {escape(result.spec.subset_label)}"/></a></figure>'
                    '</div>'
                    '</article>'
                )
            )

        section_html.append(
            (
                f'<section class="group-section"><div class="section-head"><h2>{escape(section_title)}</h2></div>'
                f'<div class="subset-grid">{"".join(cards)}</div></section>'
            )
        )

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PLSR por Turno e Genotipo</title>
  <style>
    :root {{
      --bg-1: #ece7da;
      --bg-2: #dfe7e1;
      --paper: #fffdf8;
      --paper-2: #f7f2e8;
      --ink: #14202b;
      --muted: #5a6572;
      --line: #d6d2c5;
      --accent: #0f766e;
      --accent-2: #c2410c;
      --link: #1d4ed8;
      --shadow: 0 18px 42px rgba(20, 32, 43, 0.12);
      --radius: 22px;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(194, 65, 12, 0.10), transparent 26%),
        linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 100%);
    }}
    main {{
      max-width: 1680px;
      margin: 0 auto;
      padding: 34px 28px 52px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(255, 253, 248, 0.95), rgba(247, 242, 232, 0.92));
      border: 1px solid rgba(214, 210, 197, 0.9);
      border-radius: 28px;
      padding: 28px 30px;
      box-shadow: var(--shadow);
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 34px;
      letter-spacing: -0.03em;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
    }}
    .hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .pill {{
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(15, 118, 110, 0.10);
      border: 1px solid rgba(15, 118, 110, 0.16);
      color: var(--ink);
      font-size: 13px;
      font-weight: 600;
    }}
    .hero-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
    }}
    .hero-links a, .links a {{
      color: var(--link);
      text-decoration: none;
      font-weight: 600;
    }}
    .overview-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 22px;
      margin-top: 26px;
    }}
    .overview-card, .subset-card {{
      background: rgba(255, 253, 248, 0.96);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .overview-card {{
      padding: 18px;
    }}
    .overview-card h2, .section-head h2 {{
      margin: 0 0 8px;
      font-size: 24px;
      letter-spacing: -0.02em;
    }}
    .overview-card figure, .subset-card figure {{
      margin: 14px 0 0;
    }}
    figcaption {{
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 14px;
      font-weight: 600;
    }}
    img {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 16px;
      background: white;
      border: 1px solid rgba(214, 210, 197, 0.9);
    }}
    .group-section {{
      margin-top: 30px;
    }}
    .section-head {{
      margin-bottom: 14px;
    }}
    .subset-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(520px, 1fr));
      gap: 24px;
    }}
    .subset-card {{
      padding: 18px;
    }}
    .subset-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
    }}
    .subset-header h3 {{
      margin: 0;
      font-size: 22px;
      letter-spacing: -0.02em;
    }}
    .badge {{
      white-space: nowrap;
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(194, 65, 12, 0.10);
      border: 1px solid rgba(194, 65, 12, 0.18);
      color: var(--ink);
      font-size: 12px;
      font-weight: 700;
    }}
    .meta {{
      margin-top: 10px;
      font-size: 14px;
    }}
    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }}
    .stats span {{
      padding: 7px 10px;
      border-radius: 999px;
      background: var(--paper-2);
      border: 1px solid var(--line);
      font-size: 12px;
      font-weight: 700;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 14px;
    }}
    .figure-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}
    @media (max-width: 760px) {{
      main {{
        padding: 22px 16px 34px;
      }}
      .hero {{
        padding: 22px 18px;
      }}
      h1 {{
        font-size: 28px;
      }}
      .subset-grid {{
        grid-template-columns: 1fr;
      }}
      .overview-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>PLSR por Turno e Genotipo</h1>
      <p>Pagina de navegacao dos graficos de bandas otimas para diferenciar estresse hidrico. Os subconjuntos foram ajustados com PLSR usando apenas as datas que possuem manha e tarde na base.</p>
      <div class="hero-meta">
        <span class="pill">Datas: {escape(", ".join(matched_dates))}</span>
        <span class="pill">Subconjuntos: {len(results)}</span>
        <span class="pill">Base: SNV + Savitzky-Golay + 1a derivada</span>
      </div>
      <div class="hero-links">
        <a href="resumo_plsr_subconjuntos.md">resumo_plsr_subconjuntos.md</a>
        <a href="metricas_subconjuntos_plsr.csv">metricas_subconjuntos_plsr.csv</a>
        <a href="top_bandas_otimas_subconjuntos_plsr.csv">top_bandas_otimas_subconjuntos_plsr.csv</a>
      </div>
    </section>

    <section class="overview-grid">
      <article class="overview-card">
        <h2>Top 1 por Subconjunto</h2>
        <p>Comparacao da melhor banda de cada subconjunto ao longo do espectro.</p>
        <figure>
          <figcaption><a href="banda_otima_top1_por_subconjunto.svg">banda_otima_top1_por_subconjunto.svg</a></figcaption>
          <a href="banda_otima_top1_por_subconjunto.svg"><img src="banda_otima_top1_por_subconjunto.svg" alt="Banda otima top 1 por subconjunto"/></a>
        </figure>
      </article>
      <article class="overview-card">
        <h2>Top 5 por Subconjunto</h2>
        <p>Visao consolidada das cinco bandas mais fortes em cada ajuste PLSR.</p>
        <figure>
          <figcaption><a href="top5_bandas_otimas_por_subconjunto.svg">top5_bandas_otimas_por_subconjunto.svg</a></figcaption>
          <a href="top5_bandas_otimas_por_subconjunto.svg"><img src="top5_bandas_otimas_por_subconjunto.svg" alt="Top 5 bandas otimas por subconjunto"/></a>
        </figure>
      </article>
    </section>

    {"".join(section_html)}
  </main>
</body>
</html>
"""
    (output_dir / "index.html").write_text(html, encoding="utf-8")


def plot_subset_top_bands(path: Path, result: SubsetResult) -> None:
    top_table = result.top_table
    order = np.arange(top_table.shape[0])[::-1]
    labels = [str(int(value)) for value in top_table["wavelength"][order]]
    colors = [
        DIRECTION_COLORS.get(value, "#4b5563")
        for value in top_table["direction_label"][order]
    ]

    fig, ax = plt.subplots(figsize=(10.5, max(6.0, 0.36 * top_table.shape[0])), constrained_layout=True)
    ax.barh(labels, top_table["optimal_score"][order], color=colors)
    ax.set_xlabel("Score otimo (z(VIP) + z(|coeficiente|))")
    ax.set_ylabel("Banda (nm)")
    ax.set_title(f"Top bandas otimas | {result.spec.subset_label}")
    ax.grid(alpha=0.18, axis="x")

    for bar_index, row_index in enumerate(order):
        row = top_table[row_index]
        ax.text(
            float(row["optimal_score"]) + 0.02,
            bar_index,
            f"VIP={row['vip']:.2f} | coef={row['coefficient']:.4f}",
            va="center",
            fontsize=8,
            color="#111827",
        )

    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_master_top1(path: Path, results: list[SubsetResult]) -> None:
    labels = [result.spec.subset_label for result in results]
    wavelengths = np.asarray([result.top_table[0]["wavelength"] for result in results], dtype=np.float64)
    scores = np.asarray([result.top_table[0]["optimal_score"] for result in results], dtype=np.float64)
    colors = [DIRECTION_COLORS.get(result.top_table[0]["direction_label"], "#4b5563") for result in results]
    y_positions = np.arange(len(results), dtype=np.float64)
    marker_sizes = 90 + 55 * (scores - np.min(scores)) / max(np.ptp(scores), 1e-9)

    fig, ax = plt.subplots(figsize=(11.5, max(5.5, 0.55 * len(results))), constrained_layout=True)
    for y_value, wavelength, color in zip(y_positions, wavelengths, colors, strict=False):
        ax.hlines(y_value, 350, wavelength, color="#d1d5db", linewidth=1.2)

    ax.scatter(
        wavelengths,
        y_positions,
        s=marker_sizes,
        c=colors,
        alpha=0.95,
        edgecolor="#111827",
        linewidth=0.5,
    )

    for index, result in enumerate(results):
        top_band = result.top_table[0]
        ax.annotate(
            (
                f"{int(top_band['wavelength'])} nm\n"
                f"VIP={top_band['vip']:.2f} | "
                f"coef={top_band['coefficient']:.4f}"
            ),
            (float(top_band["wavelength"]), y_positions[index]),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color="#111827",
        )

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Comprimento de onda da banda #1 (nm)")
    ax.set_title("Banda otima #1 por subconjunto")
    ax.grid(alpha=0.16, axis="x")
    ax.set_xlim(350, max(2500, float(np.max(wavelengths)) + 20))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_master_top5(path: Path, results: list[SubsetResult]) -> None:
    fig, ax = plt.subplots(figsize=(13, max(5.8, 0.58 * len(results))), constrained_layout=True)
    y_positions = np.arange(len(results), dtype=np.float64)

    for index, result in enumerate(results):
        top_rows = result.top_table[:5]
        x_values = np.asarray(top_rows["wavelength"], dtype=np.float64)
        scores = np.asarray(top_rows["optimal_score"], dtype=np.float64)
        colors = [DIRECTION_COLORS.get(value, "#4b5563") for value in top_rows["direction_label"]]
        sizes = 70 + 45 * (scores - np.min(scores)) / max(np.ptp(scores), 1e-9)

        ax.scatter(
            x_values,
            np.full_like(x_values, y_positions[index], dtype=np.float64),
            s=sizes,
            c=colors,
            alpha=0.92,
            edgecolor="#111827",
            linewidth=0.4,
        )

        for row in top_rows:
            ax.annotate(
                str(int(row["wavelength"])),
                (float(row["wavelength"]), y_positions[index]),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=7,
                color="#111827",
            )

    ax.set_yticks(y_positions)
    ax.set_yticklabels([result.spec.subset_label for result in results])
    ax.set_xlabel("Comprimento de onda (nm)")
    ax.set_title("Top 5 bandas otimas por subconjunto")
    ax.grid(alpha=0.16, axis="x")
    ax.set_xlim(350, 2500)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_subset_outputs(output_dir: Path, result: SubsetResult, band_table: np.ndarray) -> None:
    subset_dir = output_dir / result.spec.subset_type / result.spec.subset_name
    subset_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        subset_dir / "plsr_cv_metricas.csv",
        ["n_components", "rmsecv", "r2cv", "auc", "accuracy"],
        [
            [
                int(result.best_result["n_components"]),
                f"{result.best_result['rmsecv']:.10f}",
                f"{result.best_result['r2cv']:.10f}",
                f"{result.best_result['auc']:.10f}",
                f"{result.best_result['accuracy']:.10f}",
            ]
        ],
    )
    write_csv(
        subset_dir / "plsr_bandas_importantes.csv",
        ["wavelength", "direction_label", "vip", "coefficient", "abs_coefficient", "optimal_score"],
        [
            [
                int(row["wavelength"]),
                row["direction_label"],
                f"{row['vip']:.10f}",
                f"{row['coefficient']:.10f}",
                f"{row['abs_coefficient']:.10f}",
                f"{row['optimal_score']:.10f}",
            ]
            for row in np.sort(band_table, order=["optimal_score", "vip", "abs_coefficient"])[::-1]
        ],
    )
    write_csv(
        subset_dir / "top_20_bandas_otimas.csv",
        ["rank", "wavelength", "direction_label", "vip", "coefficient", "abs_coefficient", "optimal_score"],
        [
            [
                int(row["rank"]),
                int(row["wavelength"]),
                row["direction_label"],
                f"{row['vip']:.10f}",
                f"{row['coefficient']:.10f}",
                f"{row['abs_coefficient']:.10f}",
                f"{row['optimal_score']:.10f}",
            ]
            for row in result.top_table
        ],
    )
    write_subset_summary_markdown(subset_dir / "resumo_plsr_subconjunto.md", result)
    plot_pls_band_curves(
        np.asarray(band_table["wavelength"], dtype=np.float64),
        np.asarray(band_table["coefficient"], dtype=np.float64),
        np.asarray(band_table["vip"], dtype=np.float64),
        subset_dir / "plsr_coeficientes_vip.svg",
    )
    plot_subset_top_bands(subset_dir / "top_20_bandas_otimas.svg", result)


def run_subset_analysis(
    dataset,
    spec: SubsetSpec,
    matched_dates: list[str],
    *,
    max_components: int,
    cv_splits: int,
    top_k: int,
) -> tuple[SubsetResult, np.ndarray]:
    mask = build_subset_mask(
        dates=dataset.dates,
        shifts=dataset.shifts,
        genotypes=dataset.genotypes,
        matched_dates=set(matched_dates),
        shift=spec.shift,
        genotype=spec.genotype,
    )
    subset = subset_dataset(dataset, mask)
    irrigated_count = int(np.sum(subset.y == 1))
    non_irrigated_count = int(np.sum(subset.y == 0))
    min_class_count = min(irrigated_count, non_irrigated_count)
    if min_class_count < 2:
        raise ValueError(
            f"Subset {spec.subset_label!r} does not have enough samples per class for PLSR."
        )

    effective_cv_splits = min(cv_splits, min_class_count)
    cv_results, best_components = evaluate_pls_components(
        subset.x,
        subset.y,
        max_components=max_components,
        cv_splits=effective_cv_splits,
    )
    best_result = next(item for item in cv_results if int(item["n_components"]) == best_components)
    scaler, pls, x_scaled = fit_final_pls(subset.x, subset.y, best_components)
    del scaler, x_scaled

    vip_scores = calculate_vip_scores(pls)
    coefficients = pls.coef_.ravel()
    band_table, top_table, positive_table, negative_table = build_band_table(
        subset.wavelengths,
        coefficients,
        vip_scores,
        top_k=top_k,
    )

    result = SubsetResult(
        spec=spec,
        matched_dates=matched_dates,
        n_samples=subset.x.shape[0],
        irrigated_count=irrigated_count,
        non_irrigated_count=non_irrigated_count,
        effective_cv_splits=effective_cv_splits,
        best_components=best_components,
        best_result=best_result,
        top_table=top_table,
        positive_table=positive_table,
        negative_table=negative_table,
    )
    return result, band_table


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(args.processed_csv.resolve(), args.metadata_csv.resolve())
    matched_dates = find_matched_dates(dataset.dates, dataset.shifts)
    if not matched_dates:
        raise ValueError("No dates with both manha and tarde were found in the dataset.")

    genotypes = sorted(set(dataset.genotypes), key=lambda value: (GENOTYPE_ORDER.get(value, 999), value))
    subset_specs = build_subset_specs(genotypes)

    results: list[SubsetResult] = []
    consolidated_top_rows: list[list[object]] = []
    consolidated_metric_rows: list[list[object]] = []

    for spec in subset_specs:
        result, band_table = run_subset_analysis(
            dataset,
            spec,
            matched_dates,
            max_components=args.max_components,
            cv_splits=args.cv_splits,
            top_k=args.top_k,
        )
        results.append(result)
        write_subset_outputs(output_dir, result, band_table)

        top_band = result.top_table[0]
        consolidated_metric_rows.append(
            [
                spec.subset_type,
                spec.subset_name,
                spec.subset_label,
                "|".join(matched_dates),
                result.n_samples,
                result.irrigated_count,
                result.non_irrigated_count,
                result.effective_cv_splits,
                result.best_components,
                f"{result.best_result['rmsecv']:.10f}",
                f"{result.best_result['r2cv']:.10f}",
                f"{result.best_result['auc']:.10f}",
                f"{result.best_result['accuracy']:.10f}",
                int(top_band["wavelength"]),
                top_band["direction_label"],
                f"{top_band['vip']:.10f}",
                f"{top_band['coefficient']:.10f}",
                f"{top_band['optimal_score']:.10f}",
            ]
        )

        for row in result.top_table:
            consolidated_top_rows.append(
                [
                    spec.subset_type,
                    spec.subset_name,
                    spec.subset_label,
                    int(row["rank"]),
                    int(row["wavelength"]),
                    row["direction_label"],
                    f"{row['vip']:.10f}",
                    f"{row['coefficient']:.10f}",
                    f"{row['abs_coefficient']:.10f}",
                    f"{row['optimal_score']:.10f}",
                ]
            )

    results.sort(
        key=lambda item: (
            {"turno": 0, "genotipo": 1, "turno_genotipo": 2}.get(item.spec.subset_type, 99),
            SHIFT_ORDER.get(item.spec.shift or "", 99),
            GENOTYPE_ORDER.get(item.spec.genotype or "", 99),
            item.spec.subset_name,
        )
    )

    write_csv(
        output_dir / "metricas_subconjuntos_plsr.csv",
        [
            "subset_type",
            "subset_name",
            "subset_label",
            "matched_dates",
            "n_samples",
            "irrigated_count",
            "non_irrigated_count",
            "effective_cv_splits",
            "best_components",
            "rmsecv",
            "r2cv",
            "auc",
            "accuracy",
            "top_band",
            "top_band_direction",
            "top_band_vip",
            "top_band_coefficient",
            "top_band_optimal_score",
        ],
        consolidated_metric_rows,
    )
    write_csv(
        output_dir / "top_bandas_otimas_subconjuntos_plsr.csv",
        [
            "subset_type",
            "subset_name",
            "subset_label",
            "rank",
            "wavelength",
            "direction_label",
            "vip",
            "coefficient",
            "abs_coefficient",
            "optimal_score",
        ],
        consolidated_top_rows,
    )
    write_master_summary_markdown(
        output_dir / "resumo_plsr_subconjuntos.md",
        matched_dates=matched_dates,
        results=results,
    )
    plot_master_top1(output_dir / "banda_otima_top1_por_subconjunto.svg", results)
    plot_master_top5(output_dir / "top5_bandas_otimas_por_subconjunto.svg", results)
    write_index_html(output_dir, matched_dates, results)

    print(f"Output directory: {output_dir}")
    print(f"Matched dates used: {', '.join(matched_dates)}")
    print(f"Subsets analyzed: {len(results)}")
    print("Outputs:")
    print(f"  - {output_dir / 'metricas_subconjuntos_plsr.csv'}")
    print(f"  - {output_dir / 'top_bandas_otimas_subconjuntos_plsr.csv'}")
    print(f"  - {output_dir / 'resumo_plsr_subconjuntos.md'}")
    print(f"  - {output_dir / 'banda_otima_top1_por_subconjunto.svg'}")
    print(f"  - {output_dir / 'top5_bandas_otimas_por_subconjunto.svg'}")
    print(f"  - {output_dir / 'index.html'}")


if __name__ == "__main__":
    main()
