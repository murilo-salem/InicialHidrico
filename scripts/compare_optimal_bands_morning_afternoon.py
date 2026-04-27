#!/usr/bin/env python3
"""Compare raw reflectance between morning and afternoon on optimal bands."""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr

from generate_descriptive_stats import META_COLUMNS, iter_sheet_rows, normalize_metadata


DEFAULT_DATES = ("2017-02-23", "2017-02-24", "2017-03-02")
GENOTYPE_ORDER = {"BR16": 0, "CD202": 1, "EMB48": 2}
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RAW_DATE_RE = re.compile(r"^\d{8}$")
SHORT_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$")
SHIFT_COLORS = {"manha": "#1d4ed8", "tarde": "#c2410c"}
DIRECTION_COLORS = {"irrigado": "#0f766e", "nao_irrigado": "#b45309"}


@dataclass(frozen=True)
class OptimalBand:
    wavelength: int
    direction_label: str
    source_rank: int
    class_rank: int | None
    vip: float | None
    cohen_d: float | None
    q_value: float | None
    combined_score: float | None


@dataclass
class RunningBandStats:
    count: int
    sums: np.ndarray
    sums_of_squares: np.ndarray

    @classmethod
    def create(cls, size: int) -> "RunningBandStats":
        zeros = np.zeros(size, dtype=np.float64)
        return cls(count=0, sums=zeros.copy(), sums_of_squares=zeros.copy())

    def add(self, values: np.ndarray) -> None:
        self.count += 1
        self.sums += values
        self.sums_of_squares += values * values

    def mean(self) -> np.ndarray:
        if self.count == 0:
            return np.full_like(self.sums, np.nan, dtype=np.float64)
        return self.sums / self.count

    def std(self) -> np.ndarray:
        if self.count < 2:
            return np.zeros_like(self.sums, dtype=np.float64)
        numerator = self.sums_of_squares - ((self.sums * self.sums) / self.count)
        variance = np.maximum(numerator / (self.count - 1), 0.0)
        return np.sqrt(variance)


@dataclass(frozen=True)
class DateComparison:
    date_iso: str
    date_label: str
    morning_count: int
    afternoon_count: int
    pearson_r: float
    pearson_p_value: float
    mean_abs_diff: float
    rmse: float
    top_abs_diff_band: int
    top_abs_diff_value: float


@dataclass(frozen=True)
class GenotypeComparison:
    genotype: str
    date_iso: str
    date_label: str
    morning_count: int
    afternoon_count: int
    pearson_r: float
    pearson_p_value: float
    mean_abs_diff: float
    rmse: float
    top_abs_diff_band: int
    top_abs_diff_value: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare morning vs afternoon raw reflectance on the optimal bands "
            "selected by the irrigation PLSR summary."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("base_dados_unificada.xlsx"),
        help="Path to the raw workbook with reflectance values.",
    )
    parser.add_argument(
        "--optimal-bands-csv",
        type=Path,
        default=Path("dados_processados_soft/plsr_pca_irrigacao/top_10_irrigado_top_10_nao_irrigado.csv"),
        help="CSV containing the optimal bands to compare.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/pearson_bandas_otimas_turno"),
        help="Directory where outputs will be written.",
    )
    parser.add_argument(
        "--dates",
        nargs="*",
        default=list(DEFAULT_DATES),
        help=(
            "Dates to analyze. Supported formats: YYYY-MM-DD, YYYYMMDD or dd/mm. "
            f"Defaults to: {', '.join(DEFAULT_DATES)}."
        ),
    )
    return parser.parse_args()


def parse_date_token(token: str) -> str:
    cleaned = token.strip()
    if ISO_DATE_RE.match(cleaned):
        return cleaned
    if RAW_DATE_RE.match(cleaned):
        return f"{cleaned[:4]}-{cleaned[4:6]}-{cleaned[6:]}"

    short_match = SHORT_DATE_RE.match(cleaned)
    if short_match is None:
        raise ValueError(
            f"Unsupported date token: {token!r}. Use YYYY-MM-DD, YYYYMMDD or dd/mm."
        )

    day = int(short_match.group(1))
    month = int(short_match.group(2))
    year_token = short_match.group(3)
    if year_token is None:
        year = 2017
    elif len(year_token) == 2:
        year = 2000 + int(year_token)
    else:
        year = int(year_token)
    return date(year, month, day).isoformat()


