# RELATORIO MESTRE DE EXPERIMENTOS DO PROJETO AGROSATHIDRICO

## 1. Escopo deste relatorio

Este documento consolida os experimentos realmente materializados no workspace `AgroSATHidrico` na data de levantamento `2026-04-30`.

Escopo coberto:

- `outputs_v2`
- `dados_processados_soft`
- `estresse_hidrico`
- `outputs`
- scripts raiz com saidas encontradas

Regra de completude usada aqui:

- resultados interpretaveis e tabelas-chave entram no corpo do relatorio;
- tabelas gigantes entram com descricao, dimensoes, schema funcional e caminho exato do arquivo-fonte;
- quando um artefato existe, mas o script gerador nao foi localizado no workspace, ele continua inventariado como `artefato orfao`;
- quando um valor veio de artefato executado, ele tem prioridade sobre defaults do codigo;
- quando um parametro nao aparece em artefato, ele e registrado a partir do script como `default do codigo`.

Contagem de artefatos nos principais diretorios de saida:

| diretorio | arquivos |
| --- | ---: |
| `outputs_v2` | 55 |
| `dados_processados_soft` | 155 |
| `estresse_hidrico/outputs` | 167 |
| `outputs` | 61 |
| **total** | **438** |

## 2. Base comum de dados e normalizacao

### 2.1 Workbook bruto

O workbook base e `base_dados_unificada.xlsx`.

Resumo consolidado da base:

| metrica | valor |
| --- | --- |
| amostras brutas | 1732 |
| bandas espectrais | 2151 |
| faixa espectral | 350-2500 nm |
| datas absolutas | 2017-02-23, 2017-02-24, 2017-02-25, 2017-02-26, 2017-02-27, 2017-03-02 |
| genotipos | BR16, CD202, EMB48 |
| condicoes | irrigado, nao_irrigado |
| turnos | manha, tarde |
| grupos (`data x genotipo x condicao`) | 36 |
| menor grupo | 32 amostras |
| maior grupo | 68 amostras |
| valores ausentes nas colunas espectrais | 0 |

### 2.2 Inconsistencias e ajustes de metadados

Os metadados foram normalizados porque a planilha original continha inconsistencias.

Achados relevantes:

- `231` linhas com metadados brutos inconsistentes em `bloco`, `genotipo` ou `condicao`.
- `16` linhas com token `C202` no nome do arquivo, normalizadas para `CD202`.
- `IRR`, `IRRG` e `IRRIG` foram tratados como `irrigado`.
- `NIRR` e `NIRRIG` foram tratados como `nao_irrigado`.
- o agrupamento confiavel foi reconstruido a partir de `nomenclaura`.

### 2.3 Estrutura real do experimento

No subprojeto `estresse_hidrico`, a estrutura observada foi:

- `4` blocos biologicos (`B1` a `B4`);
- `8` leituras tecnicas por bloco na maior parte dos grupos;
- excecao em `2017-03-02 / manha / CD202 / IRR / B1`, com `12` leituras tecnicas;
- as analises inferenciais agregaram tecnicas por bloco, recuperando `n = 4` replicatas biologicas por grupo.

Mapeamento de datas usado nos outputs `estresse_hidrico`:

| data absoluta | rotulo no pipeline |
| --- | --- |
| 2017-02-23 | dia2 |
| 2017-02-24 | dia3 |
| 2017-02-25 | dia4 |
| 2017-02-26 | dia5 |
| 2017-02-27 | dia6 |
| 2017-03-02 | dia9 |

Observacao importante:

- nao existe uma coleta separada de `recuperacao` no workbook atual; qualquer painel `recuperacao` e placeholder.

### 2.4 Derivacoes de dataset no repositorio

| derivacao | caminho | amostras | colunas | processamento |
| --- | --- | ---: | ---: | --- |
| base bruta | `base_dados_unificada.xlsx` | 1732 | 2157 logicas | reflectancia original |
| dataset processado soft | `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv` | 1732 | 2157 | `SNV -> Savitzky-Golay -> 1a derivada` |
| metadados normalizados | `dados_processados_soft/metadados_normalizados_soft.csv` | 1732 | 8 | alinhamento por `nomenclaura` |
| replicatas por bloco e dia | `estresse_hidrico/dados/processados/replicatas_bloco_dia.csv` | 144 | 1917 | medias biologicas com indices |
| replicatas por bloco e turno | `estresse_hidrico/dados/processados/replicatas_bloco_turno.csv` | 216 | 1917 | medias biologicas com indices |

Parametros do processamento `soft`:

| parametro | valor |
| --- | --- |
| janela Savitzky-Golay | 11 |
| polyorder | 2 |
| derivada | 1 |
| delta | 1.0 |
| padding | `mirror` |
| faixa de valores processados | `-0.0743105970` a `0.0935908826` |

Parametros do preprocessamento `estresse_hidrico`:

| parametro | valor |
| --- | --- |
| remocao atmosferica | 1350-1450 nm e 1800-1950 nm |
| bandas brutas | 2151 |
| bandas retidas apos filtro | 1899 |
| suavizacao | Savitzky-Golay |
| janela | 11 |
| grau | 2 |

## 3. Inventario mestre de experimentos

