# AgroSATHidrico

Projeto de analise hiperespectral para deteccao de estresse hidrico em soja, com multiplas trilhas experimentais (pipeline v2, bloco `soft` com PLSR/significancia e pipeline dedicado `estresse_hidrico`).

## Objetivo

Identificar bandas e regioes espectrais mais discriminativas entre condicoes de irrigacao, com comparacoes adicionais por turno, dia e genotipo, usando metodos estatisticos e de aprendizado de maquina.

## Base de dados

- Arquivo principal: `base_dados_unificada.xlsx`
- Tamanho: `1732` amostras, `2151` bandas (`350-2500 nm`)
- Datas absolutas: `2017-02-23`, `2017-02-24`, `2017-02-25`, `2017-02-26`, `2017-02-27`, `2017-03-02`
- Genotipos: `BR16`, `CD202`, `EMB48`
- Condicoes: `irrigado`, `nao_irrigado`
- Turnos: `manha`, `tarde`

## Estrutura do repositorio

- `scripts/`: pipelines e utilitarios da raiz (v2, PLSR, significancia, dashboards e comparacoes).
- `estresse_hidrico/scripts/`: pipeline dedicado por etapas (`00` a `27`) para analises de estresse hidrico.
- `dados_processados_soft/`: dataset processado (`SNV + Savitzky-Golay + 1a derivada`) e resultados do bloco `soft`.
- `outputs_v2/`: saidas do pipeline v2 (`01_validation` a `09_hvi`).
- `estresse_hidrico/outputs/`: tabelas e figuras do pipeline dedicado.
- `outputs/`: saidas descritivas, plots auxiliares e experimentos adicionais (`testes_signf_diniz*`).
- `tests/`: testes unitarios das bibliotecas principais.
- `TestesSignfDiniz/`: tabelas de top bandas por dia/turno usadas em analises de estabilidade e recorrencia.

## Ambientes e dependencias

- Python `3.11` (principal)
- Dependencias recorrentes: `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, `statsmodels`, `xgboost`, `optuna`, `seaborn`
- Dependencias do subprojeto `estresse_hidrico`: ver `estresse_hidrico/requirements.txt`

## Experimentos

### 1) Pipeline v2 integrado (`scripts/pipeline_v2_soy_hyper.py`)

O que faz:
- validacao estrutural da base;
- estatistica descritiva;
- PCA;
- classificacao supervisionada (`condition`, `turno`);
- selecao de bandas multimetodo;
- PLSR binario;
- busca de pares para HVI.

Saidas:
- `outputs_v2/01_validation` ... `outputs_v2/09_hvi`
- `outputs_v2/run_manifest_v2.json`
- `outputs_v2/README_v2.md`

Comando:
```powershell
python scripts\pipeline_v2_soy_hyper.py `
  --input base_dados_unificada.xlsx `
  --metadata-csv dados_processados_soft\metadados_normalizados_soft.csv `
  --output-dir outputs_v2
```

### 2) Bloco `soft` (PLSR + significancia + subconjuntos)

Scripts principais:
- `scripts/generate_processed_dataset_for_soft.py`
- `scripts/run_plsr_pca_irrigation.py`
- `scripts/run_band_significance_analysis.py`
- `scripts/run_plsr_by_dominant_regions.py`
- `scripts/run_plsr_by_date_genotype_turno.py`
- `scripts/run_plsr_optimal_bands_by_subset.py`
- `scripts/tabulate_plsr_pearson_ttest_subsets.py`

O que faz:
- preprocessamento espectral padronizado;
- PLSR para `irrigado vs nao_irrigado`;
- ranking de bandas por combinacao de testes estatisticos e efeito;
- avalia desempenho por regioes espectrais e por subconjuntos (dia/genotipo/turno).

Saidas:
- `dados_processados_soft/plsr_pca_irrigacao/`
- `dados_processados_soft/plsr_intervalos_regioes_threshold/`
- `dados_processados_soft/plsr_data_genotipo_turno/`
- `dados_processados_soft/plsr_subconjuntos_irrigacao/`
- `dados_processados_soft/tabelas_plsr_pearson_ttest_irrigacao/`

