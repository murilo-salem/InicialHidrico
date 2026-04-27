#!/usr/bin/env python3
"""Run PLSR per date on specific bands."""

import csv
import numpy as np
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, roc_auc_score

BANDS = [521, 658, 708, 721, 1482, 1654, 937, 979, 2110, 2321]

def main():
    processed_csv = "dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv"
    metadata_csv = "dados_processados_soft/metadados_normalizados_soft.csv"

    with open(metadata_csv, "r", encoding="utf-8") as mf:
        meta_reader = csv.DictReader(mf)
        metadata = {row["nomenclaura"]: row for row in meta_reader}

    with open(processed_csv, "r", encoding="utf-8") as pf:
        reader = csv.reader(pf)
        header = next(reader)
        wavelengths = [float(v) for v in header[6:]]

    band_indices = [wavelengths.index(b) for b in BANDS if b in wavelengths]

    by_date = {}
    with open(processed_csv, "r", encoding="utf-8") as pf:
        reader = csv.reader(pf)
        next(reader)
        for row in reader:
            sample_name = row[0]
            if sample_name not in metadata:
                continue
            cond = metadata[sample_name]["condicao_normalizada"]
            date = metadata[sample_name]["data_coleta_iso"]
            y = 1 if cond == "irrigado" else 0
            values = [float(row[6 + i]) for i in band_indices]
            if date not in by_date:
                by_date[date] = {"X": [], "y": []}
            by_date[date]["X"].append(values)
            by_date[date]["y"].append(y)

    print(f"Bands: {BANDS}\n")
    print(f"{'Date':<12} | {'n':>5} | {'R2':>7} | {'RMSE':>7} | {'AUC':>7}")
    print("-" * 50)
    for date in sorted(by_date.keys()):
        X = np.array(by_date[date]["X"])
        y = np.array(by_date[date]["y"])
        n_comp = min(5, len(y) - 1, X.shape[1])
        cv = StratifiedKFold(n_splits=min(5, len(y)), shuffle=True, random_state=42)
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("pls", PLSRegression(n_components=n_comp, scale=False)),
        ])
        y_pred = cross_val_predict(pipeline, X, y, cv=cv, n_jobs=-1).ravel()
        r2 = r2_score(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        auc = roc_auc_score(y, y_pred)
        print(f"{date:<12} | {len(y):>5} | {r2:>7.4f} | {rmse:>7.4f} | {auc:>7.4f}")


if __name__ == "__main__":
    main()
