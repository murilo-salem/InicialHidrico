# Relatorio Completo Dos 3 Ultimos Experimentos

## Objetivo Deste Documento

Este arquivo consolida, em um unico relatorio, tudo o que foi feito nos 3 ultimos experimentos executados no projeto `AgroSATHidrico` dentro do subprojeto `estresse_hidrico`.

Os 3 experimentos consolidados aqui foram:

1. Implementacao e execucao completa do pipeline de analise de estresse hidrico em soja.
2. Consolidacao e interpretacao detalhada da Questao 2, com foco em Boruta por dia e graficos temporais.
3. Refinamento do Painel B da Figura 5, baseado no desvio padrao do quociente `NIRR/IRR` por comprimento de onda.

O objetivo deste relatorio e registrar:

- o que foi implementado;
- quais arquivos foram criados ou atualizados;
- quais resultados foram obtidos;
- quais limitacoes reais do dataset foram encontradas;
- quais figuras e tabelas finais ficaram disponiveis para uso tecnico e redacao.

---

## 1. Contexto Geral Do Experimento

### 1.1 Tema cientifico

O conjunto de analises foi estruturado para investigar a deteccao de estresse hidrico em soja por espectroscopia de reflectancia, com foco em:

- diferenciar plantas irrigadas (`IRR`) e nao irrigadas (`NIRR`);
- avaliar a resposta espectral ao longo do tempo;
- identificar comprimentos de onda discriminativos;
- verificar a separacao estatistica entre grupos;
- construir modelos supervisionados para classificar `cultivar x condicao`.

### 1.2 Cultivares e grupos avaliados

As cultivares presentes na base sao:

- `EMB48`
- `BR16`
- `CD202`

As condicoes analisadas sao:

- `IRR`
- `NIRR`

As 6 classes finais da classificacao supervisionada foram:

| Classe | Grupo |
|---|---|
| A | EMB48 IRR |
| B | EMB48 NIRR |
| C | BR16 IRR |
| D | BR16 NIRR |
| E | CD202 IRR |
| F | CD202 NIRR |

### 1.3 Workbook realmente encontrado

Durante a inspecao do arquivo bruto, ficou claro que o workbook atual nao corresponde exatamente ao plano teorico inicial.

As datas absolutas realmente presentes sao:

| Data | Rotulo usado no pipeline | Turnos presentes | Amostras brutas |
|---|---|---|---:|
| 2017-02-23 | dia2 | manha, tarde | 384 |
| 2017-02-24 | dia3 | manha, tarde | 384 |
| 2017-02-25 | dia4 | manha | 192 |
| 2017-02-26 | dia5 | manha | 192 |
| 2017-02-27 | dia6 | manha | 192 |
| 2017-03-02 | dia9 | manha, tarde | 388 |

Conclusoes praticas:

- o workbook atual possui `6` datas absolutas;
- o workbook atual possui `6` dias rotulados no pipeline;
- nao existe uma coleta separada de `recuperacao` como dia absoluto independente;
- por isso, a etapa de recuperacao precisou ser tratada como ausente nos outputs finais.

### 1.4 Estrutura real das replicatas

O plano teorico mencionava `n = 4` por grupo. A inspecao mostrou que isso continua valido biologicamente, mas a planilha contem leituras tecnicas repetidas.

Estrutura observada:

- `4` blocos biologicos: `B1`, `B2`, `B3`, `B4`
- `8` leituras tecnicas por bloco, na maioria dos grupos
- `32` espectros tecnicos por combinacao `data x turno x cultivar x condicao`

Portanto, para as analises inferenciais e temporais, as leituras tecnicas foram agregadas por bloco, recuperando corretamente:

- `n = 4` replicatas biologicas por grupo

Excecao observada:

- `2017-03-02 / manha / CD202 / IRR / B1` apresentou `12` leituras tecnicas em vez de `8`
- o pipeline absorveu essa excecao agregando tecnicas por bloco, sem descartar o grupo

---

## 2. Experimento 1: Implementacao E Execucao Completa Do Pipeline

## 2.1 Objetivo

O primeiro experimento teve como objetivo montar e executar um pipeline completo, reproduzivel e modular para responder as tres questoes do plano:

