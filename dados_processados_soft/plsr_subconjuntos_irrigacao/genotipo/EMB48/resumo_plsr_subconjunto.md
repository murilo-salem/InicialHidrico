# PLSR: Genotipo EMB48

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 384
- Classes: irrigado = 192, nao_irrigado = 192
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 13
- RMSECV: 0.238302
- R2CV: 0.772848
- AUC: 0.994249
- Accuracy: 0.958333
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 1661 | irrigado | 1.5811 | 0.015169 | 6.8954 |
| 2 | 994 | nao_irrigado | 1.5934 | -0.014440 | 6.7347 |
| 3 | 1660 | irrigado | 1.5140 | 0.014174 | 6.2129 |
| 4 | 391 | nao_irrigado | 1.3544 | -0.016844 | 6.1708 |
| 5 | 1663 | irrigado | 1.5114 | 0.013262 | 5.9129 |
| 6 | 2307 | nao_irrigado | 1.5962 | -0.011589 | 5.8552 |
| 7 | 1662 | irrigado | 1.5278 | 0.012567 | 5.7852 |
| 8 | 2308 | nao_irrigado | 1.5189 | -0.011631 | 5.4422 |
| 9 | 1664 | irrigado | 1.4699 | 0.012169 | 5.3409 |
| 10 | 1784 | irrigado | 1.5958 | 0.009396 | 5.1652 |
| 11 | 1187 | nao_irrigado | 0.9284 | -0.020717 | 5.0369 |
| 12 | 2306 | nao_irrigado | 1.5786 | -0.009032 | 4.9560 |
| 13 | 2304 | nao_irrigado | 1.4970 | -0.010435 | 4.9460 |
| 14 | 995 | nao_irrigado | 1.3443 | -0.013022 | 4.9159 |
| 15 | 383 | nao_irrigado | 1.2414 | -0.014594 | 4.8417 |
| 16 | 380 | nao_irrigado | 1.3273 | -0.013057 | 4.8329 |
| 17 | 2294 | irrigado | 1.6205 | 0.007808 | 4.8031 |
| 18 | 1731 | nao_irrigado | 1.0766 | -0.017300 | 4.7820 |
| 19 | 2305 | nao_irrigado | 1.5536 | -0.008841 | 4.7586 |
| 20 | 1659 | irrigado | 1.3911 | 0.011511 | 4.7000 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 880 | 0.016868 | 1.0615 |
| 1090 | 0.016016 | 0.9906 |
| 908 | 0.015712 | 1.0689 |
| 1091 | 0.015581 | 0.9526 |
| 909 | 0.015564 | 1.1000 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 1187 | -0.020717 | 0.9284 |
| 1186 | -0.018888 | 0.9021 |
| 1188 | -0.017717 | 0.8638 |
| 895 | -0.017403 | 0.8390 |
| 1731 | -0.017300 | 1.0766 |
