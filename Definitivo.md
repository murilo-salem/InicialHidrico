# RELATÓRIO DEFINITIVO - PROJETO AGROSATHIDRICO

**Versão:** 1.0
**Data de compilação:** 2026-05-22
**Status:** Documento consolidado de todos os experimentos realizados

---

## SUMÁRIO

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Dataset Base e Pré-processamento](#2-dataset-base-e-pré-processamento)
3. [Inventário Completo de Experimentos (E01-E23)](#3-inventário-completo-de-experimentos-e01-e23)
4. [Resultados Consolidados por Pipeline](#4-resultados-consolidados-por-pipeline)
5. [Tabela de Parâmetros e Hiperparâmetros](#5-tabela-de-parâmetros-e-hiperparâmetros)
6. [Catálogo de Arquivos e Artefatos](#6-catálogo-de-arquivos-e-artefatos)
7. [Conclusões Finais](#7-conclusões-finais)
8. [Limitações e Lacunas](#8-limitações-e-lacunas)

---

## 1. VISÃO GERAL DO PROJETO

### 1.1 Tema Cientifico

O projeto AgroSATHidrico investiga a detecção de estresse hídrico em soja por espectroscopia de reflectância hiperespectral. O objetivo principal é identificar comprimentos de onda discriminativos que permitam diferenciar plantas irrigadas (IRR) de não irrigadas (NIRR), avaliar a resposta espectral ao longo do tempo e construir modelos supervisionados para classificação de genótipos × condições.

### 1.2 Escopo do Documento

Este documento consolida **todos os experimentos realmente materializados** no workspace AgroSATHidrico até 2026-04-30, organizados em famílias de análise. A contagem total de artefatos nos principais diretórios de saída é de **438 arquivos**.

Escopo coberto:
- `outputs_v2` (55 arquivos)
- `dados_processados_soft` (155 arquivos)
- `estresse_hidrico/outputs` (167 arquivos)
- `outputs` (61 arquivos)

Regra de completude aplicada:
- Resultados interpretáveis e tabelas-chave entram no corpo do relatório
- Tabelas gigantes entram com descrição, dimensões, schema funcional e caminho exato
- Quando um artefato existe mas o script gerador não foi localizado, é marcado como "artefato órfão"
- Quando um valor veio de artefato executado, tem prioridade sobre defaults do código

---

## 2. DATASET BASE E PRÉ-PROCESSAMENTO

### 2.1 Workbook Bruto

O workbook base é `base_dados_unificada.xlsx`.

| Métrica | Valor |
|---|---|
| Amostras brutas | 1732 |
| Bandas espectrais | 2151 |
| Faixa espectral | 350-2500 nm |
| Datas absolutas | 2017-02-23, 2017-02-24, 2017-02-25, 2017-02-26, 2017-02-27, 2017-03-02 |
| Genótipos | BR16, CD202, EMB48 |
| Condições | irrigado, nao_irrigado |
| Turnos | manha, tarde |
| Grupos (data × genótipo × condição) | 36 |
| Menor grupo | 32 amostras |
| Maior grupo | 68 amostras |
| Valores ausentes nas colunas espectrais | 0 |

### 2.2 Inconsistências e Ajustes de Metadados

Os metadados foram normalizados porque a planilha original continha inconsistências:

- **231** linhas com metadados brutos inconsistentes em `bloco`, `genotipo` ou `condicao`
- **16** linhas com token `C202` no nome do arquivo, normalizadas para `CD202`
- `IRR`, `IRRG` e `IRRIG` foram tratados como `irrigado`
- `NIRR` e `NIRRIG` foram tratados como `nao_irrigado`
- O agrupamento confiavel foi reconstruído a partir de `nomenclaura`

### 2.3 Estrutura Real do Experimento

No subprojeto `estresse_hidrico`, a estrutura observada foi:
- **4** blocos biológicos (B1 a B4)
- **8** leituras técnicas por bloco na maior parte dos grupos
- Exceção em `2017-03-02 / manha / CD202 / IRR / B1`, com **12** leituras técnicas
- As análises inferenciais agregaram técnicas por bloco, recuperando **n = 4 replicatas biológicas** por grupo

Mapeamento de datas usado nos outputs `estresse_hidrico`:

| Data absoluta | Rótulo no pipeline |
|---|---|
| 2017-02-23 | dia2 |
| 2017-02-24 | dia3 |
| 2017-02-25 | dia4 |
| 2017-02-26 | dia5 |
| 2017-02-27 | dia6 |
| 2017-03-02 | dia9 |

**Observação importante:** Não existe uma coleta separada de `recuperação` no workbook atual.

### 2.4 Derivações de Dataset no Repositório

| Derivação | Caminho | Amostras | Colunas | Processamento |
|---|---|---|---|---|
| Base bruta | `base_dados_unificada.xlsx` | 1732 | 2157 | Reflectância original |
| Dataset processado soft | `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv` | 1732 | 2157 | SNV → Savitzky-Golay → 1a derivada |
| Metadados normalizados | `dados_processados_soft/metadados_normalizados_soft.csv` | 1732 | 8 | Alinhamento por `nomenclaura` |
| Réplicas por bloco e dia | `estresse_hidrico/dados/processados/replicatas_bloco_dia.csv` | 144 | 1917 | Médias biológicas com índices |
| Réplicas por bloco e turno | `estresse_hidrico/dados/processados/replicatas_bloco_turno.csv` | 216 | 1917 | Médias biológicas com índices |

### 2.5 Parâmetros de Pré-processamento

**Processamento `soft`:**

| Parâmetro | Valor |
|---|---|
| Janela Savitzky-Golay | 11 |
| Polyorder | 2 |
| Derivada | 1 |
| Delta | 1.0 |
| Padding | `mirror` |
| Faixa de valores processados | `-0.0743105970` a `0.0935908826` |

**Pré-processamento `estresse_hidrico`:**

| Parâmetro | Valor |
|---|---|
| Remoção atmosférica | 1350-1450 nm e 1800-1950 nm |
| Bandas brutas | 2151 |
| Bandas retidas após filtro | 1899 |
| Suavização | Savitzky-Golay |
| Janela | 11 |
| Grau | 2 |

---

## 3. INVENTÁRIO COMPLETO DE EXPERIMENTOS (E01-E23)

### 3.1 Visão Geral dos Experimentos

| ID | Família | Script ou Cluster | Técnica Central | Saídas Principais | Rastreabilidade |
|---|---|---|---|---|---|
| E01 | `outputs` | `scripts/generate_descriptive_stats.py` | Estatística descritiva | `estatistica_descritiva.xlsx`, médias, CV, contagens | Script + artefato |
| E02 | `outputs/plots` | `scripts/generate_output_plots.py` | Gráficos descritivos da base bruta normalizada | `outputs/plots/*` | Artefato presente; script utilitário inferido |
| E03 | `outputs/reflectancia_bruta_genotipos` | `scripts/generate_raw_reflectance_genotype_plots.py` | Média/CV de reflectância bruta por data, turno, genótipo e condição | 40 arquivos | Script + artefato |
| E04 | `dados_processados_soft` | `scripts/generate_processed_dataset_for_soft.py` | Pré-processamento SNV + derivada | Dataset processado e metadados | Script + artefato |
| E05 | `dados_processados_soft/plots` | `scripts/generate_processed_plots.py` | Gráficos descritivos do dataset processado | 9 arquivos | Script + artefato |
| E06 | `outputs_v2` | `scripts/pipeline_v2_soy_hyper.py` | Pipeline v2 completo | Validação, PCA, classificação, seleção de bandas, PLSR, HVI | Script + artefato |
| E07 | `dados_processados_soft/plsr_pca_irrigacao` | `scripts/run_plsr_pca_irrigation.py` | PLSR binário + PCA | 52 arquivos | Script + artefato |
| E08 | `dados_processados_soft/plsr_pca_irrigacao` | `scripts/summarize_significant_bands_irrigation.py` | Ranking de bandas e regiões significativas | Top 20, top 10 por direção, resumos | Script + artefato |
| E09 | `dados_processados_soft/plsr_pca_irrigacao/band_significance` | `scripts/run_band_significance_analysis.py` + `band_significance.py` | Significância multimétodo por banda | Ranking, top20, significativas por alpha | Script + artefato |
| E10 | `dados_processados_soft/plsr_pca_irrigacao/figuras_band_significance` | `scripts/generate_band_significance_plots.py` | Visualizações do ranking e regiões | 4 arquivos | Script + artefato |
| E11 | `dados_processados_soft/plsr_intervalos_regioes_threshold` | `scripts/run_plsr_by_dominant_regions.py` | PLSR por intervalos dominantes | Métricas por intervalo | Script + artefato |
| E12 | `dados_processados_soft/plsr_data_genotipo_turno` | `scripts/run_plsr_by_date_genotype_turno.py` | PLSR por data × genótipo × turno | Métricas, curvas, recorrência | Script + artefato |
| E13 | `dados_processados_soft/plsr_subconjuntos_irrigacao` | `scripts/run_plsr_optimal_bands_by_subset.py` | PLSR por turno, genótipo e turno × genótipo | 72 arquivos | Script + artefato |
| E14 | `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao` | `scripts/tabulate_plsr_pearson_ttest_subsets.py` | Fusão PLSR + Pearson + Welch | Tabelas por subconjunto | Script + artefato |
| E15 | `outputs/pearson_bandas_otimas_turno` | `scripts/compare_optimal_bands_morning_afternoon.py` | Pearson nas bandas ótimas entre manhã e tarde | CSVs, SVGs e resumos | Script + artefato |
| E16 | `dados_processados_soft/*.csv` | `analise_bandas_top5.py`, `analise_bandas_SR_KPCA.py`, `analise_SR_top5_nao_colinear.py` | Análises exploratórias hardcoded | 4 CSVs de análise | Script + artefato |
| E17 | `estresse_hidrico` | `scripts/00` a `05` | Pré-processamento, PERMANOVA, Boruta, temporal, classificação, figuras | Pipeline principal | Script + artefato |
| E18 | `estresse_hidrico` | `scripts/06_reducao_bandas_p_teste.py` | Welch + Kruskal + benchmark LDA | Redução de bandas e benchmark | Script + artefato |
| E19 | `estresse_hidrico` | `scripts/07_classificacao_subset_bandas.py` | LDA com subset explícito | Scores, confusion, predições | Script + artefato |
| E20 | `estresse_hidrico` | `scripts/08_optuna_classificacao_subset.py` | Tuning Optuna | Trials, best params, confusion, resumo | Script + artefato |
| E21 | `estresse_hidrico` | `scripts/06_assinaturas_espectrais.py`, `09_*`, `10_*` | Assinaturas médias e overlays Boruta/Kruskal | Figuras e tabelas auxiliares | Script + artefato |
| E22 | `outputs_v2/significant_bands_*` | Cluster de artefatos | Significância detalhada de subset específico | Threshold summaries, heatmaps, ranges | Artefato órfão |
| E23 | `outputs/spectrum_ratio_*` | Cluster de artefatos | Spectrum ratio por dia/genótipo | 2 CSVs | Artefato órfão e não rastreado no git |

---

## 4. RESULTADOS CONSOLIDADOS POR PIPELINE

### 4.1 Pipeline v2 (E06)

**Comando principal:**
```powershell
python scripts\pipeline_v2_soy_hyper.py `
  --input base_dados_unificada.xlsx `
  --metadata-csv dados_processados_soft\metadados_normalizados_soft.csv `
  --output-dir outputs_v2
```

**Parâmetros efetivos:**

| Parâmetro | Valor |
|---|---|
| Input | `base_dados_unificada.xlsx` |
| Metadata | `dados_processados_soft/metadados_normalizados_soft.csv` |
| Output | `outputs_v2` |
| classification_targets | `condition,turno` |
| Seed | 42 |
| CV splits | 5 |
| Max PLSR components | 20 |
| Band selection candidate n | 250 |
| HVI candidate bands | 80 |
| PLSR executado | Sim |
| HVI executado | Sim |

**Modelos de classificação no v2:**

| Modelo | Configuração |
|---|---|
| `lr` | `LogisticRegression(max_iter=5000, solver='lbfgs', class_weight='balanced', random_state=42)` |
| `svm` | `SVC(kernel='rbf', C=3.0, gamma='scale', class_weight='balanced')` |
| `knn` | `KNeighborsClassifier(n_neighbors=7, weights='distance')` |
| `nb` | `GaussianNB()` |
| `dt` | `DecisionTreeClassifier(class_weight='balanced', min_samples_leaf=2, random_state=42)` |
| `rf` | `RandomForestClassifier(n_estimators=300, class_weight='balanced_subsample', random_state=42)` |
| `gboost` | `GradientBoostingClassifier(random_state=42)` |
| `mlp` | `MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, early_stopping=True, random_state=42)` |

**Técnicas adicionais no v2:**
- PCA com `n_components=5`
- PLSR binário com `PLSRegression(scale=False)` e busca até `20` componentes
- Seleção de bandas com ANOVA, mutual information, random forest, logistic/L1, RFE e PLS/VIP
- Busca HVI sobre `80` bandas candidatas

**Resultados - Validação estrutural:**

| Métrica | Valor |
|---|---|
| Samples | 1732 |
| Bands | 2151 |
| Wavelength min | 350 |
| Wavelength max | 2500 |
| Groups | 36 |
| Group size min | 32 |
| Group size max | 68 |
| Dates | 6 |
| Genotypes | 3 |
| Conditions | 2 |
| Turnos | 2 |

**Resultados - PCA:**

| Componente | Var Explicada | Acumulada |
|---|---|---|
| PC1 | 0.723128 | 0.723128 |
| PC2 | 0.161277 | 0.884405 |
| PC3 | 0.077039 | 0.961444 |
| PC4 | 0.024136 | 0.985580 |
| PC5 | 0.003875 | 0.989455 |

**Resultados - Classificação supervisionada - melhores modelos por alvo:**

| Alvo | Melhor Modelo | Accuracy | Balanced Accuracy | F1-macro | ROC-AUC |
|---|---|---|---|---|---|
| `condition` | `lr` | 0.899538 | 0.899567 | 0.899527 | 0.975266 |
| `turno` | `lr` | 0.822748 | 0.811031 | 0.804360 | 0.901907 |

Observações:
- Para `condition`, o top 3 foi `lr > gboost > svm`
- Para `turno`, o top 3 foi `lr > mlp > svm`

**Resultados - PLSR binário do v2:**

| Melhor n_components | RMSECV | R²CV | AUC | Accuracy |
|---|---|---|---|---|
| 20 | 0.306758 | 0.623596 | 0.967199 | 0.898961 |

**Resultados - Top 10 bandas do ranking combinado:**

| Rank | Banda | Score | Direção |
|---|---|---|---|
| 1 | 390 | 20.955384 | irrigado |
| 2 | 375 | 18.258251 | irrigado |
| 3 | 387 | 17.211722 | nao_irrigado |
| 4 | 396 | 17.202408 | nao_irrigado |
| 5 | 379 | 16.783678 | irrigado |
| 6 | 378 | 15.968198 | irrigado |
| 7 | 395 | 15.583931 | nao_irrigado |
| 8 | 383 | 15.439004 | irrigado |
| 9 | 373 | 14.843045 | nao_irrigado |
| 10 | 394 | 14.817980 | irrigado |

**Resultados - Top 10 pares HVI:**

| Rank | Banda A | Banda B | Score | mean_condition_diff |
|---|---|---|---|---|
| 1 | 383 | 1584 | 1.831071 | 0.124788 |
| 2 | 363 | 1584 | 1.827180 | 0.139056 |
| 3 | 381 | 1584 | 1.826307 | 0.127060 |
| 4 | 386 | 1584 | 1.826182 | 0.122156 |
| 5 | 360 | 1584 | 1.825320 | 0.140279 |
| 6 | 382 | 1584 | 1.825250 | 0.125878 |
| 7 | 375 | 1584 | 1.823731 | 0.132062 |
| 8 | 390 | 1584 | 1.821943 | 0.118029 |
| 9 | 391 | 1584 | 1.820573 | 0.117130 |
| 10 | 387 | 1584 | 1.819976 | 0.120804 |

---

### 4.2 Família dados_processados_soft (E04, E07-E16)

#### 4.2.1 Pré-processamento (E04)

**Script:** `scripts/generate_processed_dataset_for_soft.py`

**Parâmetros:**

| Parâmetro | Valor |
|---|---|
| Input | `base_dados_unificada.xlsx` |
| Output dir | `dados_processados_soft` |
| Window length | 11 |
| Polyorder | 2 |
| Deriv | 1 |
| Delta | 1.0 |

**Pipeline:** SNV → Savitzky-Golay → 1a derivada

#### 4.2.2 PLSR + PCA Irrigado vs Não-Irrigado (E07)

**Script:** `scripts/run_plsr_pca_irrigation.py`

**Defaults:**

| Parâmetro | Valor |
|---|---|
| processed_csv | `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv` |
| metadata_csv | `dados_processados_soft/metadados_normalizados_soft.csv` |
| output_dir | `dados_processados_soft/plsr_pca_irrigacao` |
| max_components | 15 |
| cv_splits | 5 |

**Resultados principais:**

| Métrica | Valor |
|---|---|
| Amostras × bandas | `1732 × 2151` |
| Classes | `868 irrigado` / `864 nao_irrigado` |
| Melhor n_components PLSR | 15 |
| RMSECV | 0.244092 |
| R²CV | 0.761675 |
| AUC | 0.992006 |
| Accuracy | 0.961316 |
| PCA PC1 | 46.63% |
| PCA PC2 | 13.98% |

**Top bandas por coeficiente positivo:**
- `908`, `909`, `1149`, `1148`, `879`, `370`, `1150`, `1205`, `959`, `449`

**Top bandas por coeficiente negativo:**
- `458`, `896`, `895`, `395`, `459`, `1725`, `1724`, `457`, `1726`, `2269`

**Top VIP:**
- Concentração forte em `2270-2293` e `1661-1666`

#### 4.2.3 Bandas Significativas (E08)

**Script:** `scripts/summarize_significant_bands_irrigation.py`

**Principais regiões significativas:**

| Rank | Faixa | Bandas | Pico | Direção Dominante |
|---|---|---|---|---|
| 1 | 1910-1944 | 35 | 1924 | nao_irrigado |
| 2 | 2258-2283 | 26 | 2279 | nao_irrigado |
| 3 | 1380-1472 | 93 | 1427 | nao_irrigado |
| 4 | 422-501 | 80 | 486 | nao_irrigado |
| 5 | 1476-1673 | 198 | 1660 | irrigado |

**Top 5 bandas candidatas:**

| Rank | Banda | Direção | Score Combinado |
|---|---|---|---|
| 1 | 1924 | nao_irrigado | 8.032796 |
| 2 | 1923 | nao_irrigado | 7.969197 |
| 3 | 2279 | nao_irrigado | 7.943298 |
| 4 | 2280 | nao_irrigado | 7.917611 |
| 5 | 1427 | nao_irrigado | 7.888721 |

#### 4.2.4 Análise band_significance (E09)

**Scripts:** `scripts/run_band_significance_analysis.py` + `band_significance.py`

**Parâmetros:**

| Parâmetro | Valor |
|---|---|
| Alpha | 0.05 |
| p_adjust_method | `fdr_bh` |
| Target type efetivo | `binary` |

**Definição do ranking:**
- `effect_score`: média robusta dos efeitos disponíveis
- `significance_score`: média robusta de `-log10(p ajustado)`
- `consistency_score`: concordância de sinal entre métricas assinadas
- `ranking_score = 0.45 * effect_score + 0.45 * significance_score + 0.10 * consistency_score`

**Resultados:**

| Métrica | Valor |
|---|---|
| Bandas analisadas | 2151 |
| Bandas significativas em `alpha=0.05` | 2018 |
| Top 5 bandas | 1924, 1925, 1923, 1926, 487 |

**Top 10 do ranking:**

| Rank | Banda | Direção | ranking_score | Fonte do menor p ajustado |
|---|---|---|---|---|
| 1 | 1924 | nao_irrigado | 3.497944 | ttest |
| 2 | 1925 | nao_irrigado | 3.481386 | spearman |
| 3 | 1923 | nao_irrigado | 3.366707 | pearson |
| 4 | 1926 | nao_irrigado | 3.335651 | spearman |
| 5 | 487 | nao_irrigado | 3.312726 | spearman |
| 6 | 486 | nao_irrigado | 3.284761 | spearman |
| 7 | 488 | nao_irrigado | 3.283466 | spearman |
| 8 | 490 | nao_irrigado | 3.267614 | spearman |
| 9 | 489 | nao_irrigado | 3.254755 | spearman |
| 10 | 491 | nao_irrigado | 3.243968 | spearman |

#### 4.2.5 PLSR por Intervalos de Regiões Dominantes (E11)

**Script:** `scripts/run_plsr_by_dominant_regions.py`

**Parâmetros:**

| Parâmetro | Valor |
|---|---|
| max_components | 15 |
| cv_splits | 5 |
| Intervalos avaliados | 50 |

**Melhor intervalo:**

| Critério | Intervalo | Threshold | Faixa | Comp. | AUC | RMSECV | R²CV | Accuracy |
|---|---|---|---|---|---|---|---|---|
| Melhor AUC e melhor RMSECV | `thr_1em05_rank_05_1310_1470` | `1e-05` | `1310-1470 nm` | 15 | 0.949843 | 0.310991 | 0.613137 | 0.884527 |

Os cinco melhores por threshold foram todos variantes da faixa `1279-1472 nm` ou `1310-1470 nm`.

#### 4.2.6 PLSR por Data × Genótipo × Turno (E12)

**Script:** `scripts/run_plsr_by_date_genotype_turno.py`

**Parâmetros:**

| Parâmetro | Valor |
|---|---|
| max_components | 15 |
| cv_splits | 5 |
| top_k | 5 |
| Subconjuntos avaliados | 27 |

**Resumo:**

| Destaque | Subconjunto | R²CV | RMSECV | AUC | Accuracy |
|---|---|---|---|---|---|
| Melhor R²CV | `2017-02-27 | BR16 | manha` | 0.997001 | 0.027380 | 1.000000 | 1.000000 |
| Pior R²CV | `2017-03-02 | BR16 | tarde` | 0.854953 | 0.190425 | 1.000000 | 0.984375 |

**Padrão geral:**
- Todos os 27 subconjuntos tiveram `AUC = 1.0`
- A accuracy foi `1.0` na maioria dos subconjuntos
- A pior accuracy encontrada ainda foi `0.984375`

#### 4.2.7 PLSR por Subconjuntos de Turno e Genótipo (E13)

**Script:** `scripts/run_plsr_optimal_bands_by_subset.py`

**Defaults:**

| Parâmetro | Valor |
|---|---|
| max_components | 15 |
| cv_splits | 5 |
| top_k | 20 |
| Score de banda ótima | `z(VIP) + z(|coeficiente PLSR|)` |

**Resumo dos 11 subconjuntos:**
- Melhor accuracy: `manha / BR16 = 1.000000`
- Melhor AUC: `1.000000` em `manha / BR16`
- Pior accuracy: `Turno tarde = 0.939236`
- Faixas ótimas alternaram entre UV/visível curto (`392`, `383`) e SWIR (`2270-2281`, `1661-1668`, `2149`)

#### 4.2.8 Tabelas PLSR + Pearson + Welch (E14)

**Script:** `scripts/tabulate_plsr_pearson_ttest_subsets.py`

**Defaults:**

| Parâmetro | Valor |
|---|---|
| max_components | 15 |
| cv_splits | 5 |
| top_k | 20 |
| Regra Welch | `p < 0.005` |
| Pearson binário | `irrigado = 1`, `nao_irrigado = 0` |

**Destaques:**

| Subconjunto | Banda Top |
|---|---|
| Data 23/02/2017 | 392 |
| Data 24/02/2017 | 2281 |
| Data 02/03/2017 | 2295 |
| Turno manha | 392 |
| Turno tarde | 2281 |
| Genótipo BR16 | 2270 |
| Genótipo CD202 | 2280 |
| Genótipo EMB48 | 1661 |
| manha / CD202 | 2149 |
| manha / EMB48 | 383 |

#### 4.2.9 Análises Exploratórias Hardcoded (E16)

**Scripts:** `analise_bandas_top5.py`, `analise_bandas_SR_KPCA.py`, `analise_SR_top5_nao_colinear.py`

**Padrões observados:**
- `analise_bandas_top5*`: recorrência forte de bandas em torno de `354`, `698-701`, `1910-1914`, `725-728` e `1362-1366`
- `analise_bandas_SR_KPCA.csv`: KPCA-RBF e KPCA-POLY priorizaram repetidamente `350-352 nm`
- `analise_SR_top5_nao_colinear.csv`: para `irrigado_vs_nao_irrigado`, o top 5 global foi `1884, 1894, 1874, 731, 569`; para `manha_vs_tarde`, `1883, 358, 1000, 375, 1873`

---

### 4.3 Pipeline Estresse Hídrico (E17-E21)

#### 4.3.1 Estrutura e Execução

**Comando de execução:**
```powershell
& ..\.venv311_estresse\Scripts\python.exe .\scripts\00_preprocessamento.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\01_permanova.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\02_boruta_por_dia.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\03_graficos_temporais.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\04_classificacao.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\05_figuras_finais.py
```

**Ambiente e dependências:**
- Python `3.11`
- `numpy`, `pandas`, `scipy`, `scikit-learn`, `scikit-bio`, `Boruta`, `xgboost`, `matplotlib`, `seaborn`, `statsmodels`, `joblib`, `openpyxl`

#### 4.3.2 PERMANOVA e PERMDISP (Q1)

**Script:** `estresse_hidrico/scripts/01_permanova.py`

**Tabela consolidada:**

| Cultivar | Condição | Comparação | Métrica | F | p | q | R² | Significativo |
|---|---|---|---|---:|---:|---:|---:|---|
| EMB48 | IRR | Manha vs Tarde | euclidean | 8.632339 | 0.005 | 0.012000 | 0.281805 | Sim |
| EMB48 | NIRR | Manha vs Tarde | euclidean | 0.300935 | 0.707 | 0.707000 | 0.013494 | Não |
| BR16 | IRR | Manha vs Tarde | euclidean | 4.509718 | 0.029 | 0.046400 | 0.170116 | Sim |
| BR16 | NIRR | Manha vs Tarde | braycurtis | 0.569913 | 0.511 | 0.584000 | 0.025251 | Não |
| CD202 | IRR | Manha vs Tarde | euclidean | 6.923610 | 0.006 | 0.012000 | 0.239376 | Sim |
| CD202 | NIRR | Manha vs Tarde | euclidean | 1.289787 | 0.245 | 0.326667 | 0.055380 | Não |
| Todos | IRR vs NIRR | Manha | braycurtis | 65.740998 | 0.001 | 0.004000 | 0.484312 | Sim |
| Todos | IRR vs NIRR | Tarde | braycurtis | 14.029938 | 0.001 | 0.004000 | 0.166964 | Sim |

**PERMDISP:**
- Todos os `8` contrastes passaram em homogeneidade de dispersão (`homogeneidade_ok = Sim`)

**Interpretação:**
- O efeito de turno foi significativo apenas nos grupos irrigados
- Nos grupos não irrigados, a diferença entre manhã e tarde não foi estatisticamente robusta após correção FDR
- A condição hídrica `IRR vs NIRR` foi fortemente discriminada, especialmente de manhã
- O maior `R²` ocorreu em `IRR vs NIRR / manha`

#### 4.3.3 Boruta por Dia (Q2)

**Script:** `estresse_hidrico/scripts/02_boruta_por_dia.py`

**Hiperparâmetros:**

| Componente | Valor |
|---|---|
| Estimador base | `RandomForestClassifier` |
| `n_estimators` RF | 500 |
| `class_weight` | `balanced_subsample` |
| `random_state` | 42 |
| `n_estimators` Boruta | `auto` |
| `alpha` Boruta | 0.05 |
| `max_iter` Boruta | 100 |

**Resumo por dia:**

| Dia | Confirmadas | Tentativas | Rejeitadas |
|---|---|---:|---:|---:|
| dia2 | 1 | 5 | 1893 |
| dia3 | 52 | 57 | 1790 |
| dia4 | 93 | 17 | 1789 |
| dia5 | 0 | 177 | 1722 |
| dia6 | 2 | 124 | 1773 |
| dia9 | 110 | 45 | 1744 |

**Bandas confirmadas mais recorrentes:**
- `356 nm` e `362 nm` em `4` dias
- `352-355`, `357-359`, `361`, `363`, `366-399` e `422 nm` em `3` dias

**Interpretação dia a dia:**

| Dia | Confirmações | Faixa Principal | Observação |
|---|---|---|---|
| dia2 | 1 | 2444 nm | Estresse no início ainda não produz assinatura ampla |
| dia3 | 52 | 350-422 nm | Resposta inicial em visível curto e UV próximo |
| dia4 | 93 | 350-730 nm | Borda vermelha aparece mais claramente |
| dia5 | 0 | - | Transição sem estabilidade estatística suficiente |
| dia6 | 2 | 356, 362 nm | 124 bandas tentativas, diferenças relevantes nos IVs |
| dia9 | 110 | 352-498 nm | Maior número de confirmações, consolidação da separação |

#### 4.3.4 Séries Temporais e Desvio do Quociente (Q2)

**Scripts:** `estresse_hidrico/scripts/03_graficos_temporais.py`, `estresse_hidrico/scripts/05_figuras_finais.py`

**Resumo:**
- `70` bandas foram selecionadas para séries temporais
- Faixa temporal selecionada: `350-439 nm`
- Os picos finais do painel de desvio ficaram em `569-703 nm`

**Picos finais do quociente NIRR/IRR:**

| Dia | Pico 1 | Pico 2 |
|---|---|---|
| dia2 | 700 nm | 569 nm |
| dia3 | 595 nm | 696 nm |
| dia4 | 569 nm | 700 nm |
| dia5 | 580 nm | 697 nm |
| dia6 | 703 nm | 557 nm |
| dia9 | 703 nm | - |

**Maior diferença absoluta NIRR-IRR por índice de vegetação:**

| Índice | Dia da Maior Diferença | Delta NIRR - IRR |
|---|---|---|
| NDVI | dia6 | 0.102539 |
| EVI | dia6 | 0.050436 |
| WBI | dia6 | -0.003366 |
| PRI | dia6 | 0.012966 |
| SIPI | dia6 | 0.038239 |
| REP | dia5 | -0.982129 |

#### 4.3.5 Classificação 6 Classes (Q3)

**Script:** `estresse_hidrico/scripts/04_classificacao.py`

**As 6 classes:**

| Classe | Grupo |
|---|---|
| A | EMB48 IRR |
| B | EMB48 NIRR |
| C | BR16 IRR |
| D | BR16 NIRR |
| E | CD202 IRR |
| F | CD202 NIRR |

**Features e validação:**

| Item | Valor |
|---|---|
| Bandas de entrada | União das bandas confirmadas pelo Boruta |
| Índices fixos | `NDVI`, `EVI`, `WBI`, `PRI`, `SIPI`, `REP` |
| Total de features | 154 |
| CV | `StratifiedGroupKFold` |
| Grupos de CV | Bloco biológico |
| Folds efetivos | 4 |

**Modelos e hiperparâmetros:**

| Modelo | Configuração |
|---|---|
| Random Forest | `n_estimators=750`, `class_weight='balanced_subsample'`, `random_state=42` |
| SVM (RBF) | `class_weight='balanced'` |
| LDA | `solver='lsqr'`, `shrinkage='auto'` |
| k-NN | `n_neighbors=5`, `metric='euclidean'` |
| XGBoost | `n_estimators=400`, `max_depth=4`, `learning_rate=0.05`, `subsample=0.9`, `colsample_bytree=0.9`, `reg_lambda=1.0` |

**Desempenho:**

| Modelo | Accuracy Média | F1-macro Médio | Kappa Médio |
|---|---:|---:|---:|
| LDA | 0.625000 | 0.612368 | 0.550000 |
| XGBoost | 0.590278 | 0.569552 | 0.508333 |
| Random Forest | 0.506944 | 0.486796 | 0.408333 |
| SVM (RBF) | 0.493056 | 0.470084 | 0.391667 |
| k-NN (k=5) | 0.458333 | 0.434706 | 0.350000 |

**Melhor modelo:** `LDA`

**Escores por classe do melhor modelo (LDA):**

| Classe | Precisão | Recall | F1 | Suporte |
|---|---:|---:|---:|---:|
| A (EMB48 IRR) | 0.653846 | 0.708333 | 0.680000 | 24 |
| B (EMB48 NIRR) | 0.666667 | 0.666667 | 0.666667 | 24 |
| C (BR16 IRR) | 0.739130 | 0.708333 | 0.723404 | 24 |
| D (BR16 NIRR) | 0.615385 | 0.666667 | 0.640000 | 24 |
| E (CD202 IRR) | 0.666667 | 0.416667 | 0.512821 | 24 |
| F (CD202 NIRR) | 0.466667 | 0.583333 | 0.518519 | 24 |

**Matriz de confusão consolidada:**

| Classe Verdadeira | A | B | C | D | E | F |
|---|---:|---:|---:|---:|---:|---:|
| A (EMB48 IRR) | 17 | 0 | 2 | 0 | 3 | 2 |
| B (EMB48 NIRR) | 0 | 16 | 0 | 1 | 1 | 6 |
| C (BR16 IRR) | 3 | 0 | 17 | 3 | 1 | 0 |
| D (BR16 NIRR) | 0 | 0 | 1 | 16 | 0 | 7 |
| E (CD202 IRR) | 6 | 2 | 3 | 2 | 10 | 1 |
| F (CD202 NIRR) | 0 | 6 | 0 | 4 | 0 | 14 |

**Top 10 importâncias do Random Forest:**

| Rank | Feature | Importância |
|---|---|---|
| 1 | `REP` | 0.055622 |
| 2 | `WBI` | 0.028148 |
| 3 | `717 nm` | 0.027862 |
| 4 | `EVI` | 0.027279 |
| 5 | `718 nm` | 0.027047 |
| 6 | `719 nm` | 0.022689 |
| 7 | `720 nm` | 0.021650 |
| 8 | `2444 nm` | 0.020527 |
| 9 | `NDVI` | 0.019109 |
| 10 | `721 nm` | 0.018685 |

#### 4.3.6 Redução de Bandas por p-teste (E18)

**Script:** `estresse_hidrico/scripts/06_reducao_bandas_p_teste.py`

**Método:**
- Welch t-test para `IRR vs NIRR`
- Kruskal-Wallis para classes `A-F`
- Correção `BH`
- Benchmark via `LDA(solver='lsqr', shrinkage='auto')`

**Resultados centrais:**

| Métrica | Valor |
|---|---|
| Bandas testadas | 148 |
| `q < 0.05` Welch | 148 |
| `q < 0.01` Welch | 148 |
| `q < 0.05` Kruskal | 148 |
| `q < 0.01` Kruskal | 148 |

**Top 10 Welch t-test:**
- `721-730 nm`, com destaque máximo em `727 nm` (`|d| = 2.3492`)

**Top 10 Kruskal-Wallis:**
- Concentração em `361-391 nm`, com pico em `381 nm` (`H = 102.6561`, `eta2(H) = 0.7077`)

**Benchmark LDA:**

| Subset | Accuracy | F1-macro | Kappa |
|---|---|---|---|
| Todas as 148 bandas (baseline) | 0.6250 | 0.6124 | 0.5500 |
| `joint_top_30` | 0.6042 | - | - |
| `kruskal_top_20` | 0.6042 | - | - |
| `indices_only` | 0.5208 | - | - |

#### 4.3.7 Classificação com Subset Explícito e Optuna (E19-E20)

**Scripts:** `estresse_hidrico/scripts/07_classificacao_subset_bandas.py`, `estresse_hidrico/scripts/08_optuna_classificacao_subset.py`

**Subset base analisado:** `kruskal_top_20`
- `20` bandas espectrais + `6` índices = `26` features totais

**Resultado sem tuning (E19):**

| Subset | Accuracy Média | F1-macro Médio | Kappa Médio |
|---|---|---|---|
| `kruskal_top_20` | 0.604167 | 0.586368 | 0.525000 |

**Optuna (E20):**

| Métrica | Valor |
|---|---|
| Sampler | `TPESampler(seed=42)` |
| Trials | 80 |
| Melhor modelo | `LDA` |
| Melhor solver | `eigen` |
| Shrinkage mode | `float` |
| Shrinkage | 0.008407038530137188 |
| Objective | 0.628106 |
| Accuracy média | 0.638889 |
| F1-macro médio | 0.627411 |
| Kappa médio | 0.566667 |

**Ganho do Optuna sobre o subset LDA fixo:**
- Accuracy: `+0.034722`
- F1-macro: `+0.041043`
- Kappa: `+0.041667`

**Resumo por dia do melhor subset com tuning:**

| Dia | Accuracy Média | F1-macro Médio | Kappa Médio |
|---|---|---|---|
| dia2 | 0.416667 | 0.308333 | 0.300000 |
| dia3 | 0.541667 | 0.472222 | 0.450000 |
| dia4 | 0.500000 | 0.416667 | 0.400000 |
| dia5 | 0.416667 | 0.277778 | 0.300000 |
| dia6 | 0.500000 | 0.444444 | 0.400000 |
| dia9 | 0.375000 | 0.305556 | 0.250000 |

#### 4.3.8 Assinaturas Espectrais e Overlays Boruta/Kruskal (E21)

**Scripts:** `estresse_hidrico/scripts/06_assinaturas_espectrais.py`, `09_plot_boruta_kruskal_assinatura_media.py`, `10_plot_boruta_kruskal_por_dia.py`

**Resumo da sobreposição Boruta/Kruskal por dia:**

| Dia | Bandas Boruta | Ranges Boruta | Top 20 Kruskal |
|---|---|---|---|
| dia2 | 1 | 2444 | 1544-1549; 1552-1565 |
| dia3 | 52 | 350-400; 422 | 350-369 |
| dia4 | 93 | 350-415; 422-431; 437-439; 717-730 | 350-369 |
| dia5 | 0 | - | 359; 362-380 |
| dia6 | 2 | 356; 362 | 350-369 |
| dia9 | 110 | 352-498 com blocos recorrentes | 352-363; 366-373 |

---

## 5. TABELA DE PARÂMETROS E HIPERPARÂMETROS

| Script | Parâmetros/Defaults Principais | Hiperparâmetros/Modelos Principais |
|---|---|---|
| `scripts/generate_descriptive_stats.py` | `input=base_dados_unificada.xlsx`, `output=outputs` | Estatística descritiva por grupo |
| `scripts/generate_processed_dataset_for_soft.py` | `window=11`, `polyorder=2`, `deriv=1`, `delta=1.0` | SNV + Savitzky-Golay + 1a derivada |
| `scripts/generate_processed_plots.py` | `processed_csv`, `metadata_csv`, `output=dados_processados_soft/plots` | Médias e CV do sinal processado |
| `scripts/generate_raw_reflectance_genotype_plots.py` | `input=base_dados_unificada.xlsx`, `output=outputs/reflectancia_bruta_genotipos` | Médias e CV do sinal bruto |
| `scripts/pipeline_v2_soy_hyper.py` | `seed=42`, `cv=5`, `max_plsr=20`, `band_selection_candidate_n=250`, `hvi_candidate_bands=80` | LR balanceado, SVM RBF `C=3`, kNN `7/dist`, RF `300`, MLP `(64,32)`, RFE, MI, PLS/VIP, HVI |
| `scripts/run_plsr_pca_irrigation.py` | `max_components=15`, `cv=5` | `PLSRegression(scale=False)`, `PCA(n_components=2)` |
| `scripts/run_band_significance_analysis.py` | `alpha=0.05`, `p_adjust_method=fdr_bh` | Welch, Kruskal, Pearson, Spearman, ranking robusto |
| `scripts/run_plsr_by_dominant_regions.py` | `max_components=15`, `cv=5` | PLSR por intervalo |
| `scripts/run_plsr_by_date_genotype_turno.py` | `max_components=15`, `cv=5`, `top_k=5` | PLSR por subconjunto |
| `scripts/run_plsr_optimal_bands_by_subset.py` | `max_components=15`, `cv=5`, `top_k=20` | Score `z(VIP)+z(|coef|)` |
| `scripts/tabulate_plsr_pearson_ttest_subsets.py` | `max_components=15`, `cv=5`, `top_k=20` | Pearson + Welch `p<0.005` sobre ranking PLSR |
| `scripts/compare_optimal_bands_morning_afternoon.py` | `dates=2017-02-23,2017-02-24,2017-03-02` | Pearson, MAD, RMSE nas bandas ótimas |
| `analise_bandas_top5.py` | Caminhos hardcoded | PCA, PLS, RF `100`, MI `n_neighbors=5`, Kruskal, MWU, Spearman |
| `analise_bandas_SR_KPCA.py` | Caminhos hardcoded | PCA, KPCA `rbf` e `poly`, Spectrum Ratio |
| `analise_SR_top5_nao_colinear.py` | Caminhos hardcoded | Spectrum Ratio com `min_gap=10 nm` |
| `estresse_hidrico/scripts/02_boruta_por_dia.py` | Input réplicas por dia | RF `500`, Boruta `alpha=0.05`, `max_iter=100`, seed `42` |
| `estresse_hidrico/scripts/04_classificacao.py` | Input réplicas dia + Boruta | LDA `lsqr/auto`, RF `750`, XGBoost `400/depth4/lr0.05`, SVM RBF, kNN `5` |
| `estresse_hidrico/scripts/06_reducao_bandas_p_teste.py` | Input réplicas dia, features manifest | Welch + Kruskal + BH + benchmark LDA |
| `estresse_hidrico/scripts/07_classificacao_subset_bandas.py` | Subset obrigatório | LDA `lsqr/auto` |
| `estresse_hidrico/scripts/08_optuna_classificacao_subset.py` | `n_trials=80`, `seed=42`, subset obrigatório | Optuna sobre LDA, SVM, RF e KNN |
| `estresse_hidrico/scripts/09_plot_boruta_kruskal_assinatura_media.py` | Usa `kruskal_top_20.csv` | Overlay global Boruta vs Kruskal |
| `estresse_hidrico/scripts/10_plot_boruta_kruskal_por_dia.py` | `top_k_kruskal=20` | Overlay por dia |

---

## 6. CATÁLOGO DE ARQUIVOS E ARTEFATOS

### 6.1 Tabelas Grandes (Dados Completos Não Transcritos)

| Arquivo | Linhas | Colunas | Papel no Projeto |
|---|---|---|---|
| `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv` | 1732 | 2157 | Dataset processado principal |
| `dados_processados_soft/metadados_normalizados_soft.csv` | 1732 | 8 | Metadados alinhados |
| `outputs_v2/09_hvi/hvi_pairs_v2.csv` | 3160 | 4 | Pares HVI candidatos |
| `outputs_v2/subset_bandas_significativas_2017-02-23_manha_BR16.csv` | 2151 | 7 | Subset órfão de significância |
| `dados_processados_soft/plsr_pca_irrigacao/kruskal_pearson_spearman_irrigacao.csv` | 2151 | 8 | Ranking estatístico bruto por banda |
| `dados_processados_soft/plsr_pca_irrigacao/plsr_bandas_importantes.csv` | 2151 | 5 | VIP e coeficientes PLSR por banda |
| `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao/top_bandas_plsr_pearson_ttest.csv` | 280 | 23 | Top bandas por subconjunto |
| `estresse_hidrico/dados/processados/replicatas_bloco_dia.csv` | 144 | 1917 | Base biológica da classificação 6×6 |
| `estresse_hidrico/outputs/tabelas/lambdas_boruta_por_dia.csv` | 11394 | 5 | Boruta completo por dia |
| `estresse_hidrico/outputs/tabelas/features_classificacao.csv` | 154 | 4 | Manifesto de features do classificador |
| `estresse_hidrico/outputs/tabelas/predicoes_classificacao_cv.csv` | 144 | 10 | Predições CV do classificador principal |
| `estresse_hidrico/outputs/tabelas/optuna_classificacao_subset/optuna_trials_kruskal_top_20.csv` | 80 | 25 | Histórico de trials Optuna |
| `estresse_hidrico/outputs/tabelas/assinatura_espectral_irr_vs_nirr_media.csv` | 4302 | 6 | Assinatura média global |
| `estresse_hidrico/outputs/tabelas/assinatura_espectral_irr_vs_nirr_por_dia.csv` | 25812 | 7 | Assinatura média por dia |
| `estresse_hidrico/outputs/tabelas/series_temporais_resumo.csv` | 912 | 8 | Médias/DP por feature e dia |
| `outputs/spectrum_ratio_por_dia_genotipo_condicao.csv` | 18 | 9 | Artefato órfão por dia/genótipo |
| `outputs/spectrum_ratio_por_dia_genotipo_turno_condicao.csv` | 27 | 10 | Artefato órfão por dia/genótipo/turno |

### 6.2 Arquivos XLSX Relevantes

- `outputs/estatistica_descritiva.xlsx`
- `estresse_hidrico/outputs/tabelas/preprocessamento_resumo.xlsx`
- `estresse_hidrico/outputs/tabelas/resultados_permanova.xlsx`
- `estresse_hidrico/outputs/tabelas/resultados_boruta.xlsx`
- `estresse_hidrico/outputs/tabelas/resultados_temporais.xlsx`
- `estresse_hidrico/outputs/tabelas/resultados_classificacao.xlsx`
- `estresse_hidrico/outputs/tabelas/sintese_final.xlsx`

---

## 7. CONCLUSÕES FINAIS

### 7.1 Repositório - Visão Consolidada

O repositório contém, de forma rastreável, **quatro famílias principais de trabalho**:

1. **Pipeline v2 reprodutível** com validação, classificação, seleção de bandas, PLSR e HVI
2. **Experimentos soft** focados em PLSR, PCA, significância de bandas, subconjuntos e comparações manhã/tarde
3. **Pipeline estresse_hidrico** com pré-processamento biológico, PERMANOVA, Boruta, temporalidade, classificação 6×6 e refinamentos posteriores
4. **Relatórios descritivos**, gráficos de reflectância bruta e análises exploratórias hardcoded

### 7.2 Achados Principais

| Pipeline/Família | Melhor Desempenho | Destaque |
|---|---|---|
| Pipeline v2 (condition) | LR: accuracy=89.9%, AUC=97.5% | Classificação binária irrigado vs não irrigado |
| Pipeline v2 (turno) | LR: accuracy=82.3%, AUC=90.2% | Classificação manhã vs tarde |
| PLSR soft irrigação | AUC=0.992, R²=0.762 | Discriminação muito forte |
| Estresse hídrico (6 classes) | LDA: accuracy=62.5%, kappa=0.55 | Classificação multiclasse |

### 7.3 Bandas Mais Discriminativas

As bandas em torno das seguintes regiões aparecem repetidamente como discriminativas:

| Região Espectral |nm) | Relevância |
|---|---|
| UV/Azul curto | 350-439 | Mais estável temporalmente (Boruta), especialmente 356nm e 362nm |
| Borda vermelha | 717-730 | Importante para classificação multiclasse |
| SWIR próximo | 1425-1430 |PLS significant |
| SWIR médio | 1660-1669 | VIP PLSR |
| SWIR alto | 1880-1894 | Spectrum ratio, top recurring |
| SWIR muito alto | 1923-1926 | Top band significance (não irrigado) |
| SWIR extremo | 2270-2281 | Top coefficients PLSR |

### 7.4 Regiões Dominantes PLSR

| Rank | Faixa (nm) | Bandas | Direção Dominante |
|---|---|---|---|
| 1 | 1910-1944 | 35 | não irrigado |
| 2 | 2258-2283 | 26 | não irrigado |
| 3 | 1380-1472 | 93 | não irrigado |
| 4 | 422-501 | 80 | não irrigado |
| 5 | 1476-1673 | 198 | irrigado |

---

## 8. LIMITAÇÕES E LACUNAS

### 8.1 Limitações Reais do Dataset

- Ausência de uma coleta separada de `recuperação`
- Desbalanceamento técnico localizado em `2017-03-02 / manha / CD202 / IRR / B1`
- Divergências entre o plano teórico e a estrutura real da planilha
- Diferentes pipelines usam diferentes representações do sinal:
  - `soft`: `SNV + Savitzky-Golay + 1a derivada`
  - `estresse_hidrico`: sinal suavizado com remoção de bandas atmosféricas
  - `outputs/reflectancia_bruta_genotipos` e `pearson_bandas_otimas_turno`: reflectância bruta

### 8.2 Artefatos com Rastreabilidade Parcial

- `outputs_v2/significant_bands_2017-02-23_manha_BR16*`, `outputs_v2/heatmaps/*`, `outputs_v2/plots_ranges/*`:
  - Artefatos presentes
  - Contexto experimental inferível
  - Script gerador não localizado

- `outputs/spectrum_ratio_por_dia_genotipo_condicao.csv` e `outputs/spectrum_ratio_por_dia_genotipo_turno_condicao.csv`:
  - Artefatos presentes
  - Não rastreados no git
  - Sem referência textual encontrada no workspace

### 8.3 Nível de Confiança do Relatório

- **Alto** para métricas que vieram de `CSV`, `JSON`, `XLSX` e relatórios já exportados
- **Médio** para parâmetros inferidos diretamente de defaults do código, quando o artefato não traz o valor explicitamente
- **Médio-baixo** para a genealogia de artefatos órfãos, embora seus conteúdos tenham sido lidos e resumidos corretamente

---

## 8.4 Considerações Finais

Este documento, junto com os caminhos de origem apontados em cada seção, é a **referência consolidada** para:
- Redação técnica
- Auditoria do projeto
- Reaproveitamento dos resultados

Se uma coleta de recuperação real for adicionada posteriormente ao workbook, o pipeline pode ser reexecutado para completar a série temporal sem necessidade de refatoração estrutural.

---

**Fim do Documento**