- Q1: PERMANOVA e PERMDISP
- Q2: Boruta por dia e graficos temporais
- Q3: classificacao supervisionada e matriz de confusao

## 2.2 Estrutura criada

Foi criada a estrutura abaixo:

- `estresse_hidrico/`
- `estresse_hidrico/dados/raw/`
- `estresse_hidrico/dados/processados/`
- `estresse_hidrico/scripts/`
- `estresse_hidrico/outputs/tabelas/`
- `estresse_hidrico/outputs/figuras/`

Arquivos principais criados:

- `estresse_hidrico/README.md`
- `estresse_hidrico/requirements.txt`
- `estresse_hidrico/requirements_lock.txt`
- `estresse_hidrico/scripts/pipeline_utils.py`
- `estresse_hidrico/scripts/00_preprocessamento.py`
- `estresse_hidrico/scripts/01_permanova.py`
- `estresse_hidrico/scripts/02_boruta_por_dia.py`
- `estresse_hidrico/scripts/03_graficos_temporais.py`
- `estresse_hidrico/scripts/04_classificacao.py`
- `estresse_hidrico/scripts/05_figuras_finais.py`

## 2.3 Ambiente computacional

Foi criado e usado o ambiente:

- `.venv311_estresse`

Versao de Python usada:

- `Python 3.11`

Dependencias instaladas:

- `numpy`
- `pandas`
- `scipy`
- `scikit-learn`
- `scikit-bio`
- `Boruta`
- `xgboost`
- `matplotlib`
- `seaborn`
- `statsmodels`
- `joblib`
- `openpyxl`

O congelamento das versoes foi salvo em:

- `estresse_hidrico/requirements_lock.txt`

## 2.4 Pre-processamento implementado

### 2.4.1 Normalizacao dos metadados

Como os metadados originais da planilha tinham inconsistencias, a identificacao final dos grupos foi reconstruida a partir da coluna `nomenclaura`.

Foi padronizado:

- `cultivar`
- `condicao`
- `bloco`
- `replicata`
- `tecnica`
- `dia`
- `turno`

### 2.4.2 Integridade dos dados

Resumo final:

| Metrica | Valor |
|---|---:|
| amostras_brutas | 1732 |
| bandas_brutas | 2151 |
| datas_absolutas | 6 |
| dias_rotulados | 6 |
| turnos_originais | 2 |
| valores_ausentes | 0 |
| valores_fora_intervalo_0_1 | 0 |
| duplicatas_chave_data_turno_arquivo | 0 |
| duplicatas_chave_biologica_tecnica | 0 |
| dias_sem_recuperacao_no_workbook | 1 |

Interpretacao:

- nao havia valores ausentes;
- nao havia reflectancias fora de `[0,1]`;
- nao havia duplicatas problematicas nas chaves de analise;
- a principal divergencia em relacao ao plano original foi a ausencia de um dia separado de recuperacao.

### 2.4.3 Filtragem e suavizacao espectral

Foi aplicada:

- remocao das bandas atmosfericas `1350-1450 nm` e `1800-1950 nm`;
- suavizacao `Savitzky-Golay` com `janela = 11` e `grau = 2`

Resultado:

- bandas brutas: `2151`
- bandas retidas apos remocao das faixas atmosfericas: `1899`

### 2.4.4 Agregacao das replicatas

Arquivos gerados:

- `espectros_suavizados.csv`
- `indices_vegetacao.csv`
- `replicatas_bloco_turno.csv`
- `replicatas_bloco_dia.csv`
- `medias_grupais_turno.csv`
- `medias_grupais_dia.csv`

Numeros finais:

| Nivel | Total |
|---|---:|
| amostras_tecnicas | 1732 |
| replicatas_bloco_turno | 216 |
| replicatas_bloco_dia | 144 |

## 2.5 Calculo dos indices de vegetacao

Foram implementados e calculados:

- `NDVI`
- `EVI`
- `WBI`
- `PRI`
- `SIPI`
- `REP`

O mapeamento das bandas usadas em cada indice foi salvo em:

- `outputs/tabelas/mapeamento_indices.csv`

