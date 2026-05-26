# Classificacao por dia/turno com TOP5

- Cenarios processados: `27`
- Cenarios pulados: `3`

| scenario | analysis | dia | turno | best_model | accuracy | f1_macro | kappa |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| TOP5_cond_D02M_MANHA | cond | dia2 | MANHA | SVM (RBF) | 0.8750 | 0.8634 | 0.7500 |
| TOP5_cond_D02T_TARDE | cond | dia2 | TARDE | XGBoost | 0.7500 | 0.7268 | 0.5000 |
| TOP5_cond_D03M_MANHA | cond | dia3 | MANHA | LDA | 1.0000 | 1.0000 | 1.0000 |
| TOP5_cond_D03T_TARDE | cond | dia3 | TARDE | SVM (RBF) | 1.0000 | 1.0000 | 1.0000 |
| TOP5_cond_D04M_MANHA | cond | dia4 | MANHA | XGBoost | 0.9583 | 0.9571 | 0.9167 |
| TOP5_cond_D05M_MANHA | cond | dia5 | MANHA | Random Forest | 1.0000 | 1.0000 | 1.0000 |
| TOP5_cond_D06M_MANHA | cond | dia6 | MANHA | Random Forest | 1.0000 | 1.0000 | 1.0000 |
| TOP5_cond_D09M_MANHA | cond | dia9 | MANHA | Random Forest | 0.9583 | 0.9571 | 0.9167 |
| TOP5_cond_D09T_TARDE | cond | dia9 | TARDE | Random Forest | 0.9583 | 0.9571 | 0.9167 |
| TOP5_gen_D02M_MANHA | gen | dia2 | MANHA | k-NN (k=5) | 0.6667 | 0.6444 | 0.5000 |
| TOP5_gen_D02T_TARDE | gen | dia2 | TARDE | k-NN (k=5) | 0.6667 | 0.6472 | 0.5000 |
| TOP5_gen_D03M_MANHA | gen | dia3 | MANHA | LDA | 0.7917 | 0.7833 | 0.6875 |
| TOP5_gen_D03T_TARDE | gen | dia3 | TARDE | SVM (RBF) | 0.7500 | 0.7444 | 0.6250 |
| TOP5_gen_D04M_MANHA | gen | dia4 | MANHA | SVM (RBF) | 0.5833 | 0.5667 | 0.3750 |
| TOP5_gen_D05M_MANHA | gen | dia5 | MANHA | LDA | 0.6667 | 0.6528 | 0.5000 |
| TOP5_gen_D06M_MANHA | gen | dia6 | MANHA | SVM (RBF) | 0.6250 | 0.5972 | 0.4375 |
| TOP5_gen_D09M_MANHA | gen | dia9 | MANHA | Random Forest | 0.6250 | 0.5917 | 0.4375 |
| TOP5_gen_D09T_TARDE | gen | dia9 | TARDE | SVM (RBF) | 0.5833 | 0.5639 | 0.3750 |
| TOP5_gen_cond_D02M_MANHA | gen_cond | dia2 | MANHA | SVM (RBF) | 0.5417 | 0.4583 | 0.4500 |
| TOP5_gen_cond_D02T_TARDE | gen_cond | dia2 | TARDE | SVM (RBF) | 0.5417 | 0.4722 | 0.4500 |
| TOP5_gen_cond_D03M_MANHA | gen_cond | dia3 | MANHA | LDA | 0.7917 | 0.7222 | 0.7500 |
| TOP5_gen_cond_D03T_TARDE | gen_cond | dia3 | TARDE | SVM (RBF) | 0.6667 | 0.6111 | 0.6000 |
| TOP5_gen_cond_D04M_MANHA | gen_cond | dia4 | MANHA | LDA | 0.6667 | 0.6111 | 0.6000 |
| TOP5_gen_cond_D05M_MANHA | gen_cond | dia5 | MANHA | k-NN (k=5) | 0.5417 | 0.4514 | 0.4500 |
| TOP5_gen_cond_D06M_MANHA | gen_cond | dia6 | MANHA | SVM (RBF) | 0.6250 | 0.5069 | 0.5500 |
| TOP5_gen_cond_D09M_MANHA | gen_cond | dia9 | MANHA | LDA | 0.5833 | 0.5278 | 0.5000 |
| TOP5_gen_cond_D09T_TARDE | gen_cond | dia9 | TARDE | LDA | 0.5000 | 0.4306 | 0.4000 |