### 3) Pipeline dedicado `estresse_hidrico` (`estresse_hidrico/scripts/00-27`)

O que faz:
- preprocessamento com remocao de faixas atmosfericas e agregacao biologica por bloco;
- PERMANOVA/PERMDISP;
- Boruta por dia;
- analise temporal e assinaturas espectrais;
- classificacao multiclasse (`A-F`) com RF/SVM/LDA/kNN/XGBoost;
- reducao de bandas via Welch/Kruskal;
- classificacao com subset explicito + tuning com Optuna;
- blocos recentes: classificacao por bandas significativas globais e por top-5 dia/turno.

Execucao base (00-05):
```powershell
& ..\.venv311_estresse\Scripts\python.exe .\scripts\00_preprocessamento.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\01_permanova.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\02_boruta_por_dia.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\03_graficos_temporais.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\04_classificacao.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\05_figuras_finais.py
```

## Principais resultados

### Pipeline v2

- Melhor modelo para `condition`: `Logistic Regression`
  - `accuracy = 0.899538`
  - `balanced_accuracy = 0.899567`
  - `f1_macro = 0.899527`
  - `roc_auc = 0.975266`
- Melhor modelo para `turno`: `Logistic Regression`
  - `accuracy = 0.822748`
  - `balanced_accuracy = 0.811031`
  - `f1_macro = 0.804360`
  - `roc_auc = 0.901907`
- PLSR (binario): `AUC = 0.967199`, `accuracy = 0.898961`, melhor com `20` componentes.
- PCA: `PC1 = 72.31%`, `PC2 = 16.13%` (acumulado `88.44%`).

### Bloco `soft`

- PLSR `irrigado vs nao_irrigado`:
  - `AUC = 0.992006`
  - `accuracy = 0.961316`
  - `R2CV = 0.761675`
  - melhor com `15` componentes.
- Regioes espectrais mais recorrentes/discriminativas:
  - `1910-1944 nm`
  - `2258-2283 nm`
  - `1380-1472 nm`
  - `422-501 nm`
  - `1476-1673 nm`
- Ranking de significancia (`band_significance`): destaque para bandas `1923-1926 nm` e faixa de `486-491 nm`.

### Pipeline `estresse_hidrico`

- PERMANOVA:
  - contraste `IRR vs NIRR` significativo em `manha` e `tarde` (q ajustado `< 0.01`)
  - testes de homogeneidade de dispersao (PERMDISP) sem violacoes nos contrastes avaliados.
- Classificacao 6 classes (`A-F`), melhor modelo do fluxo principal: `LDA`
  - `accuracy = 0.6250`
  - `f1_macro = 0.6124`
  - `kappa = 0.5500`
- Subset reduzido com tuning Optuna (`kruskal_top_20`):
  - `accuracy = 0.638889`
  - `f1_macro = 0.627411`
  - `kappa = 0.566667`

## Bandas/regioes mais frequentes no projeto

Faixas que se repetem em multiplos experimentos:
- `350-439 nm`
- `717-730 nm`
- `1425-1430 nm`
- `1660-1669 nm`
- `1880-1894 nm`
- `1923-1926 nm`
- `2270-2281 nm`

## Testes

Executar testes unitarios:
```powershell
pytest -q
```

## Documentacao complementar

- `RELATORIO_MESTRE_EXPERIMENTOS.md`: inventario tecnico completo dos experimentos e resultados.
- `RELATORIO_COMPLETO_REDUCAO_DIMENSIONALIDADE_BANDAS.md`: foco em reducao de dimensionalidade e bandas significativas.
- `RELATORIO_TESTESSIGNFDINIZ_BANDAS_SIGNIFICATIVAS.md`: sintese do bloco `TestesSignfDiniz`.
- `estresse_hidrico/README.md`: instrucoes do subprojeto dedicado.