## 2.6 Q1: PERMANOVA E PERMDISP

### 2.6.1 Estrategia

Foram usados os dias com dois turnos:

- `dia2`
- `dia3`
- `dia9`

Foram executados `8` testes no total:

- `6` testes `cultivar x condicao`, comparando `manha vs tarde`
- `2` testes agregados, comparando `IRR vs NIRR` em `manha` e `tarde`

Foram testadas duas metricas:

- `braycurtis`
- `euclidean`

Para cada comparacao, o pipeline escolheu a metrica mais discriminativa com base em:

- menor `p-value`
- maior `R²`
- estabilidade da dispersao

### 2.6.2 Resultados selecionados

| Cultivar | Condicao | Comparacao | Metrica | F | p | q | R² | Significativo |
|---|---|---|---|---:|---:|---:|---:|---|
| EMB48 | IRR | Manha vs Tarde | euclidean | 8.6323 | 0.0050 | 0.0120 | 0.2818 | Sim |
| EMB48 | NIRR | Manha vs Tarde | euclidean | 0.3009 | 0.7070 | 0.7070 | 0.0135 | Nao |
| BR16 | IRR | Manha vs Tarde | euclidean | 4.5097 | 0.0290 | 0.0464 | 0.1701 | Sim |
| BR16 | NIRR | Manha vs Tarde | braycurtis | 0.5699 | 0.5110 | 0.5840 | 0.0253 | Nao |
| CD202 | IRR | Manha vs Tarde | euclidean | 6.9236 | 0.0060 | 0.0120 | 0.2394 | Sim |
| CD202 | NIRR | Manha vs Tarde | euclidean | 1.2898 | 0.2450 | 0.3267 | 0.0554 | Nao |
| Todos | IRR vs NIRR | Manha | braycurtis | 65.7410 | 0.0010 | 0.0040 | 0.4843 | Sim |
| Todos | IRR vs NIRR | Tarde | braycurtis | 14.0299 | 0.0010 | 0.0040 | 0.1670 | Sim |

### 2.6.3 Leitura dos resultados

Principais conclusoes:

- o efeito de turno foi significativo apenas nos grupos irrigados;
- nos grupos nao irrigados, a diferenca entre manha e tarde nao foi estatisticamente robusta apos correcao FDR;
- a condicao hidrica `IRR vs NIRR` foi fortemente discriminada pela assinatura espectral, especialmente de manha;
- o maior `R²` ocorreu em `IRR vs NIRR / manha`, indicando separacao multivariada mais forte nesse recorte.

### 2.6.4 PERMDISP

Todos os testes passaram no controle de homogeneidade de dispersao:

- `homogeneidade_ok = Sim` em todos os 8 contrastes

Interpretacao:

- as diferencas da PERMANOVA podem ser interpretadas como deslocamentos de localizacao no espaco multivariado, e nao apenas como mudancas na dispersao interna dos grupos.

## 2.7 Q2: Boruta, bandas recorrentes e series temporais

Essa parte foi implementada no pipeline, mas recebeu um segundo experimento inteiro dedicado ao detalhamento. A sintese tecnica do Experimento 1 foi:

- Boruta executado separadamente por dia;
- heatmap de bandas confirmadas;
- graficos temporais de bandas selecionadas;
- graficos temporais dos 6 IVs;
- graficos de desvio do quociente por dia.

## 2.8 Q3: Classificacao supervisionada

### 2.8.1 Setup

Features usadas:

- uniao de bandas confirmadas pelo Boruta
- `NDVI`, `EVI`, `WBI`, `PRI`, `SIPI`, `REP`

Total de features:

- `154`

Estrategia de validacao:

- `StratifiedGroupKFold`
- `4` folds
- agrupamento por bloco biologico

Importancia dessa escolha:

- evita vazamento entre amostras da mesma replicata biologica
- e mais rigorosa do que dividir tecnicas ou dias da mesma planta entre treino e teste

### 2.8.2 Desempenho dos modelos