def format_date_label(date_iso: str) -> str:
    year, month, day = date_iso.split("-")
    return f"{day}/{month}/{year}"


def safe_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def safe_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def load_optimal_bands(path: Path) -> list[OptimalBand]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        bands: list[OptimalBand] = []
        seen: set[int] = set()
        for source_rank, row in enumerate(reader, start=1):
            wavelength = int(float(row["wavelength"]))
            if wavelength in seen:
                continue
            seen.add(wavelength)
            direction_label = row.get("direction_label") or row.get("group_rank") or "desconhecido"
            bands.append(
                OptimalBand(
                    wavelength=wavelength,
                    direction_label=str(direction_label),
                    source_rank=source_rank,
                    class_rank=safe_int(row.get("group_rank") or row.get("rank")),
                    vip=safe_float(row.get("vip")),
                    cohen_d=safe_float(row.get("cohen_d")),
                    q_value=safe_float(row.get("q_value")),
                    combined_score=safe_float(row.get("combined_score")),
                )
            )
    if not bands:
        raise ValueError(f"No bands found in optimal-band CSV: {path}")
    return bands


def build_wavelength_index_map(header_row: list[str | None]) -> dict[int, int]:
    wavelengths = [
        int(float(value))
        for value in header_row[len(META_COLUMNS) :]
        if value is not None and value != ""
    ]
    return {wavelength: index for index, wavelength in enumerate(wavelengths)}


def collect_group_stats(
    workbook_path: Path,
    optimal_bands: list[OptimalBand],
    selected_dates: list[str],
) -> tuple[
    dict[tuple[str, str], RunningBandStats],
    dict[tuple[str, str, str], RunningBandStats],
    set[str],
    set[str],
]:
    header: list[str | None] | None = None
    band_indices: list[int] | None = None
    date_set = set(selected_dates)
    stats_by_date_shift: dict[tuple[str, str], RunningBandStats] = {}
    stats_by_date_shift_genotype: dict[tuple[str, str, str], RunningBandStats] = {}
    available_dates: set[str] = set()
    available_genotypes: set[str] = set()
    normalization_examples: list[tuple[int, str, str, str]] = []

    for row_number, row_values in iter_sheet_rows(workbook_path):
        if row_number == 1:
            header = row_values
            wavelength_index = build_wavelength_index_map(header)
            missing_bands = [band.wavelength for band in optimal_bands if band.wavelength not in wavelength_index]
            if missing_bands:
                raise ValueError(
                    "The following optimal bands are missing from the raw workbook: "
                    + ", ".join(str(value) for value in missing_bands)
                )
            band_indices = [wavelength_index[band.wavelength] for band in optimal_bands]
            continue

        if header is None or band_indices is None:
            raise ValueError("Header row was not found before reading data rows.")

        if len(row_values) < len(header):
            row_values.extend([None] * (len(header) - len(row_values)))

        metadata = normalize_metadata(row_number, row_values, normalization_examples)
        available_dates.add(metadata.collection_date_iso)
        available_genotypes.add(metadata.genotype)

        if metadata.collection_date_iso not in date_set:
            continue
        if metadata.shift not in {"manha", "tarde"}:
            continue

        spectral_slice = np.asarray(
            [float(row_values[len(META_COLUMNS) + index]) for index in band_indices],
            dtype=np.float64,
        )
        key = (metadata.collection_date_iso, metadata.shift)
        stats = stats_by_date_shift.get(key)
        if stats is None:
            stats = RunningBandStats.create(len(optimal_bands))
            stats_by_date_shift[key] = stats
        stats.add(spectral_slice)

        genotype_key = (metadata.collection_date_iso, metadata.shift, metadata.genotype)
        genotype_stats = stats_by_date_shift_genotype.get(genotype_key)
        if genotype_stats is None:
            genotype_stats = RunningBandStats.create(len(optimal_bands))
            stats_by_date_shift_genotype[genotype_key] = genotype_stats
        genotype_stats.add(spectral_slice)

    return (
        stats_by_date_shift,
        stats_by_date_shift_genotype,
        available_dates,
        available_genotypes,
    )


