# Bandas mais significativas: irrigado vs nao_irrigado

- Criterios usados:
  - significancia univariada por banda: Welch t-test com correcao FDR (Benjamini-Hochberg)
  - tamanho de efeito: Cohen's d
  - relevancia multivariada: VIP e coeficientes do PLSR
- Score combinado da tabela final: z(VIP) + z(|Cohen's d|) + z(-log10(q-value))
- Bandas com q-value < 0.05: 1986
- Bandas com q-value < 0.05 e VIP >= 1.0: 987

## Top 20 bandas candidatas

| rank | banda | direcao | VIP | Cohen's d | q-value | score combinado |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 1924 | nao_irrigado | 1.2794 | -1.9937 | 2.167e-258 | 8.0328 |
| 2 | 1923 | nao_irrigado | 1.3149 | -1.9496 | 1.266e-249 | 7.9692 |
| 3 | 2279 | nao_irrigado | 1.6993 | -1.5672 | 3.244e-180 | 7.9433 |
| 4 | 2280 | nao_irrigado | 1.6419 | -1.6171 | 9.064e-190 | 7.9176 |
| 5 | 1427 | nao_irrigado | 1.3630 | -1.8935 | 1.405e-237 | 7.8887 |
| 6 | 1428 | nao_irrigado | 1.3614 | -1.8934 | 1.399e-237 | 7.8800 |
| 7 | 1426 | nao_irrigado | 1.3640 | -1.8908 | 4.149e-237 | 7.8797 |
| 8 | 1429 | nao_irrigado | 1.3594 | -1.8940 | 1.036e-237 | 7.8733 |
| 9 | 1430 | nao_irrigado | 1.3574 | -1.8955 | 6.802e-238 | 7.8691 |
| 10 | 1425 | nao_irrigado | 1.3647 | -1.8869 | 2.201e-236 | 7.8624 |
| 11 | 1431 | nao_irrigado | 1.3551 | -1.8942 | 9.254e-238 | 7.8513 |
| 12 | 1424 | nao_irrigado | 1.3653 | -1.8814 | 2.238e-235 | 7.8357 |
| 13 | 1432 | nao_irrigado | 1.3526 | -1.8920 | 1.399e-237 | 7.8301 |
| 14 | 1433 | nao_irrigado | 1.3499 | -1.8889 | 3.745e-237 | 7.8016 |
| 15 | 1423 | nao_irrigado | 1.3657 | -1.8744 | 4.579e-234 | 7.7994 |
| 16 | 1422 | nao_irrigado | 1.3662 | -1.8702 | 3.005e-233 | 7.7778 |
| 17 | 1421 | nao_irrigado | 1.3662 | -1.8683 | 6.917e-233 | 7.7674 |
| 18 | 1434 | nao_irrigado | 1.3468 | -1.8851 | 1.337e-236 | 7.7671 |
| 19 | 1420 | nao_irrigado | 1.3660 | -1.8664 | 1.430e-232 | 7.7567 |
| 20 | 1419 | nao_irrigado | 1.3660 | -1.8628 | 5.349e-232 | 7.7388 |

## Regioes espectrais dominantes

| regiao | n bandas | banda pico | direcao dominante | VIP medio | |d| medio | menor q-value |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| 1910-1944 | 35 | 1924 | nao_irrigado | 1.1538 | 1.1740 | 2.167e-258 |
| 2258-2283 | 26 | 2279 | nao_irrigado | 1.4559 | 1.0442 | 9.030e-190 |
| 1380-1472 | 93 | 1427 | nao_irrigado | 1.2195 | 1.3006 | 6.802e-238 |
| 422-501 | 80 | 486 | nao_irrigado | 1.1667 | 1.5219 | 6.657e-228 |
| 1476-1673 | 198 | 1660 | irrigado | 1.1174 | 1.1376 | 3.167e-181 |
| 2057-2215 | 159 | 2125 | irrigado | 1.1119 | 1.1192 | 1.752e-201 |
| 2303-2314 | 12 | 2307 | nao_irrigado | 1.2500 | 1.0876 | 2.546e-142 |
| 380-411 | 32 | 391 | nao_irrigado | 1.1071 | 1.1606 | 7.598e-129 |
| 1783-1814 | 32 | 1803 | irrigado | 1.2580 | 0.7439 | 8.987e-88 |
| 814-882 | 69 | 848 | nao_irrigado | 1.0786 | 0.9537 | 3.806e-113 |
| 1836-1888 | 53 | 1875 | nao_irrigado | 1.0319 | 0.7193 | 9.416e-107 |
| 415-419 | 5 | 417 | nao_irrigado | 1.0415 | 1.0796 | 1.632e-97 |
| 708-713 | 6 | 709 | nao_irrigado | 1.0476 | 0.8468 | 7.187e-94 |
| 1724-1739 | 16 | 1732 | nao_irrigado | 1.0626 | 0.8843 | 5.660e-81 |
| 377-378 | 2 | 377 | nao_irrigado | 1.0030 | 1.0895 | 1.135e-97 |

## Leitura da analise

- No dataset processado, a separacao irrigado vs nao_irrigado aparece tanto em bandas isoladas quanto em blocos contiguos de comprimentos de onda.
- As regioes mais fortes combinando significancia univariada e relevancia no PLSR se concentram principalmente em 2270-2280 nm, 1660-1666 nm e 1420-1439 nm.
- Direcao positiva do sinal processado indica maior associacao com irrigado; direcao negativa indica maior associacao com nao_irrigado.
- Como os dados estao em SNV + Savitzky-Golay + 1a derivada, a interpretacao e sobre o sinal processado, nao sobre reflectancia bruta.