| Modelo | Accuracy media | Accuracy std | F1-macro medio | F1 std | Kappa medio |
|---|---:|---:|---:|---:|---:|
| LDA | 0.6250 | 0.1643 | 0.6124 | 0.1676 | 0.5500 |
| XGBoost | 0.5903 | 0.1545 | 0.5696 | 0.1497 | 0.5083 |
| Random Forest | 0.5069 | 0.0731 | 0.4868 | 0.0824 | 0.4083 |
| SVM (RBF) | 0.4931 | 0.0417 | 0.4701 | 0.0645 | 0.3917 |
| k-NN (k=5) | 0.4583 | 0.0949 | 0.4347 | 0.1063 | 0.3500 |

Melhor modelo:

- `LDA`

### 2.8.3 Escores por classe

| Classe | Precisao | Recall | F1-score | Suporte |
|---|---:|---:|---:|---:|
| A (EMB48 IRR) | 0.6538 | 0.7083 | 0.6800 | 24 |
| B (EMB48 NIRR) | 0.6667 | 0.6667 | 0.6667 | 24 |
| C (BR16 IRR) | 0.7391 | 0.7083 | 0.7234 | 24 |
| D (BR16 NIRR) | 0.6154 | 0.6667 | 0.6400 | 24 |
| E (CD202 IRR) | 0.6667 | 0.4167 | 0.5128 | 24 |
| F (CD202 NIRR) | 0.4667 | 0.5833 | 0.5185 | 24 |

Leitura:

- `BR16 IRR` foi a classe mais bem recuperada;
- `EMB48 IRR`, `EMB48 NIRR` e `BR16 NIRR` tiveram desempenho intermediario bom;
- `CD202 IRR` e `CD202 NIRR` foram as classes mais dificeis de separar.

### 2.8.4 Matriz de confusao

Principais padroes observados:

- `A (EMB48 IRR)` confundiu principalmente com `E (CD202 IRR)` e `F (CD202 NIRR)`
- `B (EMB48 NIRR)` confundiu principalmente com `F (CD202 NIRR)`
- `D (BR16 NIRR)` tambem confundiu principalmente com `F (CD202 NIRR)`
- `E (CD202 IRR)` teve confusoes distribuidas com varios grupos

Matriz consolidada:

| Classe verdadeira | A | B | C | D | E | F |
|---|---:|---:|---:|---:|---:|---:|
| A (EMB48 IRR) | 17 | 0 | 2 | 0 | 3 | 2 |
| B (EMB48 NIRR) | 0 | 16 | 0 | 1 | 1 | 6 |
| C (BR16 IRR) | 3 | 0 | 17 | 3 | 1 | 0 |
| D (BR16 NIRR) | 0 | 0 | 1 | 16 | 0 | 7 |
| E (CD202 IRR) | 6 | 2 | 3 | 2 | 10 | 1 |
| F (CD202 NIRR) | 0 | 6 | 0 | 4 | 0 | 14 |

### 2.8.5 Importancia das variaveis

As variaveis mais importantes no `Random Forest` foram:

1. `REP`
2. `WBI`
3. `717 nm`
4. `EVI`
5. `718 nm`
6. `719 nm`
7. `720 nm`
8. `2444 nm`
9. `NDVI`
10. `721 nm`

Leitura biologica:

- os IVs continuaram muito relevantes;
- a borda vermelha `717-730 nm` apareceu com forte peso;
- uma banda de SWIR alta (`2444 nm`) tambem entrou entre as mais relevantes;
- o modelo supervisionado valorizou bandas que nao necessariamente eram as mais recorrentes no Boruta por dia, o que e consistente com o objetivo multiclasse.

## 2.9 Arquivos finais do Experimento 1

Principais tabelas:

- `outputs/tabelas/integridade_dados.csv`
- `outputs/tabelas/cronograma_dias.csv`
- `outputs/tabelas/resultados_permanova.csv`
- `outputs/tabelas/resultados_permdisp.csv`
- `outputs/tabelas/lambdas_boruta_por_dia.csv`
- `outputs/tabelas/escores_modelos.csv`
- `outputs/tabelas/escores_por_classe.csv`
- `outputs/tabelas/rf_feature_importance.csv`
- `outputs/tabelas/sintese_final.xlsx`

Principais figuras:

