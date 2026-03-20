#!/usr/bin/env python3
"""Generate grouped plots for the processed dataset."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from generate_descriptive_stats import RunningStats, format_number, write_csv
from generate_output_plots import (
    CONDITION_ORDER,
    GENOTYPE_ORDER,
    CountRecord,
    SpectralRecord,
    create_line_chart_by_date,
    create_line_chart_by_genotype,
    create_sample_count_chart,
    write_index_html,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate grouped mean/CV plots for the processed dataset."
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
        help="Normalized metadata aligned with the processed dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft/plots"),
        help="Directory where plot files and grouped CSVs will be written.",
    )
    return parser.parse_args()


def build_grouped_records(
    processed_csv_path: Path,
    metadata_csv_path: Path,
) -> tuple[list[float], list[SpectralRecord], list[SpectralRecord], list[CountRecord]]:
    with metadata_csv_path.open("r", encoding="utf-8", newline="") as metadata_handle:
        metadata_reader = csv.DictReader(metadata_handle)
        metadata_rows = list(metadata_reader)

    with processed_csv_path.open("r", encoding="utf-8", newline="") as processed_handle:
        processed_reader = csv.reader(processed_handle)
        header = next(processed_reader)
        wavelengths = [float(value) for value in header[6:]]

        stats_by_group: dict[tuple[str, str, str], RunningStats] = {}
        counts_by_group: dict[tuple[str, str, str], int] = {}

        for row_index, row in enumerate(processed_reader, start=0):
            if row_index >= len(metadata_rows):
                raise ValueError(
                    "Processed CSV contains more rows than the normalized metadata file."
                )

            metadata = metadata_rows[row_index]
            if row[0] != metadata["nomenclaura"]:
                raise ValueError(
                    "Processed CSV and normalized metadata file are misaligned at "
                    f"row {row_index + 2}: {row[0]!r} != {metadata['nomenclaura']!r}"
                )

            group_key = (
                metadata["data_coleta_iso"],
                metadata["genotipo_normalizado"],
                metadata["condicao_normalizada"],
            )
            values = [float(value) for value in row[6:]]

            stats = stats_by_group.get(group_key)
            if stats is None:
                stats = RunningStats.create(len(values))
                stats_by_group[group_key] = stats
                counts_by_group[group_key] = 0
            stats.add(values)
            counts_by_group[group_key] += 1

        if len(metadata_rows) != row_index + 1:
            raise ValueError(
                "Normalized metadata file contains more rows than the processed CSV."
            )

    sorted_keys = sorted(
        stats_by_group,
        key=lambda key: (
            key[0],
            GENOTYPE_ORDER[key[1]],
            CONDITION_ORDER[key[2]],
        ),
    )

    mean_records: list[SpectralRecord] = []
    cv_records: list[SpectralRecord] = []
    count_records: list[CountRecord] = []

    for date_iso, genotype, condition in sorted_keys:
        stats = stats_by_group[(date_iso, genotype, condition)]
        count = counts_by_group[(date_iso, genotype, condition)]
        mean_records.append(
            SpectralRecord(
                date=date_iso,
                genotype=genotype,
                condition=condition,
                n_samples=count,
                values=stats.mean_values(),
            )
        )
        cv_records.append(
            SpectralRecord(
                date=date_iso,
                genotype=genotype,
                condition=condition,
                n_samples=count,
                values=stats.cv_values(),
            )
        )
        count_records.append(
            CountRecord(
                date=date_iso,
                genotype=genotype,
                condition=condition,
                n_samples=count,
            )
        )

    return wavelengths, mean_records, cv_records, count_records


def record_rows(records: list[SpectralRecord]) -> list[list[str]]:
    rows: list[list[str]] = []
    for record in records:
        row = [
            record.date,
            record.genotype,
            record.condition,
            str(record.n_samples),
        ]
        row.extend(format_number(value) for value in record.values)
        rows.append(row)
    return rows


def count_rows(records: list[CountRecord]) -> list[list[str]]:
    return [
        [record.date, record.genotype, record.condition, str(record.n_samples)]
        for record in records
    ]


def quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute quantile from an empty sequence.")
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]
    position = (len(sorted_values) - 1) * q
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return sorted_values[lower_index]
    weight = position - lower_index
    return (
        sorted_values[lower_index] * (1.0 - weight)
        + sorted_values[upper_index] * weight
    )


def clipped_records_for_plot(
    records: list[SpectralRecord],
    *,
    lower_quantile: float,
    upper_quantile: float,
) -> list[SpectralRecord]:
    finite_values = sorted(
        value
        for record in records
        for value in record.values
        if math.isfinite(value)
    )
    if not finite_values:
        return records

    lower_bound = quantile(finite_values, lower_quantile)
    upper_bound = quantile(finite_values, upper_quantile)

    clipped: list[SpectralRecord] = []
    for record in records:
        clipped_values = []
        for value in record.values:
            if not math.isfinite(value):
                clipped_values.append(value)
            elif value < lower_bound:
                clipped_values.append(lower_bound)
            elif value > upper_bound:
                clipped_values.append(upper_bound)
            else:
                clipped_values.append(value)
        clipped.append(
            SpectralRecord(
                date=record.date,
                genotype=record.genotype,
                condition=record.condition,
                n_samples=record.n_samples,
                values=clipped_values,
            )
        )
    return clipped


def main() -> None:
    args = parse_args()
    processed_csv_path = args.processed_csv.resolve()
    metadata_csv_path = args.metadata_csv.resolve()
    output_dir = args.output_dir.resolve()

    if not processed_csv_path.exists():
        raise FileNotFoundError(f"Processed CSV not found: {processed_csv_path}")
    if not metadata_csv_path.exists():
        raise FileNotFoundError(f"Metadata CSV not found: {metadata_csv_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    wavelengths, mean_records, cv_records, count_records = build_grouped_records(
        processed_csv_path,
        metadata_csv_path,
    )
    cv_plot_records = clipped_records_for_plot(
        cv_records,
        lower_quantile=0.02,
        upper_quantile=0.98,
    )

    common_header = [
        "data_coleta",
        "genotipo",
        "condicao",
        "n_amostras",
        *[str(int(value)) for value in wavelengths],
    ]

    mean_csv_path = output_dir / "media_processada_por_grupo.csv"
    cv_csv_path = output_dir / "coef_var_processado_por_grupo.csv"
    count_csv_path = output_dir / "amostras_processadas_por_grupo.csv"

    write_csv(mean_csv_path, common_header, record_rows(mean_records))
    write_csv(cv_csv_path, common_header, record_rows(cv_records))
    write_csv(
        count_csv_path,
        ["data_coleta", "genotipo", "condicao", "n_amostras"],
        count_rows(count_records),
    )

    media_por_data = output_dir / "media_processada_por_data.svg"
    media_por_genotipo = output_dir / "media_processada_por_genotipo.svg"
    cv_por_data = output_dir / "coef_var_processado_por_data.svg"
    cv_por_genotipo = output_dir / "coef_var_processado_por_genotipo.svg"
    amostras = output_dir / "amostras_processadas_por_grupo.svg"

    create_line_chart_by_date(
        wavelengths,
        mean_records,
        metric_label="Media processada",
        y_label="Media processada",
        output_path=media_por_data,
    )
    create_line_chart_by_genotype(
        wavelengths,
        mean_records,
        metric_label="Media processada",
        y_label="Media processada",
        output_path=media_por_genotipo,
    )
    create_line_chart_by_date(
        wavelengths,
        cv_plot_records,
        metric_label="Coeficiente de variacao processado (escala robusta)",
        y_label="CV processado (%)",
        output_path=cv_por_data,
    )
    create_line_chart_by_genotype(
        wavelengths,
        cv_plot_records,
        metric_label="Coeficiente de variacao processado (escala robusta)",
        y_label="CV processado (%)",
        output_path=cv_por_genotipo,
    )
    create_sample_count_chart(count_records, amostras)

    index_files = [
        ("Media processada por data", media_por_data.name),
        ("Media processada por genotipo", media_por_genotipo.name),
        ("Coeficiente de variacao processado por data", cv_por_data.name),
        ("Coeficiente de variacao processado por genotipo", cv_por_genotipo.name),
        ("Amostras processadas por grupo", amostras.name),
    ]
    write_index_html(output_dir, index_files)

    print(f"Plots directory: {output_dir}")
    print(f"  - {mean_csv_path}")
    print(f"  - {cv_csv_path}")
    print(f"  - {count_csv_path}")
    print(f"  - {media_por_data}")
    print(f"  - {media_por_genotipo}")
    print(f"  - {cv_por_data}")
    print(f"  - {cv_por_genotipo}")
    print(f"  - {amostras}")
    print(f"  - {output_dir / 'index.html'}")


if __name__ == "__main__":
    main()
