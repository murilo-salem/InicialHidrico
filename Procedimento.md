# Procedimento

## Objetivo

Documentar o roteiro completo de testes executados no projeto `AgroSATHidrico`, desde a inspecao do dataset original ate a modelagem multivariada para diferenciar `irrigado` vs `nao_irrigado`.

Fluxo executado:

1. Entendimento e saneamento do dataset original.
2. Estatistica descritiva no dado bruto.
3. Geracao de graficos dos outputs descritivos.
4. Pre-processamento espectral para uso no soft.
5. Geracao de graficos do dataset processado.
6. Modelagem PLSR e PCA para `irrigado` vs `nao_irrigado`.
7. Consolidacao das bandas mais relevantes e mais significativas.

---

## 1. Dataset original

### Arquivo de entrada

- `base_dados_unificada.xlsx`
- Aba analisada: `database`

### Estrutura identificada

- `1732` amostras
- `2157` colunas totais
- `6` colunas de metadados:
  - `nomenclaura`
  - `bloco`
  - `genotipo`
  - `condicao `
  - `data_coleta`
  - `turno`
- `2151` bandas espectrais, de `350` a `2500`

### Datas de coleta

- `2017-02-23`
- `2017-02-24`
- `2017-02-25`
- `2017-02-26`
- `2017-02-27`
- `2017-03-02`

### Grupos biologicos normalizados

- Genotipos:
  - `BR16`
  - `CD202`
  - `EMB48`
- Condicoes:
  - `irrigado`
  - `nao_irrigado`

### Problemas encontrados no dataset

- Os campos `genotipo` e `condicao ` da planilha original continham inconsistencias.
- Parte das linhas tinha codigos incorretos como:
  - `IRRG`
  - `NIRR`
  - `C202`
  - variantes como `EMBB48`
- Para garantir agrupamento correto, os metadados principais foram reconstruidos a partir da coluna `nomenclaura`.

### Regras de normalizacao aplicadas

- `IRR`, `IRRG` e `IRRIG` -> `irrigado`
- `NIRR` e `NIRRIG` -> `nao_irrigado`
- `C202` -> `CD202`

### Quantificacao das inconsistencias

- `231` linhas com inconsistencia em metadados brutos (`bloco`, `genotipo` ou `condicao `)
- `16` arquivos com token `C202`, normalizados para `CD202`
- `0` valores ausentes nas bandas espectrais

### Distribuicao por grupo

Os grupos foram organizados como `data_coleta x genotipo x condicao`, totalizando `36` grupos.

Observacao:

- O grupo `2017-03-02 / CD202 / irrigado` ficou com `68` amostras, enquanto os demais grupos aparecem com `32` ou `64`.

---

## 2. Estatistica descritiva do dado bruto

### Objetivo

Atender ao pedido de `Impl.md`:

- calcular `media`
- calcular `coeficiente de variacao`
- para cada `data_coleta`
- considerando `genotipo`
- e `condicao`

### Script criado

- `scripts/generate_descriptive_stats.py`

### Caracteristicas da implementacao

- Leitura do `.xlsx` feita diretamente via XML compactado.
- Nao depende de `pandas` nem `openpyxl`.
- Usa os metadados normalizados a partir de `nomenclaura`.
- Gera CSVs e um `.xlsx` consolidado.

### Arquivos gerados

Na pasta `outputs`:

- `estatistica_descritiva_media.csv`
- `estatistica_descritiva_coeficiente_variacao.csv`
- `amostras_por_grupo.csv`
- `estatistica_descritiva.xlsx`
- `resumo_dataset.md`

### Resultado

- `36` grupos gerados
- `2155` colunas por CSV agregado
  - `4` colunas de agrupamento
  - `2151` bandas

---

## 3. Graficos dos outputs descritivos do dado bruto

### Objetivo

Gerar graficos a partir dos outputs descritivos (`media`, `CV` e `n_amostras por grupo`).

### Script criado

- `scripts/generate_output_plots.py`

### Observacao tecnica

Na etapa inicial, o ambiente nao possuia:

- `matplotlib`
- `numpy`
- `pandas`
- `seaborn`

Por isso, o primeiro gerador de graficos foi implementado em `SVG` puro, sem dependencias externas.

### Arquivos gerados