- `outputs/figuras/permanova_pvalores.png`
- `outputs/figuras/heatmap_lambdas_confirmados.png`
- `outputs/figuras/confusion_matrix.png`
- `outputs/figuras/rf_feature_importance_top20.png`
- `outputs/figuras/painel_resumo_estresse_hidrico.png`

Relatorio resumido gerado pelo pipeline:

- `outputs/relatorio_resultados.md`

---

## 3. Experimento 2: Consolidacao Detalhada Da Questao 2

## 3.1 Objetivo

O segundo experimento teve como foco isolar e descrever melhor os resultados da Questao 2, que envolve:

- selecao de comprimentos de onda por dia com Boruta;
- escolha de bandas para series temporais;
- construcao dos graficos temporais das bandas e dos indices;
- interpretacao da dinamica temporal do estresse hidrico.

## 3.2 Boruta por dia

Resumo das contagens:

| Dia | Confirmadas | Tentativas | Rejeitadas |
|---|---:|---:|---:|
| dia2 | 1 | 5 | 1893 |
| dia3 | 52 | 57 | 1790 |
| dia4 | 93 | 17 | 1789 |
| dia5 | 0 | 177 | 1722 |
| dia6 | 2 | 124 | 1773 |
| dia9 | 110 | 45 | 1744 |

Interpretacao dia a dia:

### dia2

- somente `1` banda foi confirmada;
- a banda confirmada foi `2444 nm`;
- o estresse no inicio ainda nao produziu uma assinatura espectral ampla e robusta em muitas bandas;
- houve apenas algumas bandas tentativas dispersas.

### dia3

- `52` bandas confirmadas;
- faixa confirmada concentrada em `350-422 nm`;
- forte indicio de resposta inicial em regioes do visivel curto e ultravioleta proximo.

### dia4

- `93` bandas confirmadas;
- faixa confirmada expandiu de `350` ate `730 nm`;
- esse foi o primeiro dia em que a borda vermelha apareceu de forma mais clara na selecao;
- sinal de aprofundamento da resposta fisiologica.

### dia5

- nenhuma banda foi confirmada;
- houve `177` bandas tentativas;
- isso sugere um dia de transicao, com informacao espectral espalhada, mas sem estabilidade estatistica suficiente para confirmacao.

### dia6

- apenas `2` bandas confirmadas;
- confirmadas: `356` e `362 nm`;
- apesar de poucas confirmacoes, havia `124` bandas tentativas;
- esse dia mostrou diferenca relevante nos IVs, mesmo com baixa confirmacao formal no Boruta.

### dia9

- `110` bandas confirmadas;
- maior numero de bandas confirmadas de toda a serie;
- faixa confirmada de `352-498 nm`;
- indica consolidacao da separacao espectral entre `IRR` e `NIRR`.

### recuperacao

- nao foi possivel rodar uma rodada real do Boruta para recuperacao;
- o workbook atual nao contem essa coleta separada.

## 3.3 Bandas recorrentes entre dias

As bandas confirmadas mais recorrentes foram:

- `356 nm` em `4` dias
- `362 nm` em `4` dias

Bandas confirmadas em `3` dias:

- `352-355 nm`
- `357-359 nm`
- `361 nm`
- `363 nm`
- `366-399 nm`
- `422 nm`

Leitura:

- a maior estabilidade temporal ocorreu na faixa `UV/azul curto`;
- esse comportamento sugere que a resposta discriminativa entre `IRR` e `NIRR` emergiu primeiro e com mais constancia nessa regiao do espectro.

## 3.4 Heatmap de presenca por dia

Foi gerado o heatmap:

- `outputs/figuras/heatmap_lambdas_confirmados.png`

Esse heatmap cumpre o papel visual de mostrar:

- quais bandas aparecem em cada dia;
- quais bandas persistem por mais de um dia;
- como a resposta espectral se desloca e se expande ao longo do experimento.

## 3.5 Selecao das bandas para series temporais

Foi adotada a regra:

- plotar bandas confirmadas em pelo menos `2` dias

Resultado:

- `70` bandas foram selecionadas para os graficos temporais;
- a faixa selecionada foi de `350` a `439 nm`.

Essa escolha foi salva em:

- `outputs/tabelas/bandas_temporais_selecionadas.csv`

