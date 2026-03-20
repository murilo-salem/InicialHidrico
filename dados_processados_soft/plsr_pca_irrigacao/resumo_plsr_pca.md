# PLSR e PCA: irrigado vs nao_irrigado

- Dataset analisado: `1732` amostras x `2151` bandas
- Dados usados: dataset processado (`SNV + Savitzky-Golay + 1a derivada`)
- Classes: irrigado = 868, nao_irrigado = 864
- Melhor numero de componentes PLSR: 18
- RMSECV: 0.242784
- R2CV: 0.764223
- AUC: 0.992633
- Accuracy com corte 0.5: 0.963048
- PCA: PC1 = 46.63% da variancia, PC2 = 13.98%

## Bandas com coeficiente mais positivo

| banda | coeficiente | VIP | interpretacao |
| ---: | ---: | ---: | --- |
| 1149 | 0.026620 | 0.896295 | mais associado a irrigado |
| 1148 | 0.026013 | 0.892897 | mais associado a irrigado |
| 1150 | 0.022274 | 0.871105 | mais associado a irrigado |
| 909 | 0.022049 | 1.132701 | mais associado a irrigado |
| 1147 | 0.021854 | 0.872325 | mais associado a irrigado |
| 908 | 0.019846 | 1.223722 | mais associado a irrigado |
| 370 | 0.019671 | 0.947056 | mais associado a irrigado |
| 879 | 0.019594 | 1.290496 | mais associado a irrigado |
| 439 | 0.018932 | 1.132366 | mais associado a irrigado |
| 2330 | 0.018470 | 1.075741 | mais associado a irrigado |
| 2070 | 0.018195 | 1.096159 | mais associado a irrigado |
| 2114 | 0.018017 | 1.117538 | mais associado a irrigado |
| 2113 | 0.018001 | 1.113296 | mais associado a irrigado |
| 880 | 0.017973 | 1.270626 | mais associado a irrigado |
| 682 | 0.017650 | 0.763511 | mais associado a irrigado |

## Bandas com coeficiente mais negativo

| banda | coeficiente | VIP | interpretacao |
| ---: | ---: | ---: | --- |
| 458 | -0.031572 | 1.309055 | mais associado a nao_irrigado |
| 372 | -0.028851 | 1.010120 | mais associado a nao_irrigado |
| 896 | -0.028688 | 0.927928 | mais associado a nao_irrigado |
| 895 | -0.025768 | 0.900996 | mais associado a nao_irrigado |
| 459 | -0.022867 | 1.266137 | mais associado a nao_irrigado |
| 457 | -0.021694 | 1.254812 | mais associado a nao_irrigado |
| 395 | -0.020698 | 1.171993 | mais associado a nao_irrigado |
| 1731 | -0.019912 | 1.119526 | mais associado a nao_irrigado |
| 1724 | -0.019890 | 1.005717 | mais associado a nao_irrigado |
| 1725 | -0.019773 | 1.032125 | mais associado a nao_irrigado |
| 1720 | -0.019559 | 0.995943 | mais associado a nao_irrigado |
| 1175 | -0.019524 | 0.977784 | mais associado a nao_irrigado |
| 2269 | -0.019233 | 1.596899 | mais associado a nao_irrigado |
| 2268 | -0.019015 | 1.551055 | mais associado a nao_irrigado |
| 1732 | -0.018873 | 1.111647 | mais associado a nao_irrigado |

## Bandas com maior VIP

| banda | VIP | coeficiente | direcao |
| ---: | ---: | ---: | --- |
| 2278 | 1.712996 | -0.013828 | nao_irrigado |
| 2277 | 1.705768 | -0.011301 | nao_irrigado |
| 2276 | 1.703686 | -0.010680 | nao_irrigado |
| 2279 | 1.699262 | -0.014232 | nao_irrigado |
| 2275 | 1.696551 | -0.010965 | nao_irrigado |
| 2274 | 1.693350 | -0.014251 | nao_irrigado |
| 2273 | 1.690144 | -0.017830 | nao_irrigado |
| 2272 | 1.668404 | -0.015401 | nao_irrigado |
| 2271 | 1.647923 | -0.013933 | nao_irrigado |
| 2280 | 1.641925 | -0.012133 | nao_irrigado |
| 2292 | 1.635070 | 0.004329 | irrigado |
| 2291 | 1.633519 | 0.000192 | irrigado |
| 2270 | 1.632151 | -0.017419 | nao_irrigado |
| 1664 | 1.626174 | 0.012902 | irrigado |
| 1665 | 1.620540 | 0.011360 | irrigado |
| 2293 | 1.619947 | 0.005828 | irrigado |
| 1666 | 1.616743 | 0.005055 | irrigado |
| 1661 | 1.606872 | 0.010518 | irrigado |
| 2290 | 1.604527 | -0.003812 | nao_irrigado |
| 1663 | 1.600829 | 0.010025 | irrigado |
