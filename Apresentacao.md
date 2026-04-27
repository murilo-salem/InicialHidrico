# Apresentacao do projeto AgroSATHidrico

## Visao geral

O projeto `AgroSATHidrico` foi estruturado para analisar um dataset hiperespectral de soja e responder, de forma reprodutivel, quais bandas espectrais sao mais informativas para diferenciar `irrigado` e `nao_irrigado`.

A base principal contem:

- `1732` amostras
- `2151` bandas espectrais
- faixa espectral de `350` a `2500 nm`
- `6` metadados por amostra

A pipeline do projeto evoluiu em tres frentes:

1. saneamento e entendimento do dataset original
2. analises descritivas, PCA, PLSR e selecao de bandas
3. implementacao de um pipeline estatistico consolidado por banda com `Kruskal-Wallis`, `Pearson`, `Spearman` e `t-test`

Este documento consolida o que foi feito, como foi feito e quais arquivos foram gerados.

---

## 1. Fonte dos dados

### Arquivo de entrada principal

- `base_dados_unificada.xlsx`
- aba analisada: `database`

### Estrutura observada

- `1732` linhas de amostras
- `2157` colunas no total
- `6` colunas de metadados
- `2151` colunas de bandas

### Metadados

As colunas de metadados usadas na reconstruicao/normalizacao foram:

- `nomenclaura`
- `bloco`
- `genotipo`
- `condicao`
- `data_coleta`
- `turno`

### Classes e grupos biologicos

Os grupos biologicos normalizados utilizados nas analises foram:

- genotipos:
  - `BR16`
  - `CD202`
  - `EMB48`
- condicoes:
  - `irrigado`
  - `nao_irrigado`
- turnos:
  - `manha`
  - `tarde`

### Problemas encontrados no dado bruto

Havia inconsistencias nos metadados do arquivo original, incluindo:

- valores com codificacao incorreta em `condicao`
- variacoes de nomenclatura em `genotipo`
- casos como `IRR`, `IRRG`, `IRRIG`, `NIRR`, `NIRRIG`, `C202`, `EMBB48`

Para evitar agrupamentos errados, os metadados principais foram reconstruidos a partir da coluna `nomenclaura`.

### Regras de normalizacao

- `IRR`, `IRRG`, `IRRIG` -> `irrigado`
- `NIRR`, `NIRRIG` -> `nao_irrigado`
- `C202` -> `CD202`

### Arquivos de metadados e saneamento

- `dados_processados_soft/metadados_normalizados_soft.csv`
- `dados_processados_soft/resumo_processamento_soft.md`

---

## 2. Pre-processamento espectral

### Objetivo

Preparar uma versao tratada do dataset para analises multivariadas e classificacao, aplicando:

- `SNV`
- `Savitzky-Golay`
- `1a derivada`

### Script

- `scripts/generate_processed_dataset_for_soft.py`

### Parametros usados

- `window_length = 11`
- `polyorder = 2`
- `deriv = 1`
- `delta = 1.0`
- padding de borda: `mirror`

### Saidas geradas

- `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv`
- `dados_processados_soft/metadados_normalizados_soft.csv`
- `dados_processados_soft/resumo_processamento_soft.md`

### Observacao importante

O CSV processado manteve a ordem das linhas do dataset original. Apenas as bandas foram transformadas. Os metadados normalizados servem como referencia confiavel para qualquer agrupamento posterior.

---

## 3. Estatistica descritiva do dado bruto

### Objetivo

Atender ao pedido inicial de estatistica descritiva por:

- `data_coleta`
- `genotipo`
- `condicao`

com calculo de:

- media
- coeficiente de variacao

### Script

- `scripts/generate_descriptive_stats.py`

### Caracteristicas da implementacao

- leitura do `.xlsx` feita diretamente via XML compactado
- sem dependencia de `pandas` ou `openpyxl`
- uso dos metadados normalizados a partir de `nomenclaura`

### Arquivos gerados

Na pasta `outputs/`:

- `estatistica_descritiva_media.csv`
- `estatistica_descritiva_coeficiente_variacao.csv`
- `amostras_por_grupo.csv`
- `estatistica_descritiva.xlsx`
- `resumo_dataset.md`

### Resultado principal

- `36` grupos gerados
- `2155` colunas por CSV agregado
  - `4` colunas de agrupamento
  - `2151` bandas

---

## 4. Graficos dos outputs descritivos

### Objetivo

Gerar graficos a partir dos outputs descritivos do dado bruto.

### Script

- `scripts/generate_output_plots.py`

### Saidas

Na pasta `outputs/plots/`:

