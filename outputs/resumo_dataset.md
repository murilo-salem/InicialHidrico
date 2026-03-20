# Resumo do dataset

- Arquivo analisado: `base_dados_unificada.xlsx`
- Aba analisada: `database`
- Total de amostras: 1732
- Comprimentos de onda: 2151 (`350` a `2500`)
- Datas de coleta: 2017-02-23, 2017-02-24, 2017-02-25, 2017-02-26, 2017-02-27, 2017-03-02
- Genotipos normalizados: BR16, CD202, EMB48
- Condicoes normalizadas: irrigado, nao_irrigado
- Linhas com metadados brutos inconsistentes (`bloco`, `genotipo` ou `condicao `): 231
- Linhas com token `C202` no nome do arquivo, normalizadas para `CD202`: 16
- Valores ausentes nas colunas espectrais: 0

## Regras de normalizacao

- O agrupamento da analise foi derivado da coluna `nomenclaura`, porque `genotipo` e `condicao ` contem erros em parte da planilha.
- `IRR`, `IRRG` e `IRRIG` foram tratados como `irrigado`.
- `NIRR` e `NIRRIG` foram tratados como `nao_irrigado`.
- `C202` no nome do arquivo foi tratado como `CD202`.

## Amostras por grupo

| data_coleta | genotipo | condicao | n_amostras |
| --- | --- | --- | ---: |
| 2017-02-23 | BR16 | irrigado | 64 |
| 2017-02-23 | BR16 | nao_irrigado | 64 |
| 2017-02-23 | CD202 | irrigado | 64 |
| 2017-02-23 | CD202 | nao_irrigado | 64 |
| 2017-02-23 | EMB48 | irrigado | 64 |
| 2017-02-23 | EMB48 | nao_irrigado | 64 |
| 2017-02-24 | BR16 | irrigado | 64 |
| 2017-02-24 | BR16 | nao_irrigado | 64 |
| 2017-02-24 | CD202 | irrigado | 64 |
| 2017-02-24 | CD202 | nao_irrigado | 64 |
| 2017-02-24 | EMB48 | irrigado | 64 |
| 2017-02-24 | EMB48 | nao_irrigado | 64 |
| 2017-02-25 | BR16 | irrigado | 32 |
| 2017-02-25 | BR16 | nao_irrigado | 32 |
| 2017-02-25 | CD202 | irrigado | 32 |
| 2017-02-25 | CD202 | nao_irrigado | 32 |
| 2017-02-25 | EMB48 | irrigado | 32 |
| 2017-02-25 | EMB48 | nao_irrigado | 32 |
| 2017-02-26 | BR16 | irrigado | 32 |
| 2017-02-26 | BR16 | nao_irrigado | 32 |
| 2017-02-26 | CD202 | irrigado | 32 |
| 2017-02-26 | CD202 | nao_irrigado | 32 |
| 2017-02-26 | EMB48 | irrigado | 32 |
| 2017-02-26 | EMB48 | nao_irrigado | 32 |
| 2017-02-27 | BR16 | irrigado | 32 |
| 2017-02-27 | BR16 | nao_irrigado | 32 |
| 2017-02-27 | CD202 | irrigado | 32 |
| 2017-02-27 | CD202 | nao_irrigado | 32 |
| 2017-02-27 | EMB48 | irrigado | 32 |
| 2017-02-27 | EMB48 | nao_irrigado | 32 |
| 2017-03-02 | BR16 | irrigado | 64 |
| 2017-03-02 | BR16 | nao_irrigado | 64 |
| 2017-03-02 | CD202 | irrigado | 68 |
| 2017-03-02 | CD202 | nao_irrigado | 64 |
| 2017-03-02 | EMB48 | irrigado | 64 |
| 2017-03-02 | EMB48 | nao_irrigado | 64 |

## Exemplos de normalizacao automatica

| linha | arquivo | origem | ajuste |
| ---: | --- | --- | --- |
| 306 | `B3_C202_IRRIG_REPROD00000.asd` | genotype filename token | C202 -> CD202 |
| 307 | `B3_C202_IRRIG_REPROD00001.asd` | genotype filename token | C202 -> CD202 |
| 308 | `B3_C202_IRRIG_REPROD00002.asd` | genotype filename token | C202 -> CD202 |
| 309 | `B3_C202_IRRIG_REPROD00003.asd` | genotype filename token | C202 -> CD202 |
| 310 | `B3_C202_IRRIG_REPROD00004.asd` | genotype filename token | C202 -> CD202 |
| 311 | `B3_C202_IRRIG_REPROD00005.asd` | genotype filename token | C202 -> CD202 |
| 312 | `B3_C202_IRRIG_REPROD00006.asd` | genotype filename token | C202 -> CD202 |
| 313 | `B3_C202_IRRIG_REPROD00007.asd` | genotype filename token | C202 -> CD202 |
| 314 | `B3_C202_NIRRIG_REPROD00000.asd` | genotype filename token | C202 -> CD202 |
| 315 | `B3_C202_NIRRIG_REPROD00001.asd` | genotype filename token | C202 -> CD202 |
| 316 | `B3_C202_NIRRIG_REPROD00002.asd` | genotype filename token | C202 -> CD202 |
| 317 | `B3_C202_NIRRIG_REPROD00003.asd` | genotype filename token | C202 -> CD202 |
