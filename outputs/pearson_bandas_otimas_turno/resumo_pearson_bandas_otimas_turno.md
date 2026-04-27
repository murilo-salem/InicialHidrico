# Correlacao de Pearson nas bandas otimas

- Base de reflectancia usada: `base_dados_unificada.xlsx`
- Bandas otimas usadas: `top_10_irrigado_top_10_nao_irrigado.csv`
- Total de bandas comparadas: 20
- Turnos comparados: manha vs tarde
- Observacao: esta analise usa reflectancia bruta da planilha original, nao o sinal processado SNV + Savitzky-Golay + 1a derivada.

## Resumo por data

| data | n manha | n tarde | Pearson r | p-value | MAD | RMSE | maior diferenca |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 23/02/2017 | 192 | 192 | 0.999985 | 3.399e-42 | 0.014199 | 0.014655 | banda 1652 (-0.017480) |
| 24/02/2017 | 192 | 192 | 0.999708 | 1.475e-30 | 0.004589 | 0.004738 | banda 2280 (+0.007740) |
| 02/03/2017 | 196 | 192 | 0.999342 | 2.205e-27 | 0.008431 | 0.008513 | banda 1425 (+0.010173) |

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

## Maiores diferencas absolutas em 23/02/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1652 | irrigado | 0.386910 | 0.404389 | -0.017480 | 0.017480 |
| 1653 | irrigado | 0.387011 | 0.404476 | -0.017465 | 0.017465 |
| 1654 | irrigado | 0.387103 | 0.404559 | -0.017457 | 0.017457 |
| 1655 | irrigado | 0.387178 | 0.404630 | -0.017452 | 0.017452 |
| 1656 | irrigado | 0.387249 | 0.404693 | -0.017445 | 0.017445 |

## Maiores diferencas absolutas em 24/02/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 2280 | nao_irrigado | 0.252485 | 0.244744 | +0.007740 | 0.007740 |
| 2279 | nao_irrigado | 0.252955 | 0.245226 | +0.007728 | 0.007728 |
| 1661 | irrigado | 0.386738 | 0.391409 | -0.004671 | 0.004671 |
| 1660 | irrigado | 0.386725 | 0.391396 | -0.004671 | 0.004671 |
| 1659 | irrigado | 0.386705 | 0.391370 | -0.004665 | 0.004665 |

## Maiores diferencas absolutas em 02/03/2017

| banda | classe dominante | manha | tarde | delta manha - tarde | |delta| |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1425 | nao_irrigado | 0.237903 | 0.227730 | +0.010173 | 0.010173 |
| 1426 | nao_irrigado | 0.237311 | 0.227173 | +0.010138 | 0.010138 |
| 1427 | nao_irrigado | 0.236789 | 0.226696 | +0.010093 | 0.010093 |
| 1428 | nao_irrigado | 0.236336 | 0.226293 | +0.010043 | 0.010043 |
| 1429 | nao_irrigado | 0.235962 | 0.225962 | +0.010000 | 0.010000 |

## Leitura rapida

- Pearson foi calculado entre os vetores de reflectancia media das bandas otimas, comparando manha e tarde em cada data.
- r proximo de 1 indica que o perfil espectral medio entre manha e tarde manteve a mesma forma nas bandas selecionadas.
- MAD e RMSE ajudam a separar semelhanca de forma da magnitude das diferencas absolutas de reflectancia.
