# Estresse Hidrico em Soja

Pipeline reproduzivel para o experimento de deteccao de estresse hidrico por espectroscopia de reflectancia em soja.

## Estrutura

- `dados/raw/`: pasta reservada para o workbook bruto.
- `dados/processados/`: espectros suavizados, IVs e replicatas biologicas agregadas.
- `scripts/`: scripts `00` a `05` para executar o fluxo.
- `outputs/tabelas/`: tabelas finais em CSV/XLSX.
- `outputs/figuras/`: figuras finais em PNG 300 dpi.

## Observacoes do workbook atual

- O arquivo analisado possui seis datas absolutas: `2017-02-23`, `2017-02-24`, `2017-02-25`, `2017-02-26`, `2017-02-27` e `2017-03-02`.
- O workbook atual nao contem uma data separada de `recuperacao`; o pipeline continua funcional e marca essa ausencia no relatorio.
- As `32` leituras por `cultivar x condicao x data x turno` decorrem de `4` blocos biologicos (`B1` a `B4`) e `8` leituras tecnicas por bloco.
- Existe um desbalanceamento tecnico localizado em `2017-03-02 / manha / CD202 / IRR / B1`, com `12` leituras tecnicas. O pipeline agrega tecnicas por bloco e absorve essa excecao.

## Ambiente

O fluxo foi implementado e executado em Python `3.11`.

## Execucao

```powershell
& ..\.venv311_estresse\Scripts\python.exe .\scripts\00_preprocessamento.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\01_permanova.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\02_boruta_por_dia.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\03_graficos_temporais.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\04_classificacao.py
& ..\.venv311_estresse\Scripts\python.exe .\scripts\05_figuras_finais.py
```

## Principais saidas

- `dados/processados/espectros_suavizados.csv`
- `dados/processados/indices_vegetacao.csv`
- `dados/processados/replicatas_bloco_turno.csv`
- `dados/processados/replicatas_bloco_dia.csv`
- `outputs/tabelas/resultados_permanova.csv`
- `outputs/tabelas/resultados_permdisp.csv`
- `outputs/tabelas/lambdas_boruta_por_dia.csv`
- `outputs/tabelas/escores_modelos.csv`
- `outputs/tabelas/escores_por_classe.csv`
- `outputs/tabelas/rf_feature_importance.csv`
- `outputs/figuras/permanova_pvalores.png`
- `outputs/figuras/heatmap_lambdas_confirmados.png`
- `outputs/figuras/confusion_matrix.png`
- `outputs/figuras/rf_feature_importance_top20.png`
- `outputs/figuras/painel_resumo_estresse_hidrico.png`