Na pasta `outputs/plots`:

- `media_por_data.svg`
- `media_por_genotipo.svg`
- `coef_var_por_data.svg`
- `coef_var_por_genotipo.svg`
- `amostras_por_grupo.svg`
- `index.html`

---

## 4. Pre-processamento para o soft

### Objetivo

Criar um dataset processado aplicando:

- `SNV`
- `Savitzky-Golay`
- `1a derivada`

e salvar o resultado em uma pasta separada, para uso no soft.

### Script criado

- `scripts/generate_processed_dataset_for_soft.py`

### Pipeline aplicada

1. Leitura do arquivo original `base_dados_unificada.xlsx`
2. Preservacao dos `6` metadados iniciais
3. Aplicacao de `SNV` por amostra
4. Aplicacao de filtro `Savitzky-Golay`
5. Calculo da `1a derivada`

### Parametros usados

- `window_length = 11`
- `polyorder = 2`
- `deriv = 1`
- `delta = 1.0`
- padding de borda: `mirror`

### Saidas geradas

Na pasta `dados_processados_soft`:

- `base_dados_unificada_snv_savgol_1deriv.csv`
- `metadados_normalizados_soft.csv`
- `resumo_processamento_soft.md`

### Resultado

- `1732` amostras processadas
- `2151` bandas processadas
- faixa dos valores processados:
  - minimo: `-0.0743105970`
  - maximo: `0.0935908826`

### Observacao

- O CSV processado manteve a ordem das linhas e o cabecalho original.
- Apenas as bandas foram transformadas.
- O arquivo `metadados_normalizados_soft.csv` foi mantido como referencia confiavel para agrupamentos.

---

## 5. Graficos dos dados processados

### Objetivo

Gerar graficos de:

- media processada
- coeficiente de variacao processado
- numero de amostras por grupo

### Script criado

- `scripts/generate_processed_plots.py`

### Arquivos gerados

Na pasta `dados_processados_soft/plots`:

- `media_processada_por_grupo.csv`
- `coef_var_processado_por_grupo.csv`
- `amostras_processadas_por_grupo.csv`
- `media_processada_por_data.svg`
- `media_processada_por_genotipo.svg`
- `coef_var_processado_por_data.svg`
- `coef_var_processado_por_genotipo.svg`
- `amostras_processadas_por_grupo.svg`
- `index.html`

### Ajuste adicional aplicado

Os graficos:

- `coef_var_processado_por_data.svg`
- `coef_var_processado_por_genotipo.svg`

ficaram inicialmente achatados porque o `CV` do sinal derivado apresentou outliers muito grandes quando a media ficou proxima de zero.

Para corrigir a visualizacao:

- os graficos de `CV processado` passaram a usar `escala robusta`
- com clipping visual entre os quantis `2%` e `98%`

Importante:

- o CSV agregado `coef_var_processado_por_grupo.csv` nao foi alterado
- apenas a visualizacao dos SVGs foi ajustada

### Script ajustado

- `scripts/generate_output_plots.py`

---

## 6. Instalacao de bibliotecas numericas

Para executar PLSR e PCA com implementacao robusta, foram instaladas:

- `numpy`
- `scipy`
- `scikit-learn`
- `matplotlib`

Instalacao realizada com:

```powershell
python -m pip install numpy scipy scikit-learn matplotlib
```

---

## 7. PLSR para irrigado vs nao_irrigado

### Objetivo

Testar quais bandas mais se relacionam com a diferenciacao entre:

- `irrigado`
- `nao_irrigado`

usando o dataset processado.

### Script criado

- `scripts/run_plsr_pca_irrigation.py`

### Dados usados

- `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv`
- `dados_processados_soft/metadados_normalizados_soft.csv`

### Configuracao do PLSR

- resposta binaria:
  - `irrigado = 1`
  - `nao_irrigado = 0`
- pre-processamento do modelo:
  - `StandardScaler`
- modelo:
  - `PLSRegression`
- selecao de numero de componentes:
  - `StratifiedKFold`
  - `5` folds
  - busca estendida ate `25` componentes

### Resultado final do PLSR

- melhor numero de componentes: `18`
- `RMSECV = 0.242784`
- `R2CV = 0.764223`
- `AUC = 0.992633`
- `accuracy = 0.963048`

