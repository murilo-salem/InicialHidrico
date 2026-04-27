# Resumo PCA: bandas e separacao por classe

## Loadings mais fortes

### PC1

| wavelength (nm) | loading |
| ---: | ---: |
| 698 | 0.2080575729 |
| 699 | 0.2078807001 |
| 697 | 0.2042738255 |
| 700 | 0.2038386111 |
| 696 | 0.1966620548 |
| 701 | 0.1962300276 |
| 695 | 0.1856010061 |
| 702 | 0.1854736682 |
| 703 | 0.1721220219 |
| 694 | 0.1716667793 |

### PC2

| wavelength (nm) | loading |
| ---: | ---: |
| 355 | 0.3321574283 |
| 354 | 0.3320337608 |
| 356 | 0.2903321764 |
| 353 | 0.2788175524 |
| 357 | 0.2192411902 |
| 352 | 0.2106141920 |
| 358 | 0.1740303596 |
| 351 | 0.1229369958 |
| 359 | 0.1185699421 |
| 371 | 0.0984558581 |

## Separacao por classe

- irrigado: n = 868, PC1 medio = -0.017204, PC2 medio = -0.007452
  - PC1: min = -0.087105, max = 0.066688
  - PC2: min = -0.095291, max = 0.063353
- nao_irrigado: n = 864, PC1 medio = 0.017284, PC2 medio = 0.007487
  - PC1: min = -0.072888, max = 0.162620
  - PC2: min = -0.061453, max = 0.082051

### Arquivo de figura

- `pca_scores_classes.svg` mostra as duas classes em PC1 x PC2 com elipses de dispersao e centroides.
