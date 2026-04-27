# Band significance analysis

- Target type: `binary`
- Bands analyzed: `2151`
- Significant bands at alpha=0.050: `2018`
- p-value adjustment: `fdr_bh`

## Score definition

- `effect_score`: robust z-score average of the available effect metrics.
- `significance_score`: robust z-score average of `-log10(pvalue_adjusted)` across available tests.
- `consistency_score`: agreement among signed metrics when available.
- `ranking_score = 0.45 * effect_score + 0.45 * significance_score + 0.10 * consistency_score`.

## Top bands

| rank | band | direction | ranking_score | p_adj | source | significant |
| ---: | ---: | --- | ---: | ---: | --- | --- |
| 1 | 1924 | nao_irrigado | 3.4979 | 2.167e-258 | ttest | yes |
| 2 | 1925 | nao_irrigado | 3.4814 | 3.200e-258 | spearman | yes |
| 3 | 1923 | nao_irrigado | 3.3667 | 1.434e-250 | pearson | yes |
| 4 | 1926 | nao_irrigado | 3.3357 | 1.166e-249 | spearman | yes |
| 5 | 487 | nao_irrigado | 3.3127 | 1.588e-261 | spearman | yes |
| 6 | 486 | nao_irrigado | 3.2848 | 1.639e-257 | spearman | yes |
| 7 | 488 | nao_irrigado | 3.2835 | 4.626e-260 | spearman | yes |
| 8 | 490 | nao_irrigado | 3.2676 | 3.676e-264 | spearman | yes |
| 9 | 489 | nao_irrigado | 3.2548 | 1.357e-259 | spearman | yes |
| 10 | 491 | nao_irrigado | 3.2440 | 2.919e-266 | spearman | yes |
| 11 | 485 | nao_irrigado | 3.2077 | 1.119e-247 | spearman | yes |
| 12 | 1427 | nao_irrigado | 3.2016 | 1.705e-240 | pearson | yes |
| 13 | 1426 | nao_irrigado | 3.2007 | 4.415e-240 | pearson | yes |
| 14 | 1428 | nao_irrigado | 3.1979 | 1.705e-240 | pearson | yes |
| 15 | 1429 | nao_irrigado | 3.1963 | 1.695e-240 | pearson | yes |
| 16 | 1425 | nao_irrigado | 3.1959 | 1.970e-239 | pearson | yes |
| 17 | 1430 | nao_irrigado | 3.1949 | 1.260e-240 | pearson | yes |
| 18 | 1431 | nao_irrigado | 3.1888 | 1.695e-240 | pearson | yes |
| 19 | 1424 | nao_irrigado | 3.1876 | 1.843e-238 | pearson | yes |
| 20 | 1432 | nao_irrigado | 3.1804 | 2.857e-240 | pearson | yes |
