# Reflectância Bruta - Descrição dos Gráficos

**Pasta:** `outputs/reflectancia_bruta_genotipos/figuras/`
**Dados de entrada:** `tabelas/reflectancia_bruta_media_por_data_turno_genotipo_condicao.csv` e `tabelas/reflectancia_bruta_cv_por_data_turno_genotipo_condicao.csv`

---

## Cores e Legendas

| Genótipo | Cor | Marcador |
|----------|------|----------|
| BR16 | Azul (#2563eb) | Círculo |
| CD202 | Laranja (#c2410c) | Quadrado |
| EMB48 | Verde (#0f766e) | Triângulo |

| Turno | Estilo de linha |
|-------|----------------|
| Manhã | Linha contínua (—) |
| Tarde | Linha tracejada (---) |

---

## Arquivos Gerados

### 1. REFL_IRR_vs_NIRR.png
**Comparação direta: IRRIGADO vs NÃO IRRIGADO**

- 2 painéis: superior = Reflectância, inferior = Coeficiente de Variação (%)
- 6 colunas (uma por dia de coleta)
- 3 genótipos no mesmo gráfico (BR16, CD202, EMB48) com cores distintas
- Linhas cheias = Irrigado, tracejadas = Não Irrigado
- Permite visualizar diferenças espectrais entre condições de irrigação para todos os genótipos simultaneamente

---

### 2. REFL_irrigado.png / REFL_nao_irrigado.png
**3 genótipos juntos por dia e turno (Reflectância + CV)**

- 2 painéis: superior = Reflectância, inferior = Coeficiente de Variação (%)
- 6 colunas (6 dias de coleta)
- 3 genótipos plotados no mesmo painel com cores distintas
- Manhã (linha) e Tarde (tracejado) overlaid
- Cada painel mostra todos os genótipos e turnos para um mesmo dia

---

### 3. REFL_irrigado_manha.png / REFL_irrigado_tarde.png / REFL_nao_irrigado_manha.png / REFL_nao_irrigado_tarde.png
**3 genótipos juntos, POR TURNO ESPECÍFICO**

- 2 painéis: superior = Reflectância, inferior = CV (%)
- N colunas conforme disponibilidade de dados naquele turno
  - Manhã: 6 dias (23, 24, 25, 26, 27/02, 02/03)
  - Tarde: 3 dias (23, 24/02, 02/03)
- 3 genótipos no mesmo painel com cores distintas
- Facilita comparação entre genótipos dentro de um mesmo turno

---

### 4. REFL_irrigado_por_genotipo.png / REFL_nao_irrigado_por_genotipo.png
**Reflectância SEPARADA por genótipo**

- 3 linhas (uma por genótipo: BR16, CD202, EMB48) × 6 colunas (6 dias)
- Cada painel contém: linha contínua (Manhã) + linha tracejada (Tarde) do mesmo genótipo
- Painel superior = Reflectância
- Permite ver o comportamento espectral de cada genótipo ao longo dos dias

---

### 5. CV_irrigado_por_genotipo.png / CV_nao_irrigado_por_genotipo.png
**Coeficiente de Variação (%) SEPARADO por genótipo**

- Mesma estrutura do item 4 (3×6 grid)
- Cada painel: linha = CV ao longo do espectro
- Cores por genótipo (BR16=azul, CD202=laranja, EMB48=verde)
- Linhas cheias = Manhã, tracejadas = Tarde
- Útil para avaliar variabilidade espectral por genótipo/condição/dia

---

## Regiões Espectrais de Interesse

| Região | Comprimento de Onda | Características |
|--------|---------------------|------------------|
| VIS (azul-verde) | 350-500nm | Reflectância baixa, relacionada a pigmentos |
| VIS (vermelho) | 600-700nm | Absorção por clorofila |
| Red Edge | 680-750nm | Transição alta reflectância |
| NIR (próximo) | 700-1100nm | Alta reflectância, relacionado a estrutura celular |
| NIR (1910nm) | ~1880-1900nm | Banda de água - различиo IRR vs NIRRG |

---

## Observações

- Dados de reflectância brutas (sem pré-processamento além de SNV + Savitzky-Golay 1ª derivada)
- Cada curva representa a média de 32 amostras por grupo (exceto CD202 irrigado 02/03 com 36)
- Coeficiente de Variação (CV%) = (desvio padrão / média) × 100
- Banda ~1910nm (região do água) é particularmente discriminativa para IRR vs NIRRG conforme análise de Spectrum Ratio
