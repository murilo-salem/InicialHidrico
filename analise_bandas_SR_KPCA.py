import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA, KernelPCA
from sklearn.metrics.pairwise import pairwise_kernels
from scipy.stats import kruskal, spearmanr
import warnings
warnings.filterwarnings('ignore')

META_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\metadados_normalizados_soft.csv'
SPEC_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\base_dados_unificada_snv_savgol_1deriv.csv'
OUTPUT_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\analise_bandas_SR_KPCA.csv'

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

def normalize_spectrum(x):
    return x / np.trapz(x)

def normalize_minmax(x):
    mn, mx = x.min(), x.max()
    if mx == mn:
        return np.zeros_like(x)
    return (x - mn) / (mx - mn)

def sr_top_bands(df, group_col, groups_a, groups_b, top_n=5):
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
            top_idx = deviation.argsort()[-top_n:][::-1]
            key = f'{g_a}_vs_{g_b}'
            results_by_pair[key] = {
                'pair': key,
                'mean_a': g_a, 'mean_b': g_b,
                'top5_SR': ','.join([band_cols[i] for i in top_idx]),
                'top5_deviation': ','.join([f'{deviation[i]:.3f}' for i in top_idx])
            }

    return results_by_pair

def kpca_top_bands(X, kernel='rbf', top_n=5, n_components=3, gamma=None):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    kpca = KernelPCA(n_components=n_components, kernel=kernel, gamma=gamma if gamma else 0.01)
    kpca.fit(Xs)
    loadings = np.abs(kpca.eigenvectors_).sum(axis=0) if hasattr(kpca, 'eigenvectors_') else np.zeros(X.shape[1])
    top_idx = loadings.argsort()[-top_n:][::-1]
    return [X.columns[i] for i in top_idx], loadings

def pca_top_bands(X, n_components=3, top_n=5):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    pca = PCA(n_components=n_components)
    pca.fit(Xs)
    loadings = np.abs(pca.components_).sum(axis=0)
    top_idx = loadings.argsort()[-top_n:][::-1]
    return [X.columns[i] for i in top_idx], loadings

