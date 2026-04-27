# PLSR: manha / BR16

- Objetivo: diferenciar `irrigado` vs `nao_irrigado` no subconjunto selecionado.
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas: 2017-02-23, 2017-02-24, 2017-03-02
- Amostras totais: 192
- Classes: irrigado = 96, nao_irrigado = 96
- Folds efetivos: 5
- Melhor numero de componentes PLSR: 10
- RMSECV: 0.149017
- R2CV: 0.911176
- AUC: 1.000000
- Accuracy: 1.000000
- Score de banda otima usado no ranking: z(VIP) + z(|coeficiente PLSR|).

## Top bandas otimas

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 1826 | irrigado | 1.5904 | 0.007377 | 7.5808 |
| 2 | 1816 | irrigado | 1.4135 | 0.008608 | 7.4699 |
| 3 | 1835 | irrigado | 1.5702 | 0.007360 | 7.4538 |
| 4 | 907 | irrigado | 1.5978 | 0.006998 | 7.3487 |
| 5 | 906 | irrigado | 1.5698 | 0.006951 | 7.1558 |
| 6 | 1834 | irrigado | 1.5170 | 0.007178 | 7.0212 |
| 7 | 1827 | irrigado | 1.5142 | 0.007115 | 6.9604 |
| 8 | 1833 | irrigado | 1.4943 | 0.007094 | 6.8323 |
| 9 | 1815 | irrigado | 1.3853 | 0.007932 | 6.8212 |
| 10 | 1832 | irrigado | 1.4820 | 0.007044 | 6.7271 |
| 11 | 1828 | irrigado | 1.4852 | 0.007019 | 6.7271 |
| 12 | 1831 | irrigado | 1.4741 | 0.007008 | 6.6557 |
| 13 | 1829 | irrigado | 1.4713 | 0.006978 | 6.6185 |
| 14 | 1830 | irrigado | 1.4702 | 0.006985 | 6.6180 |
| 15 | 1817 | irrigado | 1.3247 | 0.007978 | 6.5122 |
| 16 | 2186 | irrigado | 1.4690 | 0.006535 | 6.2857 |
| 17 | 2185 | irrigado | 1.4591 | 0.006304 | 6.0624 |
| 18 | 2187 | irrigado | 1.4222 | 0.006379 | 5.9083 |
| 19 | 436 | irrigado | 1.3770 | 0.006471 | 5.7185 |
| 20 | 2184 | irrigado | 1.4270 | 0.005993 | 5.6564 |

## Coeficientes mais positivos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 1816 | 0.008608 | 1.4135 |
| 1817 | 0.007978 | 1.3247 |
| 1815 | 0.007932 | 1.3853 |
| 1826 | 0.007377 | 1.5904 |
| 1835 | 0.007360 | 1.5702 |

## Coeficientes mais negativos

| banda | coeficiente | VIP |
| ---: | ---: | ---: |
| 921 | -0.006423 | 0.9486 |
| 920 | -0.005907 | 0.9289 |
| 971 | -0.005819 | 0.8160 |
| 897 | -0.005652 | 0.9263 |
| 2309 | -0.005096 | 1.1677 |
