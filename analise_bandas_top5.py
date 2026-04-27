import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
from scipy.stats import kruskal, spearmanr, mannwhitneyu
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

META_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\metadados_normalizados_soft.csv'
SPEC_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\base_dados_unificada_snv_savgol_1deriv.csv'
OUTPUT_PATH = r'C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\analise_bandas_top5_completo.csv'

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

def pca_top_bands(X, n_components=3, top_n=5):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    pca = PCA(n_components=n_components)
    pca.fit(Xs)
    loadings = np.abs(pca.components_).sum(axis=0)
    top_idx = loadings.argsort()[-top_n:][::-1]
    return [X.columns[i] for i in top_idx]

def pls_top_bands(X, y, top_n=5, max_comp=5):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    n_classes = len(np.unique(y_enc))
    best_n = min(max_comp, Xs.shape[1], n_classes - 1)
    if best_n < 1: best_n = 1
    pls = PLSRegression(n_components=best_n)
    pls.fit(Xs, y_enc)
    loadings = np.abs(pls.coef_).flatten()
    top_idx = loadings.argsort()[-top_n:][::-1]
    return [X.columns[i] for i in top_idx]

def rf_top_bands(X, y, top_n=5):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(Xs, y_enc)
    importances = rf.feature_importances_
    top_idx = importances.argsort()[-top_n:][::-1]
    return [X.columns[i] for i in top_idx]

def kruskal_top_bands(X, y, top_n=5):
    groups = np.unique(y)
    if len(groups) < 2:
        return [''] * top_n
    try:
        stat, pvals = kruskal(*[X.iloc[y == g].values for g in groups])
        neg_log_p = -np.log10(pvals + 1e-30)
        top_idx = neg_log_p.argsort()[-top_n:][::-1]
        return [X.columns[i] for i in top_idx]
    except:
        return [''] * top_n

def spm_top_bands(X, y, top_n=5):
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    corrs = np.array([np.abs(spearmanr(X.iloc[:, i], y_enc)[0]) for i in range(X.shape[1])])
    corrs = np.nan_to_num(corrs, nan=0.0)
    top_idx = corrs.argsort()[-top_n:][::-1]
    return [X.columns[i] for i in top_idx]

def mi_top_bands(X, y, top_n=5):
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    mi = mutual_info_classif(Xs, y_enc, random_state=42, n_neighbors=5)
    top_idx = mi.argsort()[-top_n:][::-1]
    return [X.columns[i] for i in top_idx]

def mwu_top_bands(X, y, top_n=5):
    groups = np.unique(y)
    if len(groups) != 2:
        return [''] * top_n
    g0, g1 = y == groups[0], y == groups[1]
    stat_arr = np.zeros(X.shape[1])
    for i in range(X.shape[1]):
        try:
            _, p = mannwhitneyu(X.iloc[g0, i], X.iloc[g1, i])
            stat_arr[i] = -np.log10(p + 1e-30)
        except:
            stat_arr[i] = 0
    top_idx = stat_arr.argsort()[-top_n:][::-1]
    return [X.columns[i] for i in top_idx]

def variance_top_bands(X, top_n=5):
    vars_val = X.var()
    return vars_val.sort_values(ascending=False).head(top_n).index.tolist()

def get_label_col(factors):
    if factors is None or len(factors) == 0:
        return None
    if 'condicao_normalizada' in factors and len(factors) == 1:
        return 'condicao_normalizada'
    if 'genotipo_normalizado' in factors and len(factors) == 1:
        return 'genotipo_normalizado'
    if 'turno' in factors and len(factors) == 1:
        return 'turno'
    if 'data_coleta_iso' in factors and len(factors) == 1:
        return 'data_coleta_iso'
    if 'bloco_normalizado' in factors and len(factors) == 1:
        return 'bloco_normalizado'
    return None

