# PLSR por intervalos de regioes dominantes

- Dataset processado: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\base_dados_unificada_snv_savgol_1deriv.csv`
- Metadados: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\metadados_normalizados_soft.csv`
- Intervalos de entrada: `C:\Users\muril\OneDrive\Documentos\AgroSATHidrico\dados_processados_soft\plsr_pca_irrigacao\regioes_dominantes_por_threshold.csv`
- Total de intervalos avaliados: `50`

## Melhor intervalo por AUC

- `thr_1em05_rank_05_1310_1470` | threshold `1e-05` | faixa `1310-1470 nm` | AUC `0.949843` | RMSECV `0.310991` | R2CV `0.613137` | Accuracy `0.884527`

## Melhor intervalo por RMSECV

- `thr_1em05_rank_05_1310_1470` | threshold `1e-05` | faixa `1310-1470 nm` | RMSECV `0.310991` | AUC `0.949843` | R2CV `0.613137` | Accuracy `0.884527`

## Melhores por threshold

| threshold | faixa (nm) | bandas | comp. | AUC | RMSECV | R2CV | accuracy | top VIP | top abs coef |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1e-05 | 1310-1470 | 161 | 15 | 0.949843 | 0.310991 | 0.613137 | 0.884527 | 1438 | 1381 |
| 0.01 | 1280-1471 | 192 | 15 | 0.949421 | 0.311316 | 0.612327 | 0.886259 | 1438 | 1373 |
| 0.05 | 1279-1472 | 194 | 15 | 0.949365 | 0.311101 | 0.612864 | 0.885681 | 1438 | 1373 |
| 0.0001 | 1306-1470 | 165 | 15 | 0.949293 | 0.311497 | 0.611878 | 0.885104 | 1438 | 1381 |
| 0.001 | 1281-1471 | 191 | 14 | 0.948998 | 0.311797 | 0.611127 | 0.885681 | 1438 | 1373 |

## Top 15 intervalos por AUC

| rank AUC | threshold | rank regiao | faixa (nm) | comp. | AUC | RMSECV | R2CV | accuracy |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1e-05 | 5 | 1310-1470 | 15 | 0.949843 | 0.310991 | 0.613137 | 0.884527 |
| 2 | 0.01 | 5 | 1280-1471 | 15 | 0.949421 | 0.311316 | 0.612327 | 0.886259 |
| 3 | 0.05 | 5 | 1279-1472 | 15 | 0.949365 | 0.311101 | 0.612864 | 0.885681 |
| 4 | 0.0001 | 5 | 1306-1470 | 15 | 0.949293 | 0.311497 | 0.611878 | 0.885104 |
| 5 | 0.001 | 5 | 1281-1471 | 14 | 0.948998 | 0.311797 | 0.611127 | 0.885681 |
| 6 | 0.001 | 4 | 1477-1678 | 10 | 0.943295 | 0.327281 | 0.571546 | 0.873557 |
| 7 | 1e-05 | 4 | 1478-1677 | 10 | 0.943275 | 0.327399 | 0.571236 | 0.874134 |
| 8 | 0.01 | 3 | 1476-1679 | 10 | 0.943268 | 0.327253 | 0.571619 | 0.872402 |
| 9 | 0.0001 | 4 | 1477-1677 | 10 | 0.943258 | 0.327297 | 0.571503 | 0.872979 |
| 10 | 0.05 | 3 | 1476-1680 | 10 | 0.943240 | 0.327247 | 0.571634 | 0.872402 |
| 11 | 0.01 | 2 | 2017-2238 | 10 | 0.938215 | 0.324593 | 0.578554 | 0.878176 |
| 12 | 0.001 | 2 | 2018-2238 | 10 | 0.938173 | 0.324669 | 0.578357 | 0.878753 |
| 13 | 0.0001 | 2 | 2019-2237 | 10 | 0.938063 | 0.324765 | 0.578109 | 0.877021 |
| 14 | 1e-05 | 2 | 2020-2237 | 10 | 0.937980 | 0.324803 | 0.578009 | 0.875866 |
| 15 | 0.05 | 2 | 2016-2239 | 11 | 0.937979 | 0.324361 | 0.579156 | 0.876443 |
