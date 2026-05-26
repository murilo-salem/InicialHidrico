# Relatorio Completo - Reducao de Dimensionalidade para Selecao de Bandas

Data de consolidacao: 2026-05-22
Projeto: AgroSATHidrico

## 1) Objetivo e escopo

Este relatorio consolida **todos os metodos de reducao de dimensionalidade e selecao de bandas usados no projeto**, incluindo:

- metodos com **artefatos executados** (resultados salvos);
- metodos **implementados no codigo** (mesmo quando sem evidencias finais de execucao consolidada em um unico resumo).

Foco principal de comparacao de desempenho: **F1-macro**.

---

## 2) Inventario completo dos metodos usados

### 2.1 Metodos estatisticos univariados

- Welch t-test (IRR vs NIRR) com correcao FDR-BH.
- Kruskal-Wallis (classes A-F) com correcao FDR-BH.
- Intersecoes por limiar de q-value.
- Rankings Top-N por Welch, Kruskal e ranking conjunto (soma de ranks).

Fontes:
- `estresse_hidrico/scripts/06_reducao_bandas_p_teste.py`
- `estresse_hidrico/outputs/tabelas/reducao_bandas_p_teste/*`

### 2.2 Metodos baseados em importancia de modelo

- Random Forest importance (Gini).
- L1 Logistic (coeficientes esparsos).
- RFE (Recursive Feature Elimination).
- PLS/VIP (Variable Importance in Projection).
- Permutation importance (bloco de importancia de bandas significativas).

Fontes:
- `scripts/pipeline_v2_soy_hyper.py`
- `estresse_hidrico/scripts/26_importancia_bandas_significativas.py`
- `estresse_hidrico/outputs/tabelas/importancia_bandas_significativas_*`
- `outputs_v2/07_band_selection/*`

### 2.3 Metodos multivariados de projecao

- PCA (exploratorio e interpretacao por loadings/scores).
- KPCA (RBF e POLY) em analises exploratorias.
- PLSR (global, por intervalos, por subconjuntos e por data x genotipo x turno).

Fontes:
- `scripts/run_plsr_pca_irrigation.py`
- `scripts/run_plsr_by_dominant_regions.py`
- `scripts/run_plsr_by_date_genotype_turno.py`
- `scripts/run_plsr_optimal_bands_by_subset.py`
- `analise_bandas_SR_KPCA.py`
- `dados_processados_soft/plsr_*`

### 2.4 Metodos por relevancia combinada e recorrencia

- Score combinado em PLSR: `z(VIP) + z(|coef|)`.
- Score combinado em significancia: `z(VIP) + z(|d|) + z(-log10(q))`.
- Top-5 por recorrencia de bandas por alvo (`cond`, `gen_cond`).

Fontes:
- `scripts/summarize_significant_bands_irrigation.py`
- `scripts/tabulate_plsr_pearson_ttest_subsets.py`
- `estresse_hidrico/outputs/tabelas/classificacao_significancia_global/*`

### 2.5 Metodos por diversidade e baixa redundancia

- Clustering por correlacao absoluta (thresholds 0.95, 0.90, 0.85).
- Politicas de escolha de bandas por cluster (`hard` e `soft`).
- Benchmark de tradeoff desempenho x redundancia.

Fontes:
- `estresse_hidrico/scripts/11_benchmark_bandas_diversificadas.py`
- `estresse_hidrico/outputs/tabelas/diversificacao_bandas_correlacao/*`

### 2.6 Metodos evolutivos/heuristicos auxiliares

- Busca de pares HVI em bandas candidatas (pipeline v2).
- Spectrum Ratio (SR) e SR Top-5 nao colinear (analise exploratoria).

Fontes:
- `scripts/pipeline_v2_soy_hyper.py`
- `analise_SR_top5_nao_colinear.py`
- `dados_processados_soft/analise_SR_top5_nao_colinear.csv`

### 2.7 Boruta temporal

- Boruta por dia para selecionar bandas robustas temporalmente.

