# Correlacao de Pearson nas bandas otimas por genotipo

- Base de reflectancia usada: `base_dados_unificada.xlsx`
- Bandas otimas usadas: `top_10_irrigado_top_10_nao_irrigado.csv`
- Total de bandas comparadas: 20
- Comparacao realizada por genotipo, sempre entre manha e tarde na mesma data.
- Observacao: esta analise usa reflectancia bruta da planilha original, nao o sinal processado SNV + Savitzky-Golay + 1a derivada.

## Resumo por genotipo e data

| genotipo | data | n manha | n tarde | Pearson r | p-value | MAD | RMSE | maior diferenca |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BR16 | 23/02/2017 | 64 | 64 | 0.999949 | 2.117e-37 | 0.011702 | 0.012833 | banda 1652 (-0.016803) |
| BR16 | 24/02/2017 | 64 | 64 | 0.999738 | 5.579e-31 | 0.004059 | 0.004952 | banda 2280 (+0.009323) |
| BR16 | 02/03/2017 | 64 | 64 | 0.999276 | 5.197e-27 | 0.007905 | 0.008226 | banda 1425 (+0.011181) |
| CD202 | 23/02/2017 | 64 | 64 | 0.999984 | 8.219e-42 | 0.015119 | 0.015619 | banda 1652 (-0.018714) |
| CD202 | 24/02/2017 | 64 | 64 | 0.999652 | 7.030e-30 | 0.004091 | 0.004663 | banda 2280 (+0.010053) |
| CD202 | 02/03/2017 | 68 | 64 | 0.998983 | 1.100e-25 | 0.009341 | 0.010905 | banda 1425 (+0.016379) |
| EMB48 | 23/02/2017 | 64 | 64 | 0.999914 | 2.520e-35 | 0.015774 | 0.015924 | banda 1430 (-0.016928) |
| EMB48 | 24/02/2017 | 64 | 64 | 0.999710 | 1.397e-30 | 0.005965 | 0.007342 | banda 1658 (-0.010133) |
| EMB48 | 02/03/2017 | 64 | 64 | 0.999668 | 4.686e-30 | 0.008060 | 0.009447 | banda 1661 (-0.012929) |

## Bandas otimas utilizadas

| ordem global | rank na classe | classe dominante | banda | VIP | Cohen's d | q-value | score combinado |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | irrigado | 1660 | 1.5902 | 1.4298 | 5.624e-155 | 6.6189 |
| 2 | 2 | irrigado | 1659 | 1.5599 | 1.4576 | 5.471e-160 | 6.6077 |
| 3 | 3 | irrigado | 1654 | 1.4422 | 1.5625 | 2.153e-179 | 6.5559 |
| 4 | 4 | irrigado | 1661 | 1.6069 | 1.3964 | 6.081e-149 | 6.5275 |
| 5 | 5 | irrigado | 1655 | 1.4525 | 1.5431 | 1.011e-175 | 6.5033 |
| 6 | 6 | irrigado | 1658 | 1.5209 | 1.4754 | 3.542e-163 | 6.4964 |
| 7 | 7 | irrigado | 1653 | 1.4119 | 1.5719 | 3.167e-181 | 6.4487 |
| 8 | 8 | irrigado | 1656 | 1.4324 | 1.5077 | 3.563e-169 | 6.2035 |
| 9 | 9 | irrigado | 1657 | 1.4537 | 1.4839 | 1.035e-164 | 6.1857 |
| 10 | 10 | irrigado | 1652 | 1.3658 | 1.5593 | 4.665e-179 | 6.1385 |
| 11 | 1 | nao_irrigado | 1924 | 1.2794 | -1.9937 | 2.167e-258 | 8.0328 |
| 12 | 2 | nao_irrigado | 1923 | 1.3149 | -1.9496 | 1.266e-249 | 7.9692 |
| 13 | 3 | nao_irrigado | 2279 | 1.6993 | -1.5672 | 3.244e-180 | 7.9433 |
| 14 | 4 | nao_irrigado | 2280 | 1.6419 | -1.6171 | 9.064e-190 | 7.9176 |
| 15 | 5 | nao_irrigado | 1427 | 1.3630 | -1.8935 | 1.405e-237 | 7.8887 |
| 16 | 6 | nao_irrigado | 1428 | 1.3614 | -1.8934 | 1.399e-237 | 7.8800 |
| 17 | 7 | nao_irrigado | 1426 | 1.3640 | -1.8908 | 4.149e-237 | 7.8797 |
| 18 | 8 | nao_irrigado | 1429 | 1.3594 | -1.8940 | 1.036e-237 | 7.8733 |
| 19 | 9 | nao_irrigado | 1430 | 1.3574 | -1.8955 | 6.802e-238 | 7.8691 |
| 20 | 10 | nao_irrigado | 1425 | 1.3647 | -1.8869 | 2.201e-236 | 7.8624 |

## BR16

