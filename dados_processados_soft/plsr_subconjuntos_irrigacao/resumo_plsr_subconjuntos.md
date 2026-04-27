# PLSR por turno e genotipo

- Objetivo: identificar bandas otimas para diferenciar `irrigado` vs `nao_irrigado` em subconjuntos de turno e genotipo.
- Base usada: dataset processado (`SNV + Savitzky-Golay + 1a derivada`).
- Datas usadas em todos os subconjuntos: 2017-02-23, 2017-02-24, 2017-03-02
- Score de banda otima: z(VIP) + z(|coeficiente PLSR|).

## Resumo dos subconjuntos

| subconjunto | n | irrigado | nao_irrigado | folds | comp. | RMSECV | AUC | banda #1 | direcao | VIP | coeficiente |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Turno manha | 580 | 292 | 288 | 5 | 13 | 0.215134 | 0.994245 | 392 | nao_irrigado | 1.5166 | -0.015452 |
| Turno tarde | 576 | 288 | 288 | 5 | 13 | 0.262836 | 0.987570 | 2281 | nao_irrigado | 1.8067 | -0.014045 |
| Genotipo BR16 | 384 | 192 | 192 | 5 | 15 | 0.204262 | 0.999051 | 2270 | nao_irrigado | 1.7290 | -0.017027 |
| Genotipo CD202 | 388 | 196 | 192 | 5 | 12 | 0.211917 | 0.999070 | 2280 | nao_irrigado | 1.6435 | -0.012757 |
| Genotipo EMB48 | 384 | 192 | 192 | 5 | 13 | 0.238302 | 0.994249 | 1661 | irrigado | 1.5811 | 0.015169 |
| manha / BR16 | 192 | 96 | 96 | 5 | 10 | 0.149017 | 1.000000 | 1826 | irrigado | 1.5904 | 0.007377 |
| manha / CD202 | 196 | 100 | 96 | 5 | 14 | 0.180154 | 0.998437 | 2149 | irrigado | 1.4903 | 0.011419 |
| manha / EMB48 | 192 | 96 | 96 | 5 | 14 | 0.195264 | 0.998155 | 383 | nao_irrigado | 1.7115 | -0.018994 |
| tarde / BR16 | 192 | 96 | 96 | 5 | 15 | 0.206154 | 0.998915 | 1668 | irrigado | 1.6873 | 0.014185 |
| tarde / CD202 | 192 | 96 | 96 | 5 | 12 | 0.214434 | 0.999891 | 2281 | nao_irrigado | 1.7372 | -0.010976 |
| tarde / EMB48 | 192 | 96 | 96 | 5 | 12 | 0.229021 | 0.993273 | 975 | nao_irrigado | 1.4201 | -0.013102 |

## Top 5 bandas por subconjunto

### Turno manha

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 392 | nao_irrigado | 1.5166 | -0.015452 | 7.0812 |
| 2 | 395 | nao_irrigado | 1.3672 | -0.015698 | 6.3137 |
| 3 | 391 | nao_irrigado | 1.3576 | -0.015332 | 6.1341 |
| 4 | 406 | nao_irrigado | 1.2826 | -0.016584 | 6.1326 |
| 5 | 390 | nao_irrigado | 1.2486 | -0.016485 | 5.9056 |

### Turno tarde

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2281 | nao_irrigado | 1.8067 | -0.014045 | 7.8147 |
| 2 | 2280 | nao_irrigado | 1.8009 | -0.013695 | 7.6748 |
| 3 | 2279 | nao_irrigado | 1.7775 | -0.013636 | 7.5250 |
| 4 | 2282 | nao_irrigado | 1.7342 | -0.013516 | 7.2452 |
| 5 | 2294 | irrigado | 1.4825 | 0.017307 | 6.9936 |

### Genotipo BR16

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2270 | nao_irrigado | 1.7290 | -0.017027 | 8.0208 |
| 2 | 2271 | nao_irrigado | 1.7382 | -0.016370 | 7.8597 |
| 3 | 2272 | nao_irrigado | 1.7381 | -0.015416 | 7.5573 |
| 4 | 2269 | nao_irrigado | 1.6803 | -0.015848 | 7.3987 |
| 5 | 932 | nao_irrigado | 1.2347 | -0.022809 | 7.3226 |

