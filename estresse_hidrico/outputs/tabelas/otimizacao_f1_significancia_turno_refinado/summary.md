# Otimizacao F1-macro com bandas significativas

- Dataset: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\estresse_hidrico\dados\processados\replicatas_bloco_dia.csv`
- Significancia: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\TestesSignfDiniz\TOP5_POR_DIA_TURNO`
- Top N avaliados: `5, 8, 10, 15`
- Variantes: `jitter, mixup`
- Modelos: `SVM (RBF), LDA, Random Forest, XGBoost`

| alvo | top_n | variante | modelo | bandas | f1_macro | balanced_acc | kappa |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| condicao_genotipo_turno | 5 | jitter | Random Forest | 5 | 0.3971 | 0.4236 | 0.3712 |