### Arquivos gerados

Na pasta `dados_processados_soft/plsr_pca_irrigacao`:

- `plsr_cv_metricas.csv`
- `plsr_bandas_importantes.csv`
- `plsr_predicoes_ajuste.csv`
- `plsr_cv.svg`
- `plsr_coeficientes_vip.svg`
- `plsr_top_bandas.svg`
- `resumo_plsr_pca.md`

### Principais bandas segundo o PLSR

#### Mais associadas a irrigado

Faixas mais destacadas:

- `1147-1150`
- `908-909`
- `879-880`
- `1661-1666`
- `2070`
- `2113-2114`
- `2330`

#### Mais associadas a nao_irrigado

Faixas mais destacadas:

- `458-459`
- `372`
- `895-896`
- `1724-1732`
- `2268-2279`

#### Maiores valores de VIP

Regioes mais fortes por VIP:

- `2270-2279`
- `2291-2293`
- `1661-1666`

Interpretacao:

- VIP alto indica alta relevancia multivariada no modelo PLSR.
- O sinal positivo do coeficiente indica maior associacao com `irrigado`.
- O sinal negativo do coeficiente indica maior associacao com `nao_irrigado`.

---

## 8. PCA para irrigado vs nao_irrigado

### Objetivo

Visualizar a separacao entre as duas classes em um espaco reduzido.

### Configuracao

- PCA com `2` componentes principais

### Resultado

- `PC1 = 46.63%` da variancia
- `PC2 = 13.98%` da variancia

### Arquivos gerados

Na pasta `dados_processados_soft/plsr_pca_irrigacao`:

- `pca_scores.csv`
- `pca_loadings.csv`
- `pca_scores_classes.svg`
- `pca_loadings.svg`

### Leitura do PCA

- O PCA capturou uma parte relevante da estrutura dos dados nas duas primeiras componentes.
- A separacao entre `irrigado` e `nao_irrigado` foi visualizada no grafico de scores.
- Os loadings permitem identificar as regioes espectrais com maior contribuicao para `PC1` e `PC2`.

---

## 9. Bandas mais significativas para diferenciar irrigado vs nao_irrigado

### Objetivo

Consolidar uma tabela final de bandas candidatas, combinando:

- relevancia multivariada do PLSR
- significancia estatistica univariada
- tamanho de efeito

### Script criado

- `scripts/summarize_significant_bands_irrigation.py`

### Criterios utilizados

Para cada banda, foram calculados:

- `Welch t-test`
- correcao multipla `FDR` por `Benjamini-Hochberg`
- `Cohen's d`
- `VIP`
- coeficiente do `PLSR`

### Score combinado usado no ranking final

```text
z(VIP) + z(|Cohen's d|) + z(-log10(q-value))
```

### Resultado global

- bandas com `q-value < 0.05`: `1986`
- bandas com `q-value < 0.05` e `VIP >= 1.0`: `987`

### Arquivos gerados

Na pasta `dados_processados_soft/plsr_pca_irrigacao`:

- `bandas_significativas_completo.csv`
- `top_20_bandas_candidatas_irrigacao.csv`
- `top_10_irrigado_top_10_nao_irrigado.csv`
- `regioes_espectrais_significativas.csv`
- `resumo_bandas_significativas.md`
- `volcano_bandas_irrigacao.png`
- `top_20_bandas_candidatas.png`

### Top 20 bandas candidatas

As `20` primeiras posicoes do ranking combinado ficaram dominadas por bandas mais associadas a `nao_irrigado`, com destaque para:

- `1924`
- `1923`
- `2279`
- `2280`
- `1427`
- `1428`
- `1426`
- `1429`
- `1430`

### Tabela balanceada por classe

Para evitar um ranking final concentrado apenas em uma direcao, tambem foi gerado:

- `top_10_irrigado_top_10_nao_irrigado.csv`

#### Bandas mais fortes para irrigado

Concentradas principalmente em:

- `1652-1661`

com pico em:

- `1660`
- `1659`
- `1654`
- `1661`

#### Bandas mais fortes para nao_irrigado

Concentradas principalmente em:

- `1923-1924`
- `2279-2280`
- `1425-1430`

### Regioes espectrais dominantes

