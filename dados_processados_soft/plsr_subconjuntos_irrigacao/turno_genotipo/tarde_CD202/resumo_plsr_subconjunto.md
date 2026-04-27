# PLSR: tarde / CD202

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 192
- Classes: irrigado = 96, nao_irrigado = 96
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 12
- RMSECV: 0.214434
- R2CV: 0.816072
- AUC: 0.999891
- Accuracy: 0.994792
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2281 | nao_irrigado | 1.7372 | -0.010976 | 7.6544 |
| 2 | 553 | nao_irrigado | 1.5350 | -0.012159 | 6.9351 |
| 3 | 1670 | irrigado | 1.3904 | 0.014234 | 6.9106 |
| 4 | 1669 | irrigado | 1.4304 | 0.013640 | 6.9100 |
| 5 | 2282 | nao_irrigado | 1.6399 | -0.010344 | 6.8298 |
| 6 | 554 | nao_irrigado | 1.4595 | -0.012977 | 6.8172 |
| 7 | 2280 | nao_irrigado | 1.6925 | -0.009464 | 6.7897 |
| 8 | 1668 | irrigado | 1.4532 | 0.012557 | 6.6124 |
| 9 | 552 | nao_irrigado | 1.5564 | -0.010527 | 6.4120 |
| 10 | 1667 | irrigado | 1.4585 | 0.011562 | 6.2475 |
| 11 | 1665 | irrigado | 1.4598 | 0.011505 | 6.2329 |
| 12 | 555 | nao_irrigado | 1.3544 | -0.012565 | 6.0350 |
| 13 | 1666 | irrigado | 1.4512 | 0.011125 | 6.0311 |
| 14 | 2277 | nao_irrigado | 1.5438 | -0.009744 | 6.0260 |
| 15 | 2278 | nao_irrigado | 1.5916 | -0.008994 | 6.0087 |
| 16 | 1664 | irrigado | 1.4544 | 0.010948 | 5.9796 |
| 17 | 2279 | nao_irrigado | 1.6278 | -0.008328 | 5.9567 |
| 18 | 2276 | nao_irrigado | 1.4869 | -0.010382 | 5.9455 |
| 19 | 551 | nao_irrigado | 1.5288 | -0.009737 | 5.9351 |
| 20 | 2274 | nao_irrigado | 1.4083 | -0.011390 | 5.8840 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 1670 | 0.014234 | 1.3904 |
| 1669 | 0.013640 | 1.4304 |
| 1671 | 0.012655 | 1.2880 |
| 1668 | 0.012557 | 1.4532 |
| 1667 | 0.011562 | 1.4585 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 881 | -0.013615 | 1.1326 |
| 554 | -0.012977 | 1.4595 |
| 555 | -0.012565 | 1.3544 |
| 553 | -0.012159 | 1.5350 |
| 416 | -0.011928 | 1.2565 |
