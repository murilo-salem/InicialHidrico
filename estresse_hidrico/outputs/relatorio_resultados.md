# Relatorio de resultados - estresse hidrico em soja

## Contexto do dataset

- 2017-02-23 -> dia2 | turnos: manha | tarde | amostras brutas: 384
- 2017-02-24 -> dia3 | turnos: manha | tarde | amostras brutas: 384
- 2017-02-25 -> dia4 | turnos: manha | amostras brutas: 192
- 2017-02-26 -> dia5 | turnos: manha | amostras brutas: 192
- 2017-02-27 -> dia6 | turnos: manha | amostras brutas: 192
- 2017-03-02 -> dia9 | turnos: manha | tarde | amostras brutas: 388

## Integridade

- amostras_brutas: 1732
- bandas_brutas: 2151
- datas_absolutas: 6
- dias_rotulados: 6
- turnos_originais: 2
- valores_ausentes: 0
- valores_fora_intervalo_0_1: 0
- duplicatas_chave_data_turno_arquivo: 0
- duplicatas_chave_biologica_tecnica: 0
- dias_sem_recuperacao_no_workbook: 1

## Q1 - PERMANOVA

- EMB48 | IRR | Manha vs Tarde | F=8.6323, p=0.0050, q=0.0120, R2=0.2818, metrica=euclidean
- BR16 | IRR | Manha vs Tarde | F=4.5097, p=0.0290, q=0.0464, R2=0.1701, metrica=euclidean
- CD202 | IRR | Manha vs Tarde | F=6.9236, p=0.0060, q=0.0120, R2=0.2394, metrica=euclidean
- Todos | IRR vs NIRR | Manha | F=65.7410, p=0.0010, q=0.0040, R2=0.4843, metrica=braycurtis
- Todos | IRR vs NIRR | Tarde | F=14.0299, p=0.0010, q=0.0040, R2=0.1670, metrica=braycurtis

## Q2 - Boruta

- Bandas confirmadas recorrentes (top 10): 356, 362, 352, 353, 354, 355, 357, 358, 359, 361

## Q3 - Classificacao

- Melhor modelo: LDA
- Accuracy media: 0.6250
- F1-macro medio: 0.6124
- Kappa medio: 0.5500

### Escores por classe

- A (EMB48 IRR): Precisao=0.6538, Recall=0.7083, F1=0.6800, Suporte=24
- B (EMB48 NIRR): Precisao=0.6667, Recall=0.6667, F1=0.6667, Suporte=24
- C (BR16 IRR): Precisao=0.7391, Recall=0.7083, F1=0.7234, Suporte=24
- D (BR16 NIRR): Precisao=0.6154, Recall=0.6667, F1=0.6400, Suporte=24
- E (CD202 IRR): Precisao=0.6667, Recall=0.4167, F1=0.5128, Suporte=24
- F (CD202 NIRR): Precisao=0.4667, Recall=0.5833, F1=0.5185, Suporte=24
