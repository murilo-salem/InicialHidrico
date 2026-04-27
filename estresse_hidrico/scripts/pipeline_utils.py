#!/usr/bin/env python3
"""Shared utilities for the soybean water-stress analysis pipeline."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.signal import savgol_filter
from scipy.spatial.distance import pdist, squareform
from skbio import DistanceMatrix
from skbio.stats.distance import permanova, permdisp
from statsmodels.stats.multitest import multipletests


META_COLUMNS = [
    "sample_uid",
    "nomenclaura",
    "bloco",
    "replicata",
    "tecnica",
    "cultivar",
    "condicao",
    "data_coleta_iso",
    "dia",
    "turno_original",
    "turno",
]
INDEX_COLUMNS = ["NDVI", "EVI", "WBI", "PRI", "SIPI", "REP"]
CULTIVAR_ORDER = ["EMB48", "BR16", "CD202"]
CONDITION_ORDER = ["IRR", "NIRR"]
TURN_ORDER = ["manha", "tarde", "unico"]
DAY_LABEL_MAP = {
    "2017-02-23": "dia2",
    "2017-02-24": "dia3",
    "2017-02-25": "dia4",
    "2017-02-26": "dia5",
    "2017-02-27": "dia6",
    "2017-03-02": "dia9",
}
DAY_ORDER = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9", "recuperacao"]
DAY_DISPLAY_MAP = {
    "dia2": "Dia 2\n23/02",
    "dia3": "Dia 3\n24/02",
    "dia4": "Dia 4\n25/02",
    "dia5": "Dia 5\n26/02",
    "dia6": "Dia 6\n27/02",
    "dia9": "Dia 9\n02/03",
    "recuperacao": "Rec.\n+1",
}
DUAL_TURN_DAYS = {"dia2", "dia3", "dia9"}
ATMOSPHERIC_INTERVALS = [(1350, 1450), (1800, 1950)]
FILE_RE = re.compile(r"^(B\d+)_(BR16|CD202|C202|EMB48)_(IRRIG|NIRRIG|IRR|NIRR)(?:_|$)", re.IGNORECASE)
TECH_RE = re.compile(r"(\d{5})(?=\.asd$)", re.IGNORECASE)
CLASS_LABELS = {
    ("EMB48", "IRR"): ("A", "A (EMB48 IRR)"),
    ("EMB48", "NIRR"): ("B", "B (EMB48 NIRR)"),
    ("BR16", "IRR"): ("C", "C (BR16 IRR)"),
    ("BR16", "NIRR"): ("D", "D (BR16 NIRR)"),
    ("CD202", "IRR"): ("E", "E (CD202 IRR)"),
    ("CD202", "NIRR"): ("F", "F (CD202 NIRR)"),
}


@dataclass(frozen=True)
class PipelinePaths:
    project_dir: Path
    raw_dir: Path
    processed_dir: Path
    output_dir: Path
    table_dir: Path
    figure_dir: Path


@dataclass(frozen=True)
class PreprocessArtifacts:
    technical_df: pd.DataFrame
    block_turn_df: pd.DataFrame
    block_day_df: pd.DataFrame
    group_turn_df: pd.DataFrame
    group_day_df: pd.DataFrame
    integrity_summary_df: pd.DataFrame
    band_integrity_df: pd.DataFrame
    day_context_df: pd.DataFrame
    index_band_map_df: pd.DataFrame
    retained_band_columns: list[str]


def get_paths() -> PipelinePaths:
    project_dir = Path(__file__).resolve().parents[1]
    raw_dir = project_dir / "dados" / "raw"
    processed_dir = project_dir / "dados" / "processados"
    output_dir = project_dir / "outputs"
    table_dir = output_dir / "tabelas"
    figure_dir = output_dir / "figuras"
    return PipelinePaths(
        project_dir=project_dir,
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        output_dir=output_dir,
        table_dir=table_dir,
        figure_dir=figure_dir,
    )


def ensure_dirs(paths: PipelinePaths) -> None:
    for path in [
        paths.project_dir,
        paths.raw_dir,
        paths.processed_dir,
        paths.output_dir,
        paths.table_dir,
        paths.figure_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def resolve_input_path(explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        return explicit_path.resolve()
    paths = get_paths()
    preferred = paths.raw_dir / "base_dados_unificada.xlsx"
    if preferred.exists():
        return preferred
    fallback = paths.project_dir.parent / "base_dados_unificada.xlsx"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        "Nenhum arquivo base_dados_unificada.xlsx foi encontrado em "
        f"{preferred} ou {fallback}."
    )


def set_plot_style() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 300
    plt.rcParams["axes.titlesize"] = 13
    plt.rcParams["axes.labelsize"] = 11
    plt.rcParams["legend.fontsize"] = 10


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_excel_workbook(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            safe_name = sheet_name[:31]
            frame.to_excel(writer, sheet_name=safe_name, index=False)


def parse_filename_metadata(file_name: str) -> dict[str, object]:
    token = str(file_name).strip()
    match = FILE_RE.match(token)
    if match is None:
        raise ValueError(f"Falha ao normalizar 'nomenclaura': {token!r}")
    bloco, cultivar_token, condition_token = match.groups()
    cultivar = "CD202" if cultivar_token.upper() == "C202" else cultivar_token.upper()
    condicao = "IRR" if condition_token.upper().startswith("IRR") else "NIRR"
    tech_match = TECH_RE.search(token)
    tecnica = int(tech_match.group(1)) if tech_match else -1
    replicata = int(bloco.upper().replace("B", ""))
    return {
        "bloco": bloco.upper(),
        "replicata": replicata,
        "tecnica": tecnica,
        "cultivar": cultivar,
        "condicao": condicao,
    }


def normalize_turno(value: object) -> str:
    token = str(value).strip().lower()
    if token in {"manha", "manhã", "morning"}:
        return "manha"
    if token in {"tarde", "afternoon"}:
        return "tarde"
    if token in {"unico", "único", "single"}:
        return "unico"
    if not token or token == "nan":
        return "desconhecido"
    return token


def normalize_date(value: object) -> str:
    if pd.isna(value):
        raise ValueError("Valor de data_coleta ausente.")
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    token = str(value).strip()
    if token.endswith(".0"):
        token = token[:-2]
    if re.fullmatch(r"\d{8}", token):
        return pd.to_datetime(token, format="%Y%m%d").date().isoformat()
    return pd.to_datetime(token).date().isoformat()


def band_to_wavelength(band_column: str) -> int:
    return int(str(band_column).split("_", 1)[1])


def wavelength_to_band(wavelength_nm: int) -> str:
    return f"band_{int(wavelength_nm)}"


def get_band_columns(df: pd.DataFrame) -> list[str]:
    return sorted(
        [column for column in df.columns if str(column).startswith("band_")],
        key=band_to_wavelength,
    )


def day_sort_key(day_label: str) -> tuple[int, str]:
    if day_label in DAY_ORDER:
        return (DAY_ORDER.index(day_label), day_label)
    return (len(DAY_ORDER), day_label)


def ordered_days(days: Sequence[str]) -> list[str]:
    return sorted({str(day) for day in days}, key=day_sort_key)


def sort_metadata_frame(df: pd.DataFrame, include_turno: bool = True) -> pd.DataFrame:
    frame = df.copy()
    frame["__dia_ord"] = frame["dia"].map(lambda value: day_sort_key(value)[0])
    sort_cols = ["__dia_ord"]
    for candidate in ["data_coleta_iso", "cultivar", "condicao"]:
        if candidate in frame.columns:
            sort_cols.append(candidate)
    if include_turno and "turno" in frame.columns:
        frame["__turno_ord"] = frame["turno"].map(lambda value: TURN_ORDER.index(value) if value in TURN_ORDER else len(TURN_ORDER))
        sort_cols.append("__turno_ord")
    for candidate in ["replicata", "bloco", "tecnica", "sample_uid"]:
        if candidate in frame.columns:
            sort_cols.append(candidate)
    frame = frame.sort_values(sort_cols).drop(columns=[column for column in ["__dia_ord", "__turno_ord"] if column in frame.columns])
    return frame.reset_index(drop=True)


def in_atmospheric_interval(wavelength_nm: int) -> bool:
    return any(start <= wavelength_nm <= end for start, end in ATMOSPHERIC_INTERVALS)


def retained_band_columns(all_band_columns: Sequence[str]) -> list[str]:
    return [column for column in all_band_columns if not in_atmospheric_interval(band_to_wavelength(column))]


def contiguous_segments(columns: Sequence[str]) -> list[list[str]]:
    ordered = list(columns)
    segments: list[list[str]] = []
    current: list[str] = []
    previous_wavelength: int | None = None
    for column in ordered:
        wavelength = band_to_wavelength(column)
        if previous_wavelength is None or wavelength == previous_wavelength + 1:
            current.append(column)
        else:
            segments.append(current)
            current = [column]
        previous_wavelength = wavelength
    if current:
        segments.append(current)
    return segments


def safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        output = np.divide(
            numerator,
            denominator,
            out=np.full_like(numerator, np.nan, dtype=float),
            where=np.abs(denominator) > 1e-12,
        )
    return output


def nearest_band_column(available_band_columns: Sequence[str], target_wavelength_nm: int) -> str:
    wavelengths = np.array([band_to_wavelength(column) for column in available_band_columns], dtype=int)
    idx = int(np.argmin(np.abs(wavelengths - int(target_wavelength_nm))))
    return list(available_band_columns)[idx]


def load_raw_workbook(input_path: Path) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_excel(input_path, sheet_name=0, engine="openpyxl")
    if df.shape[1] < 7:
        raise ValueError("A planilha tem menos colunas do que o esperado.")

    original_columns = list(df.columns)
    meta_rename = {
        original_columns[0]: "nomenclaura",
        original_columns[1]: "bloco_raw",
        original_columns[2]: "genotipo_raw",
        original_columns[3]: "condicao_raw",
        original_columns[4]: "data_coleta_raw",
        original_columns[5]: "turno_raw",
    }
    df = df.rename(columns=meta_rename)

    band_rename: dict[object, str] = {}
    for raw_column in original_columns[6:]:
        wavelength = int(round(float(raw_column)))
        band_rename[raw_column] = wavelength_to_band(wavelength)
    df = df.rename(columns=band_rename)

    band_columns = get_band_columns(df)
    df[band_columns] = df[band_columns].apply(pd.to_numeric, errors="coerce")

    normalized = pd.DataFrame(df["nomenclaura"].map(parse_filename_metadata).tolist())
    df = pd.concat([df, normalized], axis=1)
    extra = pd.DataFrame(index=df.index)
    extra["data_coleta_iso"] = df["data_coleta_raw"].map(normalize_date)
    extra["dia"] = extra["data_coleta_iso"].map(DAY_LABEL_MAP).fillna(extra["data_coleta_iso"])
    extra["turno_original"] = df["turno_raw"].map(normalize_turno)
    turn_counts = extra.groupby(extra["data_coleta_iso"])["turno_original"].transform("nunique")
    extra["turno"] = np.where(turn_counts > 1, extra["turno_original"], "unico")
    extra["sample_uid"] = (
        extra["data_coleta_iso"].astype(str)
        + "__"
        + extra["turno_original"].astype(str)
        + "__"
        + df["nomenclaura"].astype(str)
    )
    df = pd.concat([df, extra], axis=1)
    return df, band_columns


def build_integrity_tables(raw_df: pd.DataFrame, band_columns: Sequence[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    spectral = raw_df[list(band_columns)]
    missing_values = int(spectral.isna().sum().sum())
    out_of_range_mask = (spectral < 0.0) | (spectral > 1.0)
    out_of_range_values = int(out_of_range_mask.sum().sum())
    duplicate_sample_keys = int(raw_df.duplicated(subset=["data_coleta_iso", "turno_original", "nomenclaura"]).sum())
    duplicate_measurement_keys = int(
        raw_df.duplicated(subset=["data_coleta_iso", "turno_original", "cultivar", "condicao", "bloco", "tecnica"]).sum()
    )

    summary_rows = [
        {"metrica": "amostras_brutas", "valor": int(len(raw_df))},
        {"metrica": "bandas_brutas", "valor": int(len(band_columns))},
        {"metrica": "datas_absolutas", "valor": int(raw_df["data_coleta_iso"].nunique())},
        {"metrica": "dias_rotulados", "valor": int(raw_df["dia"].nunique())},
        {"metrica": "turnos_originais", "valor": int(raw_df["turno_original"].nunique())},
        {"metrica": "valores_ausentes", "valor": missing_values},
        {"metrica": "valores_fora_intervalo_0_1", "valor": out_of_range_values},
        {"metrica": "duplicatas_chave_data_turno_arquivo", "valor": duplicate_sample_keys},
        {"metrica": "duplicatas_chave_biologica_tecnica", "valor": duplicate_measurement_keys},
        {
            "metrica": "dias_sem_recuperacao_no_workbook",
            "valor": int("recuperacao" not in set(raw_df["dia"])),
        },
    ]
    summary_df = pd.DataFrame(summary_rows)

    band_df = pd.DataFrame(
        {
            "banda": list(band_columns),
            "comprimento_onda_nm": [band_to_wavelength(column) for column in band_columns],
            "fora_intervalo_count": out_of_range_mask.sum(axis=0).to_numpy(dtype=int),
        }
    )
    band_df = band_df.sort_values("comprimento_onda_nm").reset_index(drop=True)

    day_context = (
        raw_df.groupby(["data_coleta_iso", "dia"], as_index=False)
        .agg(
            turnos_originais=("turno_original", lambda values: " | ".join(sorted(set(values)))),
            n_turnos_originais=("turno_original", "nunique"),
            amostras_brutas=("sample_uid", "nunique"),
        )
        .sort_values(["data_coleta_iso"])
        .reset_index(drop=True)
    )
    return summary_df, band_df, day_context


def smooth_spectra(
    raw_df: pd.DataFrame,
    band_columns: Sequence[str],
    remove_atmospheric_bands: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    kept_columns = retained_band_columns(band_columns) if remove_atmospheric_bands else list(band_columns)
    smoothed_parts: list[pd.DataFrame] = []
    for segment in contiguous_segments(kept_columns):
        values = raw_df[segment].to_numpy(dtype=float)
        filtered = savgol_filter(values, window_length=11, polyorder=2, axis=1, mode="mirror")
        smoothed_parts.append(pd.DataFrame(filtered, index=raw_df.index, columns=segment))
    smoothed = pd.concat(smoothed_parts, axis=1)[kept_columns]
    return smoothed, kept_columns


def smooth_filtered_spectra(raw_df: pd.DataFrame, band_columns: Sequence[str]) -> tuple[pd.DataFrame, list[str]]:
    return smooth_spectra(raw_df, band_columns, remove_atmospheric_bands=True)


def compute_vegetation_indices(spectrum_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    band_targets = {
        "NDVI": [800, 670],
        "EVI": [800, 670, 450],
        "WBI": [900, 970],
        "PRI": [531, 570],
        "SIPI": [800, 445, 680],
        "REP": [670, 700, 740, 780],
    }
    bands = list(spectrum_df.columns)
    mapping_rows: list[dict[str, object]] = []
    resolved: dict[tuple[str, int], str] = {}
    for index_name, targets in band_targets.items():
        for target in targets:
            column = nearest_band_column(bands, target)
            resolved[(index_name, target)] = column
            mapping_rows.append(
                {
                    "indice": index_name,
                    "alvo_nm": target,
                    "banda_resolvida": column,
                    "comprimento_onda_resolvido_nm": band_to_wavelength(column),
                }
            )

    def band(index_name: str, wavelength_nm: int) -> np.ndarray:
        return spectrum_df[resolved[(index_name, wavelength_nm)]].to_numpy(dtype=float)

    r800 = band("NDVI", 800)
    r670 = band("NDVI", 670)
    r450 = band("EVI", 450)
    r900 = band("WBI", 900)
    r970 = band("WBI", 970)
    r531 = band("PRI", 531)
    r570 = band("PRI", 570)
    r445 = band("SIPI", 445)
    r680 = band("SIPI", 680)
    r700 = band("REP", 700)
    r740 = band("REP", 740)
    r780 = band("REP", 780)

    indices_df = pd.DataFrame(
        {
            "NDVI": safe_divide(r800 - r670, r800 + r670),
            "EVI": safe_divide(2.5 * (r800 - r670), r800 + (6.0 * r670) - (7.5 * r450) + 1.0),
            "WBI": safe_divide(r900, r970),
            "PRI": safe_divide(r531 - r570, r531 + r570),
            "SIPI": safe_divide(r800 - r445, r800 - r680),
            "REP": 700.0 + (40.0 * safe_divide((((r670 + r780) / 2.0) - r700), (r740 - r700))),
        },
        index=spectrum_df.index,
    )
    mapping_df = pd.DataFrame(mapping_rows).sort_values(["indice", "alvo_nm"]).reset_index(drop=True)
    return indices_df, mapping_df


def aggregate_replicates(
    df: pd.DataFrame,
    group_columns: Sequence[str],
    feature_columns: Sequence[str],
    count_column_name: str,
) -> pd.DataFrame:
    grouped = df.groupby(list(group_columns), as_index=False, dropna=False)
    aggregated = grouped[list(feature_columns)].mean()
    counts = grouped.size().rename(columns={"size": count_column_name})
    result = aggregated.merge(counts, on=list(group_columns), how="left")
    return result


def build_block_day_spectral_dataset(
    input_path: Path,
    remove_atmospheric_bands: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    raw_df, raw_band_columns = load_raw_workbook(input_path)
    smoothed_df, smoothed_columns = smooth_spectra(
        raw_df,
        raw_band_columns,
        remove_atmospheric_bands=remove_atmospheric_bands,
    )
    metadata_df = raw_df[
        [
            "sample_uid",
            "nomenclaura",
            "bloco",
            "replicata",
            "cultivar",
            "condicao",
            "data_coleta_iso",
            "dia",
            "turno_original",
        ]
    ].copy()
    technical_df = pd.concat([metadata_df.reset_index(drop=True), smoothed_df.reset_index(drop=True)], axis=1)
    block_day_df = aggregate_replicates(
        technical_df,
        group_columns=["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco"],
        feature_columns=list(smoothed_columns),
        count_column_name="n_tecnicas_total",
    )
    block_day_df = sort_metadata_frame(block_day_df, include_turno=False)
    return block_day_df, list(smoothed_columns)


def join_unique(values: Iterable[str]) -> str:
    return " + ".join(sorted(set(values), key=lambda item: TURN_ORDER.index(item) if item in TURN_ORDER else len(TURN_ORDER)))


def assign_class_labels(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    labels = frame.apply(lambda row: CLASS_LABELS[(row["cultivar"], row["condicao"])], axis=1)
    frame["classe"] = [item[0] for item in labels]
    frame["classe_legenda"] = [item[1] for item in labels]
    frame["grupo_cv"] = frame["classe"] + "_B" + frame["replicata"].astype(str)
    return frame


def preprocess_dataset(input_path: Path) -> PreprocessArtifacts:
    raw_df, raw_band_columns = load_raw_workbook(input_path)
    integrity_summary_df, band_integrity_df, day_context_df = build_integrity_tables(raw_df, raw_band_columns)
    smoothed_spectra_df, kept_band_columns = smooth_filtered_spectra(raw_df, raw_band_columns)
    indices_df, index_band_map_df = compute_vegetation_indices(smoothed_spectra_df)

    technical_df = raw_df[
        [
            "sample_uid",
            "nomenclaura",
            "bloco",
            "replicata",
            "tecnica",
            "cultivar",
            "condicao",
            "data_coleta_iso",
            "dia",
            "turno_original",
            "turno",
        ]
    ].copy()
    technical_df[kept_band_columns] = smoothed_spectra_df[kept_band_columns]
    technical_df[INDEX_COLUMNS] = indices_df[INDEX_COLUMNS]
    technical_df = sort_metadata_frame(technical_df, include_turno=True)

    block_turn_df = aggregate_replicates(
        technical_df,
        group_columns=["cultivar", "condicao", "data_coleta_iso", "dia", "turno", "replicata", "bloco"],
        feature_columns=list(kept_band_columns) + INDEX_COLUMNS,
        count_column_name="n_tecnicas",
    )
    block_turn_df = sort_metadata_frame(block_turn_df, include_turno=True)

    block_day_df = aggregate_replicates(
        block_turn_df,
        group_columns=["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco"],
        feature_columns=list(kept_band_columns) + INDEX_COLUMNS,
        count_column_name="n_turnos_agregados",
    )
    turn_summary = (
        block_turn_df.groupby(["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco"])["turno"]
        .agg(join_unique)
        .reset_index(name="turnos_disponiveis")
    )
    tech_summary = (
        technical_df.groupby(["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco"])["sample_uid"]
        .count()
        .reset_index(name="n_tecnicas_total")
    )
    block_day_df = block_day_df.merge(turn_summary, on=["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco"], how="left")
    block_day_df = block_day_df.merge(tech_summary, on=["cultivar", "condicao", "data_coleta_iso", "dia", "replicata", "bloco"], how="left")
    block_day_df = sort_metadata_frame(block_day_df, include_turno=False)

    group_turn_df = aggregate_replicates(
        block_turn_df,
        group_columns=["cultivar", "condicao", "data_coleta_iso", "dia", "turno"],
        feature_columns=list(kept_band_columns) + INDEX_COLUMNS,
        count_column_name="n_replicatas",
    )
    group_turn_df = sort_metadata_frame(group_turn_df, include_turno=True)

    group_day_df = aggregate_replicates(
        block_day_df,
        group_columns=["cultivar", "condicao", "data_coleta_iso", "dia"],
        feature_columns=list(kept_band_columns) + INDEX_COLUMNS,
        count_column_name="n_replicatas",
    )
    group_day_df = sort_metadata_frame(group_day_df, include_turno=False)

    return PreprocessArtifacts(
        technical_df=technical_df,
        block_turn_df=block_turn_df,
        block_day_df=block_day_df,
        group_turn_df=group_turn_df,
        group_day_df=group_day_df,
        integrity_summary_df=integrity_summary_df,
        band_integrity_df=band_integrity_df,
        day_context_df=day_context_df,
        index_band_map_df=index_band_map_df,
        retained_band_columns=list(kept_band_columns),
    )


def processed_band_columns(df: pd.DataFrame) -> list[str]:
    return get_band_columns(df)


def calc_permanova_r2(f_statistic: float, n_samples: int, n_groups: int) -> float:
    numerator = f_statistic * (n_groups - 1)
    denominator = numerator + (n_samples - n_groups)
    if denominator <= 0:
        return float("nan")
    return numerator / denominator


def distance_matrix_from_features(df: pd.DataFrame, metric: str) -> DistanceMatrix:
    band_columns = processed_band_columns(df)
    feature_matrix = df[band_columns].to_numpy(dtype=float)
    distances = squareform(pdist(feature_matrix, metric=metric))
    ids = [str(index) for index in df.index]
    return DistanceMatrix(distances, ids=ids)


def run_permanova_pair(
    df: pd.DataFrame,
    grouping_column: str,
    metric: str,
    permutations: int = 999,
    seed: int = 42,
) -> dict[str, float | int | str]:
    if df[grouping_column].nunique() < 2:
        raise ValueError(f"A coluna {grouping_column!r} possui menos de dois grupos.")
    dm = distance_matrix_from_features(df, metric=metric)
    grouping = df[grouping_column].to_numpy()
    perm_result = permanova(dm, grouping, permutations=permutations, seed=seed)
    disp_result = permdisp(dm, grouping, permutations=permutations, seed=seed, warn_neg_eigval=False)
    n_samples = int(len(df))
    n_groups = int(pd.Series(grouping).nunique())
    f_statistic = float(perm_result["test statistic"])
    p_value = float(perm_result["p-value"])
    if permutations == 999 and 0.04 <= p_value <= 0.06:
        perm_result = permanova(dm, grouping, permutations=9999, seed=seed)
        disp_result = permdisp(dm, grouping, permutations=9999, seed=seed, warn_neg_eigval=False)
        f_statistic = float(perm_result["test statistic"])
        p_value = float(perm_result["p-value"])
        permutations = 9999
    return {
        "metrica": metric,
        "n_amostras": n_samples,
        "n_grupos": n_groups,
        "F": f_statistic,
        "p_value": p_value,
        "R2": calc_permanova_r2(f_statistic, n_samples, n_groups),
        "permutacoes": int(permutations),
        "permdisp_F": float(disp_result["test statistic"]),
        "permdisp_p_value": float(disp_result["p-value"]),
    }


def choose_best_metric(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    stable_rows = [row for row in rows if float(row["permdisp_p_value"]) >= 0.05]
    candidates = stable_rows or list(rows)
    ordered = sorted(
        candidates,
        key=lambda row: (
            float(row["p_value"]),
            -float(row["R2"]),
            row["metrica"],
        ),
    )
    return dict(ordered[0])


def apply_fdr(df: pd.DataFrame, p_column: str, output_column: str) -> pd.DataFrame:
    frame = df.copy()
    if frame.empty:
        frame[output_column] = []
        return frame
    _, q_values, _, _ = multipletests(frame[p_column].to_numpy(dtype=float), method="fdr_bh")
    frame[output_column] = q_values
    return frame


def significance_label(p_value: float) -> str:
    return "Sim" if p_value < 0.05 else "Nao"


def display_day_label(day_label: str) -> str:
    return DAY_DISPLAY_MAP.get(day_label, day_label)


def plot_temporal_feature(
    df: pd.DataFrame,
    feature_name: str,
    day_labels: Sequence[str],
    ylabel: str,
    title: str,
) -> plt.Figure:
    set_plot_style()
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = {"IRR": "#1f77b4", "NIRR": "#c62828"}
    x_values = np.arange(len(day_labels))
    for condition in CONDITION_ORDER:
        means: list[float] = []
        errors: list[float] = []
        for day_label in day_labels:
            subset = df[(df["dia"] == day_label) & (df["condicao"] == condition)]
            means.append(float(subset[feature_name].mean()))
            errors.append(float(subset[feature_name].std(ddof=1)))
        ax.errorbar(
            x_values,
            means,
            yerr=errors,
            label=condition,
            color=colors[condition],
            marker="o",
            linewidth=2,
            capsize=4,
        )
    ax.set_xticks(x_values)
    ax.set_xticklabels([display_day_label(day_label) for day_label in day_labels])
    ax.set_xlabel("Dia de aquisicao")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if "recuperacao" in day_labels:
        recovery_index = day_labels.index("recuperacao")
        ax.axvline(recovery_index - 0.5, linestyle="--", color="#7f7f7f", alpha=0.6)
    ax.legend(title="Condicao")
    return fig


def build_ratio_std_curve(day_df: pd.DataFrame, band_columns: Sequence[str]) -> pd.DataFrame:
    ratio_rows: list[np.ndarray] = []
    pair_rows: list[dict[str, object]] = []
    for cultivar in CULTIVAR_ORDER:
        cultivar_df = day_df[day_df["cultivar"] == cultivar]
        for replicata in sorted(cultivar_df["replicata"].unique()):
            irr = cultivar_df[(cultivar_df["replicata"] == replicata) & (cultivar_df["condicao"] == "IRR")]
            nirr = cultivar_df[(cultivar_df["replicata"] == replicata) & (cultivar_df["condicao"] == "NIRR")]
            if len(irr) != 1 or len(nirr) != 1:
                continue
            irr_values = irr.iloc[0][list(band_columns)].to_numpy(dtype=float)
            nirr_values = nirr.iloc[0][list(band_columns)].to_numpy(dtype=float)
            ratio = safe_divide(nirr_values, irr_values)
            ratio_rows.append(ratio)
            pair_rows.append(
                {
                    "cultivar": cultivar,
                    "replicata": int(replicata),
                    "n_bandas": int(len(band_columns)),
                }
            )
    if not ratio_rows:
        return pd.DataFrame(columns=["comprimento_onda_nm", "ratio_media", "ratio_std", "n_pares"])
    ratio_matrix = np.vstack(ratio_rows)
    return pd.DataFrame(
        {
            "comprimento_onda_nm": [band_to_wavelength(column) for column in band_columns],
            "ratio_media": np.nanmean(ratio_matrix, axis=0),
            "ratio_std": np.nanstd(ratio_matrix, axis=0, ddof=1),
            "n_pares": len(pair_rows),
        }
    )


def format_metric(value: float, digits: int = 4) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{value:.{digits}f}"