def build_comparison_tables(
    optimal_bands: list[OptimalBand],
    stats_by_date_shift: dict[tuple[str, str], RunningBandStats],
    selected_dates: list[str],
) -> tuple[list[DateComparison], list[list[object]]]:
    comparison_rows: list[list[object]] = []
    summaries: list[DateComparison] = []

    for date_iso in selected_dates:
        morning_stats = stats_by_date_shift.get((date_iso, "manha"))
        afternoon_stats = stats_by_date_shift.get((date_iso, "tarde"))
        if morning_stats is None or afternoon_stats is None:
            raise ValueError(
                f"Missing morning or afternoon samples for {date_iso}. "
                "Only dates with both shifts can be compared."
            )

        morning_mean = morning_stats.mean()
        afternoon_mean = afternoon_stats.mean()
        morning_std = morning_stats.std()
        afternoon_std = afternoon_stats.std()
        diff = morning_mean - afternoon_mean
        abs_diff = np.abs(diff)

        pearson_r, pearson_p_value = pearsonr(morning_mean, afternoon_mean)
        top_index = int(np.argmax(abs_diff))
        summaries.append(
            DateComparison(
                date_iso=date_iso,
                date_label=format_date_label(date_iso),
                morning_count=morning_stats.count,
                afternoon_count=afternoon_stats.count,
                pearson_r=float(pearson_r),
                pearson_p_value=float(pearson_p_value),
                mean_abs_diff=float(np.mean(abs_diff)),
                rmse=float(np.sqrt(np.mean(diff * diff))),
                top_abs_diff_band=optimal_bands[top_index].wavelength,
                top_abs_diff_value=float(diff[top_index]),
            )
        )

        for index, band in enumerate(optimal_bands):
            pct_diff = float("nan")
            if not math.isclose(morning_mean[index], 0.0, abs_tol=1e-12):
                pct_diff = (diff[index] / morning_mean[index]) * 100.0

            comparison_rows.append(
                [
                    date_iso,
                    format_date_label(date_iso),
                    band.source_rank,
                    band.class_rank if band.class_rank is not None else "",
                    band.direction_label,
                    band.wavelength,
                    morning_stats.count,
                    afternoon_stats.count,
                    float(morning_mean[index]),
                    float(afternoon_mean[index]),
                    float(morning_std[index]),
                    float(afternoon_std[index]),
                    float(diff[index]),
                    float(abs_diff[index]),
                    pct_diff,
                    band.vip if band.vip is not None else "",
                    band.cohen_d if band.cohen_d is not None else "",
                    band.q_value if band.q_value is not None else "",
                    band.combined_score if band.combined_score is not None else "",
                ]
            )

    return summaries, comparison_rows


def build_genotype_comparison_tables(
    optimal_bands: list[OptimalBand],
    stats_by_date_shift_genotype: dict[tuple[str, str, str], RunningBandStats],
    selected_dates: list[str],
    genotypes: list[str],
) -> tuple[list[GenotypeComparison], list[list[object]]]:
    comparison_rows: list[list[object]] = []
    summaries: list[GenotypeComparison] = []

    for genotype in genotypes:
        for date_iso in selected_dates:
            morning_stats = stats_by_date_shift_genotype.get((date_iso, "manha", genotype))
            afternoon_stats = stats_by_date_shift_genotype.get((date_iso, "tarde", genotype))
            if morning_stats is None or afternoon_stats is None:
                raise ValueError(
                    f"Missing morning or afternoon samples for genotype {genotype} on {date_iso}."
                )

            morning_mean = morning_stats.mean()
            afternoon_mean = afternoon_stats.mean()
            morning_std = morning_stats.std()
            afternoon_std = afternoon_stats.std()
            diff = morning_mean - afternoon_mean
            abs_diff = np.abs(diff)

            pearson_r, pearson_p_value = pearsonr(morning_mean, afternoon_mean)
            top_index = int(np.argmax(abs_diff))
            summaries.append(
                GenotypeComparison(
                    genotype=genotype,
                    date_iso=date_iso,
                    date_label=format_date_label(date_iso),
                    morning_count=morning_stats.count,
                    afternoon_count=afternoon_stats.count,
                    pearson_r=float(pearson_r),
                    pearson_p_value=float(pearson_p_value),
                    mean_abs_diff=float(np.mean(abs_diff)),
                    rmse=float(np.sqrt(np.mean(diff * diff))),
                    top_abs_diff_band=optimal_bands[top_index].wavelength,
                    top_abs_diff_value=float(diff[top_index]),
                )
            )

            for index, band in enumerate(optimal_bands):
                pct_diff = float("nan")
                if not math.isclose(morning_mean[index], 0.0, abs_tol=1e-12):
                    pct_diff = (diff[index] / morning_mean[index]) * 100.0

                comparison_rows.append(
                    [
                        genotype,
                        date_iso,
                        format_date_label(date_iso),
                        band.source_rank,
                        band.class_rank if band.class_rank is not None else "",
                        band.direction_label,
                        band.wavelength,
                        morning_stats.count,
                        afternoon_stats.count,
                        float(morning_mean[index]),
                        float(afternoon_mean[index]),
                        float(morning_std[index]),
                        float(afternoon_std[index]),
                        float(diff[index]),
                        float(abs_diff[index]),
                        pct_diff,
                        band.vip if band.vip is not None else "",
                        band.cohen_d if band.cohen_d is not None else "",
                        band.q_value if band.q_value is not None else "",
                        band.combined_score if band.combined_score is not None else "",
                    ]
                )

    return summaries, comparison_rows


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def build_plot_order(optimal_bands: list[OptimalBand]) -> np.ndarray:
    wavelengths = np.asarray([band.wavelength for band in optimal_bands], dtype=np.int32)
    return np.argsort(wavelengths)


