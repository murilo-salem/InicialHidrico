# Tabelas PLSR + Pearson + Welch t-test

- Bandas ordenadas por relevancia PLSR: z(VIP) + z(|coeficiente|).
- Limite de significancia aplicado no Welch t-test: p < 0.005.
- Pearson foi calculado entre cada banda e a classe binaria (`irrigado`=1, `nao_irrigado`=0).

## Datas

| subconjunto | rank | banda | direcao | VIP | coef. PLSR | Pearson r | p Pearson | p Welch | p Welch < 0.005 |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Data 23/02/2017 | 1 | 392 | nao_irrigado | 1.7574 | -0.024676 | -0.3350 | 1.596e-11 | 1.640e-11 | sim |
| Data 23/02/2017 | 2 | 393 | nao_irrigado | 1.9133 | -0.015098 | -0.3410 | 6.574e-12 | 6.646e-12 | sim |
| Data 23/02/2017 | 3 | 896 | nao_irrigado | 1.2914 | -0.030252 | -0.1557 | 2.217e-03 | 2.220e-03 | sim |
| Data 23/02/2017 | 4 | 391 | nao_irrigado | 1.5160 | -0.022066 | -0.3177 | 1.881e-10 | 1.967e-10 | sim |
| Data 23/02/2017 | 5 | 1665 | irrigado | 1.5400 | 0.020511 | 0.4245 | 3.116e-18 | 3.639e-18 | sim |

| Data 24/02/2017 | 1 | 2278 | nao_irrigado | 1.5491 | -0.015107 | -0.6632 | 5.271e-50 | 6.009e-50 | sim |
| Data 24/02/2017 | 2 | 2279 | nao_irrigado | 1.5515 | -0.014949 | -0.6847 | 1.979e-54 | 3.181e-54 | sim |
| Data 24/02/2017 | 3 | 2281 | nao_irrigado | 1.5276 | -0.014899 | -0.7192 | 2.240e-62 | 3.180e-61 | sim |
| Data 24/02/2017 | 4 | 2237 | irrigado | 1.6009 | 0.013805 | 0.1616 | 1.488e-03 | 1.489e-03 | sim |
| Data 24/02/2017 | 5 | 2280 | nao_irrigado | 1.5432 | -0.014631 | -0.7049 | 6.141e-59 | 2.121e-58 | sim |

| Data 02/03/2017 | 1 | 2295 | irrigado | 1.5795 | 0.009795 | 0.3035 | 1.040e-09 | 1.070e-09 | sim |
| Data 02/03/2017 | 2 | 2304 | nao_irrigado | 1.5037 | -0.010151 | -0.5469 | 1.191e-31 | 2.665e-31 | sim |
| Data 02/03/2017 | 3 | 2305 | nao_irrigado | 1.5416 | -0.008995 | -0.5667 | 2.444e-34 | 5.310e-34 | sim |
| Data 02/03/2017 | 4 | 2294 | irrigado | 1.5470 | 0.008781 | 0.3458 | 2.455e-12 | 2.405e-12 | sim |
| Data 02/03/2017 | 5 | 2296 | irrigado | 1.4562 | 0.008644 | 0.2298 | 4.809e-06 | 5.021e-06 | sim |

## Turnos

| subconjunto | rank | banda | direcao | VIP | coef. PLSR | Pearson r | p Pearson | p Welch | p Welch < 0.005 |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Turno manha | 1 | 392 | nao_irrigado | 1.5166 | -0.015452 | -0.5299 | 2.649e-43 | 2.680e-43 | sim |
| Turno manha | 2 | 395 | nao_irrigado | 1.3672 | -0.015698 | -0.4855 | 1.233e-35 | 1.197e-35 | sim |
| Turno manha | 3 | 391 | nao_irrigado | 1.3576 | -0.015332 | -0.5415 | 1.696e-45 | 2.192e-45 | sim |
| Turno manha | 4 | 406 | nao_irrigado | 1.2826 | -0.016584 | -0.4367 | 2.104e-28 | 2.084e-28 | sim |
| Turno manha | 5 | 390 | nao_irrigado | 1.2486 | -0.016485 | -0.5271 | 8.674e-43 | 1.830e-42 | sim |

