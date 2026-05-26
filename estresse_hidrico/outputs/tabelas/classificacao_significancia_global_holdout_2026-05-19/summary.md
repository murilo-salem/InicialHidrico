# Classificacao global com bandas do teste de significancia

- Dataset: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\estresse_hidrico\dados\processados\replicatas_bloco_dia.csv`
- Significancia: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\TestesSignfDiniz\TOP5_POR_DIA_TURNO`
- Numero de bandas por alvo: `5`
- Validacao: `holdout_grouped_80_20`

| alvo | analise_top5 | bandas | melhor_modelo | accuracy | balanced_acc | f1_macro | roc_auc | kappa |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| condicao | cond | band_400, band_579, band_1580, band_530, band_739 | Random Forest | 0.9444 | 0.9444 | 0.9444 | 0.9907 | 0.8889 |
| condicao_genotipo | gen_cond | band_400, band_530, band_550, band_401, band_720 | k-NN (k=5) | 0.3611 | 0.3611 | 0.3238 | nan | 0.2333 |
| condicao_genotipo_turno | gen_cond | band_400, band_530, band_550, band_401, band_720 | LDA | 0.2778 | 0.2778 | 0.2710 | nan | 0.2121 |
