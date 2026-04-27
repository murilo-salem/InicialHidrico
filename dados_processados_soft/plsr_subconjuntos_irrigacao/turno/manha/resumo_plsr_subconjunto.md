# PLSR: Turno manha

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 580
- Classes: irrigado = 292, nao_irrigado = 288
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 13
- RMSECV: 0.215134
- R2CV: 0.814860
- AUC: 0.994245
- Accuracy: 0.977586
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 392 | nao_irrigado | 1.5166 | -0.015452 | 7.0812 |
| 2 | 395 | nao_irrigado | 1.3672 | -0.015698 | 6.3137 |
| 3 | 391 | nao_irrigado | 1.3576 | -0.015332 | 6.1341 |
| 4 | 406 | nao_irrigado | 1.2826 | -0.016584 | 6.1326 |
| 5 | 390 | nao_irrigado | 1.2486 | -0.016485 | 5.9056 |
| 6 | 1661 | irrigado | 1.3958 | 0.013390 | 5.6900 |
| 7 | 436 | irrigado | 1.2188 | 0.015912 | 5.5401 |
| 8 | 389 | nao_irrigado | 1.1417 | -0.017158 | 5.5252 |
| 9 | 2170 | irrigado | 1.3173 | 0.013439 | 5.2593 |
| 10 | 375 | irrigado | 1.0646 | 0.017575 | 5.2275 |
| 11 | 437 | irrigado | 1.2540 | 0.014117 | 5.1295 |
| 12 | 2171 | irrigado | 1.3101 | 0.012968 | 5.0579 |
| 13 | 1662 | irrigado | 1.3568 | 0.011876 | 4.9519 |
| 14 | 1641 | irrigado | 1.2300 | 0.013650 | 4.8338 |
| 15 | 1660 | irrigado | 1.3558 | 0.011444 | 4.7991 |
| 16 | 458 | nao_irrigado | 1.3429 | -0.011589 | 4.7749 |
| 17 | 2169 | irrigado | 1.2891 | 0.012292 | 4.7080 |
| 18 | 435 | irrigado | 1.1271 | 0.014911 | 4.6761 |
| 19 | 2172 | irrigado | 1.2981 | 0.011994 | 4.6576 |
| 20 | 1663 | irrigado | 1.3276 | 0.010985 | 4.4820 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 375 | 0.017575 | 1.0646 |
| 436 | 0.015912 | 1.2188 |
| 435 | 0.014911 | 1.1271 |
| 437 | 0.014117 | 1.2540 |
| 1641 | 0.013650 | 1.2300 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 389 | -0.017158 | 1.1417 |
| 406 | -0.016584 | 1.2826 |
| 390 | -0.016485 | 1.2486 |
| 932 | -0.016124 | 0.9890 |
| 395 | -0.015698 | 1.3672 |
