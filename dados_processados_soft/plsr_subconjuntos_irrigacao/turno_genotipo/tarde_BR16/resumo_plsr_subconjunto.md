# PLSR: tarde / BR16

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 192
- Classes: irrigado = 96, nao_irrigado = 96
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 15
- RMSECV: 0.206154
- R2CV: 0.830002
- AUC: 0.998915
- Accuracy: 0.973958
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 1668 | irrigado | 1.6873 | 0.014185 | 7.8054 |
| 2 | 807 | irrigado | 1.2831 | 0.019238 | 7.5054 |
| 3 | 2271 | nao_irrigado | 1.6525 | -0.013797 | 7.4781 |
| 4 | 1669 | irrigado | 1.5620 | 0.014905 | 7.4017 |
| 5 | 2282 | nao_irrigado | 1.8582 | -0.010597 | 7.4000 |
| 6 | 1667 | irrigado | 1.7531 | 0.012081 | 7.3844 |
| 7 | 2272 | nao_irrigado | 1.6306 | -0.013720 | 7.3329 |
| 8 | 2276 | nao_irrigado | 1.7508 | -0.011842 | 7.2844 |
| 9 | 995 | irrigado | 1.2815 | 0.018651 | 7.2812 |
| 10 | 2275 | nao_irrigado | 1.7017 | -0.012343 | 7.2067 |
| 11 | 2270 | nao_irrigado | 1.6584 | -0.012807 | 7.1459 |
| 12 | 2273 | nao_irrigado | 1.6242 | -0.013034 | 7.0474 |
| 13 | 2274 | nao_irrigado | 1.6547 | -0.012574 | 7.0411 |
| 14 | 2277 | nao_irrigado | 1.7741 | -0.010563 | 6.9396 |
| 15 | 808 | irrigado | 1.2596 | 0.017594 | 6.7773 |
| 16 | 1666 | irrigado | 1.7487 | 0.010487 | 6.7764 |
| 17 | 806 | irrigado | 1.2027 | 0.017278 | 6.3580 |
| 18 | 2283 | nao_irrigado | 1.6291 | -0.010904 | 6.2925 |
| 19 | 2281 | nao_irrigado | 1.8422 | -0.007761 | 6.2747 |
| 20 | 1670 | irrigado | 1.4135 | 0.013885 | 6.2369 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 807 | 0.019238 | 1.2831 |
| 995 | 0.018651 | 1.2815 |
| 808 | 0.017594 | 1.2596 |
| 806 | 0.017278 | 1.2027 |
| 1669 | 0.014905 | 1.5620 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 1269 | -0.015585 | 1.0452 |
| 2271 | -0.013797 | 1.6525 |
| 2272 | -0.013720 | 1.6306 |
| 1270 | -0.013508 | 1.0489 |
| 2273 | -0.013034 | 1.6242 |
