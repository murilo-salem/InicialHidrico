#!/usr/bin/env python3
"""Generate descriptive statistics for the unified spectral dataset.

This script reads the Excel workbook directly from its XML parts, so it does
not depend on third-party Python packages.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET


NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CELL_REF_RE = re.compile(r"([A-Z]+)(\d+)")
FILE_NAME_RE = re.compile(
    r"^(B\d+)_(BR16|CD202|C202|EMB48)_(IRRIG|NIRRIG|IRR|NIRR)(?:_|$)"
)

META_COLUMNS = [
    "nomenclaura",
    "bloco",
    "genotipo",
    "condicao ",
    "data_coleta",
    "turno",
]
GENOTYPE_ORDER = {"BR16": 0, "CD202": 1, "EMB48": 2}
CONDITION_LABELS = {"IRRIG": "irrigado", "NIRRIG": "nao_irrigado"}
CONDITION_ORDER = {"IRRIG": 0, "NIRRIG": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute mean and coefficient of variation by collection date, "
            "genotype and irrigation condition."
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
        default=Path("outputs"),
        help="Directory where result files will be written.",
    )
    return parser.parse_args()


def column_index(column_letters: str) -> int:
    result = 0
    for char in column_letters:
        result = result * 26 + (ord(char) - 64)
    return result - 1


def column_letter(index: int) -> str:
    value = index + 1
    letters: list[str] = []
    while value:
        value, remainder = divmod(value - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def load_shared_strings(workbook: ZipFile) -> list[str]:
    shared_path = "xl/sharedStrings.xml"
    if shared_path not in workbook.namelist():
        return []

    root = ET.fromstring(workbook.read(shared_path))
    shared_strings: list[str] = []
    for item in root.findall(f"{NS_MAIN}si"):
        text_parts: list[str] = []
        for node in item.iter():
            if node.tag == f"{NS_MAIN}t" and node.text:
                text_parts.append(node.text)
        shared_strings.append("".join(text_parts))
    return shared_strings


def decode_cell_value(cell: ET.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.attrib.get("t")
    value_node = cell.find(f"{NS_MAIN}v")
    inline_node = cell.find(f"{NS_MAIN}is")

    if cell_type == "s" and value_node is not None:
        return shared_strings[int(value_node.text)]

    if cell_type == "inlineStr" and inline_node is not None:
        text_parts: list[str] = []
        for node in inline_node.iter():
            if node.tag == f"{NS_MAIN}t" and node.text:
                text_parts.append(node.text)
        return "".join(text_parts)

    if value_node is not None:
        return value_node.text

    return None


def iter_sheet_rows(workbook_path: Path) -> Iterator[tuple[int, list[str | None]]]:
    with ZipFile(workbook_path) as workbook:
        shared_strings = load_shared_strings(workbook)
        with workbook.open("xl/worksheets/sheet1.xml") as sheet_file:
            for _, element in ET.iterparse(sheet_file, events=("end",)):
                if element.tag != f"{NS_MAIN}row":
                    continue

                row_number = int(element.attrib["r"])
                row_values: list[str | None] = []
                next_index = 0

                for cell in element.findall(f"{NS_MAIN}c"):
                    reference = cell.attrib.get("r", "")
                    match = CELL_REF_RE.match(reference)
                    if match is None:
                        raise ValueError(f"Invalid cell reference: {reference!r}")

                    current_index = column_index(match.group(1))
                    while next_index < current_index:
                        row_values.append(None)
                        next_index += 1

                    row_values.append(decode_cell_value(cell, shared_strings))
                    next_index += 1

                yield row_number, row_values
                element.clear()


def normalize_condition_code(value: str | None) -> str | None:
    token = (value or "").strip().upper()
    if token in {"IRRIG", "IRRG", "IRR"}:
        return "IRRIG"
    if token in {"NIRRIG", "NIRR"}:
        return "NIRRIG"
    return None


def normalize_genotype_token(value: str | None) -> str | None:
    token = (value or "").strip().upper()
    if token == "C202":
        return "CD202"
    if token in {"BR16", "CD202", "EMB48"}:
        return token
    return None


@dataclass(frozen=True)
class NormalizedMetadata:
    file_name: str
    block: str
    genotype: str
    condition_code: str
    condition_label: str
    collection_date_raw: str
    collection_date_iso: str
    shift: str


@dataclass
class RunningStats:
    count: int
    sums: list[float]
    sums_of_squares: list[float]

    @classmethod
    def create(cls, size: int) -> "RunningStats":
        return cls(count=0, sums=[0.0] * size, sums_of_squares=[0.0] * size)

    def add(self, values: list[float]) -> None:
        self.count += 1
        sums = self.sums
        sums_of_squares = self.sums_of_squares
        for index, value in enumerate(values):
            sums[index] += value
            sums_of_squares[index] += value * value

    def mean_values(self) -> list[float]:
        return [value / self.count for value in self.sums]

    def cv_values(self) -> list[float]:
        means = self.mean_values()
        if self.count < 2:
            return [0.0] * len(means)

        cvs: list[float] = []
        for index, mean_value in enumerate(means):
            variance = (
                self.sums_of_squares[index]
                - (self.sums[index] * self.sums[index] / self.count)
            ) / (self.count - 1)
            variance = max(variance, 0.0)
            standard_deviation = math.sqrt(variance)
            if math.isclose(mean_value, 0.0, abs_tol=1e-12):
                cvs.append(float("nan"))
            else:
                cvs.append((standard_deviation / mean_value) * 100.0)
        return cvs


@dataclass
class AnalysisResult:
    workbook_path: Path
    sheet_name: str
    sample_count: int
    wavelength_headers: list[str]
    stats_by_group: dict[tuple[str, str, str], RunningStats]
    group_counts: list[tuple[str, str, str, int]]
    dates: list[str]
    raw_metadata_issue_rows: int
    filename_typo_rows: int
    missing_wavelength_values: int
    normalization_examples: list[tuple[int, str, str, str]]


def normalize_metadata(
    row_number: int,
    row_values: list[str | None],
    normalization_examples: list[tuple[int, str, str, str]],
) -> NormalizedMetadata:
    raw_data = dict(zip(META_COLUMNS, row_values[: len(META_COLUMNS)]))
    file_name = raw_data["nomenclaura"] or ""
    match = FILE_NAME_RE.match(file_name)
    if match is None:
        raise ValueError(
            f"Unable to derive grouping metadata from 'nomenclaura' at row {row_number}: "
            f"{file_name!r}"
        )

    block, genotype_token, condition_token = match.groups()
    genotype = "CD202" if genotype_token == "C202" else genotype_token
    condition_code = "IRRIG" if condition_token.startswith("IRR") else "NIRRIG"
    collection_date_raw = (raw_data["data_coleta"] or "").strip()
    if not collection_date_raw:
        raise ValueError(f"Missing collection date at row {row_number}")

    collection_date_iso = datetime.strptime(collection_date_raw, "%Y%m%d").date().isoformat()
    shift = (raw_data["turno"] or "").strip()
    if genotype_token == "C202" and len(normalization_examples) < 12:
        normalization_examples.append(
            (row_number, file_name, "genotype filename token", "C202 -> CD202")
        )

    return NormalizedMetadata(
        file_name=file_name,
        block=block,
        genotype=genotype,
        condition_code=condition_code,
        condition_label=CONDITION_LABELS[condition_code],
        collection_date_raw=collection_date_raw,
        collection_date_iso=collection_date_iso,
        shift=shift,
    )


def analyze_dataset(workbook_path: Path) -> AnalysisResult:
    header: list[str | None] | None = None
    wavelength_headers: list[str] = []
    stats_by_group: dict[tuple[str, str, str], RunningStats] = {}
    raw_metadata_issue_rows = 0
    filename_typo_rows = 0
    missing_wavelength_values = 0
    sample_count = 0
    normalization_examples: list[tuple[int, str, str, str]] = []
    group_counter: Counter[tuple[str, str, str]] = Counter()
    dates_seen: set[str] = set()

    for row_number, row_values in iter_sheet_rows(workbook_path):
        if row_number == 1:
            header = row_values
            wavelength_headers = [str(value) for value in header[len(META_COLUMNS) :] if value]
            continue

        if header is None:
            raise ValueError("Header row was not found in the workbook.")

        if len(row_values) < len(header):
            row_values.extend([None] * (len(header) - len(row_values)))

        metadata = normalize_metadata(row_number, row_values, normalization_examples)
        sample_count += 1
        dates_seen.add(metadata.collection_date_iso)

        raw_block = (row_values[1] or "").strip()
        raw_genotype = normalize_genotype_token(row_values[2])
        raw_condition = normalize_condition_code(row_values[3])

        if raw_block != metadata.block or raw_genotype != metadata.genotype or raw_condition != metadata.condition_code:
            raw_metadata_issue_rows += 1

        if "_C202_" in metadata.file_name:
            filename_typo_rows += 1

        spectral_values: list[float] = []
        for value in row_values[len(META_COLUMNS) : len(META_COLUMNS) + len(wavelength_headers)]:
            if value is None:
                missing_wavelength_values += 1
                raise ValueError(
                    f"Missing spectral value detected at row {row_number}; "
                    "the current implementation expects complete spectra."
                )
            spectral_values.append(float(value))

        group_key = (
            metadata.collection_date_iso,
            metadata.genotype,
            metadata.condition_code,
        )
        stats = stats_by_group.get(group_key)
        if stats is None:
            stats = RunningStats.create(len(wavelength_headers))
            stats_by_group[group_key] = stats
        stats.add(spectral_values)
        group_counter[group_key] += 1

    group_counts = [
        (date_iso, genotype, condition_code, count)
        for (date_iso, genotype, condition_code), count in sorted(
            group_counter.items(),
            key=lambda item: (
                item[0][0],
                GENOTYPE_ORDER[item[0][1]],
                CONDITION_ORDER[item[0][2]],
            ),
        )
    ]

    return AnalysisResult(
        workbook_path=workbook_path,
        sheet_name="database",
        sample_count=sample_count,
        wavelength_headers=wavelength_headers,
        stats_by_group=stats_by_group,
        group_counts=group_counts,
        dates=sorted(dates_seen),
        raw_metadata_issue_rows=raw_metadata_issue_rows,
        filename_typo_rows=filename_typo_rows,
        missing_wavelength_values=missing_wavelength_values,
        normalization_examples=normalization_examples,
    )


def format_number(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:.10f}"


def build_stat_rows(
    analysis: AnalysisResult,
    metric: str,
) -> list[list[str]]:
    rows: list[list[str]] = []
    for date_iso, genotype, condition_code, count in analysis.group_counts:
        stats = analysis.stats_by_group[(date_iso, genotype, condition_code)]
        if metric == "mean":
            values = stats.mean_values()
        elif metric == "cv":
            values = stats.cv_values()
        else:
            raise ValueError(f"Unsupported metric: {metric}")

        row = [
            date_iso,
            genotype,
            CONDITION_LABELS[condition_code],
            str(count),
        ]
        row.extend(format_number(value) for value in values)
        rows.append(row)
    return rows


def write_csv(path: Path, header: list[str], rows: Iterable[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def write_summary_markdown(path: Path, analysis: AnalysisResult) -> None:
    lines: list[str] = [
        "# Resumo do dataset",
        "",
        f"- Arquivo analisado: `{analysis.workbook_path.name}`",
        f"- Aba analisada: `{analysis.sheet_name}`",
        f"- Total de amostras: {analysis.sample_count}",
        f"- Comprimentos de onda: {len(analysis.wavelength_headers)} (`{analysis.wavelength_headers[0]}` a `{analysis.wavelength_headers[-1]}`)",
        f"- Datas de coleta: {', '.join(analysis.dates)}",
        "- Genotipos normalizados: BR16, CD202, EMB48",
        "- Condicoes normalizadas: irrigado, nao_irrigado",
        f"- Linhas com metadados brutos inconsistentes (`bloco`, `genotipo` ou `condicao `): {analysis.raw_metadata_issue_rows}",
        f"- Linhas com token `C202` no nome do arquivo, normalizadas para `CD202`: {analysis.filename_typo_rows}",
        f"- Valores ausentes nas colunas espectrais: {analysis.missing_wavelength_values}",
        "",
        "## Regras de normalizacao",
        "",
        "- O agrupamento da analise foi derivado da coluna `nomenclaura`, porque `genotipo` e `condicao ` contem erros em parte da planilha.",
        "- `IRR`, `IRRG` e `IRRIG` foram tratados como `irrigado`.",
        "- `NIRR` e `NIRRIG` foram tratados como `nao_irrigado`.",
        "- `C202` no nome do arquivo foi tratado como `CD202`.",
        "",
        "## Amostras por grupo",
        "",
        "| data_coleta | genotipo | condicao | n_amostras |",
        "| --- | --- | --- | ---: |",
    ]

    for date_iso, genotype, condition_code, count in analysis.group_counts:
        lines.append(
            f"| {date_iso} | {genotype} | {CONDITION_LABELS[condition_code]} | {count} |"
        )

    if analysis.normalization_examples:
        lines.extend(
            [
                "",
                "## Exemplos de normalizacao automatica",
                "",
                "| linha | arquivo | origem | ajuste |",
                "| ---: | --- | --- | --- |",
            ]
        )
        for row_number, file_name, source, adjustment in analysis.normalization_examples:
            lines.append(f"| {row_number} | `{file_name}` | {source} | {adjustment} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_workbook(path: Path, sheets: list[tuple[str, list[list[str | float]]]]) -> None:
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for sheet_index in range(1, len(sheets) + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{sheet_index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    root_relationships = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>',
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>',
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>',
            "</Relationships>",
        ]
    )

    workbook_xml_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'xmlns:r="{NS_REL}">'
        ),
        "<sheets>",
    ]
    for sheet_index, (sheet_name, _) in enumerate(sheets, start=1):
        workbook_xml_lines.append(
            f'<sheet name="{escape(sheet_name)}" sheetId="{sheet_index}" r:id="rId{sheet_index}"/>'
        )
    workbook_xml_lines.extend(["</sheets>", "</workbook>"])

    workbook_relationships_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for sheet_index in range(1, len(sheets) + 1):
        workbook_relationships_lines.append(
            f'<Relationship Id="rId{sheet_index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{sheet_index}.xml"/>'
        )
    workbook_relationships_lines.append(
        f'<Relationship Id="rId{len(sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_relationships_lines.append("</Relationships>")

    styles_xml = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font></fonts>',
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>',
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>',
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>',
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>',
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>',
            "</styleSheet>",
        ]
    )

    app_xml = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            (
                '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
                'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            ),
            "<Application>Codex</Application>",
            "</Properties>",
        ]
    )

    core_xml = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            (
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" '
                'xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            ),
            "<dc:title>Estatistica descritiva</dc:title>",
            "<dc:creator>Codex</dc:creator>",
            "<cp:lastModifiedBy>Codex</cp:lastModifiedBy>",
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{created_at}</dcterms:created>',
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{created_at}</dcterms:modified>',
            "</cp:coreProperties>",
        ]
    )

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", "\n".join(content_types))
        workbook.writestr("_rels/.rels", root_relationships)
        workbook.writestr("xl/workbook.xml", "\n".join(workbook_xml_lines))
        workbook.writestr(
            "xl/_rels/workbook.xml.rels", "\n".join(workbook_relationships_lines)
        )
        workbook.writestr("xl/styles.xml", styles_xml)
        workbook.writestr("docProps/app.xml", app_xml)
        workbook.writestr("docProps/core.xml", core_xml)

        for sheet_index, (_, rows) in enumerate(sheets, start=1):
            workbook.writestr(
                f"xl/worksheets/sheet{sheet_index}.xml",
                build_worksheet_xml(rows),
            )


def build_worksheet_xml(rows: list[list[str | float]]) -> str:
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]

    for row_index, row in enumerate(rows, start=1):
        xml_lines.append(f'<row r="{row_index}">')
        for column_index_value, value in enumerate(row, start=1):
            if value is None or value == "":
                continue

            reference = f"{column_letter(column_index_value - 1)}{row_index}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                xml_lines.append(f'<c r="{reference}"><v>{value}</v></c>')
                continue

            text = str(value)
            if text.startswith(" ") or text.endswith(" "):
                xml_lines.append(
                    f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'
                )
            else:
                xml_lines.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'
                )
        xml_lines.append("</row>")

    xml_lines.extend(["</sheetData>", "</worksheet>"])
    return "\n".join(xml_lines)


def build_workbook_rows(
    analysis: AnalysisResult,
    mean_rows: list[list[str]],
    cv_rows: list[list[str]],
) -> list[tuple[str, list[list[str | float]]]]:
    common_header = [
        "data_coleta",
        "genotipo",
        "condicao",
        "n_amostras",
        *analysis.wavelength_headers,
    ]

    counts_rows: list[list[str | float]] = [
        ["data_coleta", "genotipo", "condicao", "n_amostras"]
    ]
    for date_iso, genotype, condition_code, count in analysis.group_counts:
        counts_rows.append(
            [date_iso, genotype, CONDITION_LABELS[condition_code], float(count)]
        )

    summary_rows: list[list[str | float]] = [
        ["metrica", "valor"],
        ["arquivo", analysis.workbook_path.name],
        ["aba", analysis.sheet_name],
        ["total_amostras", float(analysis.sample_count)],
        ["total_datas", float(len(analysis.dates))],
        ["primeiro_comprimento_onda", float(analysis.wavelength_headers[0])],
        ["ultimo_comprimento_onda", float(analysis.wavelength_headers[-1])],
        ["total_comprimentos_onda", float(len(analysis.wavelength_headers))],
        ["linhas_com_metadados_brutos_inconsistentes", float(analysis.raw_metadata_issue_rows)],
        ["linhas_com_token_C202_normalizado", float(analysis.filename_typo_rows)],
        ["valores_ausentes_nas_colunas_espectrais", float(analysis.missing_wavelength_values)],
        [],
        ["data_coleta", "genotipo", "condicao", "n_amostras"],
    ]
    for date_iso, genotype, condition_code, count in analysis.group_counts:
        summary_rows.append(
            [date_iso, genotype, CONDITION_LABELS[condition_code], float(count)]
        )

    return [
        ("media", [common_header, *mean_rows]),
        ("coef_var", [common_header, *cv_rows]),
        ("amostras", counts_rows),
        ("resumo", summary_rows),
    ]


def main() -> None:
    args = parse_args()
    workbook_path = args.input.resolve()
    output_dir = args.output_dir.resolve()

    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    analysis = analyze_dataset(workbook_path)
    common_header = [
        "data_coleta",
        "genotipo",
        "condicao",
        "n_amostras",
        *analysis.wavelength_headers,
    ]

    mean_rows = build_stat_rows(analysis, metric="mean")
    cv_rows = build_stat_rows(analysis, metric="cv")
    count_rows = [
        [date_iso, genotype, CONDITION_LABELS[condition_code], str(count)]
        for date_iso, genotype, condition_code, count in analysis.group_counts
    ]

    mean_csv_path = output_dir / "estatistica_descritiva_media.csv"
    cv_csv_path = output_dir / "estatistica_descritiva_coeficiente_variacao.csv"
    counts_csv_path = output_dir / "amostras_por_grupo.csv"
    summary_md_path = output_dir / "resumo_dataset.md"
    workbook_output_path = output_dir / "estatistica_descritiva.xlsx"

    write_csv(mean_csv_path, common_header, mean_rows)
    write_csv(cv_csv_path, common_header, cv_rows)
    write_csv(
        counts_csv_path,
        ["data_coleta", "genotipo", "condicao", "n_amostras"],
        count_rows,
    )
    write_summary_markdown(summary_md_path, analysis)
    write_workbook(workbook_output_path, build_workbook_rows(analysis, mean_rows, cv_rows))

    print(f"Input workbook: {workbook_path}")
    print(f"Samples processed: {analysis.sample_count}")
    print(f"Groups generated: {len(analysis.group_counts)}")
    print(f"Wavelength columns: {len(analysis.wavelength_headers)}")
    print(f"Rows with raw metadata issues: {analysis.raw_metadata_issue_rows}")
    print(f"Rows with normalized C202 token: {analysis.filename_typo_rows}")
    print("Outputs:")
    print(f"  - {mean_csv_path}")
    print(f"  - {cv_csv_path}")
    print(f"  - {counts_csv_path}")
    print(f"  - {summary_md_path}")
    print(f"  - {workbook_output_path}")


if __name__ == "__main__":
    main()
