# Resumo da comprovação científica — Routly

Pipeline completo em 302 s. Par representativo: R. AMADEU ASSAD YASSIM → R. GEN. LUIZ CARLOS PEREIRA TOURINHO (HDDT1 carregado, 30 km/h).

## Arquivos

- `boxplot_cenarios_carga.png`
- `conversao_co2/diesel.csv`
- `conversao_co2/relatorio.md`
- `conversao_co2/resumo.json`
- `eficacia/distancia_x_economia.png`
- `eficacia/histograma_economia.png`
- `eficacia/pares.csv`
- `eficacia/resumo.csv`
- `monte_carlo_resultados.csv`
- `pareto_fronteira.png`
- `pareto_tradeoff.csv`
- `paridade_fisica_grade.json`
- `perfil_altimetrico_comparativo.png`
- `relatorio_estatistico.md`
- `reproducao_validacao_cmem.md`
- `testes_automatizados.txt`
- `validacao_fisica_grade.png`

## Métricas principais

- **Testes automatizados:** aprovados — 50 passed, 110 subtests passed in 29.13s
- **Paridade física (VT-CPFM × CMEM, grade −6 % a +6 %):** R² = 0.994, MAPE = 9.7 %, Pearson = 1.000
- **Conversão de CO₂ (diesel, Kaggle):** fator implícito médio 2688.6 g/L vs. projeto (EPA) 2697.2 g/L (-0.32 %), n = 175; verificações de unidades 8/8
- **Reprodução de `docs/validacao_cmem.json`:** 16/16 verificações idênticas ao registro histórico
- **Pareto:** baseline 28.83 km / 39.94 kg; Routly 30.82 km / 36.88 kg (−7.68 % CO₂, +6.89 % distância); joelho α = 0.55: −4.48 % CO₂ com +2.25 % distância; 9 rotas distintas na varredura; fronteira exata BOA* com 108 soluções (0.57 s)
- **Perfil — Rota mais curta (α = 0):** 28.83 km, subida acumulada 251 m, 8 trechos com aclive > 5 %, rampa máx. 9.8 %
- **Perfil — Routly ecológica (α = 1):** 30.82 km, subida acumulada 177 m, 3 trechos com aclive > 5 %, rampa máx. 6.5 %

### Eficácia em 3 camadas (`eficacia/resumo.csv`)

| Cenário | n | Economia média (%) | IC 95 % | Distância extra (%) | Casos negativos | p |
|---|---|---|---|---|---|---|
| VT-CPFM · 0 kg · 30 km/h | 100 | 3.21 | [2.79; 3.68] | 2.59 | 0 | 1.22e-17 |
| VT-CPFM · 10205.8 kg · 30 km/h | 100 | 7.67 | [6.82; 8.60] | 4.56 | 0 | 1.22e-17 |
| VT-CPFM · 20411.7 kg · 30 km/h | 100 | 10.39 | [9.34; 11.54] | 6.39 | 0 | 8.33e-18 |
| VT-CPFM→CMEM · 0 kg · 30 km/h | 100 | 2.38 | [2.03; 2.76] | 2.59 | 4 | 6.44e-17 |
| VT-CPFM→CMEM · 10205.8 kg · 30 km/h | 100 | 6.14 | [5.42; 6.92] | 4.56 | 1 | 1.26e-17 |
| VT-CPFM→CMEM · 20411.7 kg · 30 km/h | 100 | 8.48 | [7.56; 9.49] | 6.39 | 1 | 8.59e-18 |
| Ruído ±1 m · 20411.7 kg · 30 km/h | 100 | 8.01 | [6.90; 9.17] | 7.20 | 6 | 1.91e-16 |
| Ruído ±2 m · 20411.7 kg · 30 km/h | 100 | 4.76 | [3.56; 5.98] | 8.43 | 21 | 3.95e-10 |

### Monte Carlo (100 pares) — redução de CO₂ de J₂ sobre J₁

| Cenário | Mediana (%) | IC 95 % | Média (%) | p (Wilcoxon, bicaudal) | Mediana CMEM (%) | p CMEM |
|---|---|---|---|---|---|---|
| Vazio | 3.13 | [2.18; 3.65] | 3.21 | 1.22e-17 | 2.17 | 6.44e-17 |
| Meia carga | 7.26 | [6.29; 9.29] | 7.67 | 1.22e-17 | 5.55 | 1.26e-17 |
| Carregado | 10.39 | [9.19; 12.18] | 10.39 | 8.33e-18 | 8.44 | 8.59e-18 |
