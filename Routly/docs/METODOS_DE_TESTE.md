# Routly — Métodos de teste e validação

5 de outubro de 2026 · Vitor Rodrigues Izidoro

O Routly foi verificado em cinco camadas, do código à malha real de Curitiba: os algoritmos são ótimos, os resultados são reproduzíveis, o modelo de emissão concorda com um modelo físico independente (R² = 0,994) e a rota ecológica reduz o CO₂ de forma sistemática — mediana de 10,4 % para o caminhão carregado em 100 viagens sorteadas (Wilcoxon, p < 10⁻¹⁷).

## Resumo das camadas

| Camada | Pergunta | Método | Resultado |
| --- | --- | --- | --- |
| 1. Corretude | O código faz o que as equações e os algoritmos dizem? | 50 testes automatizados (pytest), com cálculos independentes e enumeração exaustiva | 50/50 aprovados (+110 subcasos) |
| 2. Reprodutibilidade | Os resultados se repetem com o mesmo grafo? | Recalcular as rotas do registro `docs/validacao_cmem.json` (09/09/2026) | 16/16 valores idênticos |
| 3. Modelo físico | A emissão estimada é fisicamente plausível? | VT-CPFM (modelo do Routly) × CMEM (Lai et al., 2024) por declividade; fator de CO₂ × dados do Kaggle | R² = 0,994, MAPE = 9,7 %; fator a −0,32 % da EPA |
| 4. Eficácia | Na malha real, a rota ecológica emite menos que a mais curta? | Monte Carlo (100 pares O-D × 3 cargas) + Wilcoxon pareado; medição cruzada no CMEM; ruído na altimetria | Redução mediana de 3,1 % / 7,3 % / 10,4 % (vazio / meia / cheio), p < 10⁻¹⁶ |
| 5. Multiobjetivo | Qual o custo em distância de cada kg de CO₂ poupado? | Fronteira de Pareto por A\* ponderado e BOA\*; joelho pelo ponto utopia | Compromisso: −4,5 % de CO₂ com +2,2 % de distância |

## Corretude e reprodutibilidade

Os testes conferem cada componente contra uma referência calculada por outro caminho, nunca contra a própria saída do código.

- **Algoritmos:** o BOA\* é comparado à enumeração exaustiva de todos os caminhos em 60 grafos aleatórios; o ALT e o A\* ponderado devem igualar o custo do Dijkstra, inclusive na malha real.
- **Equações:** potência, consumo e CO₂ do VT-CPFM (Wang e Rakha, 2017) e do CMEM são recalculados à mão nos testes, com rampa, carga, altitude e descida sem crédito de energia.
- **Unidades:** 8 verificações dimensionais (L/100 km → g/km, galão americano → g/L, vazão L/s integrada no tempo).
- **Reprodução histórica:** com o mesmo grafo (SHA-256 conferido), as rotas, emissões e as 39 alternativas do BOA\* gravadas em setembro são obtidas de novo, idênticas até 10⁻⁹. Isso prova que a busca é estável, não que a emissão esteja fisicamente correta — isso é a camada seguinte.

## Modelo físico

O modelo de emissão do Routly (VT-CPFM) concorda com um modelo físico independente (CMEM, parâmetros de Lai et al., 2024): R² = 0,994, MAPE = 9,7 % e correlação de Pearson 0,9998, em declividades de −6 % a +6 % e três cargas (7,2 t, 17,4 t e 27,6 t, a 30 km/h).

Os dois modelos têm formulações de consumo distintas, então a concordância não é circular. A diferença está sobretudo no consumo em descida: o CMEM inclui atrito interno do motor, o que eleva o piso em cerca de 17 %. Figura: [`validacao_fisica_grade.png`](../resultados_validacao/validacao_fisica_grade.png).

A conversão de litros de diesel em CO₂ foi comparada a 175 veículos diesel do catálogo canadense (Kaggle): o fator implícito médio é 2.688,6 g/L, contra 2.697,2 g/L da EPA usados no projeto (−0,32 %).

## Eficácia na malha real

Em 100 pares origem-destino sorteados na malha de Curitiba (semente fixa 42), a rota ecológica emitiu menos CO₂ que a rota mais curta em todos os cenários, e o ganho cresce com a carga.

