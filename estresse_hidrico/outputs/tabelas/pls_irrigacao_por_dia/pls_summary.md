# PLS Classification - IRR vs NIRR por Dia

## Features: 1200nm, 1451nm, 1951nm, 970nm, 670nm (Clorofila), NDRE

## Band Importance Ranking (Mean VIP across days):

| Rank | Feature | VIP Mean | VIP Std |
| --- | --- | ---: | ---: |
| 1 | 1200nm | 6.2886 | 0.7923 |
| 2 | 970nm | 6.2884 | 0.7357 |
| 3 | 1451nm | 6.0186 | 1.0085 |
| 4 | 670nm (Clorofila) | 5.6206 | 1.2796 |
| 5 | 1951nm | 5.4882 | 1.2748 |
| 6 | NDRE | 3.5977 | 0.5419 |

## Metrics by Day:

| Dia | Accuracy | Balanced Acc | F1 Macro | ROC AUC | Kappa |
| --- | ---: | ---: | ---: | ---: | ---: |
| dia2 | 0.6250 | 0.6250 | 0.6243 | 0.7153 | 0.2500 |
| dia3 | 0.9583 | 0.9583 | 0.9583 | 0.9931 | 0.9167 |
| dia4 | 0.9583 | 0.9583 | 0.9583 | 1.0000 | 0.9167 |
| dia5 | 0.9583 | 0.9583 | 0.9583 | 1.0000 | 0.9167 |
| dia6 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| dia9 | 0.8750 | 0.8750 | 0.8748 | 0.9236 | 0.7500 |
