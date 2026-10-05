# VT-CPFM-1 convexo — HDDT1

Implementado em `vtcpfm.py`, padrão do terminal e do carregador do grafo desde
2026-09-15. Fonte: Wang e Rakha (2017), *Fuel consumption model for heavy duty
diesel trucks: Model development and testing*,
[DOI 10.1016/j.trd.2017.06.011](https://doi.org/10.1016/j.trd.2017.06.011).
Equações 3–5, tabelas 1, 2 e 4, conferidas no `artigo1.pdf` fornecido localmente.

## Equações e unidades

```text
v = velocidade em km/h; a = aceleração em m/s²
m = 7182 + massa adicional em kg (reboque + carga)
G = delta_z / distancia_horizontal  (0,05 significa 5%)
H = altitude média dos extremos / 1000  (km)
Ch = 1 - 0,085 H

R = (rho/25,92) Cd Ch Af v² + g m (Cr/1000) (c1 v + c2) + g m G   [N]
P = [R + (1 + lambda + 0,0025 xi v²) m a] v / (3600 eta)          [kW]

f(P) = alpha0 + alpha1 P + alpha2 P²   se P >= 0                 [L/s]
f(P) = alpha0                         se P < 0

t = hypot(distancia_horizontal, delta_z) / (v/3,6)               [s]
combustivel = f(P) t                                             [L]
CO2 = combustivel * fator_CO2                                    [g]
```

Resistência, potência e vazão seguem o artigo. A integração por tempo constante,
a declividade uniforme e o uso da altitude média dos extremos são adaptações
para o grafo do Routly. A API de potência permite aceleração instantânea; a
aplicação usa `a=0`. Não simula uma trajetória acelerada a velocidade constante.
O peso de distância dos algoritmos continua horizontal; o tempo usa a rampa 3D.

| Parâmetro | Valor | Fonte |
|---|---:|---|
| Massa veicular | 7182 kg | Tabela 1, HDDT1 |
| Cd; Af | 0,78; 10,0 m² | Seção 3 / tabela 2 |
| rho; g | 1,2256 kg/m³; 9,8066 m/s² | Equação 3 / seção 3.1 |
| Cr; c1; c2 | 1,25; 0,0328; 4,575 | Tabela 2 |
| eta | 0,94 | Tabela 2 |
| lambda; xi | 0,1; 0 | Seção 3.2 |
| alpha0 | 0,00156 L/s | Tabela 4, HDDT1 convexo |
| alpha1 | 0,000081 L/(s·kW) | Tabela 4 |
| alpha2 | 0,00000001 L/(s·kW²) | Tabela 4 |

O modelo não usa os coeficientes negativos da tabela 3 (versão côncava).
Na descida, potência negativa resulta no piso de consumo `alpha0`; não há
emissão negativa. No repouso, a função de vazão retorna `alpha0`, mas as rotas
exigem velocidade positiva porque precisam de um tempo de travessia finito.
Trecho de comprimento zero e desnível zero custa zero.

## Integração e limites

O carregador exige `origem_z` e `destino_z` finitos no CSV e usa a média dos
dois em ambos os sentidos. O desnível muda de sinal no sentido oposto.
Os pesos são recalculados a cada cenário; a coluna histórica `custo_carbono`
não é utilizada. ALT e BOA* recebem os novos pesos e recalculam heurísticas.
NBA* usa heurística zero para emissão, tal como na opção CMEM.

A potência nominal informada é 330 hp, convertida a aproximadamente 246,1 kW.
Quando ultrapassada, o programa informa a quantidade de arcos afetados e
mantém os custos calculados. Isso detecta possível inviabilidade da hipótese
de velocidade constante; não implementa marcha, redução de velocidade,
remoção de ruas nem uma restrição de potência durante a busca.

**Conversão de CO₂ (etapa 3):** `--cenario-co2` seleciona um dos fatores abaixo.
Os valores e suas fontes são centralizados em `cenarios_co2.py`.

| Cenário | Fator | Uso e fonte |
|---|---:|---|
| `epa` (padrão) | 2697,19665 g/L | Diesel de referência: EPA 2025, tabela 2, 10,21 kg/galão americano |
| `artigo` | 2070 g/L | Reprodução da conversão empírica: Wang e Rakha 2017, seção 6.3, equação 9 |

O fator EPA é `10210/3.785411784`, com fonte em
[Emission Factors Hub 2025](https://www.epa.gov/system/files/documents/2025-01/ghg-emission-factors-hub-2025.pdf).
É referência de combustão, sem calibração para a mistura de diesel brasileira.
O fator do artigo foi ajustado pelos autores com medições de CO₂ e combustível,
e depois agregado entre caminhões; não é um fator universal do diesel.

O cenário `artigo` exige VT-CPFM; CMEM aceita `epa`. O modelo legado não aceita
cenário de conversão porque recebe emissão diretamente em g/km. O menu VT-CPFM
oferece a escolha quando o argumento é omitido; Enter mantém EPA. O terminal
mostra cenário, fator, fonte e alcance, e o título do mapa identifica o cenário.

**Selecionar `artigo` reproduz a conversão, não o experimento completo.**
Massa, velocidade e altitude não são alteradas ao trocar de cenário. A comparação
com curvas e medições publicadas continua pendente. Somente o fator CO₂ muda:
potência e litros permanecem iguais; emissões são multiplicadas pela razão
dos fatores. Isso preserva os custos ótimos de combustível e a fronteira de
Pareto em distância/litros. Empates e arredondamentos podem mudar a representante
escolhida entre rotas equivalentes, mas não indicam economia de combustível.

A massa adicional padrão é zero; para aproximar a massa do conjunto com
laboratório MERL, usar `--carga-kg 20411.65665`. Isso sozinho não reproduz o
experimento: faltam suas séries medidas de velocidade, aceleração e relevo.
Os coeficientes são calibrados no estudo, não na frota de Curitiba.
Permanecem as limitações de altitude por curvas próximas, tráfego e circulação.

## Uso e verificações

```bash
# Padrão VT-CPFM, consulta sem janela
.venv/bin/python estrela.py --algoritmo alt --modo emissao --carga-kg 20411.65665 --sem-mapa
.venv/bin/python estrela.py --algoritmo boa --modelo-emissao vtcpfm --carga-kg 10000 --sem-mapa

# Conversão do artigo com massa aproximada do MERL
.venv/bin/python estrela.py --algoritmo alt --cenario-co2 artigo --carga-kg 20411.65665 --sem-mapa

# Mesmo cenário físico com conversão EPA
.venv/bin/python estrela.py --algoritmo alt --cenario-co2 epa --carga-kg 20411.65665 --sem-mapa

# Baseline CMEM genérico
.venv/bin/python estrela.py --algoritmo alt --modelo-emissao cmem --caminhao hdv-generico --sem-mapa

.venv/bin/python -m unittest discover -s tests -v
```

Na API, usar `configurar_vtcpfm('artigo')` ou `configurar_vtcpfm('epa')` e passar
o objeto a `consumo_trecho_vtcpfm` ou `carregar_grafos_direcionais` pelo argumento
`caminhao`. `CaminhaoVTCPFM()` preserva EPA como padrão. O seletor
`selecionar_cenario_co2` fornece os metadados da fonte para relatórios.

Os testes verificam potência e litros por cálculo independente com conversão
de unidades, regimes da vazão, efeito de altitude e aceleração, relevo e massa,
diagnóstico de potência, entradas inválidas, custos nos dois sentidos e ALT
contra Dijkstra em um grafo controlado, com alternativas BOA*.
São verificações da implementação, não validação experimental em Curitiba.

Em execução local no CSV de Curitiba (30 km/h, massa adicional 20411,65665 kg,
ruas padrão), ALT coincidiu com Dijkstra nos dois objetivos. A rota de menor
distância teve 28.831,87 m e 39.944,92 g; a de menor emissão, 30.817,79 m e
36.875,21 g (~13,672 L). BOA* retornou 108 alternativas com os mesmos extremos.
NBA* por emissão também coincidiu com Dijkstra nessa consulta. Foram sinalizados
98 segmentos acima de 20% de declividade e 1.968 arcos acima da potência nominal.
Esses valores de CO₂ correspondem ao cenário EPA.

Após a etapa 3, 19 testes passaram, incluindo a invariância de potência, litros,
buscas e fronteira de Pareto ao trocar apenas o fator, além da seleção pelo
terminal/menu e rejeição de combinações incompatíveis.
