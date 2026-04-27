# PLSR: Turno tarde

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 576
- Classes: irrigado = 288, nao_irrigado = 288
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 13
- RMSECV: 0.262836
- R2CV: 0.723670
- AUC: 0.987570
- Accuracy: 0.939236
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2281 | nao_irrigado | 1.8067 | -0.014045 | 7.8147 |
| 2 | 2280 | nao_irrigado | 1.8009 | -0.013695 | 7.6748 |
| 3 | 2279 | nao_irrigado | 1.7775 | -0.013636 | 7.5250 |
| 4 | 2282 | nao_irrigado | 1.7342 | -0.013516 | 7.2452 |
| 5 | 2294 | irrigado | 1.4825 | 0.017307 | 6.9936 |
| 6 | 2278 | nao_irrigado | 1.7348 | -0.012435 | 6.9170 |
| 7 | 2295 | irrigado | 1.4237 | 0.017390 | 6.6886 |
| 8 | 2275 | nao_irrigado | 1.5966 | -0.013705 | 6.5304 |
| 9 | 2276 | nao_irrigado | 1.6382 | -0.012850 | 6.5019 |
| 10 | 2277 | nao_irrigado | 1.6825 | -0.011992 | 6.4874 |
| 11 | 2270 | nao_irrigado | 1.4736 | -0.015658 | 6.4384 |
| 12 | 2273 | nao_irrigado | 1.5243 | -0.014534 | 6.3783 |
| 13 | 2272 | nao_irrigado | 1.5034 | -0.014827 | 6.3507 |
| 14 | 2274 | nao_irrigado | 1.5546 | -0.013816 | 6.3284 |
| 15 | 2271 | nao_irrigado | 1.4876 | -0.014932 | 6.2937 |
| 16 | 2293 | irrigado | 1.4778 | 0.014393 | 6.0737 |
| 17 | 2269 | nao_irrigado | 1.4292 | -0.014737 | 5.9063 |
| 18 | 1666 | irrigado | 1.5794 | 0.010715 | 5.5169 |
| 19 | 1665 | irrigado | 1.5553 | 0.010769 | 5.3978 |
| 20 | 2331 | irrigado | 1.0665 | 0.019580 | 5.3534 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 2331 | 0.019580 | 1.0665 |
| 2332 | 0.017836 | 1.0237 |
| 2330 | 0.017564 | 1.0318 |
| 2295 | 0.017390 | 1.4237 |
| 2294 | 0.017307 | 1.4825 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 2270 | -0.015658 | 1.4736 |
| 1731 | -0.015494 | 1.0713 |
| 978 | -0.015191 | 1.2207 |
| 1730 | -0.015166 | 1.0593 |
| 895 | -0.014993 | 0.9392 |
