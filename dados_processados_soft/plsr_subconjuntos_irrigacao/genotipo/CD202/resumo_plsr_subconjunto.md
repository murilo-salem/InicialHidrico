# PLSR: Genotipo CD202

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 388
- Classes: irrigado = 196, nao_irrigado = 192
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 12
- RMSECV: 0.211917
- R2CV: 0.820346
- AUC: 0.999070
- Accuracy: 0.979381
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2280 | nao_irrigado | 1.6435 | -0.012757 | 7.3338 |
| 2 | 873 | irrigado | 1.2905 | 0.017655 | 7.1776 |
| 3 | 2279 | nao_irrigado | 1.6131 | -0.012618 | 7.1132 |
| 4 | 2281 | nao_irrigado | 1.6231 | -0.011979 | 6.9323 |
| 5 | 2278 | nao_irrigado | 1.5753 | -0.012456 | 6.8424 |
| 6 | 874 | irrigado | 1.2741 | 0.016465 | 6.6457 |
| 7 | 423 | nao_irrigado | 1.2316 | -0.016849 | 6.5508 |
| 8 | 2277 | nao_irrigado | 1.5140 | -0.011665 | 6.2088 |
| 9 | 422 | nao_irrigado | 1.2036 | -0.016016 | 6.0872 |
| 10 | 2308 | nao_irrigado | 1.5686 | -0.009564 | 5.7357 |
| 11 | 2276 | nao_irrigado | 1.4586 | -0.011105 | 5.6928 |
| 12 | 554 | nao_irrigado | 1.3281 | -0.013068 | 5.6909 |
| 13 | 990 | nao_irrigado | 1.2191 | -0.014454 | 5.5958 |
| 14 | 875 | irrigado | 1.1962 | 0.014637 | 5.5359 |
| 15 | 2307 | nao_irrigado | 1.5456 | -0.009274 | 5.5006 |
| 16 | 989 | nao_irrigado | 1.1740 | -0.014865 | 5.4967 |
| 17 | 555 | nao_irrigado | 1.3014 | -0.012908 | 5.4833 |
| 18 | 368 | nao_irrigado | 1.3851 | -0.011220 | 5.3253 |
| 19 | 811 | nao_irrigado | 1.0685 | -0.015841 | 5.2695 |
| 20 | 628 | irrigado | 1.3042 | 0.012102 | 5.2007 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 873 | 0.017655 | 1.2905 |
| 874 | 0.016465 | 1.2741 |
| 875 | 0.014637 | 1.1962 |
| 876 | 0.012843 | 1.1360 |
| 872 | 0.012448 | 1.1470 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 423 | -0.016849 | 1.2316 |
| 422 | -0.016016 | 1.2036 |
| 811 | -0.015841 | 1.0685 |
| 989 | -0.014865 | 1.1740 |
| 810 | -0.014516 | 1.0235 |