| Turno tarde | 1 | 2281 | nao_irrigado | 1.8067 | -0.014045 | -0.6270 | 2.917e-64 | 3.301e-64 | sim |
| Turno tarde | 2 | 2280 | nao_irrigado | 1.8009 | -0.013695 | -0.6438 | 9.779e-69 | 9.811e-69 | sim |
| Turno tarde | 3 | 2279 | nao_irrigado | 1.7775 | -0.013636 | -0.6434 | 1.296e-68 | 1.375e-68 | sim |
| Turno tarde | 4 | 2282 | nao_irrigado | 1.7342 | -0.013516 | -0.5751 | 5.058e-52 | 6.587e-52 | sim |
| Turno tarde | 5 | 2294 | irrigado | 1.4825 | 0.017307 | 0.1889 | 4.983e-06 | 5.138e-06 | sim |

## Genotipos

| subconjunto | rank | banda | direcao | VIP | coef. PLSR | Pearson r | p Pearson | p Welch | p Welch < 0.005 |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Genotipo BR16 | 1 | 2270 | nao_irrigado | 1.7290 | -0.017027 | -0.6012 | 4.178e-39 | 1.911e-37 | sim |
| Genotipo BR16 | 2 | 2271 | nao_irrigado | 1.7382 | -0.016370 | -0.6210 | 2.512e-42 | 2.074e-40 | sim |
| Genotipo BR16 | 3 | 2272 | nao_irrigado | 1.7381 | -0.015416 | -0.6314 | 4.226e-44 | 4.730e-42 | sim |
| Genotipo BR16 | 4 | 2269 | nao_irrigado | 1.6803 | -0.015848 | -0.5735 | 5.818e-35 | 1.245e-33 | sim |
| Genotipo BR16 | 5 | 2273 | nao_irrigado | 1.7390 | -0.014182 | -0.6377 | 3.243e-45 | 4.055e-43 | sim |

| Genotipo CD202 | 1 | 2280 | nao_irrigado | 1.6435 | -0.012757 | -0.6834 | 1.065e-54 | 1.409e-54 | sim |
| Genotipo CD202 | 2 | 873 | irrigado | 1.2905 | 0.017655 | -0.2410 | 1.569e-06 | 1.545e-06 | sim |
| Genotipo CD202 | 3 | 2279 | nao_irrigado | 1.6131 | -0.012618 | -0.6682 | 1.626e-51 | 2.552e-51 | sim |
| Genotipo CD202 | 4 | 2281 | nao_irrigado | 1.6231 | -0.011979 | -0.6869 | 1.823e-55 | 1.892e-55 | sim |
| Genotipo CD202 | 5 | 2278 | nao_irrigado | 1.5753 | -0.012456 | -0.6515 | 3.019e-48 | 5.047e-48 | sim |

| Genotipo EMB48 | 1 | 1661 | irrigado | 1.5811 | 0.015169 | 0.4970 | 2.415e-25 | 3.056e-25 | sim |
| Genotipo EMB48 | 2 | 1660 | irrigado | 1.5140 | 0.014174 | 0.5215 | 3.675e-28 | 4.913e-28 | sim |
| Genotipo EMB48 | 3 | 391 | nao_irrigado | 1.3544 | -0.016844 | -0.5076 | 1.522e-26 | 3.526e-26 | sim |
| Genotipo EMB48 | 4 | 1663 | irrigado | 1.5114 | 0.013262 | 0.4104 | 4.942e-17 | 5.359e-17 | sim |
| Genotipo EMB48 | 5 | 2307 | nao_irrigado | 1.5962 | -0.011589 | -0.4410 | 1.048e-19 | 1.049e-19 | sim |

## Turno x Genotipo

| subconjunto | rank | banda | direcao | VIP | coef. PLSR | Pearson r | p Pearson | p Welch | p Welch < 0.005 |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| manha / BR16 | 1 | 1826 | irrigado | 1.5904 | 0.007377 | 0.2391 | 8.387e-04 | 8.388e-04 | sim |
| manha / BR16 | 2 | 1816 | irrigado | 1.4135 | 0.008608 | 0.4753 | 3.243e-12 | 3.330e-12 | sim |
| manha / BR16 | 3 | 1827 | irrigado | 1.5142 | 0.007115 | 0.2104 | 3.399e-03 | 3.399e-03 | sim |
| manha / BR16 | 4 | 1815 | irrigado | 1.3853 | 0.007932 | 0.4841 | 1.128e-12 | 1.168e-12 | sim |
| manha / BR16 | 5 | 1817 | irrigado | 1.3247 | 0.007978 | 0.4391 | 1.869e-10 | 1.928e-10 | sim |