def main():
    print('Carregando dados...')
    df = load_and_merge()
    print(f'Dados carregados: {len(df)} amostras, {len(get_band_columns(df))} bandas')

    band_cols = get_band_columns(df)
    genotipos = sorted(df['genotipo_normalizado'].unique())
    condicoes = sorted(df['condicao_normalizada'].unique())
    turnos = sorted(df['turno'].unique())
    dias = sorted(df['data_coleta_iso'].unique())

    results = []

    def add_result(level, n, pca, kpca_rbf, kpca_poly, sr_pair=None, sr_bands=None):
        results.append({
            'level': level,
            'n_amostras': n,
            'PCA': ','.join(pca[0]) if pca else '',
            'KPCA_RBF': ','.join(kpca_rbf[0]) if kpca_rbf else '',
            'KPCA_POLY': ','.join(kpca_poly[0]) if kpca_poly else '',
            'SR_pair': sr_pair if sr_pair else '',
            'SR_bands': sr_bands if sr_bands else ''
        })

    print('=== SPRECTRUM RATIO + KPCA ===')

    print('Global...')
    X = df[band_cols]
    pca_res = pca_top_bands(X)
    kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
    kpca_poly_res = kpca_top_bands(X, kernel='poly')
    add_result('GLOBAL', len(df), pca_res, kpca_rbf_res, kpca_poly_res)

    for g in genotipos:
        sub = df[df['genotipo_normalizado'] == g]
        if len(sub) < 12: continue
        X = sub[band_cols]
        pca_res = pca_top_bands(X)
        kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
        kpca_poly_res = kpca_top_bands(X, kernel='poly')
        add_result(f'genotipo={g}', len(sub), pca_res, kpca_rbf_res, kpca_poly_res)

    for c in condicoes:
        sub = df[df['condicao_normalizada'] == c]
        if len(sub) < 12: continue
        X = sub[band_cols]
        pca_res = pca_top_bands(X)
        kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
        kpca_poly_res = kpca_top_bands(X, kernel='poly')
        add_result(f'condicao={c}', len(sub), pca_res, kpca_rbf_res, kpca_poly_res)

    for t in turnos:
        sub = df[df['turno'] == t]
        if len(sub) < 12: continue
        X = sub[band_cols]
        pca_res = pca_top_bands(X)
        kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
        kpca_poly_res = kpca_top_bands(X, kernel='poly')
        add_result(f'turno={t}', len(sub), pca_res, kpca_rbf_res, kpca_poly_res)

    for d in dias:
        sub = df[df['data_coleta_iso'] == d]
        if len(sub) < 12: continue
        X = sub[band_cols]
        pca_res = pca_top_bands(X)
        kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
        kpca_poly_res = kpca_top_bands(X, kernel='poly')
        add_result(f'dia={d}', len(sub), pca_res, kpca_rbf_res, kpca_poly_res)

    print('Genotipo x Condicao SR...')
    for g in genotipos:
        for c in condicoes:
            sub = df[(df['genotipo_normalizado'] == g) & (df['condicao_normalizada'] == c)]
            if len(sub) < 12: continue
            X = sub[band_cols]
            pca_res = pca_top_bands(X)
            kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
            kpca_poly_res = kpca_top_bands(X, kernel='poly')
            add_result(f'G|C={g}|{c}', len(sub), pca_res, kpca_rbf_res, kpca_poly_res)

    print('Genotipo x Turno SR...')
    for g in genotipos:
        for t in turnos:
            sub = df[(df['genotipo_normalizado'] == g) & (df['turno'] == t)]
            if len(sub) < 12: continue
            X = sub[band_cols]
            pca_res = pca_top_bands(X)
            kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
            kpca_poly_res = kpca_top_bands(X, kernel='poly')
            add_result(f'G|T={g}|{t}', len(sub), pca_res, kpca_rbf_res, kpca_poly_res)

    print('Condicao x Turno SR...')
    for c in condicoes:
        for t in turnos:
            sub = df[(df['condicao_normalizada'] == c) & (df['turno'] == t)]
            if len(sub) < 12: continue
            X = sub[band_cols]
            pca_res = pca_top_bands(X)
            kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
            kpca_poly_res = kpca_top_bands(X, kernel='poly')
            add_result(f'C|T={c}|{t}', len(sub), pca_res, kpca_rbf_res, kpca_poly_res)

    print('Genotipo x Condicao x Turno x Dia SR...')
    for g in genotipos:
        for c in condicoes:
            for t in turnos:
                for d in dias:
                    sub = df[(df['genotipo_normalizado'] == g) & (df['condicao_normalizada'] == c) & (df['turno'] == t) & (df['data_coleta_iso'] == d)]
                    if len(sub) < 12: continue
                    X = sub[band_cols]
                    pca_res = pca_top_bands(X)
                    kpca_rbf_res = kpca_top_bands(X, kernel='rbf')
                    kpca_poly_res = kpca_top_bands(X, kernel='poly')
                    add_result(f'G|C|T|D={g}|{c}|{t}|{d}', len(sub), pca_res, kpca_rbf_res, kpca_poly_res)

    print('Spectrum Ratio: Genotipo pairs...')
    sr_results_gen = sr_top_bands(df, 'genotipo_normalizado', genotipos, genotipos)
    for k, v in sr_results_gen.items():
        add_result(f'SR_genotipo={k}', 0, None, None, None, sr_pair=v['pair'], sr_bands=v['top5_SR'])

    print('Spectrum Ratio: Condicao pairs...')
    sr_results_cond = sr_top_bands(df, 'condicao_normalizada', condicoes, condicoes)
    for k, v in sr_results_cond.items():
        add_result(f'SR_condicao={k}', 0, None, None, None, sr_pair=v['pair'], sr_bands=v['top5_SR'])

    print('Spectrum Ratio: Turno pairs...')
    sr_results_turno = sr_top_bands(df, 'turno', turnos, turnos)
    for k, v in sr_results_turno.items():
        add_result(f'SR_turno={k}', 0, None, None, None, sr_pair=v['pair'], sr_bands=v['top5_SR'])

    print('Spectrum Ratio: Dia pairs...')
    sr_results_dia = sr_top_bands(df, 'data_coleta_iso', dias, dias)
    for k, v in sr_results_dia.items():
        add_result(f'SR_dia={k}', 0, None, None, None, sr_pair=v['pair'], sr_bands=v['top5_SR'])

    out_df = pd.DataFrame(results)
    out_df.to_csv(OUTPUT_PATH, index=False)
    print(f'Resultados salvos em: {OUTPUT_PATH}')
    print(out_df.to_string())

if __name__ == '__main__':
    main()