Regioes com maior destaque combinando significancia e relevancia no PLSR:

#### Dominantes para nao_irrigado

- `1910-1944`, pico em `1924`
- `2258-2283`, pico em `2279`
- `1380-1472`, pico em `1427`
- `422-501`, pico em `486`
- `2303-2314`, pico em `2307`

#### Dominantes para irrigado

- `1476-1673`, pico em `1660`
- `2057-2215`, pico em `2125`
- `1783-1814`, pico em `1803`
- `652-671`, pico em `666`
- `2219-2230`, pico em `2227`

### Observacao metodologica importante

Toda essa interpretacao foi feita sobre o sinal processado:

- `SNV`
- `Savitzky-Golay`
- `1a derivada`

Portanto:

- direcao positiva ou negativa indica associacao no espaco processado
- nao deve ser interpretada diretamente como reflectancia bruta maior ou menor

---

## 10. Scripts criados ao longo do procedimento

- `scripts/generate_descriptive_stats.py`
- `scripts/generate_output_plots.py`
- `scripts/generate_processed_dataset_for_soft.py`
- `scripts/generate_processed_plots.py`
- `scripts/run_plsr_pca_irrigation.py`
- `scripts/summarize_significant_bands_irrigation.py`

---

## 11. Principais artefatos finais

### Dado bruto e estatistica descritiva

- `outputs/estatistica_descritiva.xlsx`
- `outputs/estatistica_descritiva_media.csv`
- `outputs/estatistica_descritiva_coeficiente_variacao.csv`
- `outputs/amostras_por_grupo.csv`
- `outputs/resumo_dataset.md`

### Graficos do dado bruto

- `outputs/plots/index.html`

### Dataset processado para o soft

- `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv`
- `dados_processados_soft/metadados_normalizados_soft.csv`
- `dados_processados_soft/resumo_processamento_soft.md`

### Graficos do dataset processado

- `dados_processados_soft/plots/index.html`

### PLSR e PCA

- `dados_processados_soft/plsr_pca_irrigacao/resumo_plsr_pca.md`
- `dados_processados_soft/plsr_pca_irrigacao/plsr_cv.svg`
- `dados_processados_soft/plsr_pca_irrigacao/plsr_coeficientes_vip.svg`
- `dados_processados_soft/plsr_pca_irrigacao/plsr_top_bandas.svg`
- `dados_processados_soft/plsr_pca_irrigacao/pca_scores_classes.svg`
- `dados_processados_soft/plsr_pca_irrigacao/pca_loadings.svg`

### Bandas significativas

- `dados_processados_soft/plsr_pca_irrigacao/resumo_bandas_significativas.md`
- `dados_processados_soft/plsr_pca_irrigacao/top_20_bandas_candidatas_irrigacao.csv`
- `dados_processados_soft/plsr_pca_irrigacao/top_10_irrigado_top_10_nao_irrigado.csv`
- `dados_processados_soft/plsr_pca_irrigacao/regioes_espectrais_significativas.csv`
- `dados_processados_soft/plsr_pca_irrigacao/volcano_bandas_irrigacao.png`
- `dados_processados_soft/plsr_pca_irrigacao/top_20_bandas_candidatas.png`

---

## 12. Conclusao geral

O fluxo completo mostrou que:

1. O dataset original precisava de normalizacao de metadados para analise confiavel.
2. O pre-processamento `SNV + Savitzky-Golay + 1a derivada` foi aplicado com sucesso e gerou uma base separada para o soft.
3. O PLSR conseguiu discriminar `irrigado` vs `nao_irrigado` com desempenho alto:
   - `AUC = 0.992633`
   - `accuracy = 0.963048`
4. O PCA mostrou estrutura clara nas duas primeiras componentes:
   - `PC1 = 46.63%`
   - `PC2 = 13.98%`
5. As regioes espectrais mais informativas para a distincao entre classes ficaram concentradas, principalmente, em:
   - `1910-1944`
   - `2258-2283`
   - `1380-1472`
   - `1476-1673`
   - `2057-2215`

Esses resultados podem ser usados como base para:

- selecao de variaveis
- construcao de modelos supervisionados
- reducao de dimensionalidade por regioes espectrais
- comparacao futura com dados brutos ou com outros pre-processamentos
