# Otimizacao F1-macro com bandas significativas

- Dataset: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\estresse_hidrico\dados\processados\replicatas_bloco_dia.csv`
- Significancia: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\TestesSignfDiniz\TOP5_POR_DIA_TURNO`
- Top N avaliados: `5, 8, 10, 15, 20`
- Variantes: `baseline, jitter, mixup`
- Modelos: `SVM (RBF), LDA, Random Forest, XGBoost`

| alvo | top_n | variante | modelo | bandas | f1_macro | balanced_acc | kappa |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| condicao | 8 | jitter | SVM (RBF) | 6 | 0.9722 | 0.9722 | 0.9444 |
| condicao_genotipo | 10 | jitter | SVM (RBF) | 6 | 0.5916 | 0.6111 | 0.5333 |
| condicao_genotipo_turno | 5 | jitter | Random Forest | 5 | 0.3955 | 0.4236 | 0.3712 |
