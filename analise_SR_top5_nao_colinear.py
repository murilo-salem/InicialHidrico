import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA, KernelPCA
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings('ignore')

META_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\metadados_normalizados_soft.csv'
SPEC_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\base_dados_unificada_snv_savgol_1deriv.csv'
OUTPUT_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\analise_SR_top5_nao_colinear.csv'

def load_and_merge():
    meta = pd.read_csv(META_PATH)
    spec = pd.read_csv(SPEC_PATH)
    meta = meta.copy()
    spec = spec.copy()
    meta['date_key'] = meta['nomenclaura'] + '_' + meta['data_coleta_raw'].astype(str)
    spec_dedup = spec.drop_duplicates(subset=['nomenclaura', 'data_coleta']).copy()
    spec_dedup['date_key'] = spec_dedup['nomenclaura'] + '_' + spec_dedup['data_coleta'].astype(str)
    band_cols = [c for c in spec_dedup.columns if c.isdigit()]
    spec_for_merge = spec_dedup[['nomenclaura', 'date_key'] + band_cols]
    merged = meta.merge(spec_for_merge, on=['nomenclaura', 'date_key'], how='inner')
    return merged

def get_band_columns(df):
    return [c for c in df.columns if c.isdigit()]

def normalize_minmax(x):
    mn, mx = x.min(), x.max()
    if mx == mn:
        return np.zeros_like(x)
    return (x - mn) / (mx - mn)

def get_non_collinear_top5(band_names, deviations, min_gap=10):
    band_names = np.array(band_names)
    deviations = np.array(deviations)
    sorted_idx = deviations.argsort()[::-1]
    selected = []
    selected_idx = []

    for idx in sorted_idx:
        if len(selected) >= 5:
            break
        band_val = int(band_names[idx])
        too_close = False
        for sel_val in selected:
            if abs(band_val - sel_val) < min_gap:
                too_close = True
                break
        if not too_close:
            selected.append(band_val)
            selected_idx.append(idx)

    while len(selected) < 5 and len(selected_idx) < 5:
        for idx in sorted_idx:
            if idx not in selected_idx:
                selected.append(int(band_names[idx]))
                selected_idx.append(idx)
                break
        if len(selected) >= 5:
            break

    return [str(s) for s in selected]

def sr_top_bands_non_collinear(df, group_col, groups_a, groups_b, top_n=5, min_gap=10):
    band_cols = get_band_columns(df)
    results_by_pair = {}

    for g_a in groups_a:
        for g_b in groups_b:
            if g_a >= g_b:
                continue
            mask_a = df[group_col] == g_a
            mask_b = df[group_col] == g_b
            if mask_a.sum() < 3 or mask_b.sum() < 3:
                continue

            mean_a = df.loc[mask_a, band_cols].mean(axis=0).values.astype(float)
            mean_b = df.loc[mask_b, band_cols].mean(axis=0).values.astype(float)

            norm_a = normalize_minmax(mean_a)
            norm_b = normalize_minmax(mean_b)

            ratio = np.zeros_like(norm_a)
            for i in range(len(norm_a)):
                if norm_b[i] > 1e-10:
                    ratio[i] = norm_a[i] / norm_b[i]
                else:
                    ratio[i] = np.nan

            ratio = np.nan_to_num(ratio, nan=1.0)
            deviation = np.abs(ratio - 1.0)

            top5_noncoll = get_non_collinear_top5(band_cols, deviation, min_gap=min_gap)
            top5_devs = []
            for b in top5_noncoll:
                idx = list(band_cols).index(b)
                top5_devs.append(f'{deviation[idx]:.3f}')

            key = f'{g_a}_vs_{g_b}'
            results_by_pair[key] = {
                'pair': key,
                'n_a': mask_a.sum(),
                'n_b': mask_b.sum(),
                'top5_SR': ','.join(top5_noncoll),
                'top5_deviation': ','.join(top5_devs)
            }

    return results_by_pair

