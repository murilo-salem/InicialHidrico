#!/usr/bin/env python3
"""Generate raw reflectance plots: IRRIGADO vs NAO_IRRIGADO, 3 genotypes, por dia e turno."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = Path(r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico')
OUTPUT_DIR = BASE_DIR / 'outputs' / 'reflectancia_bruta_genotipos'
TABELAS_DIR = OUTPUT_DIR / 'tabelas'

MEDIA_FILE = TABELAS_DIR / 'reflectancia_bruta_media_por_data_turno_genotipo_condicao.csv'
CV_FILE = TABELAS_DIR / 'reflectancia_bruta_cv_por_data_turno_genotipo_condicao.csv'

GENOTYPE_ORDER = ["BR16", "CD202", "EMB48"]
CONDITION_ORDER = ["irrigado", "nao_irrigado"]
TURN_ORDER = ["manha", "tarde"]
ALL_DAYS = ["2017-02-23", "2017-02-24", "2017-02-25", "2017-02-26", "2017-02-27", "2017-03-02"]
DAYS_WITH_TARDE = ["2017-02-23", "2017-02-24", "2017-03-02"]

GENOTYPE_COLORS = {
    "BR16": "#2563eb",
    "CD202": "#c2410c",
    "EMB48": "#0f766e",
}
GENOTYPE_MARKERS = {
    "BR16": "o",
    "CD202": "s",
    "EMB48": "^",
}
CONDITION_TITLES = {
    "irrigado": "IRRIGADO",
    "nao_irrigado": "NAO IRRIGADO",
}
TURN_TITLES = {
    "manha": "Manha",
    "tarde": "Tarde",
}

X_TICKS = [350, 700, 1050, 1400, 1750, 2100, 2500]
X_LIM = (340, 2510)


def get_band_columns(df):
    return [c for c in df.columns if c.isdigit()]


def load_data():
    media = pd.read_csv(MEDIA_FILE)
    cv = pd.read_csv(CV_FILE)
    return media, cv


def downsample_series(waves, values, max_points=400):
    if len(waves) <= max_points:
        return waves, values
    step = len(waves) // max_points
    return waves[::step], values[::step]


def plot_condicao_reflectancia(media, cv, condition, output_dir):
    """IRRIGADO ou NAO_IRRIGADO: 3 genotipos juntos por dia/turno, com CV abaixo."""
    days = DAYS_WITH_TARDE if condition == 'tarde' else ALL_DAYS
    n_cols = len(days)
    n_rows = 2

    fig, axes = plt.subplots(2, n_cols, figsize=(5 * n_cols, 8), sharex=False, sharey=False)

    if n_cols == 1:
        axes = axes.reshape(2, 1)

    fig.suptitle(f"REFLECTANCIA BRUTA - {CONDITION_TITLES[condition]}\n3 Genotipos (BR16, CD202, EMB48) por Dia e Turno", fontsize=14, fontweight='bold', y=1.02)

    band_cols = get_band_columns(media)
    wavelengths = np.array([float(c) for c in band_cols])

    for col_idx, day in enumerate(days):
        subset_refl = media[(media['condicao'] == condition) & (media['data_coleta'] == day)]
        subset_cv = cv[(cv['condicao'] == condition) & (cv['data_coleta'] == day)]

        ax_refl = axes[0, col_idx]
        ax_cv = axes[1, col_idx]

        for genotype in GENOTYPE_ORDER:
            gen_data_refl = subset_refl[subset_refl['genotipo'] == genotype]
            gen_data_cv = subset_cv[subset_cv['genotipo'] == genotype]

            turnos_in_data = gen_data_refl['turno'].unique()

            for turn in TURN_ORDER:
                turn_data_refl = gen_data_refl[gen_data_refl['turno'] == turn]
                turn_data_cv = gen_data_cv[gen_data_cv['turno'] == turn]

                if len(turn_data_refl) == 0:
                    continue

                row_refl = turn_data_refl.iloc[0]
                row_cv = turn_data_cv.iloc[0]

                wave_s, refl_s = downsample_series(wavelengths, row_refl[band_cols].values.astype(float))
                wave_s, cv_s = downsample_series(wavelengths, row_cv[band_cols].values.astype(float))

                linestyle = '-' if turn == 'manha' else '--'
                color = GENOTYPE_COLORS[genotype]
                label = f'{genotype} ({TURN_TITLES[turn][0]})'

                ax_refl.plot(wave_s, refl_s, color=color, linestyle=linestyle, linewidth=1.2, label=label, alpha=0.9)
                ax_cv.plot(wave_s, cv_s, color=color, linestyle=linestyle, linewidth=1.2, label=label, alpha=0.9)

        ax_refl.set_xlim(*X_LIM)
        ax_refl.set_ylim(0, None)
        ax_refl.set_title(f'{day}', fontsize=11, fontweight='bold')
        ax_refl.set_ylabel('Reflectancia', fontsize=9)
        ax_refl.grid(True, alpha=0.25)
        ax_refl.set_xticks(X_TICKS)
        ax_refl.tick_params(axis='x', labelsize=7)

        ax_cv.set_xlim(*X_LIM)
        ax_cv.set_ylim(0, 60)
        ax_cv.set_ylabel('CV (%)', fontsize=9)
        ax_cv.set_xlabel('Comprimento de onda (nm)', fontsize=9)
        ax_cv.grid(True, alpha=0.25)
        ax_cv.set_xticks(X_TICKS)
        ax_cv.tick_params(axis='x', labelsize=7)

    handles = []
    for genotype in GENOTYPE_ORDER:
        for turn in TURN_ORDER:
            linestyle = '-' if turn == 'manha' else '--'
            label = f'{genotype} ({TURN_TITLES[turn][0]})'
            handles.append(Line2D([0], [0], color=GENOTYPE_COLORS[genotype], linestyle=linestyle, linewidth=2, label=label))

    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.01), ncol=6, fontsize=9)
    plt.tight_layout(rect=[0, 0.01, 1, 0.99])
    out_path = output_dir / f'REFL_{condition}.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {out_path}')


def plot_condicao_por_turno(media, cv, condition, turn, output_dir):
    """IRRIGADO ou NAO_IRRIGADO: 3 genotipos juntos por dia, PARA TURNO ESPECIFICO."""
    days = DAYS_WITH_TARDE if turn == 'tarde' else ALL_DAYS
    n_cols = len(days)
    n_rows = 2

    fig, axes = plt.subplots(2, n_cols, figsize=(5 * n_cols, 8), sharex=False, sharey=False)

    if n_cols == 1:
        axes = axes.reshape(2, 1)

    fig.suptitle(f"REFLECTANCIA BRUTA - {CONDITION_TITLES[condition]} - Turno: {TURN_TITLES[turn]}\n3 Genotipos (BR16, CD202, EMB48) por Dia", fontsize=14, fontweight='bold', y=1.02)

    band_cols = get_band_columns(media)
    wavelengths = np.array([float(c) for c in band_cols])

    for col_idx, day in enumerate(days):
        subset_refl = media[(media['condicao'] == condition) & (media['data_coleta'] == day) & (media['turno'] == turn)]
        subset_cv = cv[(cv['condicao'] == condition) & (cv['data_coleta'] == day) & (cv['turno'] == turn)]

        ax_refl = axes[0, col_idx]
        ax_cv = axes[1, col_idx]

        for genotype in GENOTYPE_ORDER:
            gen_data_refl = subset_refl[subset_refl['genotipo'] == genotype]
            gen_data_cv = subset_cv[subset_cv['genotipo'] == genotype]

            if len(gen_data_refl) == 0:
                continue

            row_refl = gen_data_refl.iloc[0]
            row_cv = gen_data_cv.iloc[0]

            wave_s, refl_s = downsample_series(wavelengths, row_refl[band_cols].values.astype(float))
            wave_s, cv_s = downsample_series(wavelengths, row_cv[band_cols].values.astype(float))

            ax_refl.plot(wave_s, refl_s, color=GENOTYPE_COLORS[genotype], linewidth=1.5, label=genotype)
            ax_cv.plot(wave_s, cv_s, color=GENOTYPE_COLORS[genotype], linewidth=1.5, label=genotype)

        ax_refl.set_xlim(*X_LIM)
        ax_refl.set_ylim(0, None)
        ax_refl.set_title(f'{day}', fontsize=11, fontweight='bold')
        ax_refl.set_ylabel('Reflectancia', fontsize=9)
        ax_refl.grid(True, alpha=0.25)
        ax_refl.set_xticks(X_TICKS)
        ax_refl.tick_params(axis='x', labelsize=7)

        ax_cv.set_xlim(*X_LIM)
        ax_cv.set_ylim(0, 60)
        ax_cv.set_ylabel('CV (%)', fontsize=9)
        ax_cv.set_xlabel('Comprimento de onda (nm)', fontsize=9)
        ax_cv.grid(True, alpha=0.25)
        ax_cv.set_xticks(X_TICKS)
        ax_cv.tick_params(axis='x', labelsize=7)

    handles = [Line2D([0], [0], color=GENOTYPE_COLORS[g], linewidth=2, label=g) for g in GENOTYPE_ORDER]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=9)
    plt.tight_layout(rect=[0, 0.01, 1, 0.99])
    out_path = output_dir / f'REFL_{condition}_{turn}.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {out_path}')


def plot_condicao_por_genotipo(media, cv, condition, output_dir):
    """IRRIGADO ou NAO_IRRIGADO: SEPARADO por genotipo - 3 painéis (um por genotipo), cada um com todos os dias/turnos."""
    n_cols = 6
    n_rows = 3

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows), sharex=False, sharey=False)

    fig.suptitle(f"REFLECTANCIA BRUTA - {CONDITION_TITLES[condition]} - Por Genotipo\nCada linha = 1 Genotipo | Cada coluna = 1 Dia | Linhas=manha, Tracejado=Tarde", fontsize=14, fontweight='bold', y=1.02)

    band_cols = get_band_columns(media)
    wavelengths = np.array([float(c) for c in band_cols])

    for row_idx, genotype in enumerate(GENOTYPE_ORDER):
        for col_idx, day in enumerate(ALL_DAYS):
            ax = axes[row_idx, col_idx]

            subset_refl = media[(media['condicao'] == condition) & (media['genotipo'] == genotype) & (media['data_coleta'] == day)]
            subset_cv = cv[(cv['condicao'] == condition) & (cv['genotipo'] == genotype) & (cv['data_coleta'] == day)]

            if len(subset_refl) == 0:
                ax.set_visible(False)
                continue

            for turn in TURN_ORDER:
                turn_data_refl = subset_refl[subset_refl['turno'] == turn]
                turn_data_cv = subset_cv[subset_cv['turno'] == turn]

                if len(turn_data_refl) == 0:
                    continue

                linestyle = '-' if turn == 'manha' else '--'

                row_refl = turn_data_refl.iloc[0]
                row_cv = turn_data_cv.iloc[0]

                wave_s, refl_s = downsample_series(wavelengths, row_refl[band_cols].values.astype(float))
                wave_s, cv_s = downsample_series(wavelengths, row_cv[band_cols].values.astype(float))

                color = GENOTYPE_COLORS[genotype]
                ax.plot(wave_s, refl_s, color=color, linestyle=linestyle, linewidth=1.2, label=f'{TURN_TITLES[turn][0]}')
                ax.plot(wave_s, cv_s * 0.01, color=color, linestyle=linestyle, linewidth=1.0, alpha=0.5)

            ax.set_xlim(*X_LIM)
            ax.set_ylim(0, None)
            ax.grid(True, alpha=0.25)
            ax.set_xticks(X_TICKS)
            ax.tick_params(axis='x', labelsize=6)

            if col_idx == 0:
                ax.set_ylabel(f'{genotype}\nRefl', fontsize=9, fontweight='bold')
            if row_idx == 0:
                ax.set_title(day, fontsize=9, fontweight='bold')
            if row_idx == 2:
                ax.set_xlabel('nm', fontsize=8)

    manha_line = Line2D([0], [0], color='gray', linestyle='-', linewidth=2, label='Manha')
    tarde_line = Line2D([0], [0], color='gray', linestyle='--', linewidth=2, label='Tarde')
    fig.legend(handles=[manha_line, tarde_line], loc='lower center', bbox_to_anchor=(0.5, -0.01), ncol=2, fontsize=9)
    plt.tight_layout(rect=[0, 0.01, 1, 0.99])
    out_path = output_dir / f'REFL_{condition}_por_genotipo.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {out_path}')


def plot_cv_por_genotipo(media, cv, condition, output_dir):
    """IRRIGADO ou NAO_IRRIGADO: SEPARADO por genotipo - SO CV."""
    n_cols = 6
    n_rows = 3

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows), sharex=False, sharey=False)

    fig.suptitle(f"COEFICIENTE DE VARIACAO (%) - {CONDITION_TITLES[condition]} - Por Genotipo\nCada linha = 1 Genotipo | Cada coluna = 1 Dia | Linhas=manha, Tracejado=Tarde", fontsize=14, fontweight='bold', y=1.02)

    band_cols = get_band_columns(cv)
    wavelengths = np.array([float(c) for c in band_cols])

    for row_idx, genotype in enumerate(GENOTYPE_ORDER):
        for col_idx, day in enumerate(ALL_DAYS):
            ax = axes[row_idx, col_idx]

            subset_refl = media[(media['condicao'] == condition) & (media['genotipo'] == genotype) & (media['data_coleta'] == day)]
            subset_cv = cv[(cv['condicao'] == condition) & (cv['genotipo'] == genotype) & (cv['data_coleta'] == day)]

            if len(subset_cv) == 0:
                ax.set_visible(False)
                continue

            for turn in TURN_ORDER:
                turn_data_refl = subset_refl[subset_refl['turno'] == turn]
                turn_data_cv = subset_cv[subset_cv['turno'] == turn]

                if len(turn_data_cv) == 0:
                    continue

                linestyle = '-' if turn == 'manha' else '--'
                color = GENOTYPE_COLORS[genotype]

                row_refl = turn_data_refl.iloc[0]
                row_cv = turn_data_cv.iloc[0]

                wave_s, refl_s = downsample_series(wavelengths, row_refl[band_cols].values.astype(float))
                wave_s, cv_s = downsample_series(wavelengths, row_cv[band_cols].values.astype(float))

                ax.plot(wave_s, cv_s, color=color, linestyle=linestyle, linewidth=1.2, label=f'{genotype} {TURN_TITLES[turn][0]}')

            ax.set_xlim(*X_LIM)
            ax.set_ylim(0, 60)
            ax.grid(True, alpha=0.25)
            ax.set_xticks(X_TICKS)
            ax.tick_params(axis='x', labelsize=6)

            if col_idx == 0:
                ax.set_ylabel(f'{genotype}\nCV (%)', fontsize=9, fontweight='bold')
            if row_idx == 0:
                ax.set_title(day, fontsize=9, fontweight='bold')
            if row_idx == 2:
                ax.set_xlabel('nm', fontsize=8)

    handles = []
    for g in GENOTYPE_ORDER:
        for t in TURN_ORDER:
            linestyle = '-' if t == 'manha' else '--'
            handles.append(Line2D([0], [0], color=GENOTYPE_COLORS[g], linestyle=linestyle, linewidth=2, label=f'{g} ({TURN_TITLES[t][0]})'))
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.01), ncol=6, fontsize=8)
    plt.tight_layout(rect=[0, 0.01, 1, 0.99])
    out_path = output_dir / f'CV_{condition}_por_genotipo.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {out_path}')


def plot_reflectancia_irr_vs_nirr(media, cv, output_dir):
    """IRRIGADO vs NAO_IRRIGADO - 3 genotipos juntos, por dia (todos turnos)."""
    n_cols = len(ALL_DAYS)
    n_rows = 2

    fig, axes = plt.subplots(2, n_cols, figsize=(5 * n_cols, 8), sharex=False, sharey=False)

    fig.suptitle("REFLECTANCIA BRUTA: IRRIGADO vs NAO IRRIGADO\n3 Genotipos por Dia | Linhas=IRRIGADO, Tracejado=NAO_IRRIGADO", fontsize=13, fontweight='bold', y=1.02)

    band_cols = get_band_columns(media)
    wavelengths = np.array([float(c) for c in band_cols])

    for col_idx, day in enumerate(ALL_DAYS):
        ax_refl = axes[0, col_idx]
        ax_cv = axes[1, col_idx]

        for genotype in GENOTYPE_ORDER:
            for cond_idx, cond in enumerate(CONDITION_ORDER):
                cond_data_refl = media[(media['condicao'] == cond) & (media['genotipo'] == genotype) & (media['data_coleta'] == day)]
                cond_data_cv = cv[(cv['condicao'] == cond) & (cv['genotipo'] == genotype) & (cv['data_coleta'] == day)]

                if len(cond_data_refl) == 0:
                    continue

                for turn in TURN_ORDER:
                    turn_data_refl = cond_data_refl[cond_data_refl['turno'] == turn]
                    turn_data_cv = cond_data_cv[cond_data_cv['turno'] == turn]

                    if len(turn_data_refl) == 0:
                        continue

                    linestyle = '-' if turn == 'manha' else '--'
                    linewidth = 1.5 if turn == 'manha' else 1.0
                    color = GENOTYPE_COLORS[genotype]

                    row_refl = turn_data_refl.iloc[0]
                    row_cv = turn_data_cv.iloc[0]

                    wave_s, refl_s = downsample_series(wavelengths, row_refl[band_cols].values.astype(float))
                    wave_s, cv_s = downsample_series(wavelengths, row_cv[band_cols].values.astype(float))

                    label = f'{genotype}'
                    ax_refl.plot(wave_s, refl_s, color=color, linestyle=linestyle, linewidth=linewidth, label=label, alpha=0.9)
                    ax_cv.plot(wave_s, cv_s, color=color, linestyle=linestyle, linewidth=linewidth, alpha=0.9)

        ax_refl.set_xlim(*X_LIM)
        ax_refl.set_ylim(0, None)
        ax_refl.set_title(f'{day}', fontsize=11, fontweight='bold')
        ax_refl.set_ylabel('Reflectancia', fontsize=9)
        ax_refl.grid(True, alpha=0.25)
        ax_refl.set_xticks(X_TICKS)
        ax_refl.tick_params(axis='x', labelsize=7)

        ax_cv.set_xlim(*X_LIM)
        ax_cv.set_ylim(0, 60)
        ax_cv.set_ylabel('CV (%)', fontsize=9)
        ax_cv.set_xlabel('nm', fontsize=9)
        ax_cv.grid(True, alpha=0.25)
        ax_cv.set_xticks(X_TICKS)
        ax_cv.tick_params(axis='x', labelsize=7)

    solid_line = Line2D([0], [0], color='gray', linestyle='-', linewidth=2, label='IRRIGADO')
    dashed_line = Line2D([0], [0], color='gray', linestyle='--', linewidth=2, label='NAO_IRRIGADO')
    handles_gen = [Line2D([0], [0], color=GENOTYPE_COLORS[g], linewidth=2, label=g) for g in GENOTYPE_ORDER]
    fig.legend(handles=handles_gen + [solid_line, dashed_line], loc='lower center', bbox_to_anchor=(0.5, -0.01), ncol=5, fontsize=9)
    plt.tight_layout(rect=[0, 0.01, 1, 0.99])
    out_path = output_dir / f'REFL_IRR_vs_NIRR.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {out_path}')


def main():
    print('Carregando dados...')
    media, cv = load_data()
    print(f'Media: {media.shape}, CV: {cv.shape}')

    figs_dir = OUTPUT_DIR / 'figuras'
    figs_dir.mkdir(parents=True, exist_ok=True)

    print('\nGerando: IRRIGADO vs NAO_IRRIGADO comparacao...')
    plot_reflectancia_irr_vs_nirr(media, cv, figs_dir)

    print('\nGerando: Por condicao (IRR + NIRRG) - 3 genotipos juntos...')
    for condition in CONDITION_ORDER:
        plot_condicao_reflectancia(media, cv, condition, figs_dir)

    print('\nGerando: Por condicao + turno...')
    for condition in CONDITION_ORDER:
        for turn in TURN_ORDER:
            plot_condicao_por_turno(media, cv, condition, turn, figs_dir)

    print('\nGerando: Por condicao + genotipo (separado)...')
    for condition in CONDITION_ORDER:
        plot_condicao_por_genotipo(media, cv, condition, figs_dir)
        plot_cv_por_genotipo(media, cv, condition, figs_dir)

    print(f'\nDone! Graficos em: {figs_dir}')


if __name__ == '__main__':
    main()