## 3.6 Graficos temporais das bandas

Foram gerados graficos `temporal_*.png` para todas as bandas temporais selecionadas.

Exemplos:

- `temporal_356nm.png`
- `temporal_362nm.png`
- `temporal_422nm.png`

Esses graficos mostram:

- eixo X = dias do experimento
- eixo Y = reflectancia media suavizada
- duas linhas principais: `IRR` e `NIRR`
- barras de erro baseadas nas `4` replicatas biologicas

## 3.7 Graficos temporais dos indices de vegetacao

Foram gerados:

- `temporal_NDVI.png`
- `temporal_EVI.png`
- `temporal_WBI.png`
- `temporal_PRI.png`
- `temporal_SIPI.png`
- `temporal_REP.png`

Resumo da maior diferenca absoluta `NIRR - IRR` por indice:

| Indice | Dia da maior diferenca | Delta NIRR - IRR |
|---|---|---:|
| NDVI | dia6 | 0.102539 |
| EVI | dia6 | 0.050436 |
| WBI | dia6 | -0.003366 |
| PRI | dia6 | 0.012966 |
| SIPI | dia6 | 0.038239 |
| REP | dia5 | -0.982129 |

Leitura:

- `NDVI`, `EVI`, `PRI` e `SIPI` diferenciaram mais fortemente os grupos em `dia6`;
- `WBI` tambem teve sua maior divergencia em `dia6`, embora com amplitude numerica pequena;
- `REP` teve a maior separacao em `dia5`, indicando resposta importante da borda vermelha naquele momento.

## 3.8 Conclusao do Experimento 2

O segundo experimento deixou claro que:

- o comportamento do Boruta foi altamente dependente do dia;
- `dia3`, `dia4` e principalmente `dia9` concentraram a maior parte das bandas confirmadas;
- a regiao `350-439 nm` foi a mais estavel ao longo do tempo;
- os IVs mostraram maior separacao entre grupos em `dia6`, enquanto o `REP` destacou `dia5`.

---

## 4. Experimento 3: Refinamento Do Painel B Da Figura 5

## 4.1 Objetivo

O terceiro experimento foi dedicado especificamente ao grafico do item `2)` da Questao 2:

- o Painel B da Figura 5
- baseado no desvio padrao do quociente `NIRR/IRR`

O objetivo era aproximar esse grafico do modelo descrito no PDF, tornando-o tecnicamente mais fiel e mais interpretavel.

## 4.2 Problema identificado na versao anterior

A primeira versao do grafico de desvio do quociente havia sido gerada a partir do dataset ja filtrado para remocao das bandas atmosfericas.

Consequencias:

- surgiam picos artificiais nas bordas de exclusao;
- as anotacoes podiam ficar dominadas por efeitos de transicao na vizinhanca das janelas removidas;
- isso reduzia a interpretabilidade do Painel B.

## 4.3 Ajustes implementados

Foram feitos os seguintes ajustes tecnicos:

1. O grafico passou a ser calculado a partir do workbook bruto suavizado, e nao do CSV ja filtrado.
2. O espectro completo passou a ser desenhado no grafico.
3. As janelas atmosfericas passaram a ser sombreadas visualmente.
4. A deteccao automatica de picos passou a ignorar:
   - borda inicial extrema;
   - borda final extrema;
   - janelas atmosfericas;
   - largas zonas de transicao apos as bandas atmosfericas.
5. As bandas confirmadas pelo Boruta passaram a ser desenhadas como marcas de referencia na base do grafico.
6. Foi gerado um arquivo especifico de picos por dia.
7. Foi criado um placeholder explicito para `recuperacao`, ja que o dia nao existe separadamente no workbook atual.

## 4.4 Arquivos atualizados

Scripts ajustados:

- `estresse_hidrico/scripts/pipeline_utils.py`
- `estresse_hidrico/scripts/03_graficos_temporais.py`

## 4.5 Graficos gerados no Painel B

Foram gerados:

- `desvio_quociente_dia2.png`
- `desvio_quociente_dia3.png`
- `desvio_quociente_dia4.png`
- `desvio_quociente_dia5.png`
- `desvio_quociente_dia6.png`
- `desvio_quociente_dia9.png`
- `desvio_quociente_recuperacao.png`