def main():
    print('Carregando dados...')
    df = load_and_merge()
    print(f'Dados carregados: {len(df)} amostras, {len(get_band_columns(df))} bandas')

    genotipos = sorted(df['genotipo_normalizado'].unique())
    condicoes = sorted(df['condicao_normalizada'].unique())
    turnos = sorted(df['turno'].unique())
    dias = sorted(df['data_coleta_iso'].unique())

    results = []

    print('Spectrum Ratio Genotipo pairs (min_gap=10nm)...')
    sr_gen = sr_top_bands_non_collinear(df, 'genotipo_normalizado', genotipos, genotipos, min_gap=10)
    for k, v in sr_gen.items():
        results.append({
            'comparison': 'genotipo',
            'pair': v['pair'],
            'group_a': k.split('_vs_')[0],
            'group_b': k.split('_vs_')[1],
            'n_a': v['n_a'],
            'n_b': v['n_b'],
            'top5_SR_noncollinear_10nm': v['top5_SR'],
            'deviations': v['top5_deviation']
        })

    print('Spectrum Ratio Condicao pairs (min_gap=10nm)...')
    sr_cond = sr_top_bands_non_collinear(df, 'condicao_normalizada', condicoes, condicoes, min_gap=10)
    for k, v in sr_cond.items():
        results.append({
            'comparison': 'condicao',
            'pair': v['pair'],
            'group_a': k.split('_vs_')[0],
            'group_b': k.split('_vs_')[1],
            'n_a': v['n_a'],
            'n_b': v['n_b'],
            'top5_SR_noncollinear_10nm': v['top5_SR'],
            'deviations': v['top5_deviation']
        })

    print('Spectrum Ratio Turno pairs (min_gap=10nm)...')
    sr_turno = sr_top_bands_non_collinear(df, 'turno', turnos, turnos, min_gap=10)
    for k, v in sr_turno.items():
        results.append({
            'comparison': 'turno',
            'pair': v['pair'],
            'group_a': k.split('_vs_')[0],
            'group_b': k.split('_vs_')[1],
            'n_a': v['n_a'],
            'n_b': v['n_b'],
            'top5_SR_noncollinear_10nm': v['top5_SR'],
            'deviations': v['top5_deviation']
        })

    print('Spectrum Ratio Dia pairs (min_gap=10nm)...')
    sr_dia = sr_top_bands_non_collinear(df, 'data_coleta_iso', dias, dias, min_gap=10)
    for k, v in sr_dia.items():
        results.append({
            'comparison': 'dia',
            'pair': v['pair'],
            'group_a': k.split('_vs_')[0],
            'group_b': k.split('_vs_')[1],
            'n_a': v['n_a'],
            'n_b': v['n_b'],
            'top5_SR_noncollinear_10nm': v['top5_SR'],
            'deviations': v['top5_deviation']
        })

    print('Spectrum Ratio Genotipo x Condicao pairs (min_gap=10nm)...')
    combos_gc = []
    for g in genotipos:
        for c in condicoes:
            combos_gc.append((g, c))
    sr_gc = sr_top_bands_non_collinear(df, 'genotipo_normalizado', genotipos, genotipos, min_gap=10)
    for k, v in sr_gc.items():
        parts = k.split('_vs_')
        g_a, g_b = parts[0], parts[1]
        results.append({
            'comparison': 'genotipo',
            'pair': v['pair'],
            'group_a': g_a,
            'group_b': g_b,
            'n_a': v['n_a'],
            'n_b': v['n_b'],
            'top5_SR_noncollinear_10nm': v['top5_SR'],
            'deviations': v['top5_deviation']
        })

    out_df = pd.DataFrame(results)
    out_df.to_csv(OUTPUT_PATH, index=False)
    print(f'Resultados salvos em: {OUTPUT_PATH}')
    print(out_df.to_string())

if __name__ == '__main__':
    main()