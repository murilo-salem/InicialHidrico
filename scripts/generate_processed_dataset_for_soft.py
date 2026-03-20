#!/usr/bin/env python3
"""Apply SNV + Savitzky-Golay first derivative to the spectral dataset."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

from generate_descriptive_stats import META_COLUMNS, format_number, iter_sheet_rows, normalize_metadata


@dataclass
class ProcessingSummary:
    input_path: Path
    output_dir: Path
    processed_csv_path: Path
    normalized_metadata_path: Path
    summary_markdown_path: Path
    sample_count: int
    wavelength_headers: list[str]
    window_length: int
    polyorder: int
    deriv: int
    delta: float
    padding_mode: str
    normalized_filename_typos: int
    processed_min: float
    processed_max: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a processed dataset for the soft using SNV + "
            "Savitzky-Golay first derivative."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("base_dados_unificada.xlsx"),
        help="Path to the source workbook.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft"),
        help="Directory where the processed dataset will be written.",
    )
    parser.add_argument(
        "--window-length",
        type=int,
        default=11,
        help="Odd Savitzky-Golay window length.",
    )
    parser.add_argument(
        "--polyorder",
        type=int,
        default=2,
        help="Savitzky-Golay polynomial order.",
    )
    parser.add_argument(
        "--deriv",
        type=int,
        default=1,
        help="Derivative order.",
    )
    parser.add_argument(
        "--delta",
        type=float,
        default=1.0,
        help="Spacing between spectral variables.",
    )
    return parser.parse_args()


def validate_savgol_params(window_length: int, polyorder: int, deriv: int) -> None:
    if window_length < 3:
        raise ValueError("window_length must be at least 3.")
    if window_length % 2 == 0:
        raise ValueError("window_length must be odd.")
    if polyorder < 0:
        raise ValueError("polyorder must be non-negative.")
    if polyorder >= window_length:
        raise ValueError("polyorder must be smaller than window_length.")
    if deriv < 0:
        raise ValueError("deriv must be non-negative.")
    if deriv > polyorder:
        raise ValueError("deriv cannot be greater than polyorder.")


def transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix)]


def multiply_matrices(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    right_transposed = transpose(right)
    result: list[list[float]] = []
    for left_row in left:
        result_row: list[float] = []
        for right_column in right_transposed:
            result_row.append(sum(a * b for a, b in zip(left_row, right_column)))
        result.append(result_row)
    return result


def invert_matrix(matrix: list[list[float]]) -> list[list[float]]:
    size = len(matrix)
    augmented = [
        [float(value) for value in row] + [1.0 if row_index == col_index else 0.0 for col_index in range(size)]
        for row_index, row in enumerate(matrix)
    ]

    for pivot_index in range(size):
        pivot_row = max(range(pivot_index, size), key=lambda index: abs(augmented[index][pivot_index]))
        pivot_value = augmented[pivot_row][pivot_index]
        if math.isclose(pivot_value, 0.0, abs_tol=1e-12):
            raise ValueError("Matrix inversion failed while computing Savitzky-Golay coefficients.")
        if pivot_row != pivot_index:
            augmented[pivot_index], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_index]

        pivot_value = augmented[pivot_index][pivot_index]
        augmented[pivot_index] = [value / pivot_value for value in augmented[pivot_index]]

        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            augmented[row_index] = [
                current - factor * pivot
                for current, pivot in zip(augmented[row_index], augmented[pivot_index])
            ]

    return [row[size:] for row in augmented]


def savitzky_golay_coefficients(
    window_length: int,
    polyorder: int,
    deriv: int,
    delta: float,
) -> list[float]:
    half_window = window_length // 2
    design_matrix = [
        [float(offset ** power) for power in range(polyorder + 1)]
        for offset in range(-half_window, half_window + 1)
    ]
    transposed = transpose(design_matrix)
    gram_matrix = multiply_matrices(transposed, design_matrix)
    gram_inverse = invert_matrix(gram_matrix)
    pseudo_inverse = multiply_matrices(gram_inverse, transposed)
    scale_factor = math.factorial(deriv) / (delta ** deriv)
    return [value * scale_factor for value in pseudo_inverse[deriv]]


def mirror_index(index: int, size: int) -> int:
    if size <= 1:
        return 0
    while index < 0 or index >= size:
        if index < 0:
            index = -index
        if index >= size:
            index = (2 * size) - index - 2
    return index


def apply_snv(values: list[float]) -> list[float]:
    if not values:
        return []
    mean_value = sum(values) / len(values)
    if len(values) == 1:
        return [0.0]
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    standard_deviation = math.sqrt(variance)
    if math.isclose(standard_deviation, 0.0, abs_tol=1e-12):
        return [0.0 for _ in values]
    return [(value - mean_value) / standard_deviation for value in values]


def apply_savgol_filter(values: list[float], coefficients: list[float]) -> list[float]:
    half_window = len(coefficients) // 2
    filtered: list[float] = []
    for center_index in range(len(values)):
        accumulator = 0.0
        for coeff_index, coefficient in enumerate(coefficients):
            source_index = mirror_index(center_index + coeff_index - half_window, len(values))
            accumulator += coefficient * values[source_index]
        filtered.append(accumulator)
    return filtered


def write_summary_markdown(summary: ProcessingSummary) -> None:
    lines = [
        "# Resumo do processamento para o soft",
        "",
        f"- Arquivo de entrada: `{summary.input_path.name}`",
        f"- Pasta de saida: `{summary.output_dir.name}`",
        f"- Amostras processadas: {summary.sample_count}",
        f"- Comprimentos de onda processados: {len(summary.wavelength_headers)} (`{summary.wavelength_headers[0]}` a `{summary.wavelength_headers[-1]}`)",
        f"- Pipeline: `SNV -> Savitzky-Golay -> 1a derivada`",
        f"- Window length: {summary.window_length}",
        f"- Polyorder: {summary.polyorder}",
        f"- Derivada: {summary.deriv}",
        f"- Delta: {summary.delta}",
        f"- Padding na borda: `{summary.padding_mode}`",
        f"- Linhas com token `C202` normalizado em metadados auxiliares: {summary.normalized_filename_typos}",
        f"- Faixa dos valores processados: {summary.processed_min:.10f} a {summary.processed_max:.10f}",
        "",
        "## Arquivos gerados",
        "",
        f"- `{summary.processed_csv_path.name}`: dataset processado, preservando as colunas originais da planilha.",
        f"- `{summary.normalized_metadata_path.name}`: metadados auxiliares normalizados a partir de `nomenclaura`.",
        f"- `{summary.summary_markdown_path.name}`: este resumo.",
        "",
        "## Observacoes",
        "",
        "- O dataset processado manteve a ordem das linhas e o cabecalho original.",
        "- Apenas as colunas espectrais foram transformadas; os 6 metadados iniciais foram preservados como vieram da planilha.",
        "- Para agrupamentos confiaveis, use o arquivo auxiliar de metadados normalizados.",
    ]
    summary.summary_markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def process_dataset(
    input_path: Path,
    output_dir: Path,
    window_length: int,
    polyorder: int,
    deriv: int,
    delta: float,
) -> ProcessingSummary:
    output_dir.mkdir(parents=True, exist_ok=True)
    processed_csv_path = output_dir / "base_dados_unificada_snv_savgol_1deriv.csv"
    normalized_metadata_path = output_dir / "metadados_normalizados_soft.csv"
    summary_markdown_path = output_dir / "resumo_processamento_soft.md"

    coefficients = savitzky_golay_coefficients(
        window_length=window_length,
        polyorder=polyorder,
        deriv=deriv,
        delta=delta,
    )

    header: list[str | None] | None = None
    wavelength_headers: list[str] = []
    sample_count = 0
    normalized_filename_typos = 0
    processed_min = float("inf")
    processed_max = float("-inf")
    normalization_examples: list[tuple[int, str, str, str]] = []

    with processed_csv_path.open("w", encoding="utf-8", newline="") as processed_handle, normalized_metadata_path.open(
        "w", encoding="utf-8", newline=""
    ) as metadata_handle:
        processed_writer = csv.writer(processed_handle)
        metadata_writer = csv.writer(metadata_handle)
        metadata_writer.writerow(
            [
                "row_number",
                "nomenclaura",
                "bloco_normalizado",
                "genotipo_normalizado",
                "condicao_normalizada",
                "data_coleta_raw",
                "data_coleta_iso",
                "turno",
            ]
        )

        for row_number, row_values in iter_sheet_rows(input_path):
            if row_number == 1:
                header = row_values
                wavelength_headers = [str(value) for value in header[len(META_COLUMNS) :] if value]
                processed_writer.writerow(header)
                continue

            if header is None:
                raise ValueError("Header row was not found in the workbook.")

            if len(row_values) < len(header):
                row_values.extend([None] * (len(header) - len(row_values)))

            metadata = normalize_metadata(row_number, row_values, normalization_examples)
            sample_count += 1
            if "_C202_" in metadata.file_name:
                normalized_filename_typos += 1

            spectral_values: list[float] = []
            for value in row_values[len(META_COLUMNS) : len(META_COLUMNS) + len(wavelength_headers)]:
                if value is None:
                    raise ValueError(
                        f"Missing spectral value detected at row {row_number}; "
                        "the processing pipeline expects complete spectra."
                    )
                spectral_values.append(float(value))

            snv_values = apply_snv(spectral_values)
            processed_values = apply_savgol_filter(snv_values, coefficients)

            processed_min = min(processed_min, min(processed_values))
            processed_max = max(processed_max, max(processed_values))

            processed_row = [value or "" for value in row_values[: len(META_COLUMNS)]]
            processed_row.extend(format_number(value) for value in processed_values)
            processed_writer.writerow(processed_row)

            metadata_writer.writerow(
                [
                    row_number,
                    metadata.file_name,
                    metadata.block,
                    metadata.genotype,
                    metadata.condition_label,
                    metadata.collection_date_raw,
                    metadata.collection_date_iso,
                    metadata.shift,
                ]
            )

    summary = ProcessingSummary(
        input_path=input_path,
        output_dir=output_dir,
        processed_csv_path=processed_csv_path,
        normalized_metadata_path=normalized_metadata_path,
        summary_markdown_path=summary_markdown_path,
        sample_count=sample_count,
        wavelength_headers=wavelength_headers,
        window_length=window_length,
        polyorder=polyorder,
        deriv=deriv,
        delta=delta,
        padding_mode="mirror",
        normalized_filename_typos=normalized_filename_typos,
        processed_min=processed_min,
        processed_max=processed_max,
    )
    write_summary_markdown(summary)
    return summary


def main() -> None:
    args = parse_args()
    validate_savgol_params(args.window_length, args.polyorder, args.deriv)

    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Workbook not found: {input_path}")

    summary = process_dataset(
        input_path=input_path,
        output_dir=output_dir,
        window_length=args.window_length,
        polyorder=args.polyorder,
        deriv=args.deriv,
        delta=args.delta,
    )

    print(f"Input workbook: {summary.input_path}")
    print(f"Samples processed: {summary.sample_count}")
    print(f"Wavelength columns: {len(summary.wavelength_headers)}")
    print(f"Pipeline: SNV + Savitzky-Golay + {summary.deriv}a derivada")
    print("Outputs:")
    print(f"  - {summary.processed_csv_path}")
    print(f"  - {summary.normalized_metadata_path}")
    print(f"  - {summary.summary_markdown_path}")


if __name__ == "__main__":
    main()
