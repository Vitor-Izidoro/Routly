# Caminhão de referência — etapas 1 a 3

O perfil padrão é o **HDDT1 — International 9800 SBA (1997), motor Cummins
M11-330**. A identificação está em `veiculos.py`; a massa adicional permanece
configurável durante a consulta.

Fonte: Wang e Rakha (2017), *Fuel consumption model for heavy duty diesel trucks:
Model development and testing*, [DOI 10.1016/j.trd.2017.06.011](https://doi.org/10.1016/j.trd.2017.06.011).
Conferido no arquivo local `artigo1.pdf`, tabelas 1 e 2 (páginas 5 e 6 do PDF,
131 e 132 da revista). O PDF não é uma dependência da aplicação.

| Dado | Valor | Origem |
|---|---:|---|
| Massa veicular | 7.182 kg | Tabela 1 |
| Potência nominal | 330 hp | Tabela 1 |
| Cilindrada | 10,8 L | Tabela 1 |
| Área frontal | 10,0 m² | Tabela 2, hipótese para os caminhões |
| Coeficiente de arrasto | 0,78 | Tabela 2, hipótese para os caminhões |

## Massa adicional

`--carga-kg` representa toda a massa além dos 7.182 kg: reboque e seu conteúdo,
quando presentes. Não é apenas a mercadoria. O padrão de zero representa
somente a massa veicular tabulada, não o conjunto do experimento.

A seção 4.2 informa aproximadamente 45.000 lb para o laboratório rebocado MERL.
A conversão é `45000 × 0,45359237 = 20411,65665 kg`; somada à massa veicular,
resulta em aproximadamente 27.594 kg. Essa é uma reconstrução aproximada,
não uma pesagem exata nem a capacidade máxima de carga do caminhão.
O valor está registrado em `MASSA_MERL_APROX_KG` e não é aplicado automaticamente.

## Integração

O padrão agora é `--modelo-emissao vtcpfm`, implementado em `vtcpfm.py`.
`CaminhaoVTCPFM` utiliza os coeficientes convexos HDDT1 da tabela 4 e os
parâmetros de resistência da tabela 2. Veja [VTCPFM.md](VTCPFM.md).
A potência nominal gera um diagnóstico quando excedida; não limita o custo.

### Opção CMEM da etapa 1

`configurar_caminhao()` aplica massa, cilindrada, área frontal e arrasto ao
CMEM simplificado existente. O terminal, o carregador do grafo e o cálculo
direto por trecho CMEM usam esse perfil. Assim, o perfil afeta os custos
de emissão recebidos por ALT, BOA* e NBA*.

**O resultado ainda é uma adaptação CMEM sem calibração para o HDDT1.**
Os parâmetros internos do motor, rotação, rolamento, eficiências e constantes
ambientais continuam no cenário de Lai et al. documentado em
[MODELO_EMISSOES.md](MODELO_EMISSOES.md). O Cr de 1,25 do VT-CPFM tem outra
definição; a eficiência de 0,94 também pertence à equação desse modelo.
Não foram transplantados para o CMEM. A potência nominal é informativa nesta
opção; a verificação de potência está disponível apenas no VT-CPFM.

A etapa 2 implementou a equação VT-CPFM e os coeficientes convexos
HDDT1 da tabela 4. Na etapa 3, `--cenario-co2 epa` mantém o fator EPA de
aproximadamente 2.697,20 g/L; `--cenario-co2 artigo` ativa o fator empírico de
2.070 g/L com VT-CPFM. A seleção muda somente a conversão de CO₂.
Nenhum resultado atual deve ser apresentado como reprodução ou validação
experimental do consumo desse caminhão.

## Execução

Na pasta `Routly`:

```bash
# HDDT1 padrão, com 10 t adicionais (incluindo reboque, se houver)
.venv/bin/python estrela.py --algoritmo alt --modo emissao --carga-kg 10000

# Massa aproximada do MERL, usando VT-CPFM
.venv/bin/python estrela.py --algoritmo boa --carga-kg 20411.65665 --sem-mapa

# Comparação com o cenário genérico anterior
.venv/bin/python estrela.py --algoritmo alt --modelo-emissao cmem --caminhao hdv-generico --sem-mapa
```

`--caminhao hddt1` torna a seleção padrão explícita. `--caminhao` só é aceito
nos modelos VT-CPFM (somente HDDT1) e CMEM; `--veiculo` continua reservado ao catálogo do modelo legado.
Na API, `CaminhaoCMEM()` preserva os parâmetros genéricos históricos;
`configurar_caminhao('hddt1')` produz a adaptação do perfil escolhido.

Os resultados históricos de `validacao_cmem.json` pertencem ao perfil
`hdv-generico`, não ao novo padrão. Os testes conferem o cálculo plano do
HDDT1 com massa adicional e sua integração aos pesos do grafo, além de
preservarem a referência numérica independente do CMEM genérico.