| ID | familia | script ou cluster | tecnica central | saidas principais | rastreabilidade |
| --- | --- | --- | --- | --- | --- |
| E01 | `outputs` | `scripts/generate_descriptive_stats.py` | estatistica descritiva | `estatistica_descritiva.xlsx`, medias, CV, contagens | script + artefato |
| E02 | `outputs/plots` | `scripts/generate_output_plots.py` | graficos descritivos da base bruta normalizada | `outputs/plots/*` | artefato presente; script utilitario inferido |
| E03 | `outputs/reflectancia_bruta_genotipos` | `scripts/generate_raw_reflectance_genotype_plots.py` e `gerar_graficos_reflectancia.py` | media/CV de reflectancia bruta por data, turno, genotipo e condicao | 40 arquivos | script + artefato |
| E04 | `dados_processados_soft` | `scripts/generate_processed_dataset_for_soft.py` | preprocessamento SNV + derivada | dataset processado e metadados | script + artefato |
| E05 | `dados_processados_soft/plots` | `scripts/generate_processed_plots.py` | graficos descritivos do dataset processado | 9 arquivos | script + artefato |
| E06 | `outputs_v2` | `scripts/pipeline_v2_soy_hyper.py` | pipeline v2 completo | validacao, PCA, classificacao, selecao de bandas, PLSR, HVI | script + artefato |
| E07 | `dados_processados_soft/plsr_pca_irrigacao` | `scripts/run_plsr_pca_irrigation.py` | PLSR binario + PCA | 52 arquivos | script + artefato |
| E08 | `dados_processados_soft/plsr_pca_irrigacao` | `scripts/summarize_significant_bands_irrigation.py` | ranking de bandas e regioes significativas | top 20, top 10 por direcao, resumos | script + artefato |
| E09 | `dados_processados_soft/plsr_pca_irrigacao/band_significance` | `scripts/run_band_significance_analysis.py` + `band_significance.py` | significancia multimetodo por banda | ranking, top20, significativas por alpha | script + artefato |
| E10 | `dados_processados_soft/plsr_pca_irrigacao/figuras_band_significance` | `scripts/generate_band_significance_plots.py` | visualizacoes do ranking e regioes | 4 arquivos | script + artefato |
| E11 | `dados_processados_soft/plsr_intervalos_regioes_threshold` | `scripts/run_plsr_by_dominant_regions.py` | PLSR por intervalos dominantes | metricas por intervalo | script + artefato |
| E12 | `dados_processados_soft/plsr_data_genotipo_turno` | `scripts/run_plsr_by_date_genotype_turno.py` + `summarize_top_bands_by_date_genotype_turno.py` | PLSR por data x genotipo x turno | metricas, curvas, recorrencia | script + artefato |
| E13 | `dados_processados_soft/plsr_subconjuntos_irrigacao` | `scripts/run_plsr_optimal_bands_by_subset.py` | PLSR por turno, genotipo e turno x genotipo | 72 arquivos | script + artefato |
| E14 | `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao` | `scripts/tabulate_plsr_pearson_ttest_subsets.py` | fusao PLSR + Pearson + Welch | tabelas por subconjunto | script + artefato |
| E15 | `outputs/pearson_bandas_otimas_turno` | `scripts/compare_optimal_bands_morning_afternoon.py` | Pearson nas bandas otimas entre manha e tarde | CSVs, SVGs e resumos | script + artefato |
| E16 | `dados_processados_soft/*.csv` | `analise_bandas_top5.py`, `analise_bandas_SR_KPCA.py`, `analise_SR_top5_nao_colinear.py` | analises exploratorias hardcoded | 4 CSVs de analise | script + artefato |
| E17 | `estresse_hidrico` | `scripts/00` a `05` | preprocessamento, PERMANOVA, Boruta, temporal, classificacao, figuras | pipeline principal | script + artefato |
| E18 | `estresse_hidrico` | `scripts/06_reducao_bandas_p_teste.py` | Welch + Kruskal + benchmark LDA | reducao de bandas e benchmark | script + artefato |
| E19 | `estresse_hidrico` | `scripts/07_classificacao_subset_bandas.py` | LDA com subset explicito | scores, confusion, predicoes | script + artefato |
| E20 | `estresse_hidrico` | `scripts/08_optuna_classificacao_subset.py` | tuning Optuna | trials, best params, confusion, resumo | script + artefato |
| E21 | `estresse_hidrico` | `scripts/06_assinaturas_espectrais.py`, `09_*`, `10_*` | assinaturas medias e overlays Boruta/Kruskal | figuras e tabelas auxiliares | script + artefato |
| E22 | `outputs_v2/significant_bands_*` | cluster de artefatos | significancia detalhada de subset especifico | threshold summaries, heatmaps, ranges | artefato orfao |
| E23 | `outputs/spectrum_ratio_*` | cluster de artefatos | spectrum ratio por dia/genotipo | 2 CSVs | artefato orfao e nao rastreado no git |

## 4. Familia `outputs_v2`

### 4.1 Escopo, comando e parametros

Pipeline principal:

```powershell
python scripts\pipeline_v2_soy_hyper.py `
  --input base_dados_unificada.xlsx `
  --metadata-csv dados_processados_soft\metadados_normalizados_soft.csv `
  --output-dir outputs_v2
