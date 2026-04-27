# PLSR: manha / EMB48

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 192
- Classes: irrigado = 96, nao_irrigado = 96
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 14
- RMSECV: 0.195264
- R2CV: 0.847488
- AUC: 0.998155
- Accuracy: 0.973958
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 383 | nao_irrigado | 1.7115 | -0.018994 | 10.1218 |
| 2 | 988 | irrigado | 1.2568 | 0.018969 | 7.1864 |
| 3 | 382 | nao_irrigado | 1.5184 | -0.012718 | 6.7020 |
| 4 | 384 | nao_irrigado | 1.6102 | -0.010442 | 6.5034 |
| 5 | 408 | nao_irrigado | 1.3944 | -0.013532 | 6.1861 |
| 6 | 385 | nao_irrigado | 1.5050 | -0.010520 | 5.8534 |
| 7 | 388 | nao_irrigado | 1.3547 | -0.012961 | 5.7326 |
| 8 | 386 | nao_irrigado | 1.3870 | -0.011388 | 5.3951 |
| 9 | 389 | nao_irrigado | 1.3517 | -0.011886 | 5.3403 |
| 10 | 409 | nao_irrigado | 1.5033 | -0.008940 | 5.2942 |
| 11 | 2286 | irrigado | 1.0874 | 0.016573 | 5.2648 |
| 12 | 669 | nao_irrigado | 1.5464 | -0.007984 | 5.2401 |
| 13 | 1276 | irrigado | 1.1590 | 0.015077 | 5.2067 |
| 14 | 989 | irrigado | 1.1652 | 0.014950 | 5.2023 |
| 15 | 670 | nao_irrigado | 1.4929 | -0.008759 | 5.1647 |
| 16 | 668 | nao_irrigado | 1.5668 | -0.007238 | 5.1130 |
| 17 | 407 | nao_irrigado | 1.2228 | -0.013313 | 5.0057 |
| 18 | 387 | nao_irrigado | 1.3477 | -0.010971 | 4.9977 |
| 19 | 1633 | irrigado | 1.1741 | 0.014101 | 4.9653 |
| 20 | 971 | irrigado | 1.4161 | 0.009424 | 4.9013 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 988 | 0.018969 | 1.2568 |
| 2286 | 0.016573 | 1.0874 |
| 2285 | 0.015193 | 1.0109 |
| 1276 | 0.015077 | 1.1590 |
| 989 | 0.014950 | 1.1652 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 383 | -0.018994 | 1.7115 |
| 932 | -0.014897 | 0.9999 |
| 931 | -0.014788 | 1.0115 |
| 408 | -0.013532 | 1.3944 |
| 407 | -0.013313 | 1.2228 |
