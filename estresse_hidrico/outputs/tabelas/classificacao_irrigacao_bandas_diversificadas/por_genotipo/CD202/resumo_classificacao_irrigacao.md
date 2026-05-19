# Classificacao binaria IRR vs NIRR - CD202

## Configuracao

- modelo: `LDA (solver=lsqr, shrinkage=auto)`
- bandas: `band_381, band_721, band_2444`
- escopo: `por_genotipo`
- genotipo: `CD202`
- n amostras: `48`
- n grupos CV: `8`
- n folds: `4`

## Metricas CV

- accuracy: `0.916667 +- 0.068041`
- balanced accuracy: `0.916667 +- 0.068041`
- F1 irrigado: `0.904545 +- 0.081818`
- F1 macro: `0.915185 +- 0.069993`
- ROC AUC: `0.993056 +- 0.013889`
- kappa: `0.833333 +- 0.136083`

## Distribuicao de grupos por classe

| condicao | n amostras | n grupos |
| --- | ---: | ---: |
| IRR | 24 | 4 |
| NIRR | 24 | 4 |
