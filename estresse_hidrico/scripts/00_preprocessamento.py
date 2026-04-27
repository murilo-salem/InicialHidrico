#!/usr/bin/env python3
"""Pre-process the soybean spectral workbook for the water-stress analyses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import (
    INDEX_COLUMNS,
    assign_class_labels,
    ensure_dirs,
    get_paths,
    preprocess_dataset,
    resolve_input_path,
    write_csv,
    write_excel_workbook,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa o pre-processamento do experimento de estresse hidrico.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Caminho opcional para base_dados_unificada.xlsx.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = get_paths()
    ensure_dirs(paths)
    input_path = resolve_input_path(args.input)

    artifacts = preprocess_dataset(input_path)
    technical_df = assign_class_labels(artifacts.technical_df)
    block_turn_df = assign_class_labels(artifacts.block_turn_df)
    block_day_df = assign_class_labels(artifacts.block_day_df)

    spectra_columns = artifacts.retained_band_columns
    technical_spectra_df = technical_df[
        [
            "sample_uid",
            "nomenclaura",
            "bloco",
            "replicata",
            "tecnica",
            "cultivar",
            "condicao",
            "classe",
            "classe_legenda",
            "data_coleta_iso",
            "dia",
            "turno_original",
            "turno",
        ]
        + spectra_columns
    ]
    technical_indices_df = technical_df[
        [
            "sample_uid",
            "nomenclaura",
            "bloco",
            "replicata",
            "tecnica",
            "cultivar",
            "condicao",
            "classe",
            "classe_legenda",
            "data_coleta_iso",
            "dia",
            "turno_original",
            "turno",
        ]
        + INDEX_COLUMNS
    ]

    write_csv(technical_spectra_df, paths.processed_dir / "espectros_suavizados.csv")
    write_csv(technical_indices_df, paths.processed_dir / "indices_vegetacao.csv")
    write_csv(block_turn_df, paths.processed_dir / "replicatas_bloco_turno.csv")
    write_csv(block_day_df, paths.processed_dir / "replicatas_bloco_dia.csv")
    write_csv(artifacts.group_turn_df, paths.processed_dir / "medias_grupais_turno.csv")
    write_csv(artifacts.group_day_df, paths.processed_dir / "medias_grupais_dia.csv")

    write_csv(artifacts.integrity_summary_df, paths.table_dir / "integridade_dados.csv")
    write_csv(artifacts.band_integrity_df, paths.table_dir / "integridade_bandas.csv")
    write_csv(artifacts.day_context_df, paths.table_dir / "cronograma_dias.csv")
    write_csv(artifacts.index_band_map_df, paths.table_dir / "mapeamento_indices.csv")

    write_excel_workbook(
        paths.table_dir / "preprocessamento_resumo.xlsx",
        {
            "integridade": artifacts.integrity_summary_df,
            "cronograma_dias": artifacts.day_context_df,
            "mapeamento_indices": artifacts.index_band_map_df,
            "replicatas_turno": block_turn_df,
            "replicatas_dia": block_day_df,
            "medias_grupais_turno": artifacts.group_turn_df,
            "medias_grupais_dia": artifacts.group_day_df,
        },
    )

    summary = {
        "input_path": str(input_path),
        "amostras_tecnicas": int(len(technical_df)),
        "replicatas_bloco_turno": int(len(block_turn_df)),
        "replicatas_bloco_dia": int(len(block_day_df)),
        "bandas_retidas": int(len(spectra_columns)),
        "indices_vegetacao": INDEX_COLUMNS,
        "datas_no_workbook": artifacts.day_context_df["data_coleta_iso"].tolist(),
        "dias_rotulados": artifacts.day_context_df["dia"].tolist(),
        "possui_recuperacao": bool((artifacts.day_context_df["dia"] == "recuperacao").any()),
    }
    summary_path = paths.processed_dir / "preprocessamento_resumo.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
