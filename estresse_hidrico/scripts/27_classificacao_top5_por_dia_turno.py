#!/usr/bin/env python3
"""Run classification for each day/turn using TOP5 significant bands."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from significance_classification_utils import (
    available_band_columns,
    band_column_to_wavelength,
    build_group_labels,
    build_model_library,
    choose_best_model,
    evaluate_model_cv,
    prepare_targets,
    sanitize_model_name,
    write_csv,
)


SCENARIO_PATTERN = re.compile(r"^TOP5_(cond|gen|gen_cond)_D(\d{2})([MT])_(MANHA|TARDE)\.csv$")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    workspace_dir = project_dir.parent
    parser = argparse.ArgumentParser(
        description="Executa classificacao para cada dia/turno usando bandas TOP5 selecionadas."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "dados" / "processados" / "replicatas_bloco_dia.csv",
    )
    parser.add_argument(
        "--top5-dir",
        type=Path,
        default=workspace_dir / "TestesSignfDiniz" / "TOP5_POR_DIA_TURNO",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "outputs" / "tabelas" / "classificacao_top5_por_dia_turno",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def map_analysis_to_target_column(analysis: str) -> str:
    if analysis == "cond":
        return "target_condicao"
    if analysis == "gen":
        return "cultivar"
    if analysis == "gen_cond":
        return "target_condicao_genotipo"
    raise ValueError(f"Analise nao suportada: {analysis}")


def day_code_to_label(day_code: str) -> str:
    return f"dia{int(day_code)}"


def resolve_features_from_top5(top5_df: pd.DataFrame, band_columns: list[str]) -> tuple[list[str], pd.DataFrame]:
    band_lookup = {band_column_to_wavelength(column): column for column in band_columns}
    wavelengths = sorted(band_lookup)
    rows: list[dict[str, object]] = []
    selected: list[str] = []
    used: set[str] = set()
    for _, row in top5_df.sort_values("rank").iterrows():
        w = int(round(float(row["wavelength_nm"])))
        if w in band_lookup:
            band = band_lookup[w]
            resolved = w
            exact = True
        else:
            resolved = min(wavelengths, key=lambda c: (abs(c - w), c))
            band = band_lookup[resolved]
            exact = False
        if band in used:
            continue
        used.add(band)
        selected.append(band)
        rows.append(
            {
                "rank": int(row["rank"]),
                "wavelength_nm": w,
                "resolved_wavelength_nm": int(resolved),
                "band_column": band,
                "resolved_exact_match": bool(exact),
                "q_FDR_BH": float(row["q_FDR_BH"]) if pd.notna(row["q_FDR_BH"]) else None,
            }
        )
    if not selected:
        raise ValueError("Nenhuma banda foi resolvida a partir do TOP5.")
    return selected, pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = prepare_targets(pd.read_csv(args.input.resolve()))
    band_columns = available_band_columns(frame)
    if not band_columns:
        raise ValueError("Nenhuma coluna band_* no dataset.")

    scenario_files = []
    for path in sorted(args.top5_dir.resolve().glob("TOP5_*.csv")):
        match = SCENARIO_PATTERN.match(path.name)
        if match:
            scenario_files.append((path, match))

    all_metrics: list[dict[str, object]] = []
    all_best: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []

    for scenario_path, match in scenario_files:
        analysis = match.group(1)
        day_code = match.group(2)
        turno_code = match.group(3)
        turno_label = match.group(4)
        day_label = day_code_to_label(day_code)
        subset = frame.loc[frame["dia"].astype(str) == day_label].copy().reset_index(drop=True)
        if subset.empty:
            skipped.append({"scenario": scenario_path.stem, "reason": f"dia {day_label} ausente no dataset"})
            continue

        top5_df = pd.read_csv(scenario_path)
        features, manifest_df = resolve_features_from_top5(top5_df, band_columns)
        label_column = map_analysis_to_target_column(analysis)
        class_names = sorted(subset[label_column].astype(str).unique().tolist())
        groups = build_group_labels(subset[label_column], subset["replicata"])
        min_groups = int(pd.Series(groups).groupby(subset[label_column]).nunique().min())
        n_splits = min(5, max(2, min_groups))
        models = build_model_library(num_classes=len(class_names), random_state=args.seed)

        scenario_id = scenario_path.stem
        scenario_dir = output_dir / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        write_csv(manifest_df, scenario_dir / "bandas_resolvidas.csv")

        metric_rows: list[dict[str, object]] = []
        for model_name, model in models.items():
            artifacts = evaluate_model_cv(
                model_name=model_name,
                model=model,
                frame=subset,
                feature_columns=features,
                label_column=label_column,
                target_name=analysis,
                class_names=class_names,
                groups=groups,
                n_splits=n_splits,
            )
            row = dict(artifacts.metrics_row)
            row.update(
                {
                    "scenario_id": scenario_id,
                    "analysis": analysis,
                    "dia_code": day_code,
                    "dia": day_label,
                    "turno_code": turno_code,
                    "turno": turno_label,
                    "validation_mode": "cv_grouped",
                    "split_seed": args.seed,
                }
            )
            metric_rows.append(row)
            all_metrics.append(row)
            slug = sanitize_model_name(model_name)
            write_csv(pd.DataFrame([row]), scenario_dir / f"metricas_{slug}.csv")
            write_csv(artifacts.per_class_df, scenario_dir / f"metricas_por_classe_{slug}.csv")
            write_csv(artifacts.confusion_df, scenario_dir / f"matriz_confusao_{slug}.csv")
            write_csv(artifacts.predictions_df, scenario_dir / f"predicoes_cv_{slug}.csv")

        metrics_df = pd.DataFrame(metric_rows)
        write_csv(metrics_df, scenario_dir / "metricas_todos_modelos.csv")
        best = dict(choose_best_model(metrics_df))
        best.update(
            {
                "scenario_id": scenario_id,
                "analysis": analysis,
                "dia_code": day_code,
                "dia": day_label,
                "turno_code": turno_code,
                "turno": turno_label,
            }
        )
        all_best.append(best)
        print(
            f"[{scenario_id}] best={best['model']} "
            f"ACC={best['accuracy_media']:.4f} F1={best['f1_macro_media']:.4f} "
            f"KAPPA={best['kappa_media']:.4f}"
        )

    all_metrics_df = pd.DataFrame(all_metrics)
    all_best_df = pd.DataFrame(all_best)
    write_csv(all_metrics_df, output_dir / "metricas_todos_cenarios.csv")
    write_csv(all_best_df, output_dir / "melhor_modelo_por_cenario.csv")
    if skipped:
        write_csv(pd.DataFrame(skipped), output_dir / "cenarios_pulados.csv")

    summary_lines = [
        "# Classificacao por dia/turno com TOP5",
        "",
        f"- Cenarios processados: `{len(all_best)}`",
        f"- Cenarios pulados: `{len(skipped)}`",
        "",
        "| scenario | analysis | dia | turno | best_model | accuracy | f1_macro | kappa |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    if not all_best_df.empty:
        for _, row in all_best_df.sort_values(["analysis", "dia_code", "turno_code"]).iterrows():
            summary_lines.append(
                f"| {row['scenario_id']} | {row['analysis']} | {row['dia']} | {row['turno']} | {row['model']} | "
                f"{row['accuracy_media']:.4f} | {row['f1_macro_media']:.4f} | {row['kappa_media']:.4f} |"
            )
    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"\nOutput: {output_dir}")


if __name__ == "__main__":
    main()
