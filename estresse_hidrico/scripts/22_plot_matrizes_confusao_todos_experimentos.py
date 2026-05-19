#!/usr/bin/env python3
"""Generate consolidated confusion-matrix figures for all available experiments."""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TABLES_DIR = REPO_ROOT / "estresse_hidrico" / "outputs" / "tabelas"
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "estresse_hidrico"
    / "outputs"
    / "figuras"
    / "matrizes_confusao_todos_experimentos"
)

DAY_SEQUENCE = ["dia2", "dia3", "dia4", "dia5", "dia6", "dia9"]
CULTIVAR_SEQUENCE = ["BR16", "CD202", "EMB48"]
TARGET_SEQUENCE = ["condicao", "condicao_genotipo", "condicao_genotipo_turno"]
MODEL_SEQUENCE = ["Random_Forest", "SVM_RBF", "LDA", "k-NN_k5", "k_NN_k_5", "XGBoost"]

DAY_ORDER = {day: idx for idx, day in enumerate(DAY_SEQUENCE)}
CULTIVAR_ORDER = {cultivar: idx for idx, cultivar in enumerate(CULTIVAR_SEQUENCE)}
TARGET_ORDER = {target: idx for idx, target in enumerate(TARGET_SEQUENCE)}
MODEL_ORDER = {model: idx for idx, model in enumerate(MODEL_SEQUENCE)}

PRETTY_MODELS = {
    "Random_Forest": "Random Forest",
    "RandomForest": "Random Forest",
    "SVM_RBF": "SVM (RBF)",
    "LDA": "LDA",
    "k-NN_k5": "k-NN (k=5)",
    "k_NN_k_5": "k-NN (k=5)",
    "XGBoost": "XGBoost",
}

PRETTY_TARGETS = {
    "condicao": "Condicao",
    "condicao_genotipo": "Condicao + genotipo",
    "condicao_genotipo_turno": "Condicao + genotipo + turno",
}

BASE_META_COLUMNS = {
    "analysis_id",
    "analysis_label",
    "scope",
    "cultivar",
    "dia",
    "modelo",
    "model",
    "target",
    "real",
    "Classe verdadeira",
}


@dataclass
class MatrixEntry:
    panel_title: str
    source_path: Path
    row_labels: list[str]
    col_labels: list[str]
    matrix: np.ndarray
    order_key: tuple


@dataclass
class FigureSpec:
    figure_id: str
    title: str
    ncols: int
    sort_rank: int
    entries: list[MatrixEntry] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot all available confusion matrices grouped by experiment family."
    )
    parser.add_argument(
        "--tables-dir",
        type=Path,
        default=DEFAULT_TABLES_DIR,
        help="Directory containing result CSV tables.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where consolidated figures will be written.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_model_id(model_id: str) -> str:
    return model_id.strip().replace(" ", "_")


def extract_model_id_from_filename(path: Path) -> str:
    name = path.stem
    if name.startswith("matriz_confusao_"):
        return normalize_model_id(name.removeprefix("matriz_confusao_"))
    if name.startswith("confusion_matrix_"):
        return normalize_model_id(name.removeprefix("confusion_matrix_"))
    if name.startswith("optuna_confusion_matrix_"):
        return normalize_model_id(name.removeprefix("optuna_confusion_matrix_"))
    return normalize_model_id(name)


def pretty_model(model_id: str) -> str:
    return PRETTY_MODELS.get(model_id, model_id.replace("_", " "))


def pretty_day(day: str) -> str:
    match = re.search(r"(\d+)", day)
    return f"Dia {match.group(1)}" if match else day


def pretty_target(target: str) -> str:
    return PRETTY_TARGETS.get(target, target.replace("_", " "))


def shorten_label(label: str) -> str:
    text = str(label).strip()
    text = text.replace("Nao irrigado", "NIRR")
    text = text.replace("Irrigado", "IRR")
    text = text.replace("manha + tarde", "M+T")
    text = text.replace("unico", "U")

    match = re.match(r"^[A-Z]\s+\(([^)]+)\)$", text)
    if match:
        text = match.group(1)

    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
        return "\n".join(parts)

    tokens = text.split()
    if len(tokens) == 2 and all(len(token) <= 8 for token in tokens):
        return "\n".join(tokens)

    if len(text) > 18 and " " in text:
        left, right = text.split(" ", 1)
        return f"{left}\n{right}"

    return text


def compact_label(label: str) -> str:
    text = str(label).strip()
    text = text.replace("Nao irrigado", "NIRR")
    text = text.replace("Irrigado", "IRR")
    text = text.replace("manha + tarde", "MT")
    text = text.replace("unico", "U")

    match = re.match(r"^[A-Z]\s+\(([^)]+)\)$", text)
    if match:
        text = match.group(1)

    def abbreviate_token(token: str) -> str:
        token = token.strip()
        mapping = {
            "IRR": "I",
            "NIRR": "N",
            "BR16": "B16",
            "CD202": "C202",
            "EMB48": "E48",
            "MT": "MT",
            "U": "U",
        }
        return mapping.get(token, token)

    if "|" in text:
        parts = [abbreviate_token(part) for part in text.split("|")]
        return "_".join(parts)

    tokens = [abbreviate_token(token) for token in text.split()]
    text = "_".join(tokens)
    text = re.sub(r"[^A-Za-z0-9_+.-]", "", text)
    return text


def select_true_label_column(df: pd.DataFrame, excluded_columns: set[str]) -> str:
    if "real" in df.columns:
        return "real"
    if "Classe verdadeira" in df.columns:
        return "Classe verdadeira"

    for column in df.columns:
        if column in excluded_columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[column]):
            return column

    raise ValueError("Unable to determine the true-label column.")


