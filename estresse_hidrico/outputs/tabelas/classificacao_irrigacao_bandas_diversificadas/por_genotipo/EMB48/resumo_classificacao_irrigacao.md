# Classificacao binaria IRR vs NIRR - EMB48

## Configuracao

- modelo: `LDA (solver=lsqr, shrinkage=auto)`
- bandas: `band_381, band_721, band_2444`
- escopo: `por_genotipo`
- genotipo: `EMB48`
- n amostras: `48`
- n grupos CV: `8`
- n folds: `4`

## Metricas CV

- accuracy: `0.937500 +- 0.041667`
- balanced accuracy: `0.937500 +- 0.041667`
- F1 irrigado: `0.935315 +- 0.043625`
- F1 macro: `0.937063 +- 0.041958`
- ROC AUC: `1.000000 +- 0.000000`
- kappa: `0.875000 +- 0.083333`

## Distribuicao de grupos por classe

| condicao | n amostras | n grupos |
| --- | ---: | ---: |
| IRR | 24 | 4 |
| NIRR | 24 | 4 |
