# PLSR e PCA: irrigado vs nao_irrigado

- Dataset analisado: `1732` amostras x `2151` bandas
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`)
- Classes: irrigado = 868, nao_irrigado = 864
- Melhor numero de componentes PLSR: 15
- RMSECV: 0.244092
- R2CV: 0.761675
- AUC: 0.992006
- Accuracy com corte 0.5: 0.961316
- PCA: PC1 = 46.63% da variancia, PC2 = 13.98%

## Bandas com coeficiente mais positivo

| banda | coeficiente | VIP | interpretacao |
| ---: | ---: | ---: | --- |
| 908 | 0.020123 | 1.222319 | mais associado a irrigado |
| 909 | 0.020077 | 1.131717 | mais associado a irrigado |
| 1149 | 0.017861 | 0.893524 | mais associado a irrigado |
| 1148 | 0.017393 | 0.890081 | mais associado a irrigado |
| 879 | 0.017022 | 1.291971 | mais associado a irrigado |
| 370 | 0.016182 | 0.946052 | mais associado a irrigado |
| 1150 | 0.015238 | 0.871369 | mais associado a irrigado |
| 1205 | 0.015170 | 0.870976 | mais associado a irrigado |
| 959 | 0.015000 | 1.203357 | mais associado a irrigado |
| 449 | 0.014853 | 1.236854 | mais associado a irrigado |
| 1147 | 0.014802 | 0.871901 | mais associado a irrigado |
| 880 | 0.014633 | 1.275505 | mais associado a irrigado |
| 2330 | 0.014378 | 1.080638 | mais associado a irrigado |
| 910 | 0.014264 | 0.997712 | mais associado a irrigado |
| 2331 | 0.013594 | 1.103330 | mais associado a irrigado |

## Bandas com coeficiente mais negativo

| banda | coeficiente | VIP | interpretacao |
| ---: | ---: | ---: | --- |
| 458 | -0.023747 | 1.308757 | mais associado a nao_irrigado |
| 896 | -0.023699 | 0.931552 | mais associado a nao_irrigado |
| 895 | -0.021471 | 0.902816 | mais associado a nao_irrigado |
| 395 | -0.018361 | 1.166259 | mais associado a nao_irrigado |
| 459 | -0.018178 | 1.266077 | mais associado a nao_irrigado |
| 1725 | -0.017498 | 1.034750 | mais associado a nao_irrigado |
| 1724 | -0.017282 | 1.007962 | mais associado a nao_irrigado |
| 457 | -0.016825 | 1.252713 | mais associado a nao_irrigado |
| 1726 | -0.016674 | 1.057850 | mais associado a nao_irrigado |
| 2269 | -0.016435 | 1.601719 | mais associado a nao_irrigado |
| 1731 | -0.016120 | 1.124083 | mais associado a nao_irrigado |
| 372 | -0.016049 | 0.987820 | mais associado a nao_irrigado |
| 2268 | -0.015829 | 1.556311 | mais associado a nao_irrigado |
| 2270 | -0.015485 | 1.636516 | mais associado a nao_irrigado |
| 1723 | -0.015465 | 0.981546 | mais associado a nao_irrigado |

## Bandas com maior VIP

| banda | VIP | coeficiente | direcao |
| ---: | ---: | ---: | --- |
| 2278 | 1.718336 | -0.012116 | nao_irrigado |
| 2277 | 1.710585 | -0.010518 | nao_irrigado |
| 2276 | 1.708457 | -0.010116 | nao_irrigado |
| 2279 | 1.704506 | -0.012687 | nao_irrigado |
| 2275 | 1.701345 | -0.010458 | nao_irrigado |
| 2274 | 1.699011 | -0.012533 | nao_irrigado |
| 2273 | 1.696424 | -0.014819 | nao_irrigado |
| 2272 | 1.673606 | -0.013840 | nao_irrigado |
| 2271 | 1.651501 | -0.013325 | nao_irrigado |
| 2280 | 1.646228 | -0.011882 | nao_irrigado |
| 2292 | 1.640833 | 0.003684 | irrigado |
| 2291 | 1.639366 | 0.001550 | irrigado |
| 2270 | 1.636516 | -0.015485 | nao_irrigado |
| 1664 | 1.631233 | 0.010687 | irrigado |
| 2293 | 1.625761 | 0.004753 | irrigado |
| 1665 | 1.624429 | 0.009115 | irrigado |
| 1666 | 1.623229 | 0.005577 | irrigado |
| 1661 | 1.613315 | 0.011318 | irrigado |
| 2290 | 1.609842 | -0.000811 | nao_irrigado |
| 1663 | 1.607916 | 0.009745 | irrigado |
