# AgroSATHidrico v2

Pipeline reprodutível para análise de dataset hiperespectral de soja.

## O que a v2 faz

- Lê `base_dados_unificada.xlsx` ou a versão `.csv` processada.
- Harmoniza o dataset com `dados_processados_soft/metadados_normalizados_soft.csv`.
- Valida estrutura, metadados e faixa espectral de `350` a `2500 nm`.
- Gera estatística descritiva por `data_coleta_iso x genotipo_normalizado x condicao_normalizada`.
- Executa PCA, índices de vegetação, clusterização hierárquica e classificação supervisionada.
- Faz seleção de bandas por ANOVA, mutual information, random forest, regressão L1, RFE e PLS/VIP.
- Executa PLSR binário para `condicao_normalizada` quando aplicável.
- Calcula HVI otimizado por pares de bandas candidatos.

## Comando principal

```powershell
python scripts\pipeline_v2_soy_hyper.py `
  --input base_dados_unificada.xlsx `
  --metadata-csv dados_processados_soft\metadados_normalizados_soft.csv `
  --output-dir outputs_v2
```

## Entradas aceitas

- `base_dados_unificada.xlsx`
- `dados_processados_soft/base_dados_unificada_snv_savgol_1deriv.csv`
- `dados_processados_soft/metadados_normalizados_soft.csv`

## Saídas

As saídas são organizadas por etapa em `outputs_v2/`:

- `01_validation/`
- `02_descriptive_stats/`
- `03_pca/`
- `04_indices/`
- `05_cluster/`
- `06_classification/`
- `07_band_selection/`
- `08_plsr/`
- `09_hvi/`

Também são gravados:

- `run_manifest_v2.json`
- `README_v2.md`
- `pipeline_v2.log`

## Dependências

- Python 3.10+
- `numpy`
- `scipy`
- `scikit-learn`
- `matplotlib`

O carregamento do `.xlsx` é feito diretamente pelos XMLs internos do arquivo, então `openpyxl` não é obrigatório para esta pipeline.

## Limitações metodológicas

- O dataset atual não contém os alvos bioquímicos laboratoriais do artigo original.
- Por isso, a regressão para clorofilas, prolina, fenólicos, RWC, lignina, celulose, ELK e RSA não faz parte do fluxo base.
- Essas análises ficam como extensão opcional caso novos alvos sejam incorporados.

## Script principal

- [`scripts/pipeline_v2_soy_hyper.py`](scripts/pipeline_v2_soy_hyper.py)