Fontes:
- `estresse_hidrico/scripts/02_boruta_por_dia.py`
- `estresse_hidrico/outputs/tabelas/resumo_boruta_por_dia.csv`
- `estresse_hidrico/outputs/tabelas/bandas_temporais_selecionadas.csv`

---

## 3) Resultados consolidados por metodo

## 3.1 PLSR + PCA (global, irrigado vs nao_irrigado)

Base analisada: `1732 x 2151` (amostras x bandas).

Resultados principais:
- Melhor `n_components` PLSR: **15**.
- `RMSECV=0.244092`.
- `R2CV=0.761675`.
- `AUC=0.992006`.
- `Accuracy (cutoff 0.5)=0.961316`.
- PCA: `PC1=46.63%`, `PC2=13.98%`.

Fonte: `dados_processados_soft/plsr_pca_irrigacao/resumo_plsr_pca.md`.

## 3.2 PLSR por intervalos espectrais dominantes

- Intervalos avaliados: **50**.
- Melhor intervalo (AUC e RMSECV): `1310-1470 nm` (threshold `1e-05`).
- Metricas desse intervalo: `AUC=0.949843`, `RMSECV=0.310991`, `R2CV=0.613137`, `Accuracy=0.884527`.

Fonte: `dados_processados_soft/plsr_intervalos_regioes_threshold/resumo_plsr_intervalos.md`.

## 3.3 PLSR por data x genotipo x turno

- Subconjuntos avaliados: **27**.
- Melhor R2CV: `2017-02-27 | BR16 | manha` com `R2CV=0.997001`, `RMSECV=0.027380`, `AUC=1.000000`, `Accuracy=1.000000`.
- Pior R2CV: `2017-03-02 | BR16 | tarde` com `R2CV=0.854953`, `RMSECV=0.190425`, `AUC=1.000000`, `Accuracy=0.984375`.

Fonte: `dados_processados_soft/plsr_data_genotipo_turno/resumo_plsr_data_genotipo_turno.md`.

## 3.4 Tabelas PLSR + Pearson + Welch

- Ranking por subconjunto usa: `z(VIP) + z(|coef|)`.
- Limiar de Welch no resumo: `p < 0.005`.
- O bloco identifica bandas relevantes por data, turno, genotipo e combinacoes turno x genotipo com convergencia de criterios.

Fonte: `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao/resumo_top_bandas_plsr_pearson_ttest.md`.

## 3.5 Boruta por dia

Resumo de bandas confirmadas:
- `dia2=1`, `dia3=52`, `dia4=93`, `dia5=0`, `dia6=2`, `dia9=110`.

Resultado agregado:
- `bandas_temporais_selecionadas.csv` com **70** bandas no total.

Fontes:
- `estresse_hidrico/outputs/tabelas/resumo_boruta_por_dia.csv`
- `estresse_hidrico/outputs/tabelas/bandas_temporais_selecionadas.csv`

## 3.6 Reducao por p-teste (Welch/Kruskal) + benchmark LDA

Universo avaliado:
- **148 bandas**.

Significancia (com FDR-BH):
- Welch: `q<0.05 -> 148`, `q<0.01 -> 148`.
- Kruskal: `q<0.05 -> 148`, `q<0.01 -> 148`.

Benchmark LDA dos subsets:
- Baseline (`148` bandas): `accuracy=0.6250`, `f1_macro=0.6124`, `kappa=0.5500`.
- `joint_top_30` (`30` bandas): `f1_macro=0.5865`.
- `kruskal_top_20` (`20` bandas): `f1_macro=0.5864`.
- `ttest_top_10` (`10` bandas): `f1_macro=0.5389`.
- `indices_only`: `f1_macro=0.4877`.

Leitura:
- Nessa base/classificador, cortes agressivos de bandas reduziram desempenho.

Fonte: `estresse_hidrico/outputs/tabelas/reducao_bandas_p_teste/resumo_reducao_bandas_p_teste.md`.

## 3.7 Diversificacao por correlacao (hard/soft)

Configuracao:
- thresholds: `0.95, 0.90, 0.85`.
- tamanhos de subset: `10,15,20,30`.

