#!/usr/bin/env python3
"""Plot raw spectral signatures by irrigation condition, all dates."""

import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COND_COLORS = {"irrigado": "#0f766e", "nao_irrigado": "#c2410c"}
DATE_MARKERS = {"2017-02-23": "o", "2017-02-24": "s", "2017-02-25": "^", "2017-02-26": "D"}


def main():
    wavelengths = []
    data = {"irrigado": {}, "nao_irrigado": {}}

    with open("outputs/estatistica_descritiva_media.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cond = row["condicao"]
            date = row["data_coleta"]
            if cond not in data:
                continue
            if date not in data[cond]:
                data[cond][date] = []
            if not wavelengths:
                wavelengths = [float(k) for k in row.keys() if k.isdigit()]
                wavelengths.sort()
            values = [float(row[str(int(w))]) for w in wavelengths]
            data[cond][date].append(values)

    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)

    for cond in ["irrigado", "nao_irrigado"]:
        label = "Irrigado" if cond == "irrigado" else "Nao irrigado"
        for date in sorted(data[cond].keys()):
            arr = np.array(data[cond][date])
            mean_spec = arr.mean(axis=0)
            ax.plot(wavelengths, mean_spec, color=COND_COLORS[cond], linewidth=1.4,
                    marker=DATE_MARKERS.get(date, "o"), markersize=3, markevery=50,
                    label=f"{label} ({date})", alpha=0.8)

    ax.set_xlabel("Comprimento de onda (nm)")
    ax.set_ylabel("Reflectancia")
    ax.set_title("Assinaturas espectrais: irrigado vs nao irrigado por data (raw)")
    ax.grid(alpha=0.18)
    ax.legend(loc="best", fontsize=8)
    fig.savefig("dados_processados_soft/plsr_pca_irrigacao/assinatura_espectral_condicao_raw_por_data.svg", dpi=180)
    plt.close(fig)
    print("Saved: dados_processados_soft/plsr_pca_irrigacao/assinatura_espectral_condicao_raw_por_data.svg")


if __name__ == "__main__":
    main()