def matrix_from_dataframe(df: pd.DataFrame, extra_meta_columns: set[str] | None = None) -> tuple[list[str], list[str], np.ndarray]:
    extra_meta_columns = extra_meta_columns or set()
    excluded_columns = BASE_META_COLUMNS | extra_meta_columns
    true_col = select_true_label_column(df, excluded_columns)
    pred_cols = [column for column in df.columns if column not in excluded_columns and column != true_col]

    if not pred_cols:
        raise ValueError("No predicted-label columns were found.")

    numeric_matrix = df[pred_cols].apply(pd.to_numeric, errors="coerce")
    valid_rows = numeric_matrix.notna().all(axis=1)
    numeric_matrix = numeric_matrix.loc[valid_rows]
    label_rows = df.loc[valid_rows, true_col].astype(str)

    if numeric_matrix.empty:
        raise ValueError("Confusion matrix contains no numeric rows.")

    return label_rows.tolist(), [str(column) for column in pred_cols], numeric_matrix.to_numpy(dtype=float)


def add_single_entry(
    figure: FigureSpec,
    path: Path,
    panel_title: str,
    order_key: tuple,
    extra_meta_columns: set[str] | None = None,
) -> None:
    if not path.exists():
        return

    df = read_csv(path)
    row_labels, col_labels, matrix = matrix_from_dataframe(df, extra_meta_columns)
    figure.entries.append(
        MatrixEntry(
            panel_title=panel_title,
            source_path=path,
            row_labels=row_labels,
            col_labels=col_labels,
            matrix=matrix,
            order_key=order_key,
        )
    )


def add_grouped_entries(
    figure: FigureSpec,
    path: Path,
    group_columns: list[str],
    panel_title_builder,
    order_key_builder,
) -> None:
    if not path.exists():
        return

    df = read_csv(path)
    grouped = df.groupby(group_columns, sort=False, dropna=False)

    for raw_key, group_df in grouped:
        key = raw_key if isinstance(raw_key, tuple) else (raw_key,)
        row_labels, col_labels, matrix = matrix_from_dataframe(group_df, set(group_columns))
        figure.entries.append(
            MatrixEntry(
                panel_title=panel_title_builder(*key),
                source_path=path,
                row_labels=row_labels,
                col_labels=col_labels,
                matrix=matrix,
                order_key=order_key_builder(*key),
            )
        )


