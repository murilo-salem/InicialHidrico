# PLSR: tarde / EMB48

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 192
- Classes: irrigado = 96, nao_irrigado = 96
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 12
- RMSECV: 0.229021
- R2CV: 0.790197
- AUC: 0.993273
- Accuracy: 0.973958
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 975 | nao_irrigado | 1.4201 | -0.013102 | 6.6810 |
| 2 | 2229 | irrigado | 1.3600 | 0.012297 | 6.0015 |
| 3 | 858 | nao_irrigado | 1.4482 | -0.010939 | 5.9910 |
| 4 | 391 | nao_irrigado | 1.2681 | -0.013129 | 5.7814 |
| 5 | 859 | nao_irrigado | 1.4185 | -0.010374 | 5.5886 |
| 6 | 976 | nao_irrigado | 1.3713 | -0.010929 | 5.5263 |
| 7 | 2230 | irrigado | 1.4317 | 0.009691 | 5.3966 |
| 8 | 1731 | nao_irrigado | 1.0883 | -0.014742 | 5.3447 |
| 9 | 2390 | nao_irrigado | 1.1461 | -0.013379 | 5.1499 |
| 10 | 369 | irrigado | 1.2296 | 0.012023 | 5.1116 |
| 11 | 974 | nao_irrigado | 1.2988 | -0.010720 | 5.0097 |
| 12 | 1732 | nao_irrigado | 1.0783 | -0.013938 | 4.9661 |
| 13 | 987 | nao_irrigado | 1.3182 | -0.009979 | 4.8311 |
| 14 | 986 | nao_irrigado | 1.2567 | -0.010870 | 4.8168 |
| 15 | 2391 | nao_irrigado | 1.1387 | -0.012627 | 4.8071 |
| 16 | 1730 | nao_irrigado | 1.0517 | -0.013843 | 4.7688 |
| 17 | 990 | nao_irrigado | 1.2416 | -0.010960 | 4.7619 |
| 18 | 1663 | irrigado | 1.4612 | 0.007622 | 4.7525 |
| 19 | 995 | nao_irrigado | 1.1874 | -0.011702 | 4.7315 |
| 20 | 857 | nao_irrigado | 1.3886 | -0.008464 | 4.6520 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 2229 | 0.012297 | 1.3600 |
| 2447 | 0.012290 | 1.0721 |
| 369 | 0.012023 | 1.2296 |
| 2448 | 0.011452 | 1.0032 |
| 431 | 0.011216 | 1.0537 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 1731 | -0.014742 | 1.0883 |
| 1732 | -0.013938 | 1.0783 |
| 1730 | -0.013843 | 1.0517 |
| 2390 | -0.013379 | 1.1461 |
| 391 | -0.013129 | 1.2681 |