Resultados:
- Melhor subset geral: `original_bands` com `F1=0.612368`.
- Melhor diversificado por desempenho: `kruskal_cluster_soft_corr_0p95_top_20` com `F1=0.582915`.
- Recomendado por tradeoff (max diversidade): `kruskal_cluster_hard_corr_0p95_top_10` com `3` bandas e `F1=0.517282`.

Leitura:
- A reducao de redundancia foi forte (queda de mediana |corr|), mas com custo relevante de F1.

Fonte: `estresse_hidrico/outputs/tabelas/diversificacao_bandas_correlacao/resumo_benchmark_diversificacao_bandas.md`.

## 3.8 Top-5 por recorrencia de significancia para classificacao global

Selecionando 5 bandas por alvo:
- `condicao`: melhor modelo `Random Forest`, `f1_macro=0.9583`.
- `condicao_genotipo`: melhor `LDA`, `f1_macro=0.5120`.
- `condicao_genotipo_turno`: melhor `LDA`, `f1_macro=0.3300`.

Bandas usadas:
- `condicao`: `400, 579, 1580, 530, 739`.
- `condicao_genotipo` e `condicao_genotipo_turno`: `400, 530, 550, 401, 720`.

Fonte: `estresse_hidrico/outputs/tabelas/classificacao_significancia_global/summary.md`.

## 3.9 KPCA e SR (exploratorio)

- KPCA (RBF/POLY) apresentou recorrencia forte de bandas em `350-352 nm` em varios recortes.
- PCA exploratorio variou por recorte (ex.: global com bandas na faixa de `1911-1914 nm`).
- SR nao-colinear destacou bandas no entorno de `1880-1890 nm` em multiplas comparacoes.

Fontes:
- `dados_processados_soft/analise_bandas_SR_KPCA.csv`
- `dados_processados_soft/analise_SR_top5_nao_colinear.csv`

## 3.10 Pipeline v2 - metodos implementados de selecao

O bloco v2 implementa e combina:
- ANOVA F-score
- Mutual Information
- Random Forest importance
- Logistic L1
- RFE
- PLS coef/VIP
- score combinado de ranking
- busca HVI

Exemplo do ranking consolidado (top linhas): `outputs_v2/07_band_selection/band_ranking_top_100_v2.csv`.

Observacao:
- este relatorio considera o v2 como metodo historico completo de reducao/selecao no projeto.

---

## 4) Comparativo transversal dos metodos

| Metodo/familia | Tipo | Saida de reducao | Evidencia forte de desempenho | Efeito observado |
| --- | --- | --- | --- | --- |
| PLSR+VIP global | multivariado supervisionado | ranking por VIP/coef | AUC 0.9920 (IRR vs NIRR) | muito forte para discriminacao binaria |
| PLSR por intervalos | multivariado supervisionado | faixa dominante | melhor em 1310-1470 nm | identifica regioes espectrais compactas |
| PLSR por subgrupos | multivariado supervisionado | top 5 por subconjunto | muitos subconjuntos com AUC=1.0 | alta sensibilidade ao contexto temporal/genetico |
| Boruta por dia | wrapper (RF) | confirmadas por dia + uniao | 70 bandas agregadas | forte variacao temporal |
| Welch/Kruskal + FDR | filtro univariado | q-threshold + top-N | baseline melhor com 148 bandas | cortes top-N perderam F1 no LDA global |
| Diversificacao por correlacao | filtro de redundancia | subsets hard/soft cluster | F1 cai frente ao baseline | melhora diversidade, piora desempenho |
| Top-5 recorrencia | filtro recorrencia | 5 bandas por alvo | condicao com F1 0.9583 | muito eficiente para alvo binario |
| KPCA/SR (exploratorio) | projecao/heuristico | bandas recorrentes | sem benchmark unico consolidado | util para hipoteses e zonas candidatas |
| v2 combinado (ANOVA+MI+RF+L1+RFE+PLS/VIP+HVI) | ensemble de criterios | ranking composto + HVI | resultados v2 consistentes | metodo abrangente para pre-selecao |

