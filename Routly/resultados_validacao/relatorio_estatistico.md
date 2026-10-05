# Relatório estatístico — Monte Carlo + Wilcoxon signed-rank

- Pares Origem-Destino: **100**, sorteados na maior componente conexa da malha (semente 42); os mesmos pares em todos os cenários (delineamento pareado).
- Veículo: HDDT1 — International 9800 SBA (1997), Cummins M11-330, massa base 7182 kg; velocidade constante 30 km/h; modelo VT-CPFM-1 (Wang e Rakha, 2017); fator CO₂ EPA.
- J₁: rota de menor distância (ALT). J₂: rota de menor emissão (ALT, ótimo exato).
- H₀: a mediana das diferenças CO₂(J₁) − CO₂(J₂) é zero. H₁ (bicaudal): é diferente de zero. Também é reportado o p unicaudal (H₁: J₁ > J₂).
- Teste: `scipy.stats.wilcoxon` (zero_method="wilcox": pares com rotas de mesmo custo são descartados; o SciPy usa a distribuição exata quando n ≤ 50 sem empates e a aproximação normal nos demais casos). Efeito r = z/√n. IC 95 % da mediana por bootstrap (10.000 reamostras).

## Resultado principal (rota escolhida e medida pelo VT-CPFM)

| Cenário | Massa total (t) | n | Rotas iguais | Redução mediana (%) | IC 95 % mediana | Média ± DP (%) | Q1–Q3 (%) | Distância extra mediana (%) | W | p bicaudal | p unicaudal | r |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Vazio | 7.2 | 100 | 3 | 3.13 | [2.18; 3.65] | 3.21 ± 2.33 | 1.17–5.07 | 1.91 | 0 | 1.218e-17 | 6.090e-18 | 0.87 |
| Meia carga | 17.4 | 100 | 3 | 7.26 | [6.29; 9.29] | 7.67 ± 4.55 | 4.26–11.04 | 4.29 | 0 | 1.218e-17 | 6.091e-18 | 0.87 |
| Carregado | 27.6 | 100 | 2 | 10.39 | [9.19; 12.18] | 10.39 ± 5.76 | 5.95–14.48 | 5.66 | 0 | 8.330e-18 | 4.165e-18 | 0.87 |

## Validação cruzada (rota escolhida pelo VT-CPFM, medida pelo CMEM)

Aqui o sinal da diferença **não** é garantido pela otimização: o CMEM (Lai et al., 2024) é um modelo físico independente. Uma economia significativa indica que o ganho não é artefato do modelo usado na busca.

| Cenário | n | Redução mediana (%) | Média (%) | Pares com piora | W | p bicaudal |
|---|---|---|---|---|---|---|
| Vazio | 100 | 2.17 | 2.38 | 4 | 54 | 6.438e-17 |
| Meia carga | 100 | 5.55 | 6.14 | 1 | 1 | 1.257e-17 |
| Carregado | 100 | 8.44 | 8.48 | 1 | 1 | 8.591e-18 |

## Leitura e limitações

- Como J₂ é o ótimo exato de emissão no mesmo modelo, CO₂(J₂) ≤ CO₂(J₁) em todo par; o teste quantifica se a redução é sistemática na população de viagens, não se o algoritmo "acerta" o sinal. A validação cruzada acima é a evidência que não depende dessa garantia.
- Aviso do modelo no cenário Vazio: 98 segmentos têm declividade estimada acima de 20%; revise as altitudes antes de interpretar emissões como valores reais.
- Aviso do modelo no cenário Vazio: 8 arcos exigem potência acima de 246.1 kW no cenário VT-CPFM; a velocidade constante pode ser inviável. Custos mantidos sem recorte.
- Aviso do modelo no cenário Meia carga: 98 segmentos têm declividade estimada acima de 20%; revise as altitudes antes de interpretar emissões como valores reais.
- Aviso do modelo no cenário Meia carga: 327 arcos exigem potência acima de 246.1 kW no cenário VT-CPFM; a velocidade constante pode ser inviável. Custos mantidos sem recorte.
- Aviso do modelo no cenário Carregado: 98 segmentos têm declividade estimada acima de 20%; revise as altitudes antes de interpretar emissões como valores reais.
- Aviso do modelo no cenário Carregado: 1968 arcos exigem potência acima de 246.1 kW no cenário VT-CPFM; a velocidade constante pode ser inviável. Custos mantidos sem recorte.
- Velocidade constante, sem tráfego, paradas ou semáforos; altitude por extremidade de aresta (curvas de nível IPPUC); ruas tratadas como bidirecionais.
- Figura: `boxplot_cenarios_carga.png`. Dados por par: `monte_carlo_resultados.csv`.