| manha / CD202 | 1 | 2149 | irrigado | 1.4903 | 0.011419 | 0.7946 | 6.522e-44 | 7.316e-43 | sim |
| manha / CD202 | 2 | 2150 | irrigado | 1.4622 | 0.011441 | 0.7908 | 3.211e-43 | 4.365e-42 | sim |
| manha / CD202 | 3 | 2170 | irrigado | 1.5130 | 0.010634 | 0.7812 | 1.453e-41 | 1.890e-41 | sim |
| manha / CD202 | 4 | 2148 | irrigado | 1.4982 | 0.010727 | 0.7967 | 2.685e-44 | 2.672e-43 | sim |
| manha / CD202 | 5 | 2151 | irrigado | 1.4386 | 0.011418 | 0.7911 | 2.828e-43 | 4.189e-42 | sim |

| manha / EMB48 | 1 | 383 | nao_irrigado | 1.7115 | -0.018994 | -0.6475 | 3.324e-24 | 1.527e-23 | sim |
| manha / EMB48 | 2 | 382 | nao_irrigado | 1.5184 | -0.012718 | -0.6113 | 4.652e-21 | 1.701e-20 | sim |
| manha / EMB48 | 3 | 384 | nao_irrigado | 1.6102 | -0.010442 | -0.6634 | 1.023e-25 | 4.593e-25 | sim |
| manha / EMB48 | 4 | 408 | nao_irrigado | 1.3944 | -0.013532 | -0.5779 | 1.695e-18 | 2.371e-18 | sim |
| manha / EMB48 | 5 | 385 | nao_irrigado | 1.5050 | -0.010520 | -0.6978 | 2.402e-29 | 4.414e-29 | sim |

| tarde / BR16 | 1 | 1668 | irrigado | 1.6873 | 0.014185 | 0.5586 | 3.789e-17 | 4.240e-17 | sim |
| tarde / BR16 | 2 | 2271 | nao_irrigado | 1.6525 | -0.013797 | -0.7157 | 1.918e-31 | 1.008e-29 | sim |
| tarde / BR16 | 3 | 1669 | irrigado | 1.5620 | 0.014905 | 0.5126 | 2.947e-14 | 3.090e-14 | sim |
| tarde / BR16 | 4 | 2282 | nao_irrigado | 1.8582 | -0.010597 | -0.6077 | 9.009e-21 | 9.069e-21 | sim |
| tarde / BR16 | 5 | 1667 | irrigado | 1.7531 | 0.012081 | 0.6004 | 3.416e-20 | 3.688e-20 | sim |

| tarde / CD202 | 1 | 2281 | nao_irrigado | 1.7372 | -0.010976 | -0.6589 | 2.816e-25 | 3.248e-25 | sim |
| tarde / CD202 | 2 | 1670 | irrigado | 1.3904 | 0.014234 | 0.2375 | 9.111e-04 | 9.161e-04 | sim |
| tarde / CD202 | 3 | 1669 | irrigado | 1.4304 | 0.013640 | 0.2983 | 2.647e-05 | 2.658e-05 | sim |
| tarde / CD202 | 4 | 2282 | nao_irrigado | 1.6399 | -0.010344 | -0.6332 | 6.527e-23 | 7.600e-23 | sim |
| tarde / CD202 | 5 | 2280 | nao_irrigado | 1.6925 | -0.009464 | -0.6482 | 2.888e-24 | 3.005e-24 | sim |

| tarde / EMB48 | 1 | 2229 | irrigado | 1.3600 | 0.012297 | 0.5813 | 9.638e-19 | 1.174e-18 | sim |
| tarde / EMB48 | 2 | 858 | nao_irrigado | 1.4482 | -0.010939 | -0.2359 | 9.858e-04 | 9.860e-04 | sim |
| tarde / EMB48 | 3 | 391 | nao_irrigado | 1.2681 | -0.013129 | -0.4073 | 4.543e-09 | 5.720e-09 | sim |
| tarde / EMB48 | 4 | 859 | nao_irrigado | 1.4185 | -0.010374 | -0.2351 | 1.027e-03 | 1.027e-03 | sim |
| tarde / EMB48 | 5 | 2230 | irrigado | 1.4317 | 0.009691 | 0.5732 | 3.697e-18 | 4.406e-18 | sim |

