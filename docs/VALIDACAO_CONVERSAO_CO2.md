# Unidades e compatibilidade do fator de CO₂

Na raiz de Routly, execute:

```console
python experimentos/validar_conversao_co2.py
python -m unittest discover -s tests -p test_conversao_co2.py -v
```

O script usa somente a biblioteca padrão. Se o CSV ignorado pelo Git não existir,
ele baixa automaticamente o pacote público do Kaggle, extrai apenas
`CO2 Emissions_Canada.csv` e confere suas colunas antes da análise. Um caminho
alternativo pode ser indicado por `--dataset CAMINHO`; se também estiver ausente,
o arquivo será baixado nesse local.

- Dataset: https://www.kaggle.com/datasets/debajyotipodder/co2-emission-by-vehicles
- Notebook de referência: https://www.kaggle.com/code/muizah/c02-emission

O CSV é reutilizado nas execuções seguintes. O relatório registra as URLs, se o
download ocorreu e o SHA-256 exato do arquivo analisado. Portanto, resultados de
execuções diferentes podem confirmar se utilizaram os mesmos bytes de entrada.

## Método

1. Verificar L/100 km → L/km → g/km com casos conhecidos, consumo zero e
   conversão do fator EPA de kg/galão americano para g/L.
2. Conferir a integração real do VT-CPFM em trecho plano: 1 km a 36 km/h
   corresponde a 100 segundos. Conferir proporcionalidade com a distância
   e conversão de litros para gramas. Isso verifica unidades, não a equação física.
3. Selecionar somente combustível `D` (diesel), usando consumo **combinado**.
   Consumo e emissão devem ser finitos e positivos. Linhas inválidas são
   contabilizadas e identificadas no resumo; ausência de dados válidos é erro.
4. Calcular `fator implícito (g/L) = CO₂ (g/km) × 100 / consumo (L/100 km)`.
   Comparar média, mediana, mínimo e máximo com `FATOR_EPA_G_L`, importado
   diretamente do projeto. Diferença percentual = `(implícito / EPA - 1) × 100`.

Não há tolerância empírica de aprovação: a proximidade é apresentada numericamente.
As verificações aritméticas usam tolerância numérica de 1e-12, sem relação com
precisão de medição. O código de saída é 1 se uma verificação de unidades falhar;
entrada inválida produz código 2. Diferenças entre fatores não provocam aprovação
ou reprovação automática e não modificam parâmetros dos modelos.

## Resultados

Pasta padrão: `experimentos/resultados_conversao_co2` (alterável por `--saida`).

- `relatorio.md`: resumo legível e limitações.
- `resumo.json`: métricas, verificações, linhas rejeitadas, fonte, SHA-256 do
  dataset e versão do Python.
- `diesel.csv`: cálculos por registro com número da linha original.

## Alcance

Esta é uma verificação de consistência da conversão de consumo em CO₂.
Consumo e emissão do catálogo podem derivar do mesmo procedimento e não ser
observações independentes. Arredondamentos e registros repetidos são preservados;
a média é por registro, sem ponderação por frota. Não se estima significância
estatística nem se afirma equivalência entre os fatores.

Os resultados não validam litros consumidos pelo caminhão, efeitos de carga e
relevo, nem economia real de rotas. O fator EPA permanece referência de combustão,
sem calibração para diesel brasileiro.
