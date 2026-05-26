# Analise TestesSignfDiniz - Bandas significativas

## Escopo e leitura metodologica

- Fonte principal: `TestesSignfDiniz/TOP5_POR_DIA_TURNO/*.csv`.
- As analises sao globais por recorte `dia x turno`, com tres alvos: `cond`, `gen`, `gen_cond`.
- Importante: nao ha p-valor separado por classe individual (ex.: `IRR|BR16`) nesses CSVs; a significancia em `gen_cond` representa o efeito conjunto entre classes de condicao e genotipo.

## Cobertura dos testes

- `cond`: 50 linhas TOP5, 10 recortes dia-turno, 41 bandas unicas.
- `gen`: 47 linhas TOP5, 10 recortes dia-turno, 36 bandas unicas.
- `gen_cond`: 50 linhas TOP5, 10 recortes dia-turno, 40 bandas unicas.

## Top bandas mais significativas - cond (global)

| banda (nm) | freq TOP5 | melhor rank | q minimo | q mediano |
| ---: | ---: | ---: | ---: | ---: |
| 400 | 5 | 1 | 7.549e-32 | 1.202e-26 |
| 1539 | 1 | 2 | 1.419e-29 | 1.419e-29 |
| 530 | 2 | 3 | 1.032e-26 | 4.227e-14 |
| 411 | 1 | 1 | 1.403e-23 | 1.403e-23 |
| 1541 | 1 | 2 | 1.919e-21 | 1.919e-21 |
| 1536 | 1 | 2 | 4.210e-20 | 4.210e-20 |
| 1530 | 1 | 2 | 5.659e-20 | 5.659e-20 |
| 1610 | 1 | 4 | 9.891e-20 | 9.891e-20 |
| 1939 | 1 | 5 | 1.432e-18 | 1.432e-18 |
| 1600 | 1 | 3 | 1.362e-16 | 1.362e-16 |

## Top bandas mais significativas - gen (global)

| banda (nm) | freq TOP5 | melhor rank | q minimo | q mediano |
| ---: | ---: | ---: | ---: | ---: |
| 522 | 1 | 1 | 7.614e-27 | 7.614e-27 |
| 710 | 1 | 2 | 3.498e-25 | 3.498e-25 |
| 707 | 2 | 1 | 5.485e-25 | 2.897e-07 |
| 704 | 1 | 1 | 5.769e-24 | 5.769e-24 |
| 730 | 4 | 2 | 3.683e-22 | 2.193e-12 |
| 550 | 2 | 1 | 7.400e-22 | 4.294e-12 |
| 705 | 1 | 1 | 9.704e-21 | 9.704e-21 |
| 1381 | 1 | 3 | 6.343e-19 | 6.343e-19 |
| 721 | 2 | 1 | 2.994e-18 | 2.059e-11 |
| 1375 | 1 | 2 | 3.250e-18 | 3.250e-18 |

## Top bandas mais significativas - gen_cond (global)

| banda (nm) | freq TOP5 | melhor rank | q minimo | q mediano |
| ---: | ---: | ---: | ---: | ---: |
| 401 | 2 | 1 | 1.311e-28 | 2.385e-14 |
| 530 | 3 | 2 | 2.359e-28 | 3.591e-19 |
| 1526 | 1 | 3 | 4.444e-28 | 4.444e-28 |
| 400 | 4 | 1 | 1.729e-26 | 1.030e-21 |
| 521 | 1 | 1 | 2.798e-25 | 2.798e-25 |
| 550 | 2 | 2 | 1.609e-24 | 7.947e-13 |
| 720 | 2 | 3 | 4.791e-24 | 3.650e-14 |
| 710 | 1 | 2 | 4.937e-24 | 4.937e-24 |
| 417 | 1 | 1 | 3.735e-23 | 3.735e-23 |
| 706 | 1 | 2 | 3.735e-23 | 3.735e-23 |

## Top bandas - gen_cond no turno MANHA

| banda (nm) | freq TOP5 | melhor rank | q minimo | q mediano |
| ---: | ---: | ---: | ---: | ---: |
| 401 | 2 | 1 | 1.311e-28 | 2.385e-14 |
| 530 | 3 | 2 | 2.359e-28 | 3.591e-19 |
| 1526 | 1 | 3 | 4.444e-28 | 4.444e-28 |
| 400 | 4 | 1 | 1.729e-26 | 1.030e-21 |
| 521 | 1 | 1 | 2.798e-25 | 2.798e-25 |
| 550 | 1 | 2 | 1.609e-24 | 1.609e-24 |
| 720 | 1 | 3 | 4.791e-24 | 4.791e-24 |
| 710 | 1 | 2 | 4.937e-24 | 4.937e-24 |
| 417 | 1 | 1 | 3.735e-23 | 3.735e-23 |
| 706 | 1 | 2 | 3.735e-23 | 3.735e-23 |
| 1522 | 1 | 1 | 8.289e-23 | 8.289e-23 |
| 729 | 1 | 4 | 1.362e-22 | 1.362e-22 |

## Top bandas - gen_cond no turno TARDE

| banda (nm) | freq TOP5 | melhor rank | q minimo | q mediano |
| ---: | ---: | ---: | ---: | ---: |
| 528 | 1 | 1 | 1.000e-21 | 1.000e-21 |
| 707 | 1 | 1 | 1.378e-21 | 1.378e-21 |
| 1374 | 1 | 2 | 2.680e-19 | 2.680e-19 |
| 717 | 1 | 1 | 2.519e-18 | 2.519e-18 |
| 740 | 1 | 3 | 4.937e-16 | 4.937e-16 |
| 1510 | 1 | 2 | 1.108e-15 | 1.108e-15 |
| 1490 | 1 | 4 | 2.231e-15 | 2.231e-15 |
| 519 | 1 | 5 | 3.132e-14 | 3.132e-14 |
| 720 | 1 | 3 | 7.300e-14 | 7.300e-14 |
| 620 | 1 | 4 | 1.668e-13 | 1.668e-13 |
| 550 | 1 | 2 | 1.589e-12 | 1.589e-12 |
| 1383 | 1 | 3 | 2.003e-12 | 2.003e-12 |

## Banda #1 por recorte (gen_cond)

| data_turno | banda #1 (nm) | q_FDR_BH |
| --- | ---: | ---: |
| D02M_MANHA | 521 | 2.798e-25 |
| D02T_TARDE | 528 | 1.000e-21 |
| D03M_MANHA | 400 | 1.729e-26 |
| D03T_TARDE | 707 | 1.378e-21 |
| D04M_MANHA | 417 | 3.735e-23 |
| D05M_MANHA | 1522 | 8.289e-23 |
| D06M_MANHA | 401 | 1.311e-28 |
| D09M_MANHA | 400 | 4.643e-24 |
| D09T_TARDE | 717 | 2.519e-18 |
| D10M_MANHA | 400 | 1.099e-18 |

## Resposta direta: bandas mais significativas para `condicao x turno x genotipo`

Como os testes de `gen_cond` sao globais por recorte (sem decompor p-valor por classe individual), a melhor aproximacao e listar as bandas mais fortes de `gen_cond` por turno e no agregado:

**Agregado (todos os turnos):** 401, 530, 1526, 400, 521, 550, 720, 710
- **MANHA:** 401, 530, 1526, 400, 521, 550, 720, 710
- **TARDE:** 528, 707, 1374, 717, 740, 1510, 1490, 519

Faixas recorrentes observadas na interacao (`gen_cond`): predominio em torno de 400-550 nm, 620-740 nm e blocos no SWIR (aprox. 1350-1910 nm em alguns recortes).