def empty_figure_specs() -> list[FigureSpec]:
    return [
        FigureSpec(
            figure_id="01_multiclasse_global_e_subsets",
            title="Matrizes de confusao - classificacao multiclasse global e subsets",
            ncols=3,
            sort_rank=1,
        ),
        FigureSpec(
            figure_id="02_subset_por_dia_lda_optuna",
            title="Matrizes de confusao - subset por dia (LDA/Optuna)",
            ncols=3,
            sort_rank=2,
        ),
        FigureSpec(
            figure_id="03_irrigacao_bandas_diversificadas",
            title="Matrizes de confusao - irrigacao com bandas diversificadas",
            ncols=4,
            sort_rank=3,
        ),
        FigureSpec(
            figure_id="04_irrigacao_por_dia_todos_genotipos",
            title="Matrizes de confusao - irrigacao por dia (todos os genotipos)",
            ncols=5,
            sort_rank=4,
        ),
        FigureSpec(
            figure_id="11_significancia_global",
            title="Matrizes de confusao - classificacao global com bandas do teste de significancia",
            ncols=5,
            sort_rank=11,
        ),
    ]


def build_figure_specs(tables_dir: Path) -> list[FigureSpec]:
    figures = {figure.figure_id: figure for figure in empty_figure_specs()}

    add_single_entry(
        figures["01_multiclasse_global_e_subsets"],
        tables_dir / "confusion_matrix.csv",
        panel_title="04_classificacao",
        order_key=(0,),
    )
    add_single_entry(
        figures["01_multiclasse_global_e_subsets"],
        tables_dir / "classificacao_subset_bandas" / "confusion_matrix_kruskal_top_20.csv",
        panel_title="07_subset_bandas",
        order_key=(1,),
    )
    add_single_entry(
        figures["01_multiclasse_global_e_subsets"],
        tables_dir / "optuna_classificacao_subset" / "optuna_confusion_matrix_kruskal_top_20.csv",
        panel_title="08_optuna_subset",
        order_key=(2,),
    )

    add_grouped_entries(
        figures["02_subset_por_dia_lda_optuna"],
        tables_dir / "classificacao_subset_por_dia" / "lda_optuna_best_kruskal_top_20_confusion_by_day.csv",
        group_columns=["dia"],
        panel_title_builder=lambda day: pretty_day(day),
        order_key_builder=lambda day: (DAY_ORDER.get(day, 999),),
    )

    add_single_entry(
        figures["03_irrigacao_bandas_diversificadas"],
        tables_dir / "classificacao_irrigacao_bandas_diversificadas" / "matriz_confusao.csv",
        panel_title="Global",
        order_key=(0,),
    )
    for cultivar in CULTIVAR_SEQUENCE:
        add_single_entry(
            figures["03_irrigacao_bandas_diversificadas"],
            tables_dir
            / "classificacao_irrigacao_bandas_diversificadas"
            / "por_genotipo"
            / cultivar
            / "matriz_confusao.csv",
            panel_title=cultivar,
            order_key=(1 + CULTIVAR_ORDER[cultivar],),
        )

    por_dia_dir = tables_dir / "classificacao_irrigacao_por_dia"
    for path in sorted(por_dia_dir.glob("dia*/matriz_confusao_*.csv")):
        day = path.parent.name
        model_id = extract_model_id_from_filename(path)
        add_single_entry(
            figures["04_irrigacao_por_dia_todos_genotipos"],
            path,
            panel_title=f"{pretty_day(day)}\n{pretty_model(model_id)}",
            order_key=(DAY_ORDER.get(day, 999), MODEL_ORDER.get(model_id, 999), model_id),
        )

    for day in DAY_SEQUENCE:
        figure_id = f"05_irrigacao_por_dia_genotipo_{day}"
        figures[figure_id] = FigureSpec(
            figure_id=figure_id,
            title=f"Matrizes de confusao - irrigacao por dia e genotipo - {pretty_day(day)}",
            ncols=5,
            sort_rank=5 + DAY_ORDER[day],
        )
        for cultivar in CULTIVAR_SEQUENCE:
            base_dir = tables_dir / "classificacao_irrigacao_por_dia_genotipo" / day / cultivar
            for path in sorted(base_dir.glob("matriz_confusao_*.csv")):
                model_id = extract_model_id_from_filename(path)
                add_single_entry(
                    figures[figure_id],
                    path,
                    panel_title=f"{cultivar}\n{pretty_model(model_id)}",
                    order_key=(CULTIVAR_ORDER[cultivar], MODEL_ORDER.get(model_id, 999), model_id),
                )

    sign_dir = tables_dir / "classificacao_significancia_global"
    for target in TARGET_SEQUENCE:
        target_dir = sign_dir / target
        for path in sorted(target_dir.glob("matriz_confusao_*.csv")):
            model_id = extract_model_id_from_filename(path)
            add_single_entry(
                figures["11_significancia_global"],
                path,
                panel_title=f"{pretty_target(target)}\n{pretty_model(model_id)}",
                order_key=(TARGET_ORDER[target], MODEL_ORDER.get(model_id, 999), model_id),
            )

    return sorted(
        [figure for figure in figures.values() if figure.entries],
        key=lambda figure: (figure.sort_rank, figure.figure_id),
    )