### 23/02/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1652 | irrigado | 0.393972 | 0.410776 | -0.016803 | 0.016803 |
| 1653 | irrigado | 0.394074 | 0.410866 | -0.016791 | 0.016791 |
| 1657 | irrigado | 0.394369 | 0.411158 | -0.016789 | 0.016789 |
| 1654 | irrigado | 0.394163 | 0.410951 | -0.016788 | 0.016788 |
| 1655 | irrigado | 0.394246 | 0.411033 | -0.016788 | 0.016788 |

### 24/02/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 2280 | nao_irrigado | 0.255272 | 0.245949 | +0.009323 | 0.009323 |
| 2279 | nao_irrigado | 0.255760 | 0.246443 | +0.009317 | 0.009317 |
| 1425 | nao_irrigado | 0.250209 | 0.243819 | +0.006390 | 0.006390 |
| 1426 | nao_irrigado | 0.249611 | 0.243267 | +0.006343 | 0.006343 |
| 1427 | nao_irrigado | 0.249075 | 0.242795 | +0.006280 | 0.006280 |

### 02/03/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1425 | nao_irrigado | 0.241667 | 0.230486 | +0.011181 | 0.011181 |
| 1426 | nao_irrigado | 0.241050 | 0.229907 | +0.011142 | 0.011142 |
| 1427 | nao_irrigado | 0.240520 | 0.229412 | +0.011108 | 0.011108 |
| 1428 | nao_irrigado | 0.240051 | 0.228985 | +0.011066 | 0.011066 |
| 1429 | nao_irrigado | 0.239658 | 0.228638 | +0.011020 | 0.011020 |


## CD202

### 23/02/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1652 | irrigado | 0.381354 | 0.400068 | -0.018714 | 0.018714 |
| 1653 | irrigado | 0.381454 | 0.400158 | -0.018703 | 0.018703 |
| 1654 | irrigado | 0.381550 | 0.400246 | -0.018695 | 0.018695 |
| 1655 | irrigado | 0.381621 | 0.400315 | -0.018694 | 0.018694 |
| 1656 | irrigado | 0.381696 | 0.400383 | -0.018688 | 0.018688 |

### 24/02/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 2280 | nao_irrigado | 0.245265 | 0.235212 | +0.010053 | 0.010053 |
| 2279 | nao_irrigado | 0.245729 | 0.235691 | +0.010038 | 0.010038 |
| 1425 | nao_irrigado | 0.231116 | 0.226384 | +0.004732 | 0.004732 |
| 1426 | nao_irrigado | 0.230577 | 0.225867 | +0.004710 | 0.004710 |
| 1427 | nao_irrigado | 0.230109 | 0.225420 | +0.004689 | 0.004689 |

### 02/03/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1425 | nao_irrigado | 0.241442 | 0.225063 | +0.016379 | 0.016379 |
| 1426 | nao_irrigado | 0.240863 | 0.224526 | +0.016337 | 0.016337 |
| 1427 | nao_irrigado | 0.240345 | 0.224072 | +0.016273 | 0.016273 |
| 1428 | nao_irrigado | 0.239897 | 0.223690 | +0.016207 | 0.016207 |
| 1429 | nao_irrigado | 0.239523 | 0.223371 | +0.016153 | 0.016153 |


## EMB48

### 23/02/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1430 | nao_irrigado | 0.238961 | 0.255889 | -0.016928 | 0.016928 |
| 1652 | irrigado | 0.385402 | 0.402323 | -0.016921 | 0.016921 |
| 1653 | irrigado | 0.385505 | 0.402405 | -0.016900 | 0.016900 |
| 1654 | irrigado | 0.385595 | 0.402482 | -0.016886 | 0.016886 |
| 1655 | irrigado | 0.385667 | 0.402541 | -0.016874 | 0.016874 |

### 24/02/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1658 | irrigado | 0.382077 | 0.392210 | -0.010133 | 0.010133 |
| 1660 | irrigado | 0.382129 | 0.392261 | -0.010132 | 0.010132 |
| 1659 | irrigado | 0.382105 | 0.392235 | -0.010130 | 0.010130 |
| 1657 | irrigado | 0.382038 | 0.392163 | -0.010125 | 0.010125 |
| 1661 | irrigado | 0.382156 | 0.392274 | -0.010118 | 0.010118 |

### 02/03/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1661 | irrigado | 0.376229 | 0.389158 | -0.012929 | 0.012929 |
| 1660 | irrigado | 0.376226 | 0.389138 | -0.012911 | 0.012911 |
| 1658 | irrigado | 0.376153 | 0.389063 | -0.012910 | 0.012910 |
| 1657 | irrigado | 0.376104 | 0.389005 | -0.012902 | 0.012902 |
| 1659 | irrigado | 0.376200 | 0.389101 | -0.012901 | 0.012901 |

## Leitura rapida

- Pearson foi calculado separadamente em cada genotipo, usando os vetores de reflectancia media das bandas otimas.
- Isso mostra se o padrao manha vs tarde se mantem igualmente para BR16, CD202 e EMB48.
- MAD e RMSE continuam sendo medidas de diferenca absoluta, mesmo quando r permanece muito alto.