### Genotipo CD202

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2280 | nao_irrigado | 1.6435 | -0.012757 | 7.3338 |
| 2 | 873 | irrigado | 1.2905 | 0.017655 | 7.1776 |
| 3 | 2279 | nao_irrigado | 1.6131 | -0.012618 | 7.1132 |
| 4 | 2281 | nao_irrigado | 1.6231 | -0.011979 | 6.9323 |
| 5 | 2278 | nao_irrigado | 1.5753 | -0.012456 | 6.8424 |

### Genotipo EMB48

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 1661 | irrigado | 1.5811 | 0.015169 | 6.8954 |
| 2 | 994 | nao_irrigado | 1.5934 | -0.014440 | 6.7347 |
| 3 | 1660 | irrigado | 1.5140 | 0.014174 | 6.2129 |
| 4 | 391 | nao_irrigado | 1.3544 | -0.016844 | 6.1708 |
| 5 | 1663 | irrigado | 1.5114 | 0.013262 | 5.9129 |

### manha / BR16

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 1826 | irrigado | 1.5904 | 0.007377 | 7.5808 |
| 2 | 1816 | irrigado | 1.4135 | 0.008608 | 7.4699 |
| 3 | 1835 | irrigado | 1.5702 | 0.007360 | 7.4538 |
| 4 | 907 | irrigado | 1.5978 | 0.006998 | 7.3487 |
| 5 | 906 | irrigado | 1.5698 | 0.006951 | 7.1558 |

### manha / CD202

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2149 | irrigado | 1.4903 | 0.011419 | 6.9215 |
| 2 | 2150 | irrigado | 1.4622 | 0.011441 | 6.7569 |
| 3 | 2170 | irrigado | 1.5130 | 0.010634 | 6.7165 |
| 4 | 2148 | irrigado | 1.4982 | 0.010727 | 6.6660 |
| 5 | 2151 | irrigado | 1.4386 | 0.011418 | 6.6002 |

### manha / EMB48

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 383 | nao_irrigado | 1.7115 | -0.018994 | 10.1218 |
| 2 | 988 | irrigado | 1.2568 | 0.018969 | 7.1864 |
| 3 | 382 | nao_irrigado | 1.5184 | -0.012718 | 6.7020 |
| 4 | 384 | nao_irrigado | 1.6102 | -0.010442 | 6.5034 |
| 5 | 408 | nao_irrigado | 1.3944 | -0.013532 | 6.1861 |

### tarde / BR16

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 1668 | irrigado | 1.6873 | 0.014185 | 7.8054 |
| 2 | 807 | irrigado | 1.2831 | 0.019238 | 7.5054 |
| 3 | 2271 | nao_irrigado | 1.6525 | -0.013797 | 7.4781 |
| 4 | 1669 | irrigado | 1.5620 | 0.014905 | 7.4017 |
| 5 | 2282 | nao_irrigado | 1.8582 | -0.010597 | 7.4000 |

### tarde / CD202

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2281 | nao_irrigado | 1.7372 | -0.010976 | 7.6544 |
| 2 | 553 | nao_irrigado | 1.5350 | -0.012159 | 6.9351 |
| 3 | 1670 | irrigado | 1.3904 | 0.014234 | 6.9106 |
| 4 | 1669 | irrigado | 1.4304 | 0.013640 | 6.9100 |
| 5 | 2282 | nao_irrigado | 1.6399 | -0.010344 | 6.8298 |

### tarde / EMB48

| rank | banda | direcao | VIP | coeficiente | score otimo |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 975 | nao_irrigado | 1.4201 | -0.013102 | 6.6810 |
| 2 | 2229 | irrigado | 1.3600 | 0.012297 | 6.0015 |
| 3 | 858 | nao_irrigado | 1.4482 | -0.010939 | 5.9910 |
| 4 | 391 | nao_irrigado | 1.2681 | -0.013129 | 5.7814 |
| 5 | 859 | nao_irrigado | 1.4185 | -0.010374 | 5.5886 |

