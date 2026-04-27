# Pipeline v2 summary

- Run timestamp: 2026-04-07T12:45:47.722090+00:00
- Input: `base_dados_unificada.xlsx`
- Metadata: `dados_processados_soft\metadados_normalizados_soft.csv`
- Output dir: `outputs_v2`
- Samples: 1732
- Bands: 2151
- Groups: 36
- Genotypes: BR16, CD202, EMB48
- Conditions: irrigado, nao_irrigado
- Turnos: manha, tarde

## Included analyses

- Structural validation
- Descriptive statistics by date x genotype x condition
- PCA and scatter plots by metadata
- Vegetation indices and summary correlations
- Hierarchical clustering of group mean spectra
- Supervised classification for selected targets
- Band selection using ANOVA, MI, RF, L1 logistic, RFE, and PLS/VIP
- Optional binary PLSR
- Optional HVI pair search

## Methodological note

- The dataset does not contain the laboratory biochemical targets from the original paper.
- Those regression analyses are therefore not reproduced in the base pipeline and remain optional extensions.
