# Custo de emissão para caminhões

Implementado em 2026-09-09 em `emissoes.py`. O padrão da aplicação passa a ser
`--modelo-emissao cmem`. A fórmula anterior continua em `--modelo-emissao legado`.

## Referências e escolha

[Lai et al. (2024), *The pollution-routing problem with speed optimization and
uneven topography*](https://doi.org/10.1016/j.cor.2024.106557), seção 3.1 e tabela 2,
apresentam uma formulação baseada no CMEM com velocidade, carga e inclinação.
Usamos a coluna HDV como cenário bibliográfico. [PDF no repositório universitário](https://pure.tue.nl/ws/portalfiles/portal/320873655/1-s2.0-S0305054824000297-main.pdf).

O antecedente é [Bektaş e Laporte (2011), *The Pollution-Routing
Problem*](https://doi.org/10.1016/j.trb.2011.02.004). Aproveitamos a modelagem de
consumo; não implementamos o problema de múltiplas entregas desses trabalhos.

Parâmetros do cenário HDV, mantidos conforme a tabela 2 de Lai et al.:

| Parâmetro | Valor |
|---|---:|
| Massa vazia | 13.000 kg |
| Atrito interno do motor | 0,17 kJ/(rev·L) |
| Rotação | 33 rev/s |
| Cilindrada | 11 L |
| Área frontal | 8,2 m² |
| Coeficiente de arrasto | 0,70 |
| Coeficiente de rolamento | 0,008 |
| Fatores de eficiência ε e ω | 0,4 e 0,9 |
| Poder calorífico κ | 45 kJ/g |
| Conversão ψ | 737 g/L |
| Densidade do ar | 1,2041 kg/m³ |
| Gravidade | 9,81 m/s² |
| Razão ξ; aceleração | 1; 0 m/s² |

São parâmetros de referência, não ficha técnica de um caminhão brasileiro.
Em particular, ψ é o valor do benchmark; não é uma medição do diesel local.
As eficiências são utilizadas como produto, evitando reinterpretar isoladamente
os nomes dos fatores da tabela.

A [EPA, Emission Factors Hub 2025, tabela 2](https://www.epa.gov/system/files/documents/2025-01/ghg-emission-factors-hub-2025.pdf)
fornece 10,21 kg CO₂/galão americano de diesel. Convertemos para
`10210 / 3.785411784 ≈ 2697,20 g CO₂/L`. O fator cobre combustão, não o ciclo de
vida do combustível. Aqui não calculamos CO₂ equivalente, CH₄ ou N₂O.

## Adaptação implementada no Routly

A formulação abaixo é nossa adaptação estacionária por aresta, não uma
reprodução do simulador CMEM completo. O CSV fornece comprimento horizontal
`d` em metros e desnível assinado `Δz` em metros. Admitimos uma rampa uniforme:

```text
L = sqrt(d² + Δz²)            comprimento aproximado sobre a rampa (m)
sin(θ) = Δz/L
cos(θ) = d/L
v = velocidade_kmh/3,6        velocidade sobre a rampa (m/s)
t = L/v                      tempo (s)
m = massa_vazia + carga      massa total (kg)

F = m·g·(sin(θ) + Cr·cos(θ)) + 0,5·ρ·Cd·A·v²        força (N)
P_rodas = max(0, F·v)                                potência (W)
P_interno = k·N·V                                    potência (kW)

combustível_L = t · [P_interno + P_rodas/(1000·ε·ω)] / (κ·ψ)
CO₂_g = combustível_L · fator_CO₂_g_L
```

O termo de potência interna tem unidade kJ/s, equivalente a kW. Dividir a
potência das rodas por 1000 converte W em kW. Multiplicar por tempo fornece
energia em kJ; dividir por κ·ψ, em kJ/L, fornece litros.

**Tratamento local das descidas:** limitamos a potência nas rodas a zero,
mas mantemos as perdas internas do motor. Não atribuímos consumo negativo,
regeneração ou créditos de emissão. Esse piso é uma hipótese explícita da
implementação, não uma afirmação de que o artigo utiliza esse mesmo recorte.
Não modela corte de injeção, marcha selecionada ou frenagem real.

A velocidade padrão de 30 km/h e a carga padrão de 0 kg são escolhas de
cenário do projeto, não velocidades observadas nem estimadas pelo artigo.
O menu permite alterá-las. A rotação permanece fixa mesmo ao variar velocidade;
essa simplificação deve entrar na análise de sensibilidade.

O peso de distância permanece o comprimento horizontal do CSV, para preservar
a comparação com o baseline. O consumo usa o comprimento aproximado 3D.
Subdividir uma rampa uniforme, mantendo velocidade e carga, preserva seu custo.
A massa altera os custos relativos entre trechos; o fator CO₂/L, isoladamente,
continua apenas escalando os custos de combustível.

## Uso

```bash
# Dentro de Routly: menu com carga e velocidade
bash validar.sh

# Caminhão de 13t + carga de 10t, velocidade constante de 30 km/h
.venv/bin/python estrela.py --algoritmo alt --modo emissao --carga-kg 10000 --velocidade-kmh 30
.venv/bin/python estrela.py --algoritmo boa --carga-kg 10000 --velocidade-kmh 30

# Reproduzir a fórmula anterior
.venv/bin/python estrela.py --algoritmo boa --modelo-emissao legado --taxa-emissao 200
```

Use `--sem-mapa` para execução sem janela. No modo CMEM, o programa mostra
litros estimados além do CO₂. `--veiculo` e `--taxa-emissao` só são aceitos no
modelo legado. Outros parâmetros físicos podem ser configurados pela classe
imutável `CaminhaoCMEM`, passada ao carregador do grafo.

ALT refaz as tabelas para o cenário de custo carregado. BOA* calcula suas duas
heurísticas no grafo reverso com esses mesmos pesos. No NBA* legado, a
heurística de emissão é zerada para CMEM: o antigo limite de 200 g/km não tem
justificativa nesse modelo. A busca por distância do NBA* não foi reformulada.

## Qualidade dos dados e o que ainda falta

A inspeção do CSV local encontrou 40.393 segmentos e 29.471 nós no grafo.
Há 98 segmentos com `abs(Δz)/d > 0,20`, chegando a aproximadamente 50,7%.
Esse limiar é um diagnóstico escolhido para revisão, não uma regra legal de
circulação. O programa avisa e mantém os valores; não recorta a declividade
nem remove ruas silenciosamente.

Altitudes por curva de nível mais próxima podem criar saltos artificiais.
Também não temos o perfil interno dos segmentos: não é possível recuperar uma
subida seguida de descida apenas conhecendo suas duas extremidades. Não foi
feita uma nova interpolação sem os shapefiles necessários.

Outras limitações do cenário:

- Sem observações de velocidade por rua, trânsito, paradas ou aceleração.
- Sem limite de potência para verificar se o caminhão sustenta a velocidade
  escolhida na subida. Não é uma simulação de desempenho do veículo.
- Sem caracterização da mistura de biodiesel brasileira nem calibração de
  combustível/eficiência local; o diesel é uma referência bibliográfica.
- Massa constante em toda a consulta; não há descarregamento intermediário.
- Todas as ruas continuam com ambos os sentidos; permissões, altura, peso e
  restrições de circulação de caminhões ainda precisam de dados próprios.

**Próxima validação científica:** revisar os segmentos com maiores declividades,
obter perfil de elevação mais confiável e dados de consumo de um caminhão
identificado em rotas com diferentes cargas. Comparar litros previstos e
medidos por percurso, separar percursos de calibração e avaliação e relatar
viés e erro absoluto. Sem isso, falar em economia *estimada pelo modelo*,
jamais em economia comprovada na operação real.

## Verificações executadas

Os testes em `tests/test_emissoes.py` verificam unidades por cálculo independente,
subida/descida, carga, piso não negativo, segmentação uniforme, entradas inválidas,
custos do grafo reverso e um caso em que a rota de menor emissão é mais longa.
Os testes anteriores de ALT e BOA* permanecem.

Uma execução na malha real, entre os nós determinísticos das ruas de exemplo,
comparou ALT com Dijkstra nos dois objetivos, com carga zero e 10.000 kg.
Os valores são registrados em `validacao_cmem.json`; a igualdade dos custos
verifica a busca, não a precisão física da estimativa de emissão.
