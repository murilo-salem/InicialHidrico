# PLSR: manha / CD202

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 196
- Classes: irrigado = 100, nao_irrigado = 96
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 14
- RMSECV: 0.180154
- R2CV: 0.870124
- AUC: 0.998437
- Accuracy: 0.979592
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2149 | irrigado | 1.4903 | 0.011419 | 6.9215 |
| 2 | 2150 | irrigado | 1.4622 | 0.011441 | 6.7569 |
| 3 | 2170 | irrigado | 1.5130 | 0.010634 | 6.7165 |
| 4 | 2148 | irrigado | 1.4982 | 0.010727 | 6.6660 |
| 5 | 2151 | irrigado | 1.4386 | 0.011418 | 6.6002 |
| 6 | 2169 | irrigado | 1.5395 | 0.009580 | 6.4165 |
| 7 | 2152 | irrigado | 1.4166 | 0.011282 | 6.4036 |
| 8 | 890 | irrigado | 1.2012 | 0.013828 | 6.1879 |
| 9 | 2171 | irrigado | 1.4393 | 0.010421 | 6.1653 |
| 10 | 2168 | irrigado | 1.5421 | 0.008494 | 5.9547 |
| 11 | 2153 | irrigado | 1.3908 | 0.010366 | 5.8400 |
| 12 | 2147 | irrigado | 1.4728 | 0.009073 | 5.7793 |
| 13 | 422 | nao_irrigado | 1.4090 | -0.009970 | 5.7782 |
| 14 | 970 | nao_irrigado | 1.2596 | -0.012055 | 5.7694 |
| 15 | 464 | nao_irrigado | 1.2573 | -0.011241 | 5.3968 |
| 16 | 2167 | irrigado | 1.5258 | 0.007238 | 5.3001 |
| 17 | 423 | nao_irrigado | 1.3968 | -0.009023 | 5.2856 |
| 18 | 889 | irrigado | 1.1261 | 0.012639 | 5.1976 |
| 19 | 2172 | irrigado | 1.3536 | 0.009231 | 5.1091 |
| 20 | 465 | nao_irrigado | 1.2729 | -0.010332 | 5.0934 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 890 | 0.013828 | 1.2012 |
| 889 | 0.012639 | 1.1261 |
| 891 | 0.011844 | 1.0999 |
| 2150 | 0.011441 | 1.4622 |
| 2149 | 0.011419 | 1.4903 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 811 | -0.014204 | 0.9398 |
| 810 | -0.013373 | 0.9569 |
| 970 | -0.012055 | 1.2596 |
| 399 | -0.012010 | 0.9948 |
| 464 | -0.011241 | 1.2573 |
