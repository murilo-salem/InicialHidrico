# Classificacao binaria IRR vs NIRR - BR16

## Configuracao

- modelo: `LDA (solver=lsqr, shrinkage=auto)`
- bandas: `band_381, band_721, band_2444`
- escopo: `por_genotipo`
- genotipo: `BR16`
- n amostras: `48`
- n grupos CV: `8`
- n folds: `4`

## Metricas CV

- accuracy: `0.937500 +- 0.041667`
- balanced accuracy: `0.937500 +- 0.041667`
- F1 irrigado: `0.931818 +- 0.045455`
- F1 macro: `0.937063 +- 0.041958`
- ROC AUC: `0.979167 +- 0.026595`
- kappa: `0.875000 +- 0.083333`

## Distribuicao de grupos por classe

| condicao | n amostras | n grupos |
| --- | ---: | ---: |
| IRR | 24 | 4 |
| NIRR | 24 | 4 |