```

Defaults do codigo e parametros efetivos observados:

| parametro | valor |
| --- | --- |
| input | `base_dados_unificada.xlsx` |
| metadata | `dados_processados_soft/metadados_normalizados_soft.csv` |
| output | `outputs_v2` |
| classification_targets | `condition,turno` |
| seed | 42 |
| cv_splits | 5 |
| max_plsr_components | 20 |
| band_selection_candidate_n | 250 |
| hvi_candidate_bands | 80 |
| PLSR executado | sim |
| HVI executado | sim |

Modelos de classificacao no v2:

- `lr`: `LogisticRegression(max_iter=5000, solver='lbfgs', class_weight='balanced', random_state=42)`
- `svm`: `SVC(kernel='rbf', C=3.0, gamma='scale', class_weight='balanced')`
- `knn`: `KNeighborsClassifier(n_neighbors=7, weights='distance')`
- `nb`: `GaussianNB()`
- `dt`: `DecisionTreeClassifier(class_weight='balanced', min_samples_leaf=2, random_state=42)`
- `rf`: `RandomForestClassifier(n_estimators=300, class_weight='balanced_subsample', random_state=42)`
- `gboost`: `GradientBoostingClassifier(random_state=42)`
- `mlp`: `MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, early_stopping=True, random_state=42)`

Tecnicas adicionais no v2:

- PCA com `n_components=5`;
- PLSR binario com `PLSRegression(scale=False)` e busca ate `20` componentes;
- selecao de bandas com ANOVA, mutual information, random forest, logistic/L1, RFE e PLS/VIP;
- busca HVI sobre `80` bandas candidatas.

### 4.2 Validacao estrutural e dimensoes

Arquivos de referencia:

- `outputs_v2/run_manifest_v2.json`
- `outputs_v2/01_validation/validation_report_v2.json`
- `outputs_v2/01_validation/validation_summary_v2.csv`

Resumo:

| metrica | valor |
| --- | --- |
| samples | 1732 |
| bands | 2151 |
| wavelength_min | 350 |
| wavelength_max | 2500 |
| groups | 36 |
| group_size_min | 32 |
| group_size_max | 68 |
| dates | 6 |
| genotypes | 3 |
| conditions | 2 |
| turnos | 2 |

### 4.3 Resultados principais do v2

PCA:

| componente | var explicada | acumulada |
| --- | ---: | ---: |
| PC1 | 0.723128 | 0.723128 |
| PC2 | 0.161277 | 0.884405 |
| PC3 | 0.077039 | 0.961444 |
| PC4 | 0.024136 | 0.985580 |
| PC5 | 0.003875 | 0.989455 |

Classificacao supervisionada: melhores modelos por alvo.

| alvo | melhor modelo | accuracy | balanced_accuracy | f1_macro | roc_auc |
| --- | --- | ---: | ---: | ---: | ---: |
| `condition` | `lr` | 0.899538 | 0.899567 | 0.899527 | 0.975266 |
| `turno` | `lr` | 0.822748 | 0.811031 | 0.804360 | 0.901907 |

Observacoes:

- para `condition`, o top 3 foi `lr > gboost > svm`;
- para `turno`, o top 3 foi `lr > mlp > svm`;
- a tabela completa esta em `outputs_v2/06_classification/classification_metrics_v2.csv`.

PLSR binario do v2:

| melhor n_components | RMSECV | R2CV | AUC | accuracy |
| ---: | ---: | ---: | ---: | ---: |
| 20 | 0.306758 | 0.623596 | 0.967199 | 0.898961 |

Top 10 bandas do ranking combinado (`outputs_v2/07_band_selection/band_ranking_top_100_v2.csv`):

| rank | banda | score | direcao |
| ---: | ---: | ---: | --- |
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

Top 10 pares HVI (`outputs_v2/09_hvi/hvi_pairs_v2.csv`):

| rank | banda A | banda B | score | mean_condition_diff |
| ---: | ---: | ---: | ---: | ---: |
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

### 4.4 Cluster suplementar de artefatos do v2

Artefatos presentes:

- `outputs_v2/significant_bands_2017-02-23_manha_BR16/*`
- `outputs_v2/significant_bands_2017-02-23_manha_BR16_v2/*`
- `outputs_v2/subset_bandas_significativas_2017-02-23_manha_BR16.csv`
- `outputs_v2/heatmaps/*`
- `outputs_v2/plots_ranges/*`

Como o script gerador nao foi localizado no workspace, estes arquivos ficam marcados como `artefato orfao`. Ainda assim, os dados sao objetivos:

Resumo do subset `2017-02-23 | manha | BR16`:

| arquivo | linhas | colunas | nota |
| --- | ---: | ---: | --- |
| `subset_bandas_significativas_2017-02-23_manha_BR16.csv` | 2151 | 7 | estatistica por banda |
| `significant_bands_2017-02-23_manha_BR16/threshold_summary.csv` | 5 | 5 | thresholds `0.05`, `0.01`, `0.001`, `0.0001`, `0.00001` |
| `significant_bands_2017-02-23_manha_BR16_v2/threshold_summary.csv` | 3 | 5 | thresholds `0.05`, `0.001`, `0.0001` |
| `heatmaps/heatmap_top_pairs_selected_thr_1e-04.csv` | 50 | 3 | pares mais correlacionados |
| `plots_ranges/ranges_p001_selected_thr_1e-04.csv` | 93 | 6 | intervalos por direcao |

Threshold summary do subset original:

| threshold | kw_n | pearson_n | spearman_n | union_any_test_n |
| ---: | ---: | ---: | ---: | ---: |
| 0.05000 | 879 | 878 | 879 | 999 |
| 0.01000 | 610 | 614 | 621 | 678 |
| 0.00100 | 400 | 429 | 421 | 454 |
| 0.00010 | 308 | 330 | 332 | 345 |
| 0.00001 | 220 | 253 | 263 | 270 |

## 5. Familia `dados_processados_soft` e experimentos associados

### 5.1 Preprocessamento e diagnosticos descritivos

Script principal:

- `scripts/generate_processed_dataset_for_soft.py`

Parametros:

| parametro | valor |
| --- | --- |
| input | `base_dados_unificada.xlsx` |
| output_dir | `dados_processados_soft` |
| window_length | 11 |
| polyorder | 2 |
| deriv | 1 |
| delta | 1.0 |

Artefatos:

- `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv`
- `dados_processados_soft/metadados_normalizados_soft.csv`
- `dados_processados_soft/resumo_processamento_soft.md`
- `dados_processados_soft/plots/*`
- `outputs/resumo_dataset.md`
- `outputs/estatistica_descritiva.xlsx`
- `outputs/plots/*`

Resultados sinteticos:

- `1732` amostras processadas;
- `2151` comprimentos de onda mantidos no dataset `soft`;
- pipeline `SNV -> Savitzky-Golay -> 1a derivada`;
- `dados_processados_soft/plots` agrega medias, CV e contagens sobre o sinal processado;
- `outputs/plots` e `outputs/estatistica_descritiva*` resumem a base em sinal bruto/normalizado sem produzir nova modelagem.

### 5.2 PLSR + PCA irrigado vs nao_irrigado

Script:

- `scripts/run_plsr_pca_irrigation.py`

Defaults:

| parametro | valor |
| --- | --- |
| processed_csv | `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv` |
| metadata_csv | `dados_processados_soft/metadados_normalizados_soft.csv` |
| output_dir | `dados_processados_soft/plsr_pca_irrigacao` |
| max_components | 15 |
| cv_splits | 5 |

Resultados principais:

| metrica | valor |
| --- | ---: |
| amostras x bandas | `1732 x 2151` |
| classes | `868 irrigado` / `864 nao_irrigado` |
| melhor n_components PLSR | 15 |
| RMSECV | 0.244092 |
| R2CV | 0.761675 |
| AUC | 0.992006 |
| accuracy | 0.961316 |
| PCA PC1 | 46.63% |
| PCA PC2 | 13.98% |

Top bandas por coeficiente positivo:

- `908`, `909`, `1149`, `1148`, `879`, `370`, `1150`, `1205`, `959`, `449`.

Top bandas por coeficiente negativo:

- `458`, `896`, `895`, `395`, `459`, `1725`, `1724`, `457`, `1726`, `2269`.

Top VIP:

- concentracao forte em `2270-2293` e `1661-1666`.

Arquivos-fonte completos:

- `dados_processados_soft/plsr_pca_irrigacao/plsr_cv_metricas.csv`
- `dados_processados_soft/plsr_pca_irrigacao/plsr_bandas_importantes.csv`
- `dados_processados_soft/plsr_pca_irrigacao/plsr_predicoes_ajuste.csv`
- `dados_processados_soft/plsr_pca_irrigacao/pca_scores.csv`
- `dados_processados_soft/plsr_pca_irrigacao/pca_loadings.csv`

### 5.3 Resumos de bandas significativas no bloco irrigacao

Script:

- `scripts/summarize_significant_bands_irrigation.py`

Saidas centrais:

- `top_20_bandas_candidatas_irrigacao.csv`
- `top_10_irrigado_top_10_nao_irrigado.csv`
- `bandas_significativas_q_lt_0_01.csv`
- `bandas_significativas_q_lt_0_05.csv`
- `regioes_espectrais_significativas.csv`
- `regioes_dominantes_por_threshold.csv`

Contagens:

| arquivo | linhas | colunas |
| --- | ---: | ---: |
| `bandas_significativas_q_lt_0_01.csv` | 1928 | 14 |
| `bandas_significativas_q_lt_0_05.csv` | 1986 | 9 |
| `regioes_espectrais_significativas.csv` | 37 | 9 |
| `regioes_dominantes_por_threshold.csv` | 50 | 5 |
| `top_20_bandas_candidatas_irrigacao.csv` | 20 | 12 |
| `top_10_irrigado_top_10_nao_irrigado.csv` | 20 | 7 |

Principais regioes significativas:

| rank | faixa | bandas | pico | direcao dominante |
| ---: | --- | ---: | ---: | --- |
| 1 | 1910-1944 | 35 | 1924 | nao_irrigado |
| 2 | 2258-2283 | 26 | 2279 | nao_irrigado |
| 3 | 1380-1472 | 93 | 1427 | nao_irrigado |
| 4 | 422-501 | 80 | 486 | nao_irrigado |
| 5 | 1476-1673 | 198 | 1660 | irrigado |

Top 5 bandas candidatas:

| rank | banda | direcao | score combinado |
| ---: | ---: | --- | ---: |
| 1 | 1924 | nao_irrigado | 8.032796 |
| 2 | 1923 | nao_irrigado | 7.969197 |
| 3 | 2279 | nao_irrigado | 7.943298 |
| 4 | 2280 | nao_irrigado | 7.917611 |
| 5 | 1427 | nao_irrigado | 7.888721 |

### 5.4 Analise `band_significance`

Scripts:

- `scripts/run_band_significance_analysis.py`
- biblioteca `band_significance.py`
- testes em `tests/test_band_significance.py`

Parametros:

| parametro | valor |
| --- | --- |
| alpha | 0.05 |
| p_adjust_method | `fdr_bh` |
| target_type efetivo | `binary` |

Definicao do ranking:

- `effect_score`: media robusta dos efeitos disponiveis;
- `significance_score`: media robusta de `-log10(p ajustado)`;
- `consistency_score`: concordancia de sinal entre metricas assinadas;
- `ranking_score = 0.45 * effect_score + 0.45 * significance_score + 0.10 * consistency_score`.

Resultados:

| metrica | valor |
| --- | ---: |
| bandas analisadas | 2151 |
| bandas significativas em `alpha=0.05` | 2018 |
| top 5 bandas | 1924, 1925, 1923, 1926, 487 |

Top 10 do ranking (`dados_processados_soft/plsr_pca_irrigacao/band_significance/band_significance_top20.csv`):

| rank | banda | direcao | ranking_score | fonte do menor p ajustado |
| ---: | ---: | --- | ---: | --- |
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

### 5.5 PLSR por intervalos de regioes dominantes

Script:

- `scripts/run_plsr_by_dominant_regions.py`

Parametros:

| parametro | valor |
| --- | --- |
| max_components | 15 |
| cv_splits | 5 |
| intervalos avaliados | 50 |

Melhor intervalo:

| criterio | intervalo | threshold | faixa | comp. | AUC | RMSECV | R2CV | accuracy |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| melhor AUC e melhor RMSECV | `thr_1em05_rank_05_1310_1470` | `1e-05` | `1310-1470 nm` | 15 | 0.949843 | 0.310991 | 0.613137 | 0.884527 |

Os cinco melhores por threshold foram todos variantes da faixa `1279-1472 nm` ou `1310-1470 nm`.

### 5.6 PLSR por data x genotipo x turno

Script:

- `scripts/run_plsr_by_date_genotype_turno.py`

Parametros:

| parametro | valor |
| --- | --- |
| max_components | 15 |
| cv_splits | 5 |
| top_k | 5 |
| subconjuntos avaliados | 27 |

Resumo:

| destaque | subconjunto | R2CV | RMSECV | AUC | accuracy |
| --- | --- | ---: | ---: | ---: | ---: |
| melhor R2CV | `2017-02-27 | BR16 | manha` | 0.997001 | 0.027380 | 1.000000 | 1.000000 |
| pior R2CV | `2017-03-02 | BR16 | tarde` | 0.854953 | 0.190425 | 1.000000 | 0.984375 |

Padrao geral:

- todos os 27 subconjuntos tiveram `AUC = 1.0`;
- a accuracy foi `1.0` na maioria dos subconjuntos;
- a pior accuracy encontrada ainda foi `0.984375`.

Arquivos-fonte:

- `dados_processados_soft/plsr_data_genotipo_turno/metricas_plsr_data_genotipo_turno.csv`
- `dados_processados_soft/plsr_data_genotipo_turno/top_bandas_plsr_data_genotipo_turno.csv`
- `dados_processados_soft/plsr_data_genotipo_turno/curvas_componentes_plsr_data_genotipo_turno.csv`
- `dados_processados_soft/plsr_data_genotipo_turno/recorrencia_top_bandas_global.csv`
- `dados_processados_soft/plsr_data_genotipo_turno/recorrencia_top_bandas_por_direcao.csv`

### 5.7 PLSR por subconjuntos de turno e genotipo

Script:

- `scripts/run_plsr_optimal_bands_by_subset.py`

Defaults:

| parametro | valor |
| --- | --- |
| max_components | 15 |
| cv_splits | 5 |
| top_k | 20 |
| score de banda otima | `z(VIP) + z(|coeficiente PLSR|)` |

Resumo dos 11 subconjuntos:

- melhor accuracy: `manha / BR16 = 1.000000`;
- melhor AUC: `1.000000` em `manha / BR16`;
- pior accuracy: `Turno tarde = 0.939236`;
- faixas otimas alternaram entre UV/visivel curto (`392`, `383`) e SWIR (`2270-2281`, `1661-1668`, `2149`).

Arquivos-fonte:

- `dados_processados_soft/plsr_subconjuntos_irrigacao/metricas_subconjuntos_plsr.csv`
- `dados_processados_soft/plsr_subconjuntos_irrigacao/top_bandas_otimas_subconjuntos_plsr.csv`
- diretorios por subconjunto em `genotipo/*`, `turno/*` e `turno_genotipo/*`

### 5.8 Tabelas PLSR + Pearson + Welch

Script:

- `scripts/tabulate_plsr_pearson_ttest_subsets.py`

Defaults:

| parametro | valor |
| --- | --- |
| max_components | 15 |
| cv_splits | 5 |
| top_k | 20 |
| regra Welch | `p < 0.005` |
| Pearson binario | `irrigado = 1`, `nao_irrigado = 0` |

Saidas:

- `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao/top_bandas_plsr_pearson_ttest.csv`
- `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao/bandas_plsr_pearson_ttest_completo.csv`
- `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao/resumo_top_bandas_plsr_pearson_ttest.md`

Resumo dos destaques:

- `Data 23/02/2017`: banda `392` no topo;
- `Data 24/02/2017`: banda `2281` no topo;
- `Data 02/03/2017`: banda `2295` no topo;
- `Turno manha`: banda `392` no topo;
- `Turno tarde`: banda `2281` no topo;
- `Genotipo BR16`: banda `2270` no topo;
- `Genotipo CD202`: banda `2280` no topo;
- `Genotipo EMB48`: banda `1661` no topo;
- `manha / CD202`: banda `2149` no topo;
- `manha / EMB48`: banda `383` no topo.

### 5.9 Reflectancia bruta e comparacoes manha vs tarde nas bandas otimas

Scripts:

- `scripts/generate_raw_reflectance_genotype_plots.py`
- `scripts/compare_optimal_bands_morning_afternoon.py`
- `gerar_graficos_reflectancia.py`

Analise de Pearson nas bandas otimas (`20` bandas):

| data | n manha | n tarde | Pearson r | MAD | RMSE | maior diferenca |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 23/02/2017 | 192 | 192 | 0.999985 | 0.014199 | 0.014655 | banda 1652 |
| 24/02/2017 | 192 | 192 | 0.999708 | 0.004589 | 0.004738 | banda 2280 |
| 02/03/2017 | 196 | 192 | 0.999342 | 0.008431 | 0.008513 | banda 1425 |

Por genotipo, o mesmo padrao se manteve com `r` entre `0.998983` e `0.999984`.

### 5.10 Analises exploratorias hardcoded

Scripts:

- `analise_bandas_top5.py`
- `analise_bandas_SR_KPCA.py`
- `analise_SR_top5_nao_colinear.py`

Estas rotinas usam caminhos hardcoded para os CSVs processados e produziram:

| arquivo | linhas | colunas | observacao |
| --- | ---: | ---: | --- |
| `dados_processados_soft/analise_bandas_top5.csv` | 54 | 13 | grade condensada por `genotipo x condicao x turno x dia` |
| `dados_processados_soft/analise_bandas_top5_completo.csv` | 216 | 10 | grade expandida de subconjuntos |
| `dados_processados_soft/analise_bandas_SR_KPCA.csv` | 104 | 7 | PCA, KPCA-RBF, KPCA-POLY e SR |
| `dados_processados_soft/analise_SR_top5_nao_colinear.csv` | 23 | 8 | top 5 SR nao colineares por comparacao |

Padroes observados:

- `analise_bandas_top5*`: recorrencia forte de bandas em torno de `354`, `698-701`, `1910-1914`, `725-728` e `1362-1366`, dependendo do recorte;
- `analise_bandas_SR_KPCA.csv`: KPCA-RBF e KPCA-POLY priorizaram repetidamente `350-352 nm`;
- `analise_SR_top5_nao_colinear.csv`: para `irrigado_vs_nao_irrigado`, o top 5 global foi `1884, 1894, 1874, 731, 569`; para `manha_vs_tarde`, `1883, 358, 1000, 375, 1873`.

## 6. Familia `estresse_hidrico`

### 6.1 Pipeline principal `00` a `05`

Execucao documentada no README:

```powershell
& ..\.venv311_estresse\Scripts\python.exe .\scripts\00_preprocessamento.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\01_permanova.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\02_boruta_por_dia.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\03_graficos_temporais.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\04_classificacao.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\05_figuras_finais.py
```

Ambiente e dependencias registradas:

- Python `3.11`;
- `numpy`, `pandas`, `scipy`, `scikit-learn`, `scikit-bio`, `Boruta`, `xgboost`, `matplotlib`, `seaborn`, `statsmodels`, `joblib`, `openpyxl`.

### 6.2 PERMANOVA e PERMDISP

Script:

- `estresse_hidrico/scripts/01_permanova.py`

Arquivo-fonte completo:

- `estresse_hidrico/outputs/tabelas/resultados_permanova.csv`
- `estresse_hidrico/outputs/tabelas/resultados_permdisp.csv`

Tabela consolidada:

| cultivar | condicao | comparacao | metrica | F | p | q | R2 | significativo |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| EMB48 | IRR | Manha vs Tarde | euclidean | 8.632339 | 0.005 | 0.012000 | 0.281805 | Sim |
| EMB48 | NIRR | Manha vs Tarde | euclidean | 0.300935 | 0.707 | 0.707000 | 0.013494 | Nao |
| BR16 | IRR | Manha vs Tarde | euclidean | 4.509718 | 0.029 | 0.046400 | 0.170116 | Sim |
| BR16 | NIRR | Manha vs Tarde | braycurtis | 0.569913 | 0.511 | 0.584000 | 0.025251 | Nao |
| CD202 | IRR | Manha vs Tarde | euclidean | 6.923610 | 0.006 | 0.012000 | 0.239376 | Sim |
| CD202 | NIRR | Manha vs Tarde | euclidean | 1.289787 | 0.245 | 0.326667 | 0.055380 | Nao |
| Todos | IRR vs NIRR | Manha | braycurtis | 65.740998 | 0.001 | 0.004000 | 0.484312 | Sim |
| Todos | IRR vs NIRR | Tarde | braycurtis | 14.029938 | 0.001 | 0.004000 | 0.166964 | Sim |

PERMDISP:

- todos os `8` contrastes passaram em homogeneidade de dispersao (`homogeneidade_ok = Sim`).

### 6.3 Boruta por dia

Script:

- `estresse_hidrico/scripts/02_boruta_por_dia.py`

Hiperparametros:

| componente | valor |
| --- | --- |
| estimador base | `RandomForestClassifier` |
| `n_estimators` RF | 500 |
| `class_weight` | `balanced_subsample` |
| `random_state` | 42 |
| `n_estimators` Boruta | `auto` |
| `alpha` Boruta | 0.05 |
| `max_iter` Boruta | 100 |

Resumo por dia:

| dia | confirmadas | tentativas | rejeitadas |
| --- | ---: | ---: | ---: |
| dia2 | 1 | 5 | 1893 |
| dia3 | 52 | 57 | 1790 |
| dia4 | 93 | 17 | 1789 |
| dia5 | 0 | 177 | 1722 |
| dia6 | 2 | 124 | 1773 |
| dia9 | 110 | 45 | 1744 |

Bandas confirmadas mais recorrentes:

- `356 nm` e `362 nm` em `4` dias;
- `352-355`, `357-359`, `361`, `363`, `366-399` e `422 nm` em `3` dias.

### 6.4 Series temporais e painel de desvio do quociente

Scripts:

- `estresse_hidrico/scripts/03_graficos_temporais.py`
- `estresse_hidrico/scripts/05_figuras_finais.py`

Artefatos centrais:

- `estresse_hidrico/outputs/tabelas/series_temporais_resumo.csv`
- `estresse_hidrico/outputs/tabelas/desvio_quociente_por_dia.csv`
- `estresse_hidrico/outputs/tabelas/desvio_quociente_picos_por_dia.csv`
- `estresse_hidrico/outputs/tabelas/bandas_temporais_selecionadas.csv`
- `estresse_hidrico/outputs/figuras/temporal_*.png`
- `estresse_hidrico/outputs/figuras/desvio_quociente_*.png`

Resumo:

- `70` bandas foram selecionadas para series temporais;
- faixa temporal selecionada: `350-439 nm`;
- `series_temporais_resumo.csv` tem `912` linhas e `8` colunas;
- os picos finais do painel de desvio ficaram em `569-703 nm`, nao em coincidencia pontual com Boruta.

Picos finais do quociente `NIRR/IRR`:

| dia | pico 1 | pico 2 |
| --- | --- | --- |
| dia2 | 700 nm | 569 nm |
| dia3 | 595 nm | 696 nm |
| dia4 | 569 nm | 700 nm |
| dia5 | 580 nm | 697 nm |
| dia6 | 703 nm | 557 nm |
| dia9 | 703 nm | - |

### 6.5 Classificacao 6 classes do pipeline principal

Script:

- `estresse_hidrico/scripts/04_classificacao.py`

Features e validacao:

| item | valor |
| --- | --- |
| bandas de entrada | uniao das bandas confirmadas pelo Boruta |
| indices fixos | `NDVI`, `EVI`, `WBI`, `PRI`, `SIPI`, `REP` |
| total de features | 154 |
| CV | `StratifiedGroupKFold` |
| grupos de CV | bloco biologico |
| folds efetivos | 4 |

Modelos e hiperparametros:

- `Random Forest`: `n_estimators=750`, `class_weight='balanced_subsample'`, `random_state=42`
- `SVM (RBF)`: `class_weight='balanced'`
- `LDA`: `solver='lsqr'`, `shrinkage='auto'`
- `k-NN`: `n_neighbors=5`, `metric='euclidean'`
- `XGBoost`: `n_estimators=400`, `max_depth=4`, `learning_rate=0.05`, `subsample=0.9`, `colsample_bytree=0.9`, `reg_lambda=1.0`

Desempenho:

| modelo | accuracy_media | f1_macro_media | kappa_media |
| --- | ---: | ---: | ---: |
| LDA | 0.625000 | 0.612368 | 0.550000 |
| XGBoost | 0.590278 | 0.569552 | 0.508333 |
| Random Forest | 0.506944 | 0.486796 | 0.408333 |
| SVM (RBF) | 0.493056 | 0.470084 | 0.391667 |
| k-NN (k=5) | 0.458333 | 0.434706 | 0.350000 |

Escores por classe do melhor modelo (`LDA`):

| classe | precisao | recall | f1 | suporte |
| --- | ---: | ---: | ---: | ---: |
| A (EMB48 IRR) | 0.653846 | 0.708333 | 0.680000 | 24 |
| B (EMB48 NIRR) | 0.666667 | 0.666667 | 0.666667 | 24 |
| C (BR16 IRR) | 0.739130 | 0.708333 | 0.723404 | 24 |
| D (BR16 NIRR) | 0.615385 | 0.666667 | 0.640000 | 24 |
| E (CD202 IRR) | 0.666667 | 0.416667 | 0.512821 | 24 |
| F (CD202 NIRR) | 0.466667 | 0.583333 | 0.518519 | 24 |

Top 10 importancias do Random Forest:

| rank | feature | importancia |
| ---: | --- | ---: |
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

### 6.6 Reducao de bandas por p-teste

Script:

- `estresse_hidrico/scripts/06_reducao_bandas_p_teste.py`

Metodo:

- Welch t-test para `IRR vs NIRR`;
- Kruskal-Wallis para classes `A-F`;
- correcao `BH`;
- benchmark via `LDA(solver='lsqr', shrinkage='auto')`.

Resultados centrais:

| metrica | valor |
| --- | --- |
| bandas testadas | 148 |
| `q < 0.05` Welch | 148 |
| `q < 0.01` Welch | 148 |
| `q < 0.05` Kruskal | 148 |
| `q < 0.01` Kruskal | 148 |

Top 10 Welch t-test:

- `721-730 nm`, com destaque maximo em `727 nm` (`|d| = 2.3492`).

Top 10 Kruskal-Wallis:

- concentracao em `361-391 nm`, com pico em `381 nm` (`H = 102.6561`, `eta2(H) = 0.7077`).

Benchmark LDA:

- subconjuntos que mantiveram todas as `148` bandas reproduziram exatamente o baseline (`accuracy=0.6250`, `f1_macro=0.6124`, `kappa=0.5500`);
- melhor subconjunto reduzido: `joint_top_30` com `accuracy=0.6042`;
- `kruskal_top_20` tambem atingiu `accuracy=0.6042`;
- `indices_only` caiu para `accuracy=0.5208`.

Arquivo-fonte:

- `estresse_hidrico/outputs/tabelas/reducao_bandas_p_teste/lda_benchmark_reduced_band_subsets.csv`

### 6.7 Classificacao com subset explicito e Optuna

Scripts:

- `estresse_hidrico/scripts/07_classificacao_subset_bandas.py`
- `estresse_hidrico/scripts/08_optuna_classificacao_subset.py`

Subset base analisado:

- `kruskal_top_20`
- `20` bandas espectrais + `6` indices = `26` features totais

Resultado sem tuning (`07_*`):

| subset | accuracy_media | f1_macro_media | kappa_media |
| --- | ---: | ---: | ---: |
| `kruskal_top_20` | 0.604167 | 0.586368 | 0.525000 |

Optuna (`08_*`):

| metrica | valor |
| --- | --- |
| sampler | `TPESampler(seed=42)` |
| trials | 80 |
| melhor modelo | `LDA` |
| melhor solver | `eigen` |
| shrinkage mode | `float` |
| shrinkage | 0.008407038530137188 |
| objective | 0.628106 |
| accuracy_media | 0.638889 |
| f1_macro_media | 0.627411 |
| kappa_media | 0.566667 |

Ganho do Optuna sobre o subset LDA fixo:

- accuracy: `+0.034722`
- f1_macro: `+0.041043`
- kappa: `+0.041667`

Resumo por dia do melhor subset com tuning:

| dia | accuracy_media | f1_macro_media | kappa_media |
| --- | ---: | ---: | ---: |
| dia2 | 0.416667 | 0.308333 | 0.300000 |
| dia3 | 0.541667 | 0.472222 | 0.450000 |
| dia4 | 0.500000 | 0.416667 | 0.400000 |
| dia5 | 0.416667 | 0.277778 | 0.300000 |
| dia6 | 0.500000 | 0.444444 | 0.400000 |
| dia9 | 0.375000 | 0.305556 | 0.250000 |

### 6.8 Assinaturas espectrais e overlays Boruta/Kruskal

Scripts:

- `estresse_hidrico/scripts/06_assinaturas_espectrais.py`
- `estresse_hidrico/scripts/09_plot_boruta_kruskal_assinatura_media.py`
- `estresse_hidrico/scripts/10_plot_boruta_kruskal_por_dia.py`

Artefatos:

| arquivo | linhas | colunas | funcao |
| --- | ---: | ---: | --- |
| `assinatura_espectral_irr_vs_nirr_media.csv` | 4302 | 6 | media global IRR vs NIRR |
| `assinatura_espectral_irr_vs_nirr_por_dia.csv` | 25812 | 7 | media por dia |
| `boruta_kruskal_por_dia/resumo_boruta_kruskal_por_dia.csv` | 6 | 5 | comparacao de ranges por dia |
| `boruta_kruskal_por_dia/kruskal_top20_por_dia.csv` | 120 | 11 | top 20 por dia |

Resumo da sobreposicao Boruta/Kruskal por dia:

| dia | bandas Boruta | ranges Boruta | top 20 Kruskal |
| --- | ---: | --- | --- |
| dia2 | 1 | 2444 | 1544-1549; 1552-1565 |
| dia3 | 52 | 350-400; 422 | 350-369 |
| dia4 | 93 | 350-415; 422-431; 437-439; 717-730 | 350-369 |
| dia5 | 0 | - | 359; 362-380 |
| dia6 | 2 | 356; 362 | 350-369 |
| dia9 | 110 | 352-498 com blocos recorrentes | 352-363; 366-373 |

## 7. Familia `outputs`

### 7.1 Estatistica descritiva da base

Saidas principais:

- `outputs/estatistica_descritiva.xlsx`
- `outputs/estatistica_descritiva_media.csv`
- `outputs/estatistica_descritiva_coeficiente_variacao.csv`
- `outputs/amostras_por_grupo.csv`

Esses artefatos resumem a base antes das modelagens mais pesadas e servem de suporte para os graficos em `outputs/plots`.

### 7.2 Reflectancia bruta por genotipo

Resumo do cluster `outputs/reflectancia_bruta_genotipos`:

- sinal usado: reflectancia bruta da planilha original;
- figuras separadas por `irrigado` e `nao_irrigado`;
- paineis por dia e por dia x turno;
- tabelas para medias, CV e contagens por `data x genotipo x condicao` e `data x turno x genotipo x condicao`.

### 7.3 Artefatos `spectrum_ratio_*` nao rastreados no git

Arquivos:

- `outputs/spectrum_ratio_por_dia_genotipo_condicao.csv`
- `outputs/spectrum_ratio_por_dia_genotipo_turno_condicao.csv`

Status:

- aparecem como nao rastreados no `git status`;
- nenhuma referencia textual ao nome desses arquivos foi encontrada no workspace;
- portanto, permanecem como `artefatos orfaos recentes`.

Mesmo assim, os dados sao legiveis:

| arquivo | linhas | colunas | recorte |
| --- | ---: | ---: | --- |
| `spectrum_ratio_por_dia_genotipo_condicao.csv` | 18 | 9 | `dia x genotipo` |
| `spectrum_ratio_por_dia_genotipo_turno_condicao.csv` | 27 | 10 | `dia x genotipo x turno` |

Padrao observado:

- grande recorrencia do topo em `1880-1884`, `1870-1874`, `1890-1894`, `1392-1403`, `356-381`, `567`, `729-731`;
- exemplo: `2017-02-24 / EMB48` teve top1 em `1884 nm` com desvio `20.294`.

## 8. Matriz de parametros e hiperparametros por script

Esta secao registra apenas os parametros principais e os hiperparametros que mudam comportamento.

| script | parametros/defaults principais | hiperparametros/modelos principais |
| --- | --- | --- |
| `scripts/generate_descriptive_stats.py` | `input=base_dados_unificada.xlsx`, `output=outputs` | estatistica descritiva por grupo |
| `scripts/generate_processed_dataset_for_soft.py` | `window=11`, `polyorder=2`, `deriv=1`, `delta=1.0` | SNV + Savitzky-Golay + 1a derivada |
| `scripts/generate_processed_plots.py` | `processed_csv`, `metadata_csv`, `output=dados_processados_soft/plots` | medias e CV do sinal processado |
| `scripts/generate_raw_reflectance_genotype_plots.py` | `input=base_dados_unificada.xlsx`, `output=outputs/reflectancia_bruta_genotipos` | medias e CV do sinal bruto |
| `scripts/pipeline_v2_soy_hyper.py` | `seed=42`, `cv=5`, `max_plsr=20`, `band_selection_candidate_n=250`, `hvi_candidate_bands=80` | LR balanceado, SVM RBF `C=3`, kNN `7/dist`, RF `300`, MLP `(64,32)`, RFE, MI, PLS/VIP, HVI |
| `scripts/run_plsr_pca_irrigation.py` | `max_components=15`, `cv=5` | `PLSRegression(scale=False)`, `PCA(n_components=2)` |
| `scripts/run_band_significance_analysis.py` | `alpha=0.05`, `p_adjust_method=fdr_bh` | Welch, Kruskal, Pearson, Spearman, ranking robusto |
| `scripts/run_plsr_by_dominant_regions.py` | `max_components=15`, `cv=5` | PLSR por intervalo |
| `scripts/run_plsr_by_date_genotype_turno.py` | `max_components=15`, `cv=5`, `top_k=5` | PLSR por subconjunto |
| `scripts/run_plsr_optimal_bands_by_subset.py` | `max_components=15`, `cv=5`, `top_k=20` | score `z(VIP)+z(|coef|)` |
| `scripts/tabulate_plsr_pearson_ttest_subsets.py` | `max_components=15`, `cv=5`, `top_k=20` | Pearson + Welch `p<0.005` sobre ranking PLSR |
| `scripts/compare_optimal_bands_morning_afternoon.py` | `dates=2017-02-23,2017-02-24,2017-03-02` | Pearson, MAD, RMSE nas bandas otimas |
| `analise_bandas_top5.py` | caminhos hardcoded | PCA, PLS, RF `100`, MI `n_neighbors=5`, Kruskal, MWU, Spearman |
| `analise_bandas_SR_KPCA.py` | caminhos hardcoded | PCA, KPCA `rbf` e `poly`, Spectrum Ratio |
| `analise_SR_top5_nao_colinear.py` | caminhos hardcoded | Spectrum Ratio com `min_gap=10 nm` |
| `estresse_hidrico/scripts/02_boruta_por_dia.py` | input replicatas por dia | RF `500`, Boruta `alpha=0.05`, `max_iter=100`, seed `42` |
| `estresse_hidrico/scripts/04_classificacao.py` | input replicatas dia + Boruta | LDA `lsqr/auto`, RF `750`, XGBoost `400/depth4/lr0.05`, SVM RBF, kNN `5` |
| `estresse_hidrico/scripts/06_reducao_bandas_p_teste.py` | input replicatas dia, features manifest | Welch + Kruskal + BH + benchmark LDA |
| `estresse_hidrico/scripts/07_classificacao_subset_bandas.py` | subset obrigatorio | LDA `lsqr/auto` |
| `estresse_hidrico/scripts/08_optuna_classificacao_subset.py` | `n_trials=80`, `seed=42`, subset obrigatorio | Optuna sobre LDA, SVM, RF e KNN |
| `estresse_hidrico/scripts/09_plot_boruta_kruskal_assinatura_media.py` | usa `kruskal_top_20.csv` | overlay global Boruta vs Kruskal |
| `estresse_hidrico/scripts/10_plot_boruta_kruskal_por_dia.py` | `top_k_kruskal=20` | overlay por dia |

## 9. Catalogo de tabelas grandes e arquivos-fonte

Esta secao registra onde estao os dados completos que nao foram transcritos integralmente no corpo.

| arquivo | linhas | colunas | papel no projeto |
| --- | ---: | ---: | --- |
| `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv` | 1732 | 2157 | dataset processado principal |
| `dados_processados_soft/metadados_normalizados_soft.csv` | 1732 | 8 | metadados alinhados |
| `outputs_v2/09_hvi/hvi_pairs_v2.csv` | 3160 | 4 | pares HVI candidatos |
| `outputs_v2/subset_bandas_significativas_2017-02-23_manha_BR16.csv` | 2151 | 7 | subset orfao de significancia |
| `dados_processados_soft/plsr_pca_irrigacao/kruskal_pearson_spearman_irrigacao.csv` | 2151 | 8 | ranking estatistico bruto por banda |
| `dados_processados_soft/plsr_pca_irrigacao/plsr_bandas_importantes.csv` | 2151 | 5 | VIP e coeficientes PLSR por banda |
| `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao/top_bandas_plsr_pearson_ttest.csv` | 280 | 23 | top bandas por subconjunto |
| `estresse_hidrico/dados/processados/replicatas_bloco_dia.csv` | 144 | 1917 | base biologica da classificacao 6x6 |
| `estresse_hidrico/outputs/tabelas/lambdas_boruta_por_dia.csv` | 11394 | 5 | Boruta completo por dia |
| `estresse_hidrico/outputs/tabelas/features_classificacao.csv` | 154 | 4 | manifesto de features do classificador |
| `estresse_hidrico/outputs/tabelas/predicoes_classificacao_cv.csv` | 144 | 10 | predicoes CV do classificador principal |
| `estresse_hidrico/outputs/tabelas/optuna_classificacao_subset/optuna_trials_kruskal_top_20.csv` | 80 | 25 | historico de trials Optuna |
| `estresse_hidrico/outputs/tabelas/assinatura_espectral_irr_vs_nirr_media.csv` | 4302 | 6 | assinatura media global |
| `estresse_hidrico/outputs/tabelas/assinatura_espectral_irr_vs_nirr_por_dia.csv` | 25812 | 7 | assinatura media por dia |
| `estresse_hidrico/outputs/tabelas/series_temporais_resumo.csv` | 912 | 8 | medias/DP por feature e dia |
| `outputs/spectrum_ratio_por_dia_genotipo_condicao.csv` | 18 | 9 | artefato orfao por dia/genotipo |
| `outputs/spectrum_ratio_por_dia_genotipo_turno_condicao.csv` | 27 | 10 | artefato orfao por dia/genotipo/turno |

Arquivos `XLSX` relevantes nao expandidos aqui:

- `outputs/estatistica_descritiva.xlsx`
- `estresse_hidrico/outputs/tabelas/preprocessamento_resumo.xlsx`
- `estresse_hidrico/outputs/tabelas/resultados_permanova.xlsx`
- `estresse_hidrico/outputs/tabelas/resultados_boruta.xlsx`
- `estresse_hidrico/outputs/tabelas/resultados_temporais.xlsx`
- `estresse_hidrico/outputs/tabelas/resultados_classificacao.xlsx`
- `estresse_hidrico/outputs/tabelas/sintese_final.xlsx`

## 10. Limitacoes, lacunas e nivel de confianca

### 10.1 Limitacoes reais do dataset

- ausencia de uma coleta separada de `recuperacao`;
- desbalanceamento tecnico localizado em `2017-03-02 / manha / CD202 / IRR / B1`;
- divergencias entre o plano teorico e a estrutura real da planilha;
- diferentes pipelines usam diferentes representacoes do sinal:
  - `soft`: `SNV + Savitzky-Golay + 1a derivada`;
  - `estresse_hidrico`: sinal suavizado com remocao de bandas atmosfericas;
  - `outputs/reflectancia_bruta_genotipos` e `pearson_bandas_otimas_turno`: reflectancia bruta.

### 10.2 Artefatos com rastreabilidade parcial

- `outputs_v2/significant_bands_2017-02-23_manha_BR16*`, `outputs_v2/heatmaps/*`, `outputs_v2/plots_ranges/*`:
  - artefatos presentes;
  - contexto experimental inferivel;
  - script gerador nao localizado.

- `outputs/spectrum_ratio_por_dia_genotipo_condicao.csv` e `outputs/spectrum_ratio_por_dia_genotipo_turno_condicao.csv`:
  - artefatos presentes;
  - nao rastreados no git;
  - sem referencia textual encontrada no workspace.

### 10.3 Nivel de confianca do relatorio

- **alto** para metricas que vieram de `CSV`, `JSON`, `XLSX` e relatorios ja exportados;
- **medio** para parametros inferidos diretamente de defaults do codigo, quando o artefato nao traz o valor explicitamente;
- **medio-baixo** para a genealogia de artefatos orfaos, embora seus conteudos tenham sido lidos e resumidos corretamente.

## 11. Fechamento

O repositorio contem, de forma rastreavel, quatro familias principais de trabalho:

1. um pipeline `v2` reprodutivel com validacao, classificacao, selecao de bandas, PLSR e HVI;
2. um conjunto grande de experimentos `soft` focado em PLSR, PCA, significancia de bandas, subconjuntos e comparacoes manha/tarde;
3. um pipeline dedicado de `estresse_hidrico` com preprocessamento biologico, PERMANOVA, Boruta, temporalidade, classificacao 6x6 e refinamentos posteriores;
4. um conjunto menor de relatorios descritivos, graficos de reflectancia bruta e analises exploratorias hardcoded.

Em termos de desempenho e achados principais:

- no `outputs_v2`, `lr` foi o melhor classificador tanto para `condition` quanto para `turno`;
- no bloco `soft`, o PLSR `irrigado vs nao_irrigado` foi muito forte (`AUC=0.992006`), com regioes dominantes em `1910-1944`, `2258-2283`, `1380-1472`, `422-501` e `1476-1673`;
- no `estresse_hidrico`, o melhor modelo principal foi `LDA` (`accuracy=0.6250`), e o tuning Optuna sobre `kruskal_top_20` elevou esse subset para `0.638889`;
- as bandas em torno de `350-439 nm`, `717-730 nm`, `1425-1430 nm`, `1660-1669 nm`, `1880-1894 nm`, `1923-1926 nm` e `2270-2281 nm` aparecem repetidamente como discriminativas, embora cada pipeline tenha enfases diferentes.

Este arquivo, junto com os caminhos de origem apontados em cada secao, e a referencia consolidada para redacao tecnica, auditoria do projeto e reaproveitamento dos resultados.
