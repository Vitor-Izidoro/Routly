# Avaliação da eficácia do Routly

Os testes em `tests/test_algoritmos.py`, `test_emissoes.py`, `test_vtcpfm.py` e
`test_cenarios_co2.py` comprovam que **o código está correto** (algoritmos ótimos,
fórmulas iguais às dos artigos). Esta pasta e `tests/test_eficacia.py` respondem a
outra pergunta: **na malha real de Curitiba, a rota ecológica emite menos CO₂ do
que a rota que um GPS comum escolheria (a mais curta)? Quanto, e a que custo?**

Ambos precisam de `grafo_curitiba_carbono.csv` na raiz do projeto (gerado por `main.py`).

---

## `experimentos/avaliar_eficacia.py` — experimento completo

Sorteia pares origem-destino (semente fixa) na maior componente conectada da
malha e, para cada par, calcula com ALT a rota **mais curta** e a rota de
**menor emissão**. Mede economia de CO₂, distância extra e significância estatística.

```bash
python experimentos/avaliar_eficacia.py                     # padrão: 300 pares, 0/10/20 t, 30 km/h
python experimentos/avaliar_eficacia.py --pares 1000 --velocidades 20 30 50
python experimentos/avaliar_eficacia.py --pares 60 --cargas 0 20000 --sem-graficos   # rápido (~1 min)
```

| Opção | Padrão | Significado |
|---|---|---|
| `--pares` | 300 | Número de pares origem-destino sorteados |
| `--semente` | 42 | Semente do sorteio (mesma semente → mesmos pares) |
| `--cargas` | 0 10000 20000 | Massa adicional (reboque + carga) em kg |
| `--velocidades` | 30 | Velocidades constantes em km/h |
| `--landmarks` | 8 | Landmarks do ALT |
| `--ruido-m` | 1 2 | Desvios do ruído de altitude (m); sem valores desliga a camada 3 |
| `--sem-cmem` | — | Desliga a camada 2 |
| `--sem-graficos` | — | Não gera PNGs |
| `--saida` | `experimentos/resultados` | Pasta dos resultados |

### As três camadas

1. **Economia de CO₂ (VT-CPFM).** Para cada carga × velocidade: economia média
   com IC de 95% (bootstrap), mediana, máximo, distância extra, nº de rotas
   idênticas, nº de casos com economia negativa e p-valor do teste de Wilcoxon
   pareado. Também recorta por **faixa de distância** (<3, 3–8, >8 km) e por
   **relevo** (subida acumulada por km da rota curta, acima/abaixo da mediana).
2. **Validação cruzada.** A rota é escolhida pelo VT-CPFM, mas as duas rotas
   são medidas com o **CMEM**. Se a economia se mantém num modelo físico
   independente, ela não é um artefato de uma fórmula só.
3. **Sensibilidade aos dados.** Soma ruído gaussiano (±1 m, ±2 m) às
   altitudes de cada nó, escolhe as rotas nessa malha "errada" e mede o CO₂ na
   malha original. Mostra quanto do ganho sobrevive a erros de altimetria.

### Saídas (em `--saida`)

- `resumo.csv`: uma linha por cenário/recorte, com todas as métricas acima.
- `pares.csv`: uma linha por par e cenário (distâncias, CO₂ das duas rotas, economia).
- `histograma_economia.png`: distribuição da economia por carga.
- `distancia_x_economia.png`: distância extra × economia (o custo do ganho).

### Exemplo de resultado (60 pares, semente 42, 30 km/h)

| Cenário | Economia média [IC95] | Distância extra | Casos negativos |
|---|---|---|---|
| Vazio (7,2 t) | 3,2% [2,6–3,7] | +2,4% | 0 |
| 20 t de carga | 9,8% [8,5–11,1] | +6,3% | 0 |
| 20 t, medido com CMEM | 8,1% [6,9–9,2] | +6,3% | 0 |
| 20 t, altitude ±1 m | 7,4% [6,0–8,8] | +7,1% | 4 |
| 20 t, altitude ±2 m | 4,3% [2,7–5,8] | +8,0% | 13 |

Leitura: a economia cresce com a carga e com o relevo, se mantém em outro
modelo físico e é sensível à qualidade da altimetria. A maioria dos pares
sorteados é longa (>8 km); para avaliar trajetos curtos, aumente `--pares`.

---

## `tests/test_eficacia.py` — teste automatizado de regressão

Versão rápida (20 pares fixos, ~20 s) que roda junto com os demais testes:

```bash
python -m unittest discover -s tests -v
```

Rode a partir da raiz do projeto. Sem o CSV do grafo, os testes de malha são pulados.

| Teste | O que garante |
|---|---|
| `test_todos_os_pares_tem_rota` | Os 20 pares da componente principal têm rota |
| `test_rota_ecologica_nunca_emite_mais_nem_e_mais_curta` | Em todo par: CO₂ eco ≤ CO₂ curta e distância eco ≥ distância curta |
| `test_economia_media_minima` | Economia média > 1,5% (vazio) e > 5% (20 t) |
| `test_economia_cresce_com_a_carga` | Caminhão carregado economiza mais que vazio |
| `test_economia_estatisticamente_significativa` | Wilcoxon pareado com p < 0,01 (20 t) |
| `test_alt_emissao_igual_ao_dijkstra_na_malha_real` | ALT encontra o ótimo exato na malha real |
| `test_economia_confirmada_por_modelo_independente` | Rota VT-CPFM medida com CMEM economiza > 3% em média |
| `test_wilcoxon_simetrico_e_deslocado` | O teste estatístico implementado se comporta corretamente |

Os limites ficam abaixo do observado, para detectar regressões (por exemplo, uma
mudança na fórmula que anule o efeito do relevo) sem falhar por acaso.

---

## Limitações: o que isto ainda não prova

- A economia é **simulada**: velocidade constante, sem tráfego, semáforos ou paradas.
- Todas as ruas são tratadas como de mão dupla; altitude vem da curva de nível mais próxima.
- Cerca de 3 mil nós estão fora da componente principal e não entram no sorteio.
- A comprovação definitiva é **medir no mundo real**: percorrer a rota curta e
  a ecológica de alguns pares (os de maior economia prevista em `pares.csv`) com o
  mesmo veículo, registrando o consumo via OBD-II ou tanque cheio.
