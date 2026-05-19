# Benchmark de bandas diversificadas por correlacao

## Configuracao

- thresholds de cluster: `0.95, 0.90, 0.85`
- tamanhos de subset: `10, 15, 20, 30`
- threshold de referencia para metricas dos baselines: `0.90`
- tolerancia de F1 para recomendacao: `0.020`
- subsets diversificados dentro da tolerancia: `0`

## Resumo de clusters

| threshold | n clusters | maior cluster | mediana tam. | media tam. | singletons |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.95 | 3 | 133 | 14.00 | 49.33 | 1 |
| 0.90 | 3 | 133 | 14.00 | 49.33 | 1 |
| 0.85 | 3 | 133 | 14.00 | 49.33 | 1 |

## Melhor subset geral

- subset: `original_bands`
- tipo: `baseline`
- F1-macro: `0.612368`
- accuracy: `0.625000`
- mediana |corr|: `0.991506`

## Melhor subset diversificado por desempenho

- subset: `kruskal_cluster_soft_corr_0p95_top_20`
- ranking: `kruskal`
- politica: `soft`
- threshold: `0.95`
- F1-macro: `0.582915`
- accuracy: `0.597222`

## Subset recomendado para tradeoff

- subset: `kruskal_cluster_hard_corr_0p95_top_10`
- ranking: `kruskal`
- politica: `hard`
- threshold: `0.95`
- k solicitado: `10`
- bandas selecionadas: `3`
- F1-macro: `0.517282`
- accuracy: `0.548611`
- kappa: `0.458333`
- mediana |corr|: `0.651583`
- maior bloco contiguo: `1`
- regioes espectrais: `1800-2500|350-499|700-999`
- observacao: nenhum subset diversificado ficou dentro da tolerancia de F1 de `0.020` em relacao ao melhor subset geral.
- regra aplicada: fallback para o melhor tradeoff de redundancia/diversidade entre os subsets diversificados disponiveis.

## Comparacao com baseline pareado

- baseline: `kruskal_top_10`
- delta F1-macro: `-0.057414`
- delta accuracy: `-0.048611`
- delta mediana |corr|: `-0.347276`
- delta maior bloco contiguo: `-5`

## Top 10 subsets diversificados pelo criterio de recomendacao

| subset | ranking | politica | threshold | n bandas | F1 | accuracy | mediana |corr| | regioes | bloco contiguo |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| kruskal_cluster_hard_corr_0p95_top_10 | kruskal | hard | 0.95 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p95_top_15 | kruskal | hard | 0.95 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p95_top_20 | kruskal | hard | 0.95 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p95_top_30 | kruskal | hard | 0.95 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p90_top_10 | kruskal | hard | 0.90 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p90_top_15 | kruskal | hard | 0.90 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p90_top_20 | kruskal | hard | 0.90 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p90_top_30 | kruskal | hard | 0.90 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p85_top_10 | kruskal | hard | 0.85 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
| kruskal_cluster_hard_corr_0p85_top_15 | kruskal | hard | 0.85 | 3 | 0.5173 | 0.5486 | 0.6516 | 3 | 1 |
