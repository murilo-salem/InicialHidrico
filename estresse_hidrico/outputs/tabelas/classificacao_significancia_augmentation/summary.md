# Classificacao com augmentation espectral

- Dataset: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\estresse_hidrico\dados\processados\replicatas_bloco_dia.csv`
- Significancia: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\TestesSignfDiniz\TOP5_POR_DIA_TURNO`
- Numero de bandas por alvo: `5`
- Metodo: `spectral_jitter`, copias por amostra: `3`
- Ruido: `0.015`, escala: `+/-0.02`, offset: `0.005`

| alvo | variante | melhor_modelo | accuracy | balanced_acc | f1_macro | roc_auc | kappa |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| condicao | baseline | Random Forest | 0.9583 | 0.9583 | 0.9583 | 0.9907 | 0.9167 |
| condicao | augmentation | SVM (RBF) | 0.9792 | 0.9792 | 0.9791 | 0.9977 | 0.9583 |
| condicao_genotipo | baseline | LDA | 0.5486 | 0.5486 | 0.5120 | nan | 0.4583 |
| condicao_genotipo | augmentation | SVM (RBF) | 0.5625 | 0.5625 | 0.5147 | nan | 0.4750 |
| condicao_genotipo_turno | baseline | LDA | 0.3611 | 0.3611 | 0.3300 | nan | 0.3030 |
| condicao_genotipo_turno | augmentation | LDA | 0.3958 | 0.3958 | 0.3596 | nan | 0.3409 |