def analyze_subset(df, factors_dict, label_col=None, top_n=5):
    mask = pd.Series(True, index=df.index)
    for k, v in factors_dict.items():
        if v is not None:
            mask &= df[k] == v

    subset = df[mask]
    if len(subset) < 12:
        return None

    band_cols = get_band_columns(subset)
    X = subset[band_cols]

    n_amostras = len(subset)
    level_key = ' | '.join([f'{k}={v}' if v is not None else k for k, v in factors_dict.items()])

    results = {
        'level': level_key,
        'n_amostras': n_amostras,
        'PCA': '', 'Var': '', 'Kruskal': '', 'MWU': '', 'SPCM': '', 'RF': '', 'MI': '', 'PLS': ''
    }

    results['PCA'] = ','.join(pca_top_bands(X, top_n=top_n))
    results['Var'] = ','.join(variance_top_bands(X, top_n=top_n))

    if label_col is not None and len(np.unique(subset[label_col])) >= 2:
        y = subset[label_col].values
        results['Kruskal'] = ','.join(kruskal_top_bands(X, y, top_n=top_n))
        results['MWU'] = ','.join(mwu_top_bands(X, y, top_n=top_n))
        results['SPCM'] = ','.join(spm_top_bands(X, y, top_n=top_n))
        results['RF'] = ','.join(rf_top_bands(X, y, top_n=top_n))
        results['MI'] = ','.join(mi_top_bands(X, y, top_n=top_n))
        results['PLS'] = ','.join(pls_top_bands(X, y, top_n=top_n))

    return results

def main():
    print('Carregando dados...')
    df = load_and_merge()
    print(f'Dados carregados: {len(df)} amostras, {len(get_band_columns(df))} bandas')

    genotipos = sorted(df['genotipo_normalizado'].unique())
    condicoes = sorted(df['condicao_normalizada'].unique())
    turnos = sorted(df['turno'].unique())
    dias = sorted(df['data_coleta_iso'].unique())

    results = []
    tasks = []

    def add_task(factors_dict, label_col):
        tasks.append((factors_dict, label_col))

    add_task({}, None)

    for g in genotipos:
        add_task({'genotipo_normalizado': g}, None)

    for c in condicoes:
        add_task({'condicao_normalizada': c}, None)

    for t in turnos:
        add_task({'turno': t}, None)

    for d in dias:
        add_task({'data_coleta_iso': d}, None)

    for g in genotipos:
        for c in condicoes:
            add_task({'genotipo_normalizado': g, 'condicao_normalizada': c}, None)

    for g in genotipos:
        for t in turnos:
            add_task({'genotipo_normalizado': g, 'turno': t}, None)

    for g in genotipos:
        for d in dias:
            add_task({'genotipo_normalizado': g, 'data_coleta_iso': d}, None)

    for c in condicoes:
        for t in turnos:
            add_task({'condicao_normalizada': c, 'turno': t}, None)

    for c in condicoes:
        for d in dias:
            add_task({'condicao_normalizada': c, 'data_coleta_iso': d}, None)

    for t in turnos:
        for d in dias:
            add_task({'turno': t, 'data_coleta_iso': d}, None)

    for g in genotipos:
        for c in condicoes:
            for t in turnos:
                add_task({'genotipo_normalizado': g, 'condicao_normalizada': c, 'turno': t}, None)

    for g in genotipos:
        for c in condicoes:
            for d in dias:
                add_task({'genotipo_normalizado': g, 'condicao_normalizada': c, 'data_coleta_iso': d}, None)

    for g in genotipos:
        for t in turnos:
            for d in dias:
                add_task({'genotipo_normalizado': g, 'turno': t, 'data_coleta_iso': d}, None)

    for c in condicoes:
        for t in turnos:
            for d in dias:
                add_task({'condicao_normalizada': c, 'turno': t, 'data_coleta_iso': d}, None)

    for g in genotipos:
        for c in condicoes:
            for t in turnos:
                for d in dias:
                    add_task({'genotipo_normalizado': g, 'condicao_normalizada': c, 'turno': t, 'data_coleta_iso': d}, None)

    total = len(tasks)
    print(f'Total de análises: {total}')

    for i, (factors_dict, label_col) in enumerate(tasks):
        if (i + 1) % 10 == 0 or i == 0:
            print(f'Progresso: {i+1}/{total}')
        r = analyze_subset(df, factors_dict, label_col)
        if r is not None:
            results.append(r)

    out_df = pd.DataFrame(results)
    out_df.to_csv(OUTPUT_PATH, index=False)
    print(f'Resultados salvos em: {OUTPUT_PATH}')
    print(out_df.to_string())

if __name__ == '__main__':
    main()