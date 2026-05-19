# Classificacao binaria IRR vs NIRR

## Configuracao

- modelo: `LDA (solver=lsqr, shrinkage=auto)`
- bandas: `band_381, band_721, band_2444`
- escopo: `global`
- n amostras: `144`
- n grupos CV: `24`
- n folds: `5`

## Metricas CV

- accuracy: `0.911667 +- 0.048448`
- balanced accuracy: `0.916667 +- 0.035410`
- F1 irrigado: `0.906016 +- 0.042466`
- F1 macro: `0.909837 +- 0.047727`
- ROC AUC: `0.995370 +- 0.004630`
- kappa: `0.822049 +- 0.091821`

## Distribuicao de grupos por classe

| condicao | n amostras | n grupos |
| --- | ---: | ---: |
| IRR | 72 | 12 |
| NIRR | 72 | 12 |