def choose_panel_size(entries: list[MatrixEntry]) -> float:
    max_dimension = max(max(entry.matrix.shape) for entry in entries)
    if max_dimension <= 2:
        return 3.6
    if max_dimension <= 6:
        return 4.5
    return 5.4


def annotation_font_size(entry: MatrixEntry) -> int:
    max_dimension = max(entry.matrix.shape)
    if max_dimension <= 2:
        return 12
    if max_dimension <= 6:
        return 9
    return 7


def tick_font_size(entry: MatrixEntry) -> int:
    max_dimension = max(entry.matrix.shape)
    if max_dimension <= 2:
        return 11
    if max_dimension <= 6:
        return 8
    return 6


def title_font_size(entry: MatrixEntry) -> int:
    max_dimension = max(entry.matrix.shape)
    if max_dimension <= 2:
        return 11
    if max_dimension <= 6:
        return 10
    return 9


def plot_entry(ax: plt.Axes, entry: MatrixEntry, show_xlabel: bool, show_ylabel: bool):
    matrix = np.asarray(entry.matrix, dtype=float)
    row_sums = matrix.sum(axis=1, keepdims=True)
    normalized = np.divide(matrix, row_sums, out=np.zeros_like(matrix, dtype=float), where=row_sums != 0)

    image = ax.imshow(normalized, cmap="Blues", vmin=0.0, vmax=1.0)

    ann_size = annotation_font_size(entry)
    tick_size = tick_font_size(entry)
    title_size = title_font_size(entry)

    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            count = int(round(matrix[row_idx, col_idx]))
            text_color = "white" if normalized[row_idx, col_idx] >= 0.5 else "black"
            ax.text(
                col_idx,
                row_idx,
                str(count),
                ha="center",
                va="center",
                fontsize=ann_size,
                color=text_color,
            )

    x_labels = [shorten_label(label) for label in entry.col_labels]
    y_labels = [shorten_label(label) for label in entry.row_labels]

    ax.set_xticks(np.arange(len(x_labels)))
    ax.set_yticks(np.arange(len(y_labels)))
    ax.set_xticklabels(
        x_labels,
        fontsize=tick_size,
        rotation=45 if len(x_labels) > 6 else 0,
        ha="right" if len(x_labels) > 6 else "center",
    )
    ax.set_yticklabels(y_labels, fontsize=tick_size)
    ax.set_title(entry.panel_title, fontsize=title_size, fontweight="bold", pad=6)

    if show_xlabel:
        ax.set_xlabel("Predito", fontsize=tick_size)
    if show_ylabel:
        ax.set_ylabel("Real", fontsize=tick_size)

    ax.set_xticks(np.arange(-0.5, len(x_labels), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(y_labels), 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=0.6)
    ax.tick_params(which="minor", bottom=False, left=False)

    return image


def text_table_font_size(entry: MatrixEntry) -> float:
    max_dimension = max(entry.matrix.shape)
    if max_dimension <= 2:
        return 10.5
    if max_dimension <= 6:
        return 7.6
    return 5.4


def table_title_font_size(entry: MatrixEntry) -> int:
    max_dimension = max(entry.matrix.shape)
    if max_dimension <= 2:
        return 9
    if max_dimension <= 6:
        return 8
    return 7


def render_text_table(ax: plt.Axes, entry: MatrixEntry) -> None:
    row_labels = [compact_label(label) for label in entry.row_labels]
    col_labels = [compact_label(label) for label in entry.col_labels]
    values = np.asarray(entry.matrix, dtype=int)

    df = pd.DataFrame(values, index=row_labels, columns=col_labels)
    table_text = df.to_string()

    ax.axis("off")
    ax.set_title("Tabela", fontsize=table_title_font_size(entry), fontweight="bold", pad=4)
    ax.text(
        0.0,
        0.98,
        table_text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        family="monospace",
        fontsize=text_table_font_size(entry),
    )


def render_figure(spec: FigureSpec, output_dir: Path, pdf: PdfPages | None) -> Path:
    entries = sorted(spec.entries, key=lambda entry: entry.order_key)
    n_panels = len(entries)
    ncols = spec.ncols
    nrows = math.ceil(n_panels / ncols)
    panel_size = choose_panel_size(entries)
    fig_width = max(12.0, ncols * panel_size)
    fig_height = max(6.0, nrows * panel_size)

    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_width, fig_height), squeeze=False)
    axes_flat = list(axes.ravel())
    last_image = None

    for idx, (ax, entry) in enumerate(zip(axes_flat, entries)):
        row_idx = idx // ncols
        col_idx = idx % ncols
        last_image = plot_entry(
            ax,
            entry,
            show_xlabel=row_idx == nrows - 1,
            show_ylabel=col_idx == 0,
        )

    for ax in axes_flat[n_panels:]:
        ax.axis("off")

    fig.suptitle(
        f"{spec.title}\nCor = proporcao por classe real; texto = contagem absoluta",
        fontsize=16,
        y=0.995,
    )
    fig.subplots_adjust(left=0.06, right=0.94, top=0.90, bottom=0.08, wspace=0.35, hspace=0.45)

    if last_image is not None:
        used_axes = axes_flat[:n_panels]
        colorbar = fig.colorbar(last_image, ax=used_axes, fraction=0.018, pad=0.01)
        colorbar.set_label("Proporcao por classe real", fontsize=10)
        colorbar.ax.tick_params(labelsize=9)

    output_path = output_dir / f"{spec.figure_id}.png"
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    if pdf is not None:
        pdf.savefig(fig, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output_path


def render_significance_figure_with_tables(spec: FigureSpec, output_dir: Path) -> Path:
    entries = sorted(spec.entries, key=lambda entry: entry.order_key)
    n_panels = len(entries)
    ncols = spec.ncols
    nrows = math.ceil(n_panels / ncols)
    panel_size = choose_panel_size(entries)
    fig_width = max(34.0, ncols * panel_size * 2.35)
    fig_height = max(10.0, nrows * panel_size * 1.20)

    width_ratios: list[float] = []
    for _ in range(ncols):
        width_ratios.extend([1.0, 1.85])

    fig = plt.figure(figsize=(fig_width, fig_height))
    grid = fig.add_gridspec(
        nrows=nrows,
        ncols=ncols * 2,
        width_ratios=width_ratios,
        wspace=0.22,
        hspace=0.40,
    )
    last_image = None
    used_axes: list[plt.Axes] = []

    for idx, entry in enumerate(entries):
        row_idx = idx // ncols
        col_idx = idx % ncols
        matrix_ax = fig.add_subplot(grid[row_idx, col_idx * 2])
        table_ax = fig.add_subplot(grid[row_idx, col_idx * 2 + 1])
        last_image = plot_entry(
            matrix_ax,
            entry,
            show_xlabel=row_idx == nrows - 1,
            show_ylabel=col_idx == 0,
        )
        render_text_table(table_ax, entry)
        used_axes.extend([matrix_ax, table_ax])

    for idx in range(n_panels, nrows * ncols):
        row_idx = idx // ncols
        col_idx = idx % ncols
        for axis_idx in (col_idx * 2, col_idx * 2 + 1):
            ax = fig.add_subplot(grid[row_idx, axis_idx])
            ax.axis("off")

    fig.suptitle(
        f"{spec.title} - matrizes com tabelas laterais\nCor = proporcao por classe real; texto = contagem absoluta",
        fontsize=16,
        y=0.995,
    )
    fig.subplots_adjust(left=0.035, right=0.97, top=0.91, bottom=0.06)

    if last_image is not None and used_axes:
        colorbar = fig.colorbar(last_image, ax=used_axes, fraction=0.010, pad=0.006)
        colorbar.set_label("Proporcao por classe real", fontsize=10)
        colorbar.ax.tick_params(labelsize=9)

    output_path = output_dir / f"{spec.figure_id}_com_tabelas.png"
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def write_catalog(figures: list[FigureSpec], output_dir: Path) -> Path:
    rows: list[dict[str, object]] = []
    for figure in figures:
        for entry in sorted(figure.entries, key=lambda item: item.order_key):
            rows.append(
                {
                    "figure_id": figure.figure_id,
                    "figure_title": figure.title,
                    "panel_title": entry.panel_title,
                    "n_true_classes": len(entry.row_labels),
                    "n_pred_classes": len(entry.col_labels),
                    "row_labels": " | ".join(entry.row_labels),
                    "col_labels": " | ".join(entry.col_labels),
                    "source_path": str(entry.source_path),
                }
            )

    catalog_path = output_dir / "catalogo_matrizes_confusao.csv"
    pd.DataFrame(rows).to_csv(catalog_path, index=False, encoding="utf-8-sig")
    return catalog_path


def write_readme(
    figures: list[FigureSpec],
    output_paths: list[Path],
    catalog_path: Path,
    output_dir: Path,
    supplemental_figures: list[tuple[Path, str]] | None = None,
) -> Path:
    total_matrices = sum(len(figure.entries) for figure in figures)
    supplemental_figures = supplemental_figures or []
    readme_path = output_dir / "README.md"
    lines = [
        "# Matrizes de confusao - todos os experimentos",
        "",
        f"- Figuras geradas: {len(output_paths) + len(supplemental_figures)}",
        f"- Matrizes consolidadas: {total_matrices}",
        "- Escala de cor: proporcao por classe real",
        "- Texto dentro das celulas: contagem absoluta",
        "",
        "## Arquivos principais",
        f"- PDF consolidado: `{(output_dir / 'matrizes_confusao_todos_experimentos.pdf').name}`",
        f"- Catalogo CSV: `{catalog_path.name}`",
        "",
        "## Figuras",
    ]

    for figure, output_path in zip(figures, output_paths):
        lines.append(f"- `{output_path.name}`: {figure.title} ({len(figure.entries)} matrizes)")
    for output_path, description in supplemental_figures:
        lines.append(f"- `{output_path.name}`: {description}")

    readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return readme_path


def main() -> None:
    args = parse_args()
    tables_dir = args.tables_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    figures = build_figure_specs(tables_dir)
    if not figures:
        raise FileNotFoundError(f"No confusion matrices were discovered under {tables_dir}")

    pdf_path = output_dir / "matrizes_confusao_todos_experimentos.pdf"
    output_paths: list[Path] = []
    supplemental_figures: list[tuple[Path, str]] = []

    with PdfPages(pdf_path) as pdf:
        for figure in figures:
            output_paths.append(render_figure(figure, output_dir, pdf))

    significance_figure = next(
        (figure for figure in figures if figure.figure_id == "11_significancia_global"),
        None,
    )
    if significance_figure is not None:
        supplemental_path = render_significance_figure_with_tables(significance_figure, output_dir)
        supplemental_figures.append(
            (
                supplemental_path,
                f"{significance_figure.title} com tabela textual ao lado de cada matriz ({len(significance_figure.entries)} matrizes)",
            )
        )

    catalog_path = write_catalog(figures, output_dir)
    readme_path = write_readme(
        figures,
        output_paths,
        catalog_path,
        output_dir,
        supplemental_figures=supplemental_figures,
    )

    print(f"Figures generated: {len(output_paths) + len(supplemental_figures)}")
    print(f"Matrices consolidated: {sum(len(figure.entries) for figure in figures)}")
    print(f"PDF: {pdf_path}")
    print(f"Catalog: {catalog_path}")
    print(f"README: {readme_path}")


if __name__ == "__main__":
    main()
