# Resumo do processamento para o soft

- Arquivo de entrada: `base_dados_unificada.xlsx`
- Pasta de saida: `dados_processados_soft`
- Amostras processadas: 1732
- Comprimentos de onda processados: 2151 (`350` a `2500`)
- Pipeline: `SNV -> Savitzky-Golay -> 1a derivada`
- Window length: 11
- Polyorder: 2
- Derivada: 1
- Delta: 1.0
- Padding na borda: `mirror`
- Linhas com token `C202` normalizado em metadados auxiliares: 16
- Faixa dos valores processados: -0.0743105970 a 0.0935908826

## Arquivos gerados

- `base_dados_unificada_snv_savgol_1deriv.csv`: dataset processado, preservando as colunas originais da planilha.
- `metadados_normalizados_soft.csv`: metadados auxiliares normalizados a partir de `nomenclaura`.
- `resumo_processamento_soft.md`: este resumo.

## Observacoes

- O dataset processado manteve a ordem das linhas e o cabecalho original.
- Apenas as colunas espectrais foram transformadas; os 6 metadados iniciais foram preservados como vieram da planilha.
- Para agrupamentos confiaveis, use o arquivo auxiliar de metadados normalizados.