- `media_por_data.svg`
- `media_por_genotipo.svg`
- `coef_var_por_data.svg`
- `coef_var_por_genotipo.svg`
- `amostras_por_grupo.svg`
- `index.html`

### Observacao

Nesta etapa o projeto utilizou SVG puro, sem dependencias externas de visualizacao mais pesadas, para garantir reprodutibilidade no ambiente inicial.

---

## 5. Graficos do dataset processado

### Objetivo

Visualizar o efeito do pre-processamento em:

- media processada
- coeficiente de variacao processado
- numero de amostras por grupo

### Script

- `scripts/generate_processed_plots.py`

### Saidas

Na pasta `dados_processados_soft/plots/`:

- `media_processada_por_grupo.csv`
- `coef_var_processado_por_grupo.csv`
- `amostras_processadas_por_grupo.csv`
- `media_processada_por_data.svg`
- `media_processada_por_genotipo.svg`
- `coef_var_processado_por_data.svg`
- `coef_var_processado_por_genotipo.svg`
- `amostras_processadas_por_grupo.svg`
- `index.html`

### Ajuste adicional

Os graficos de coeficiente de variacao precisaram de tratamento visual porque o sinal derivado gerou outliers quando a media ficou proxima de zero.

---

## 6. PCA e PLSR para `irrigado` vs `nao_irrigado`

### Objetivo

Executar uma analise multivariada para verificar separacao entre as classes `irrigado` e `nao_irrigado`.

### Script

- `scripts/run_plsr_pca_irrigation.py`

### Entrada usada

- `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv`
- `dados_processados_soft/metadados_normalizados_soft.csv`

### O que foi usado como variavel explicativa

Somente as **bandas espectrais**.

### O que foi usado como rotulo

A condicao binaria:

- `irrigado`
- `nao_irrigado`

### Resultado do PCA

- `PC1 = 46.63%` da variancia
- `PC2 = 13.98%` da variancia

### Leitura do PCA

- houve separacao visual entre as classes
- a estrutura ficou mais clara no espaco das duas primeiras componentes
- os metadados foram usados apenas para colorir e interpretar o grafico, nao como features do PCA

### Arquivos gerados

Na pasta `dados_processados_soft/plsr_pca_irrigacao/`:

- `pca_scores.csv`
- `pca_loadings.csv`
- `pca_scores_classes.svg`
- `pca_loadings.svg`
- `resumo_plsr_pca.md`

### Resultado do PLSR

Na mesma execucao, o PLSR binario foi ajustado para diferenciar as classes:

- melhor numero de componentes: `15`
- `RMSECV = 0.244092`
- `R2CV = 0.761675`
- `AUC = 0.992006`
- `Accuracy = 0.961316`

### Arquivos do PLSR

- `plsr_cv_metricas.csv`
- `plsr_predicoes_ajuste.csv`
- `plsr_bandas_importantes.csv`
- `plsr_top_bandas.svg`
- `plsr_coeficientes_vip.svg`
- `plsr_cv.svg`

---

## 7. Bandas mais fortes em PCA

### Loadings mais fortes em PC1

As bandas com maior peso em `PC1` ficaram concentradas em torno de:

- `694-703 nm`

### Loadings mais fortes em PC2

As bandas com maior peso em `PC2` ficaram concentradas em torno de:

- `351-359 nm`

### Arquivo adicional gerado

- `dados_processados_soft/plsr_pca_irrigacao/resumo_pca_bandas_classes.md`

---

## 8. Bandas mais significativas por `q-value`

### Objetivo

Selecionar bandas com significancia estatistica univariada para diferenciar `irrigado` e `nao_irrigado`.

### Base estatistica usada

- Welch t-test por banda
- correcao FDR Benjamini-Hochberg
- `q-value` como referencia de significancia
- medida de efeito com `Cohen's d`
- score combinado com `VIP`, `|Cohen's d|` e `-log10(q-value)`

### Script e arquivos produzidos anteriormente

- `scripts/summarize_significant_bands_irrigation.py`
- `dados_processados_soft/plsr_pca_irrigacao/bandas_significativas_completo.csv`
- `dados_processados_soft/plsr_pca_irrigacao/resumo_bandas_significativas.md`
- `dados_processados_soft/plsr_pca_irrigacao/top_20_bandas_candidatas_irrigacao.csv`
- `dados_processados_soft/plsr_pca_irrigacao/top_10_irrigado_top_10_nao_irrigado.csv`
- `dados_processados_soft/plsr_pca_irrigacao/regioes_espectrais_significativas.csv`
- `dados_processados_soft/plsr_pca_irrigacao/volcano_bandas_irrigacao.png`
- `dados_processados_soft/plsr_pca_irrigacao/top_20_bandas_candidatas.png`