Observacao:

- o arquivo de recuperacao e um placeholder, nao um painel com dados reais

## 4.6 Picos finais identificados por dia

Tabela final:

| Dia | Pico 1 | Pico 2 |
|---|---|---|
| dia2 | 700 nm | 569 nm |
| dia3 | 595 nm | 696 nm |
| dia4 | 569 nm | 700 nm |
| dia5 | 580 nm | 697 nm |
| dia6 | 703 nm | 557 nm |
| dia9 | 703 nm | - |

Valores exatos:

| Dia | Rank | Pico nm | ratio_std |
|---|---:|---:|---:|
| dia2 | 1 | 700 | 0.107937 |
| dia2 | 2 | 569 | 0.102929 |
| dia3 | 1 | 595 | 0.153170 |
| dia3 | 2 | 696 | 0.135485 |
| dia4 | 1 | 569 | 0.100677 |
| dia4 | 2 | 700 | 0.093516 |
| dia5 | 1 | 580 | 0.131201 |
| dia5 | 2 | 697 | 0.123665 |
| dia6 | 1 | 703 | 0.111168 |
| dia6 | 2 | 557 | 0.107283 |
| dia9 | 1 | 703 | 0.106416 |

## 4.7 Comparacao com Boruta

No arquivo final de picos:

- apenas o pico `377 nm` de uma versao intermediaria havia coincidido diretamente com Boruta em `dia9`;
- apos o refinamento para evitar artefatos, os picos finais destacados ficaram em regioes mais interpretaveis, mas nao necessariamente com correspondencia direta de `± 3 nm` com as bandas confirmadas do Boruta.

Interpretacao:

- o Painel B e um indicador de variabilidade do quociente entre pares `NIRR/IRR`;
- o Boruta e um metodo supervisionado de selecao de features;
- portanto, embora se esperasse alguma convergencia, os dois metodos nao precisam apontar exatamente para as mesmas bandas pontuais.

## 4.8 Importancia metodologica do Experimento 3

Esse terceiro experimento melhorou o produto final porque:

- removeu a dominancia de artefatos de borda;
- deixou o grafico alinhado ao espirito do PDF de referencia;
- separou melhor picos biologicamente mais interpretaveis;
- tornou o Painel B mais apresentavel para uso tecnico e redacao.

---

## 5. Inventario Consolidado Dos Arquivos Produzidos

## 5.1 Scripts

- `scripts/pipeline_utils.py`
- `scripts/00_preprocessamento.py`
- `scripts/01_permanova.py`
- `scripts/02_boruta_por_dia.py`
- `scripts/03_graficos_temporais.py`
- `scripts/04_classificacao.py`
- `scripts/05_figuras_finais.py`

## 5.2 Tabelas principais

- `outputs/tabelas/integridade_dados.csv`
- `outputs/tabelas/cronograma_dias.csv`
- `outputs/tabelas/mapeamento_indices.csv`
- `outputs/tabelas/resultados_permanova.csv`
- `outputs/tabelas/resultados_permdisp.csv`
- `outputs/tabelas/resultados_permanova_metricas.csv`
- `outputs/tabelas/lambdas_boruta_por_dia.csv`
- `outputs/tabelas/resumo_boruta_por_dia.csv`
- `outputs/tabelas/lambdas_confirmados_recorrentes.csv`
- `outputs/tabelas/lambdas_tentativas_por_dia.csv`
- `outputs/tabelas/bandas_temporais_selecionadas.csv`
- `outputs/tabelas/series_temporais_resumo.csv`
- `outputs/tabelas/desvio_quociente_por_dia.csv`
- `outputs/tabelas/desvio_quociente_picos_por_dia.csv`
- `outputs/tabelas/escores_modelos.csv`
- `outputs/tabelas/escores_por_classe.csv`
- `outputs/tabelas/confusion_matrix.csv`
- `outputs/tabelas/rf_feature_importance.csv`
- `outputs/tabelas/features_classificacao.csv`
- `outputs/tabelas/predicoes_classificacao_cv.csv`
- `outputs/tabelas/preprocessamento_resumo.xlsx`
- `outputs/tabelas/resultados_permanova.xlsx`
- `outputs/tabelas/resultados_boruta.xlsx`
- `outputs/tabelas/resultados_temporais.xlsx`
- `outputs/tabelas/resultados_classificacao.xlsx`
- `outputs/tabelas/sintese_final.xlsx`