def plot_comparisons(
    path: Path,
    optimal_bands: list[OptimalBand],
    stats_by_date_shift: dict[tuple[str, str], RunningBandStats],
    summaries: list[DateComparison],
) -> None:
    plot_order = build_plot_order(optimal_bands)
    sorted_wavelengths = np.asarray([optimal_bands[index].wavelength for index in plot_order], dtype=np.int32)
    scatter_colors = [
        DIRECTION_COLORS.get(optimal_bands[index].direction_label, "#4b5563")
        for index in range(len(optimal_bands))
    ]

    fig, axes = plt.subplots(
        len(summaries),
        2,
        figsize=(14, max(4.6 * len(summaries), 5.0)),
        constrained_layout=True,
        squeeze=False,
    )

    for row_index, summary in enumerate(summaries):
        line_ax = axes[row_index, 0]
        scatter_ax = axes[row_index, 1]

        morning_mean = stats_by_date_shift[(summary.date_iso, "manha")].mean()
        afternoon_mean = stats_by_date_shift[(summary.date_iso, "tarde")].mean()
        ordered_morning = morning_mean[plot_order]
        ordered_afternoon = afternoon_mean[plot_order]

        line_ax.plot(
            sorted_wavelengths,
            ordered_morning,
            marker="o",
            markersize=4.0,
            linewidth=1.7,
            color=SHIFT_COLORS["manha"],
            label="manha",
        )
        line_ax.plot(
            sorted_wavelengths,
            ordered_afternoon,
            marker="s",
            markersize=4.0,
            linewidth=1.7,
            color=SHIFT_COLORS["tarde"],
            label="tarde",
        )
        line_ax.set_title(
            f"{summary.date_label} | reflectancia media nas bandas otimas"
        )
        line_ax.set_xlabel("Comprimento de onda (nm)")
        line_ax.set_ylabel("Reflectancia media")
        line_ax.grid(alpha=0.2)
        line_ax.legend(loc="best")

        scatter_ax.scatter(
            morning_mean,
            afternoon_mean,
            s=42,
            c=scatter_colors,
            alpha=0.92,
            edgecolor="#111827",
            linewidth=0.35,
        )
        lower = float(min(np.min(morning_mean), np.min(afternoon_mean)))
        upper = float(max(np.max(morning_mean), np.max(afternoon_mean)))
        padding = (upper - lower) * 0.05 if not math.isclose(upper, lower) else 0.02
        line_values = [lower - padding, upper + padding]
        scatter_ax.plot(line_values, line_values, linestyle="--", linewidth=1.0, color="#111827", alpha=0.55)
        scatter_ax.set_xlim(line_values)
        scatter_ax.set_ylim(line_values)
        scatter_ax.set_xlabel("Reflectancia media - manha")
        scatter_ax.set_ylabel("Reflectancia media - tarde")
        scatter_ax.set_title(
            f"{summary.date_label} | Pearson r={summary.pearson_r:.6f}"
        )
        scatter_ax.grid(alpha=0.2)

        for band, x_value, y_value in zip(optimal_bands, morning_mean, afternoon_mean, strict=False):
            scatter_ax.annotate(
                str(band.wavelength),
                (x_value, y_value),
                xytext=(4, 3),
                textcoords="offset points",
                fontsize=6.5,
                color="#111827",
            )

        scatter_ax.text(
            0.03,
            0.97,
            (
                f"p={summary.pearson_p_value:.3e}\n"
                f"MAD={summary.mean_abs_diff:.6f}\n"
                f"RMSE={summary.rmse:.6f}"
            ),
            transform=scatter_ax.transAxes,
            va="top",
            ha="left",
            fontsize=8.5,
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8, "edgecolor": "#d1d5db"},
        )

    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_comparisons_by_genotype(
    path: Path,
    optimal_bands: list[OptimalBand],
    stats_by_date_shift_genotype: dict[tuple[str, str, str], RunningBandStats],
    summaries: list[GenotypeComparison],
) -> None:
    plot_order = build_plot_order(optimal_bands)
    sorted_wavelengths = np.asarray(
        [optimal_bands[index].wavelength for index in plot_order],
        dtype=np.int32,
    )
    scatter_colors = [
        DIRECTION_COLORS.get(optimal_bands[index].direction_label, "#4b5563")
        for index in range(len(optimal_bands))
    ]

    fig, axes = plt.subplots(
        len(summaries),
        2,
        figsize=(14, max(4.4 * len(summaries), 5.0)),
        constrained_layout=True,
        squeeze=False,
    )

    for row_index, summary in enumerate(summaries):
        line_ax = axes[row_index, 0]
        scatter_ax = axes[row_index, 1]

        morning_mean = stats_by_date_shift_genotype[(summary.date_iso, "manha", summary.genotype)].mean()
        afternoon_mean = stats_by_date_shift_genotype[(summary.date_iso, "tarde", summary.genotype)].mean()
        ordered_morning = morning_mean[plot_order]
        ordered_afternoon = afternoon_mean[plot_order]

        line_ax.plot(
            sorted_wavelengths,
            ordered_morning,
            marker="o",
            markersize=4.0,
            linewidth=1.7,
            color=SHIFT_COLORS["manha"],
            label="manha",
        )
        line_ax.plot(
            sorted_wavelengths,
            ordered_afternoon,
            marker="s",
            markersize=4.0,
            linewidth=1.7,
            color=SHIFT_COLORS["tarde"],
            label="tarde",
        )
        line_ax.set_title(
            f"{summary.genotype} | {summary.date_label} | reflectancia media nas bandas otimas"
        )
        line_ax.set_xlabel("Comprimento de onda (nm)")
        line_ax.set_ylabel("Reflectancia media")
        line_ax.grid(alpha=0.2)
        line_ax.legend(loc="best")

        scatter_ax.scatter(
            morning_mean,
            afternoon_mean,
            s=42,
            c=scatter_colors,
            alpha=0.92,
            edgecolor="#111827",
            linewidth=0.35,
        )
        lower = float(min(np.min(morning_mean), np.min(afternoon_mean)))
        upper = float(max(np.max(morning_mean), np.max(afternoon_mean)))
        padding = (upper - lower) * 0.05 if not math.isclose(upper, lower) else 0.02
        line_values = [lower - padding, upper + padding]
        scatter_ax.plot(line_values, line_values, linestyle="--", linewidth=1.0, color="#111827", alpha=0.55)
        scatter_ax.set_xlim(line_values)
        scatter_ax.set_ylim(line_values)
        scatter_ax.set_xlabel("Reflectancia media - manha")
        scatter_ax.set_ylabel("Reflectancia media - tarde")
        scatter_ax.set_title(
            f"{summary.genotype} | {summary.date_label} | Pearson r={summary.pearson_r:.6f}"
        )
        scatter_ax.grid(alpha=0.2)

        for band, x_value, y_value in zip(optimal_bands, morning_mean, afternoon_mean, strict=False):
            scatter_ax.annotate(
                str(band.wavelength),
                (x_value, y_value),
                xytext=(4, 3),
                textcoords="offset points",
                fontsize=6.5,
                color="#111827",
            )

        scatter_ax.text(
            0.03,
            0.97,
            (
                f"p={summary.pearson_p_value:.3e}\n"
                f"MAD={summary.mean_abs_diff:.6f}\n"
                f"RMSE={summary.rmse:.6f}"
            ),
            transform=scatter_ax.transAxes,
            va="top",
            ha="left",
            fontsize=8.5,
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8, "edgecolor": "#d1d5db"},
        )

    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_summary_markdown(
    path: Path,
    *,
    workbook_path: Path,
    optimal_bands_path: Path,
    optimal_bands: list[OptimalBand],
    summaries: list[DateComparison],
    comparison_rows: list[list[object]],
) -> None:
    lines = [
        "# Correlacao de Pearson nas bandas otimas",
        "",
        f"- Base de reflectancia usada: `{workbook_path.name}`",
        f"- Bandas otimas usadas: `{optimal_bands_path.name}`",
        f"- Total de bandas comparadas: {len(optimal_bands)}",
        "- Turnos comparados: manha vs tarde",
        "- Observacao: esta analise usa reflectancia bruta da planilha original, nao o sinal processado SNV + Savitzky-Golay + 1a derivada.",
        "",
        "## Resumo por data",
        "",
        "| data | n manha | n tarde | Pearson r | p-value | MAD | RMSE | maior diferenca |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    rows_by_date: dict[str, list[list[object]]] = {}
    for row in comparison_rows:
        rows_by_date.setdefault(str(row[0]), []).append(row)

    for summary in summaries:
        lines.append(
            f"| {summary.date_label} | {summary.morning_count} | {summary.afternoon_count} | "
            f"{summary.pearson_r:.6f} | {summary.pearson_p_value:.3e} | {summary.mean_abs_diff:.6f} | "
            f"{summary.rmse:.6f} | banda {summary.top_abs_diff_band} ({summary.top_abs_diff_value:+.6f}) |"
        )

    lines.extend(
        [
            "",
            "## Bandas otimas utilizadas",
            "",
            "| ordem global | rank na classe | classe dominante | banda | VIP | Cohen's d | q-value | score combinado |",
            "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for band in optimal_bands:
        vip_text = "" if band.vip is None else f"{band.vip:.4f}"
        d_text = "" if band.cohen_d is None else f"{band.cohen_d:.4f}"
        q_text = "" if band.q_value is None else f"{band.q_value:.3e}"
        score_text = "" if band.combined_score is None else f"{band.combined_score:.4f}"
        class_rank_text = "" if band.class_rank is None else str(band.class_rank)
        lines.append(
            f"| {band.source_rank} | {class_rank_text} | {band.direction_label} | {band.wavelength} | "
            f"{vip_text} | {d_text} | {q_text} | {score_text} |"
        )

    for summary in summaries:
        date_rows = sorted(rows_by_date[summary.date_iso], key=lambda row: float(row[13]), reverse=True)
        lines.extend(
            [
                "",
                f"## Maiores diferencas absolutas em {summary.date_label}",
                "",
                "| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |",
                "| ---: | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in date_rows[:5]:
            lines.append(
                f"| {int(row[5])} | {row[4]} | {float(row[8]):.6f} | {float(row[9]):.6f} | "
                f"{float(row[12]):+.6f} | {float(row[13]):.6f} |"
            )

    lines.extend(
        [
            "",
            "## Leitura rapida",
            "",
            "- Pearson foi calculado entre os vetores de reflectancia media das bandas otimas, comparando manha e tarde em cada data.",
            "- r proximo de 1 indica que o perfil espectral medio entre manha e tarde manteve a mesma forma nas bandas selecionadas.",
            "- MAD e RMSE ajudam a separar semelhanca de forma da magnitude das diferencas absolutas de reflectancia.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_genotype_summary_markdown(
    path: Path,
    *,
    workbook_path: Path,
    optimal_bands_path: Path,
    optimal_bands: list[OptimalBand],
    summaries: list[GenotypeComparison],
    comparison_rows: list[list[object]],
) -> None:
    lines = [
        "# Correlacao de Pearson nas bandas otimas por genotipo",
        "",
        f"- Base de reflectancia usada: `{workbook_path.name}`",
        f"- Bandas otimas usadas: `{optimal_bands_path.name}`",
        f"- Total de bandas comparadas: {len(optimal_bands)}",
        "- Comparacao realizada por genotipo, sempre entre manha e tarde na mesma data.",
        "- Observacao: esta analise usa reflectancia bruta da planilha original, nao o sinal processado SNV + Savitzky-Golay + 1a derivada.",
        "",
        "## Resumo por genotipo e data",
        "",
        "| genotipo | data | n manha | n tarde | Pearson r | p-value | MAD | RMSE | maior diferenca |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    rows_by_group: dict[tuple[str, str], list[list[object]]] = {}
    for row in comparison_rows:
        rows_by_group.setdefault((str(row[0]), str(row[1])), []).append(row)

    for summary in summaries:
        lines.append(
            f"| {summary.genotype} | {summary.date_label} | {summary.morning_count} | {summary.afternoon_count} | "
            f"{summary.pearson_r:.6f} | {summary.pearson_p_value:.3e} | {summary.mean_abs_diff:.6f} | "
            f"{summary.rmse:.6f} | banda {summary.top_abs_diff_band} ({summary.top_abs_diff_value:+.6f}) |"
        )

    lines.extend(
        [
            "",
            "## Bandas otimas utilizadas",
            "",
            "| ordem global | rank na classe | classe dominante | banda | VIP | Cohen's d | q-value | score combinado |",
            "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for band in optimal_bands:
        vip_text = "" if band.vip is None else f"{band.vip:.4f}"
        d_text = "" if band.cohen_d is None else f"{band.cohen_d:.4f}"
        q_text = "" if band.q_value is None else f"{band.q_value:.3e}"
        score_text = "" if band.combined_score is None else f"{band.combined_score:.4f}"
        class_rank_text = "" if band.class_rank is None else str(band.class_rank)
        lines.append(
            f"| {band.source_rank} | {class_rank_text} | {band.direction_label} | {band.wavelength} | "
            f"{vip_text} | {d_text} | {q_text} | {score_text} |"
        )

    current_genotype: str | None = None
    for summary in summaries:
        if summary.genotype != current_genotype:
            current_genotype = summary.genotype
            lines.extend(
                [
                    "",
                    f"## {summary.genotype}",
                    "",
                ]
            )

        date_rows = sorted(
            rows_by_group[(summary.genotype, summary.date_iso)],
            key=lambda row: float(row[14]),
            reverse=True,
        )
        lines.extend(
            [
                f"### {summary.date_label}",
                "",
                "| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |",
                "| ---: | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in date_rows[:5]:
            lines.append(
                f"| {int(row[6])} | {row[5]} | {float(row[9]):.6f} | {float(row[10]):.6f} | "
                f"{float(row[13]):+.6f} | {float(row[14]):.6f} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Leitura rapida",
            "",
            "- Pearson foi calculado separadamente em cada genotipo, usando os vetores de reflectancia media das bandas otimas.",
            "- Isso mostra se o padrao manha vs tarde se mantem igualmente para BR16, CD202 e EMB48.",
            "- MAD e RMSE continuam sendo medidas de diferenca absoluta, mesmo quando r permanece muito alto.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    workbook_path = args.input.resolve()
    optimal_bands_path = args.optimal_bands_csv.resolve()
    output_dir = args.output_dir.resolve()
    selected_dates = [parse_date_token(token) for token in args.dates]

    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")
    if not optimal_bands_path.exists():
        raise FileNotFoundError(f"Optimal-band CSV not found: {optimal_bands_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    optimal_bands = load_optimal_bands(optimal_bands_path)
    (
        stats_by_date_shift,
        stats_by_date_shift_genotype,
        available_dates,
        available_genotypes,
    ) = collect_group_stats(
        workbook_path,
        optimal_bands,
        selected_dates,
    )

    missing_dates = [date_iso for date_iso in selected_dates if date_iso not in available_dates]
    if missing_dates:
        raise ValueError(
            "Requested dates are not present in the workbook: "
            + ", ".join(missing_dates)
            + ". Available dates: "
            + ", ".join(sorted(available_dates))
        )

    summaries, comparison_rows = build_comparison_tables(
        optimal_bands,
        stats_by_date_shift,
        selected_dates,
    )
    ordered_genotypes = sorted(
        available_genotypes,
        key=lambda genotype: (GENOTYPE_ORDER.get(genotype, 999), genotype),
    )
    genotype_summaries, genotype_comparison_rows = build_genotype_comparison_tables(
        optimal_bands,
        stats_by_date_shift_genotype,
        selected_dates,
        ordered_genotypes,
    )

    summary_csv_path = output_dir / "pearson_bandas_otimas_turno.csv"
    comparison_csv_path = output_dir / "comparacao_reflectancia_bandas_otimas_turno.csv"
    summary_md_path = output_dir / "resumo_pearson_bandas_otimas_turno.md"
    plot_path = output_dir / "comparacao_bandas_otimas_turno.svg"
    genotype_summary_csv_path = output_dir / "pearson_bandas_otimas_turno_por_genotipo.csv"
    genotype_comparison_csv_path = output_dir / "comparacao_reflectancia_bandas_otimas_turno_por_genotipo.csv"
    genotype_summary_md_path = output_dir / "resumo_pearson_bandas_otimas_turno_por_genotipo.md"
    genotype_plot_path = output_dir / "comparacao_bandas_otimas_turno_por_genotipo.svg"

    write_csv(
        summary_csv_path,
        [
            "date_iso",
            "date_label",
            "morning_count",
            "afternoon_count",
            "pearson_r",
            "pearson_p_value",
            "mean_abs_diff",
            "rmse",
            "top_abs_diff_band",
            "top_abs_diff_value",
        ],
        [
            [
                item.date_iso,
                item.date_label,
                item.morning_count,
                item.afternoon_count,
                item.pearson_r,
                item.pearson_p_value,
                item.mean_abs_diff,
                item.rmse,
                item.top_abs_diff_band,
                item.top_abs_diff_value,
            ]
            for item in summaries
        ],
    )
    write_csv(
        comparison_csv_path,
        [
            "date_iso",
            "date_label",
            "source_rank",
            "class_rank",
            "direction_label",
            "wavelength",
            "morning_count",
            "afternoon_count",
            "morning_mean_reflectance",
            "afternoon_mean_reflectance",
            "morning_std_reflectance",
            "afternoon_std_reflectance",
            "diff_morning_minus_afternoon",
            "abs_diff",
            "pct_diff_vs_morning",
            "vip",
            "cohen_d",
            "q_value",
            "combined_score",
        ],
        comparison_rows,
    )
    write_summary_markdown(
        summary_md_path,
        workbook_path=workbook_path,
        optimal_bands_path=optimal_bands_path,
        optimal_bands=optimal_bands,
        summaries=summaries,
        comparison_rows=comparison_rows,
    )
    plot_comparisons(plot_path, optimal_bands, stats_by_date_shift, summaries)
    write_csv(
        genotype_summary_csv_path,
        [
            "genotype",
            "date_iso",
            "date_label",
            "morning_count",
            "afternoon_count",
            "pearson_r",
            "pearson_p_value",
            "mean_abs_diff",
            "rmse",
            "top_abs_diff_band",
            "top_abs_diff_value",
        ],
        [
            [
                item.genotype,
                item.date_iso,
                item.date_label,
                item.morning_count,
                item.afternoon_count,
                item.pearson_r,
                item.pearson_p_value,
                item.mean_abs_diff,
                item.rmse,
                item.top_abs_diff_band,
                item.top_abs_diff_value,
            ]
            for item in genotype_summaries
        ],
    )
    write_csv(
        genotype_comparison_csv_path,
        [
            "genotype",
            "date_iso",
            "date_label",
            "source_rank",
            "class_rank",
            "direction_label",
            "wavelength",
            "morning_count",
            "afternoon_count",
            "morning_mean_reflectance",
            "afternoon_mean_reflectance",
            "morning_std_reflectance",
            "afternoon_std_reflectance",
            "diff_morning_minus_afternoon",
            "abs_diff",
            "pct_diff_vs_morning",
            "vip",
            "cohen_d",
            "q_value",
            "combined_score",
        ],
        genotype_comparison_rows,
    )
    write_genotype_summary_markdown(
        genotype_summary_md_path,
        workbook_path=workbook_path,
        optimal_bands_path=optimal_bands_path,
        optimal_bands=optimal_bands,
        summaries=genotype_summaries,
        comparison_rows=genotype_comparison_rows,
    )
    plot_comparisons_by_genotype(
        genotype_plot_path,
        optimal_bands,
        stats_by_date_shift_genotype,
        genotype_summaries,
    )

    print(f"Raw workbook: {workbook_path}")
    print(f"Optimal bands: {optimal_bands_path}")
    print(f"Dates analyzed: {', '.join(selected_dates)}")
    print(f"Genotypes analyzed: {', '.join(ordered_genotypes)}")
    print("Outputs:")
    print(f"  - {summary_csv_path}")
    print(f"  - {comparison_csv_path}")
    print(f"  - {summary_md_path}")
    print(f"  - {plot_path}")
    print(f"  - {genotype_summary_csv_path}")
    print(f"  - {genotype_comparison_csv_path}")
    print(f"  - {genotype_summary_md_path}")
    print(f"  - {genotype_plot_path}")


if __name__ == "__main__":
    main()
