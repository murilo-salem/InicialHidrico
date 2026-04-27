# PLSR: Genotipo BR16

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 384
- Classes: irrigado = 192, nao_irrigado = 192
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 15
- RMSECV: 0.204262
- R2CV: 0.833108
- AUC: 0.999051
- Accuracy: 0.979167
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2270 | nao_irrigado | 1.7290 | -0.017027 | 8.0208 |
| 2 | 2271 | nao_irrigado | 1.7382 | -0.016370 | 7.8597 |
| 3 | 2272 | nao_irrigado | 1.7381 | -0.015416 | 7.5573 |
| 4 | 2269 | nao_irrigado | 1.6803 | -0.015848 | 7.3987 |
| 5 | 932 | nao_irrigado | 1.2347 | -0.022809 | 7.3226 |
| 6 | 2273 | nao_irrigado | 1.7390 | -0.014182 | 7.1716 |
| 7 | 933 | nao_irrigado | 1.2323 | -0.021851 | 7.0076 |
| 8 | 1665 | irrigado | 1.6392 | 0.015029 | 6.9293 |
| 9 | 2274 | nao_irrigado | 1.7531 | -0.012351 | 6.6646 |
| 10 | 1664 | irrigado | 1.5752 | 0.015043 | 6.6069 |
| 11 | 2275 | nao_irrigado | 1.7828 | -0.010994 | 6.3873 |
| 12 | 2268 | nao_irrigado | 1.6031 | -0.013490 | 6.2584 |
| 13 | 2276 | nao_irrigado | 1.8119 | -0.009279 | 5.9935 |
| 14 | 1666 | irrigado | 1.6382 | 0.010822 | 5.5939 |
| 15 | 1826 | irrigado | 1.6765 | 0.009859 | 5.4853 |
| 16 | 995 | irrigado | 0.9359 | 0.021758 | 5.4635 |
| 17 | 2277 | nao_irrigado | 1.8189 | -0.006591 | 5.1794 |
| 18 | 2267 | nao_irrigado | 1.5182 | -0.010957 | 5.0232 |
| 19 | 1827 | irrigado | 1.6084 | 0.009314 | 4.9645 |
| 20 | 1663 | irrigado | 1.4655 | 0.011464 | 4.9142 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 995 | 0.021758 | 0.9359 |
| 370 | 0.018697 | 0.8899 |
| 369 | 0.017909 | 0.8076 |
| 994 | 0.017851 | 0.8482 |
| 358 | 0.016822 | 0.7313 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 932 | -0.022809 | 1.2347 |
| 933 | -0.021851 | 1.2323 |
| 902 | -0.017453 | 1.0769 |
| 2270 | -0.017027 | 1.7290 |
| 931 | -0.016865 | 1.0942 |