### Cortes avaliados

Foram geradas selecoes para:

- `q < 0.05`
- `q < 0.01`
- `q < 0.001`
- `q < 0.0001`
- `q < 0.00001`

### Principais contagens

- `q < 0.05`: `1986` bandas
- `q < 0.01`: `1928` bandas
- `q < 0.001`: `1873` bandas
- `q < 0.0001`: `1826` bandas
- `q < 0.00001`: `1784` bandas

### Direcao dominante

Em todos os cortes, houve mais bandas associadas a `nao_irrigado` do que a `irrigado`.

### Regioes mais recorrentes

As regioes espectrais mais dominantes ao longo dos cortes foram:

- `353-553 nm`
- `765-986 nm`
- `1476-1680 nm`
- `2016-2239 nm`
- `2294-2415 nm`

### Arquivos gerados para os cortes

- `bandas_significativas_q_lt_0_05.csv`
- `bandas_significativas_q_lt_0_05_irrigado.csv`
- `bandas_significativas_q_lt_0_05_nao_irrigado.csv`
- `bandas_significativas_q_lt_0_01.csv`
- `bandas_significativas_q_lt_0_01_irrigado.csv`
- `bandas_significativas_q_lt_0_01_nao_irrigado.csv`
- `resumo_bandas_q_lt_0_05.md`
- `resumo_bandas_q_lt_0_05_separadas.md`
- `resumo_bandas_q_lt_0_01.md`
- `resumo_bandas_q_lt_0_01_separadas.md`
- `resumo_regioes_q_lt_0_01.md`
- `resumo_regioes_por_threshold.md`
- `regioes_dominantes_por_threshold.csv`
- `regioes_espectrais_q_lt_0_01.csv`
- `regioes_espectrais_q_lt_0_01.png`

---

## 9. Analise estatistica consolidada: Kruskal-Wallis, Pearson, Spearman e t-test

### Objetivo

Foi implementado um pipeline estatistico mais geral para avaliar a relevancia de cada banda com multiplos criterios, reduzindo dependencia de um unico teste.

### Novo modulo implementado

- `band_significance.py`

### Novo runner implementado

- `scripts/run_band_significance_analysis.py`

### Testes adicionados

- `tests/test_band_significance.py`

### O que o pipeline faz

Para cada banda:

- `Kruskal-Wallis`
- `t-test` de Welch
- `Pearson`
- `Spearman`
- ajuste de multiplas comparacoes com FDR/BH
- calculo de um `ranking_score` reproduzivel

### Estrategia do ranking

O score final foi documentado no resumo gerado pelo pipeline:

- `effect_score`: media robusta dos efeitos disponiveis
- `significance_score`: media robusta de `-log10(pvalue_adjusted)`
- `consistency_score`: consistencia de sinal entre metricas assinadas
- `ranking_score = 0.45 * effect_score + 0.45 * significance_score + 0.10 * consistency_score`

### Tratamento de dados

O pipeline:

- ignora `NaN` de forma explicita
- valida tamanho minimo por grupo
- evita quebra em bandas com variancia zero
- registra bandas descartadas por insuficiencia de dados

### Saidas do novo pipeline

Na pasta:

- `dados_processados_soft/plsr_pca_irrigacao/band_significance/`

Foram gerados:

- `band_significance_ranking.csv`
- `band_significance_significant_alpha_0_05.csv`
- `band_significance_top20.csv`
- `band_significance_top20.png`
- `resumo_band_significance.md`

### Resultado no dataset real

- `1732` amostras
- `2151` bandas
- `2018` bandas significativas em `alpha = 0.05`

### Top do ranking

As bandas mais fortes no ranking consolidado ficaram concentradas em:

- `1924-1926 nm`
- `485-492 nm`
- `1424-1432 nm`

### Exemplo de interpretacao

O pipeline deixa claro que:

- significancia estatistica nao implica causalidade
- o ranking univariado ajuda a priorizar bandas
- ainda assim, validacao supervisionada continua necessaria

---

## 10. Analise estatistica com Kruskal-Wallis, Pearson e Spearman

### Objetivo

Rodar uma analise banda a banda com:

- `Kruskal-Wallis`
- `Pearson`
- `Spearman`

para o contraste `irrigado` vs `nao_irrigado`.

### Arquivo gerado

- `dados_processados_soft/plsr_pca_irrigacao/kruskal_pearson_spearman_irrigacao.csv`
- `dados_processados_soft/plsr_pca_irrigacao/resumo_kruskal_pearson_spearman_irrigacao.md`

### Resultado principal

As bandas mais fortes ficaram concentradas em:

- `485-492 nm`
- `1414-1416 nm`
- `1923-1926 nm`

### Top bandas

As primeiras bandas do ranking por `Kruskal H` foram:

- `491`
- `490`
- `487`
- `488`
- `489`
- `1925`
- `492`
- `486`
- `1924`
- `1926`

### Resumo dos cortes de p-value

O resumo gerado mostrou os totais de bandas abaixo de cada limiar:

- `0.05` -> `2001` em Kruskal, `1987` em Pearson, `2001` em Spearman
- `0.01` -> `1959`, `1933`, `1959`
- `0.001` -> `1878`, `1876`, `1878`
- `0.0001` -> `1828`, `1828`, `1828`
- `0.00001` -> `1782`, `1786`, `1782`

---

## 11. Experimentos e validacoes sinteticas

### Objetivo

Validar o novo pipeline estatistico com datasets artificiais para garantir que:

- o ranking prioriza bandas informativas
- os testes funcionam para target binario, continuo e multiclass
- o ajuste de p-values e a ordenacao sao reproduziveis

### Casos testados

- dataset binario com banda linear forte
- banda monotonicamente nao linear
- banda ruido
- dataset continuo com correlacao linear e monotonica
- dataset multiclass com separacao clara entre tres grupos

### Resultado

Os testes sintéticos passaram e confirmaram que as bandas informativas sobem no ranking.

### Arquivo de teste

- `tests/test_band_significance.py`

---

## 12. Inventario de scripts principais

### Etapas iniciais

- `scripts/generate_descriptive_stats.py`
- `scripts/generate_output_plots.py`
- `scripts/generate_processed_dataset_for_soft.py`
- `scripts/generate_processed_plots.py`

### Analises multivariadas

- `scripts/run_plsr_pca_irrigation.py`
- `scripts/run_plsr_optimal_bands_by_subset.py`
- `scripts/tabulate_plsr_pearson_ttest_subsets.py`
- `scripts/summarize_significant_bands_irrigation.py`
- `scripts/compare_optimal_bands_morning_afternoon.py`

### Novo pipeline estatistico

- `band_significance.py`
- `scripts/run_band_significance_analysis.py`

---

## 13. Limitações metodologicas

### Colinearidade

Existe forte correlacao entre bandas vizinhas. Isso pode fazer com que bandas contiguas aparecam em bloco no ranking.

### Analise univariada

Mesmo combinando varios testes, o ranking continua sendo univariado por banda. Ele e excelente para priorizacao, mas nao substitui um modelo supervisionado multivariado.

### Interpretacao biologica

O sinal do ranking aponta direcao estatistica, mas a interpretacao biologica das regioes espectrais ainda depende de conhecimento de dominio.

### Dados processados

Grande parte das analises finais foi feita sobre o sinal `SNV + Savitzky-Golay + 1a derivada`, ou seja, sobre um dado transformado e nao sobre reflectancia bruta.

---

## 14. Reprodutibilidade

### Comando de execucao do novo pipeline

```powershell
python scripts\run_band_significance_analysis.py
```

### Comando de testes

```powershell
python -m unittest discover -s tests -v
```

### Observacao sobre dependencias

O ambiente disponivel nao tinha `pandas` nem `statsmodels` instalados no momento da implementacao. Por isso:

- o pipeline foi escrito sem dependencia obrigatoria de `pandas`
- a correcao BH/FDR foi implementada internamente
- `statsmodels` permanece suportado de forma opcional

---

## 15. Principais arquivos de saida por pasta

### `outputs/`

- estatistica descritiva do dado bruto
- graficos SVG dos outputs descritivos

### `dados_processados_soft/`

- dataset processado
- metadados normalizados
- resumos do processamento
- graficos do dataset processado

### `dados_processados_soft/plsr_pca_irrigacao/`

- PCA e PLSR
- bandas significativas por `q-value`
- resumos em Markdown
- regioes espectrais dominantes
- analise de `Kruskal`, `Pearson`, `Spearman`
- novo ranking consolidado por banda

### `dados_processados_soft/plsr_pca_irrigacao/band_significance/`

- ranking completo do novo pipeline
- top 20
- bandas significativas em `alpha=0.05`
- grafico das top bandas

---

## 16. Conclusao

O projeto passou de uma exploracao inicial do dataset para um conjunto consistente de pipelines reprodutiveis para:

- saneamento
- estatistica descritiva
- visualizacao
- PCA
- PLSR
- selecao de bandas
- analise estatistica consolidada por banda

O resultado mais importante e que hoje ha uma base clara para priorizacao de bandas com criterios estatisticos multiplos, com saida exportavel, ranking interpretavel e validacao sintetica do metodo.

