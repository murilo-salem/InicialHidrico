#!/usr/bin/env python3
"""Summarize recurring top PLSR bands for date x genotype x turno subsets."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


SHIFT_ORDER = {"manha": 0, "tarde": 1}
GENOTYPE_ORDER = {"BR16": 0, "CD202": 1, "EMB48": 2}
DIRECTION_ORDER = {"irrigado": 0, "nao_irrigado": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize recurrence and direction of top PLSR bands for "
            "date x genotype x turno subsets."
        )
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("dados_processados_soft/plsr_data_genotipo_turno/top_bandas_plsr_data_genotipo_turno.csv"),
        help="Input CSV with top PLSR bands per subset.",
    )
    parser.add_argument(
        "--metrics-csv",
        type=Path,
        default=Path("dados_processados_soft/plsr_data_genotipo_turno/metricas_plsr_data_genotipo_turno.csv"),
        help="Input CSV with subset-level PLSR metrics.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados_processados_soft/plsr_data_genotipo_turno"),
        help="Directory where summary outputs will be written.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, object]] = []
        for row in reader:
            rows.append(
                {
                    "data_coleta_iso": row["data_coleta_iso"],
                    "genotipo": row["genotipo"],
                    "turno": row["turno"],
                    "rank": int(row["rank"]),
                    "wavelength": int(row["wavelength"]),
                    "vip": float(row["vip"]),
                    "coefficient": float(row["coefficient"]),
                    "abs_coefficient": float(row["abs_coefficient"]),
                    "score": float(row["score"]),
                    "direction": row["direction"],
                }
            )
    if not rows:
        raise ValueError(f"Input CSV is empty: {path}")
    return rows


def read_metric_map(path: Path) -> dict[tuple[str, str, str], dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        metrics: dict[tuple[str, str, str], dict[str, object]] = {}
        for row in reader:
            key = (
                row["data_coleta_iso"],
                row["genotipo"],
                row["turno"],
            )
            metrics[key] = {
                "r2cv": float(row["r2cv"]),
                "rmsecv": float(row["rmsecv"]),
                "auc": float(row["auc"]),
                "accuracy": float(row["accuracy"]),
                "best_components": int(row["best_components"]),
            }
    if not metrics:
        raise ValueError(f"Metrics CSV is empty: {path}")
    return metrics


def write_dict_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def classify_spectral_range(wavelength: int) -> tuple[str, int, int]:
    if 350 <= wavelength <= 699:
        return "VIS", 350, 699
    if 700 <= wavelength <= 1300:
        return "NIR", 700, 1300
    if 1301 <= wavelength <= 1800:
        return "SWIR1", 1301, 1800
    if 1801 <= wavelength <= 2500:
        return "SWIR2", 1801, 2500
    return "OUT_OF_RANGE", -1, -1


def unique_subset_count(rows: list[dict[str, object]]) -> int:
    return len(
        {
            (
                str(row["data_coleta_iso"]),
                str(row["genotipo"]),
                str(row["turno"]),
            )
            for row in rows
        }
    )


def aggregate_global_recurrence(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["wavelength"])].append(row)

    subset_count = unique_subset_count(rows)
    result_rows: list[dict[str, object]] = []
    for wavelength, items in grouped.items():
        irrigado_count = sum(1 for item in items if item["direction"] == "irrigado")
        nao_irrigado_count = sum(1 for item in items if item["direction"] == "nao_irrigado")
        dominant_direction = "irrigado" if irrigado_count >= nao_irrigado_count else "nao_irrigado"
        result_rows.append(
            {
                "wavelength": wavelength,
                "occurrences": len(items),
                "subset_frequency": len(items) / subset_count,
                "mean_rank": sum(int(item["rank"]) for item in items) / len(items),
                "best_rank": min(int(item["rank"]) for item in items),
                "mean_vip": sum(float(item["vip"]) for item in items) / len(items),
                "mean_coefficient": sum(float(item["coefficient"]) for item in items) / len(items),
                "mean_abs_coefficient": sum(float(item["abs_coefficient"]) for item in items) / len(items),
                "mean_score": sum(float(item["score"]) for item in items) / len(items),
                "irrigado_count": irrigado_count,
                "nao_irrigado_count": nao_irrigado_count,
                "dominant_direction": dominant_direction,
            }
        )

    result_rows.sort(
        key=lambda item: (
            -int(item["occurrences"]),
            float(item["mean_rank"]),
            -float(item["mean_score"]),
            int(item["wavelength"]),
        )
    )
    return result_rows


def aggregate_direction_recurrence(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["direction"]), int(row["wavelength"]))].append(row)

    subset_count = unique_subset_count(rows)
    result_rows: list[dict[str, object]] = []
    for (direction, wavelength), items in grouped.items():
        result_rows.append(
            {
                "direction": direction,
                "wavelength": wavelength,
                "occurrences": len(items),
                "subset_frequency": len(items) / subset_count,
                "mean_rank": sum(int(item["rank"]) for item in items) / len(items),
                "best_rank": min(int(item["rank"]) for item in items),
                "mean_vip": sum(float(item["vip"]) for item in items) / len(items),
                "mean_coefficient": sum(float(item["coefficient"]) for item in items) / len(items),
                "mean_abs_coefficient": sum(float(item["abs_coefficient"]) for item in items) / len(items),
                "mean_score": sum(float(item["score"]) for item in items) / len(items),
            }
        )

    result_rows.sort(
        key=lambda item: (
            DIRECTION_ORDER.get(str(item["direction"]), 99),
            -int(item["occurrences"]),
            float(item["mean_rank"]),
            -float(item["mean_score"]),
            int(item["wavelength"]),
        )
    )
    return result_rows


def build_detail_rows(
    rows: list[dict[str, object]],
    metric_map: dict[tuple[str, str, str], dict[str, object]],
) -> list[dict[str, object]]:
    detail_rows: list[dict[str, object]] = []
    for row in rows:
        key = (
            str(row["data_coleta_iso"]),
            str(row["genotipo"]),
            str(row["turno"]),
        )
        if key not in metric_map:
            raise KeyError(f"Metrics not found for subset {key!r}")
        detail_row = dict(row)
        range_label, range_start, range_end = classify_spectral_range(int(row["wavelength"]))
        detail_row.update(metric_map[key])
        detail_row["range_label"] = range_label
        detail_row["range_start"] = range_start
        detail_row["range_end"] = range_end
        detail_rows.append(detail_row)
    detail_rows.sort(
        key=lambda item: (
            str(item["data_coleta_iso"]),
            GENOTYPE_ORDER.get(str(item["genotipo"]), 99),
            SHIFT_ORDER.get(str(item["turno"]), 99),
            int(item["rank"]),
        )
    )
    return detail_rows


def write_summary_markdown(
    path: Path,
    *,
    input_csv: Path,
    metrics_csv: Path,
    global_rows: list[dict[str, object]],
    direction_rows: list[dict[str, object]],
    detail_rows: list[dict[str, object]],
) -> None:
    lines = [
        "# Resumo das top bandas PLSR por data x genotipo x turno",
        "",
        f"- Fonte: `{input_csv}`",
        f"- Metricas: `{metrics_csv}`",
        f"- Subconjuntos avaliados: `{unique_subset_count(detail_rows)}`",
        "",
        "## Bandas mais recorrentes no top 5 global",
        "",
        "| rank | banda | ocorrencias | freq. subconjuntos | rank medio | VIP medio | |coef| medio | score medio | direcao dominante |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for rank, row in enumerate(global_rows[:20], start=1):
        lines.append(
            "| "
            f"{rank} | "
            f"{row['wavelength']} | "
            f"{row['occurrences']} | "
            f"{float(row['subset_frequency']):.4f} | "
            f"{float(row['mean_rank']):.4f} | "
            f"{float(row['mean_vip']):.4f} | "
            f"{float(row['mean_abs_coefficient']):.6f} | "
            f"{float(row['mean_score']):.4f} | "
            f"{row['dominant_direction']} |"
        )

    for direction in ["irrigado", "nao_irrigado"]:
        direction_subset = [row for row in direction_rows if row["direction"] == direction][:15]
        lines.extend(
            [
                "",
                f"## Bandas mais recorrentes para `{direction}`",
                "",
                "| rank | banda | ocorrencias | freq. subconjuntos | rank medio | VIP medio | coef. medio | score medio |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for rank, row in enumerate(direction_subset, start=1):
            lines.append(
                "| "
                f"{rank} | "
                f"{row['wavelength']} | "
                f"{row['occurrences']} | "
                f"{float(row['subset_frequency']):.4f} | "
                f"{float(row['mean_rank']):.4f} | "
                f"{float(row['mean_vip']):.4f} | "
                f"{float(row['mean_coefficient']):.6f} | "
                f"{float(row['mean_score']):.4f} |"
            )

    lines.extend(
        [
            "",
            "## Top 5 detalhado por subconjunto",
            "",
            "| data | genotipo | turno | R2CV | rank | banda | range | inicio | fim | direcao | VIP | coeficiente | |coef| | score |",
            "| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in detail_rows:
        lines.append(
            "| "
            f"{row['data_coleta_iso']} | "
            f"{row['genotipo']} | "
            f"{row['turno']} | "
            f"{float(row['r2cv']):.6f} | "
            f"{row['rank']} | "
            f"{row['wavelength']} | "
            f"{row['range_label']} | "
            f"{row['range_start']} | "
            f"{row['range_end']} | "
            f"{row['direction']} | "
            f"{float(row['vip']):.6f} | "
            f"{float(row['coefficient']):.6f} | "
            f"{float(row['abs_coefficient']):.6f} | "
            f"{float(row['score']):.6f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_csv = args.input_csv.resolve()
    metrics_csv = args.metrics_csv.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(input_csv)
    metric_map = read_metric_map(metrics_csv)
    global_rows = aggregate_global_recurrence(rows)
    direction_rows = aggregate_direction_recurrence(rows)
    detail_rows = build_detail_rows(rows, metric_map)

    write_dict_csv(
        output_dir / "recorrencia_top_bandas_global.csv",
        [
            "wavelength",
            "occurrences",
            "subset_frequency",
            "mean_rank",
            "best_rank",
            "mean_vip",
            "mean_coefficient",
            "mean_abs_coefficient",
            "mean_score",
            "irrigado_count",
            "nao_irrigado_count",
            "dominant_direction",
        ],
        global_rows,
    )
    write_dict_csv(
        output_dir / "recorrencia_top_bandas_por_direcao.csv",
        [
            "direction",
            "wavelength",
            "occurrences",
            "subset_frequency",
            "mean_rank",
            "best_rank",
            "mean_vip",
            "mean_coefficient",
            "mean_abs_coefficient",
            "mean_score",
        ],
        direction_rows,
    )
    write_dict_csv(
        output_dir / "top5_bandas_detalhado.csv",
        [
            "data_coleta_iso",
            "genotipo",
            "turno",
            "r2cv",
            "rmsecv",
            "auc",
            "accuracy",
            "best_components",
            "rank",
            "wavelength",
            "range_label",
            "range_start",
            "range_end",
            "direction",
            "vip",
            "coefficient",
            "abs_coefficient",
            "score",
        ],
        detail_rows,
    )
    write_summary_markdown(
        output_dir / "resumo_top5_bandas_recorrencia.md",
        input_csv=input_csv,
        metrics_csv=metrics_csv,
        global_rows=global_rows,
        direction_rows=direction_rows,
        detail_rows=detail_rows,
    )

    print(f"Input CSV: {input_csv}")
    print(f"Subsets evaluated: {unique_subset_count(detail_rows)}")
    print(f"Top recurring band: {global_rows[0]['wavelength']} nm")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