---

## 5) Conclusoes praticas

1. Para `IRR vs NIRR`, os metodos PLSR/VIP e Top-5 recorrencia entregaram os melhores sinais de discriminacao.
2. Reduzir muito o numero de bandas por top-N univariado (10-30) degradou F1 no benchmark LDA principal.
3. Diversificar por correlacao reduziu redundancia, mas com tradeoff negativo de desempenho no cenario global testado.
4. A relevancia de bandas e dependente de contexto (data, genotipo, turno); um unico subconjunto global pode sub-otimizar cenarios locais.
5. O pipeline v2 continua sendo a estrategia mais completa de triagem, por combinar criterios estatisticos, de modelo e heuristica (HVI).

---

## 6) Recomendacao de uso por cenario

- Cenario de alta acuracia binaria global (`IRR vs NIRR`): iniciar com PLSR/VIP e validar com classificacao supervisionada.
- Cenario de interpretabilidade por janela espectral: usar PLSR por intervalos dominantes.
- Cenario de robustez temporal: usar Boruta por dia + recorrencia entre dias.
- Cenario multi-alvo (`condicao`, `condicao_genotipo`, `condicao_genotipo_turno`): usar Top-5 por alvo e comparar sem/com augmentation.
- Cenario de baixa redundancia para deploy: usar diversificacao por correlacao, aceitando perda controlada de F1.

---

## 7) Rastreabilidade (scripts e artefatos-chave)

Scripts:
- `scripts/pipeline_v2_soy_hyper.py`
- `scripts/run_plsr_pca_irrigation.py`
- `scripts/run_plsr_by_dominant_regions.py`
- `scripts/run_plsr_by_date_genotype_turno.py`
- `scripts/run_plsr_optimal_bands_by_subset.py`
- `scripts/summarize_significant_bands_irrigation.py`
- `scripts/tabulate_plsr_pearson_ttest_subsets.py`
- `estresse_hidrico/scripts/02_boruta_por_dia.py`
- `estresse_hidrico/scripts/06_reducao_bandas_p_teste.py`
- `estresse_hidrico/scripts/11_benchmark_bandas_diversificadas.py`
- `estresse_hidrico/scripts/26_importancia_bandas_significativas.py`
- `analise_bandas_SR_KPCA.py`
- `analise_SR_top5_nao_colinear.py`

Artefatos principais:
- `dados_processados_soft/plsr_pca_irrigacao/resumo_plsr_pca.md`
- `dados_processados_soft/plsr_intervalos_regioes_threshold/resumo_plsr_intervalos.md`
- `dados_processados_soft/plsr_data_genotipo_turno/resumo_plsr_data_genotipo_turno.md`
- `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao/resumo_top_bandas_plsr_pearson_ttest.md`
- `estresse_hidrico/outputs/tabelas/resumo_boruta_por_dia.csv`
- `estresse_hidrico/outputs/tabelas/bandas_temporais_selecionadas.csv`
- `estresse_hidrico/outputs/tabelas/reducao_bandas_p_teste/resumo_reducao_bandas_p_teste.md`
- `estresse_hidrico/outputs/tabelas/diversificacao_bandas_correlacao/resumo_benchmark_diversificacao_bandas.md`
- `estresse_hidrico/outputs/tabelas/classificacao_significancia_global/summary.md`
- `outputs_v2/README_v2.md`
- `outputs_v2/07_band_selection/band_ranking_top_100_v2.csv`
- `dados_processados_soft/analise_bandas_SR_KPCA.csv`
- `dados_processados_soft/analise_SR_top5_nao_colinear.csv`

---

## 8) Limitacoes declaradas

- Nem todo metodo implementado tem o mesmo nivel de consolidacao em um unico resumo numerico final.
- KPCA/SR estao mais no papel exploratorio do que em benchmark unico de classificacao.
- Resultados entre pipelines (`soft`, `v2`, `estresse_hidrico`) devem sempre ser comparados respeitando contexto de preprocessamento, alvo e validacao.