## 5.3 Figuras principais

- `outputs/figuras/permanova_pvalores.png`
- `outputs/figuras/heatmap_lambdas_confirmados.png`
- `outputs/figuras/confusion_matrix.png`
- `outputs/figuras/rf_feature_importance_top20.png`
- `outputs/figuras/painel_resumo_estresse_hidrico.png`
- `outputs/figuras/desvio_quociente_dia2.png`
- `outputs/figuras/desvio_quociente_dia3.png`
- `outputs/figuras/desvio_quociente_dia4.png`
- `outputs/figuras/desvio_quociente_dia5.png`
- `outputs/figuras/desvio_quociente_dia6.png`
- `outputs/figuras/desvio_quociente_dia9.png`
- `outputs/figuras/desvio_quociente_recuperacao.png`
- `outputs/figuras/temporal_NDVI.png`
- `outputs/figuras/temporal_EVI.png`
- `outputs/figuras/temporal_WBI.png`
- `outputs/figuras/temporal_PRI.png`
- `outputs/figuras/temporal_SIPI.png`
- `outputs/figuras/temporal_REP.png`
- dezenas de figuras `temporal_XXXnm.png` para bandas especificas

---

## 6. Conclusoes Consolidadas

Os 3 experimentos, vistos em conjunto, permitiram chegar a um conjunto coerente de resultados:

1. O pipeline completo foi implementado e executado com sucesso.
2. O dataset atual foi normalizado e reorganizado corretamente ao nivel biologico.
3. A diferenca `IRR vs NIRR` foi fortemente detectavel por PERMANOVA, especialmente no periodo da manha.
4. O efeito de turno apareceu apenas nos grupos irrigados, e nao se sustentou nos grupos nao irrigados apos FDR.
5. O Boruta mostrou que a discriminacao espectral varia fortemente ao longo do tempo, com maxima expressao em `dia9`.
6. As bandas mais recorrentes ficaram concentradas entre `350` e `439 nm`, especialmente em `356` e `362 nm`.
7. Os indices de vegetacao diferenciaram mais fortemente os grupos em `dia6`, com destaque para `NDVI`, `EVI`, `PRI`, `SIPI` e `WBI`; o `REP` teve maior contraste em `dia5`.
8. Na classificacao supervisionada, o melhor modelo foi `LDA`, com `accuracy media = 0.6250`, `F1-macro = 0.6124` e `kappa = 0.5500`.
9. A borda vermelha `717-730 nm`, o `REP`, o `WBI` e `2444 nm` apareceram como features importantes na classificacao multiclasse.
10. O Painel B foi refinado para ficar metodologicamente mais consistente e mais utilizavel.

---

## 7. Limitacoes Registradas

As limitacoes mais importantes foram:

- ausencia de uma coleta de recuperacao separada no workbook atual;
- existencia de um grupo tecnicamente desbalanceado em `2017-03-02 / manha / CD202 / IRR / B1`;
- diferenca entre o plano teorico e a estrutura real do arquivo;
- nem sempre houve correspondencia pontual direta entre os picos do quociente `NIRR/IRR` e as bandas confirmadas pelo Boruta.

Essas limitacoes nao invalidam o pipeline, mas precisam ser explicitadas em qualquer relatorio, artigo ou apendice metodologico.

---

## 8. Estado Final

Ao final dos 3 experimentos, o projeto ficou com:

- pipeline operacional e reproduzivel;
- tabelas exportadas em `CSV` e `XLSX`;
- figuras em `PNG` a `300 dpi`;
- relatorio sintetico;
- relatorio consolidado;
- base pronta para redacao tecnica ou expansao futura.

Se uma coleta de recuperacao real for adicionada posteriormente ao workbook, o pipeline pode ser reexecutado para completar a serie temporal sem necessidade de refatoracao estrutural.