Para cada par calculam-se J₁ (rota mais curta, o que um GPS comum faria) e J₂ (rota de menor emissão). O teste de Wilcoxon pareado compara as emissões de J₁ e J₂ nos mesmos pares; o IC 95 % da mediana vem de bootstrap.

| Cenário (massa total) | Redução mediana de CO₂ | IC 95 % | Distância extra mediana | Medida no CMEM | Pares com piora no CMEM |
| --- | --- | --- | --- | --- | --- |
| Vazio (7,2 t) | 3,13 % | 2,18–3,65 % | 1,91 % | 2,17 % | 4 |
| Meia carga (17,4 t) | 7,26 % | 6,29–9,29 % | 4,29 % | 5,55 % | 1 |
| Carregado (27,6 t) | 10,39 % | 9,19–12,18 % | 5,66 % | 8,44 % | 1 |

Três leituras complementam a tabela:

- **Validação cruzada:** a rota escolhida pelo VT-CPFM, medida no CMEM, ainda economiza (8,44 % carregado), então o ganho não é artefato de uma fórmula só.
- **Relevo:** com carga cheia, a economia média é 12,1 % nas rotas de relevo acidentado e 8,7 % nas planas; viagens curtas (< 3 km) quase não ganham (2,6 %, n = 4).
- **Ruído na altimetria:** somando erro aleatório às altitudes, a economia cai de 10,4 % para 8,0 % (±1 m) e 4,8 % (±2 m), e a rota ecológica passa a emitir mais em 6 e 21 dos 100 pares. A qualidade da altimetria é o fator que mais limita o resultado.

Figura: [`boxplot_cenarios_carga.png`](../resultados_validacao/boxplot_cenarios_carga.png).

## Análise multiobjetivo

No par de referência (R. Amadeu Assad Yassim → R. Gen. Luiz Carlos Pereira Tourinho, caminhão carregado), a solução de compromisso reduz 4,5 % do CO₂ com só 2,2 % a mais de distância — cerca de 60 % do ganho máximo por um terço do desvio.

Seguindo a abordagem de Reynoso-Meza, cada aresta recebe um custo que pondera distância e emissão, ambas normalizadas pelos pontos utopia e nadir:

$$C(e) = (1 - \alpha)\,\hat{d}(e) + \alpha\,\hat{E}_{CO_2}(e), \qquad \alpha \in [0, 1]$$

- **Varredura:** 21 valores de α produzem 9 rotas distintas, do baseline GPS (α = 0: 28,83 km, 39,94 kg) à rota Routly (α = 1: 30,82 km, 36,88 kg; −7,7 % de CO₂, +6,9 % de distância).
- **Joelho de Pareto:** a solução mais próxima do ponto utopia no espaço normalizado (α = 0,55).
- **Fronteira exata:** o BOA\* encontra as 108 rotas não dominadas em 0,5 s. A soma ponderada só alcança as soluções da envoltória convexa — uma limitação conhecida do método, visível no gráfico.
- **Prova física:** no perfil altimétrico, a rota curta acumula 251 m de subida e 8 trechos acima de 5 % de inclinação; a Routly, 177 m e 3 trechos.

Figuras: [`pareto_fronteira.png`](../resultados_validacao/pareto_fronteira.png) e [`perfil_altimetrico_comparativo.png`](../resultados_validacao/perfil_altimetrico_comparativo.png).

## Limitações e reprodução

A economia demonstrada é simulada; o passo que falta para uma comprovação definitiva é medir consumo real (OBD-II ou tanque cheio) em alguns pares de maior economia prevista.

- **Wilcoxon no mesmo modelo:** como J₂ é o ótimo de emissão, J₂ nunca emite mais que J₁ nesse modelo; o teste mede se a redução é sistemática, e a evidência independente é a medição cruzada no CMEM.
- **Referência física:** o CMEM é um modelo calculado, não medição de campo.
- **Hipóteses de operação:** velocidade constante de 30 km/h, sem tráfego, semáforos ou paradas; todas as ruas como mão dupla.
- **Potência:** com 27,6 t, 1.968 arcos exigem mais que os 246 kW nominais do HDDT1 nessa velocidade; os custos não são limitados.
- **Altimetria:** 98 trechos têm declividade acima de 20 %, provável erro de interpolação das curvas de nível do IPPUC.

Tudo é reproduzível com um comando (cerca de 5 minutos), que grava figuras, CSVs e relatórios em `resultados_validacao/`:

```
python main.py --opcao 3.6 --pares 100
```
