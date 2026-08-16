# Mapa-De-Carbono

# Sistema de Rotas Ecológicas - Curitiba

Este projeto é um motor de roteamento determinístico construído em Python. Ele processa dados espaciais brutos (Shapefiles) do Instituto de Pesquisa e Planejamento Urbano de Curitiba (IPPUC) e implementa o algoritmo A* (A-Estrela) para calcular rotas baseadas não apenas na distância, mas no esforço físico e custo de carbono gerado pela variação de relevo (altimetria) da cidade.

---

## 1. O Pipeline de Processamento (ETL)

### `main.py`
É o coração da preparação de dados. Este script atua como um pipeline de ETL (Extração, Transformação e Carga).
* **O que faz:** Lê os Shapefiles da malha viária e das curvas de nível.
* **Lógica Espacial:** Transforma as linhas das ruas em "Nós" (cruzamentos) matemáticos. Utiliza um índice espacial (R-Tree) via `sjoin_nearest` para cruzar a localização de cada esquina com a curva de nível mais próxima, descobrindo o eixo Z (altitude) de cada ponto em milissegundos.
* **Regra de Negócio:** Reconstrói as ruas como "Arestas" de um grafo. Calcula o `custo_carbono` aplicando uma fórmula de penalidade caso o $Z_{destino}$ seja maior que o $Z_{origem}$ (aclive).
* **Saída:** Exporta o arquivo `grafo_curitiba_carbono.csv`.

## 2. O Banco de Dados

### `grafo_curitiba_carbono.csv`
É o banco de dados final, limpo e otimizado do sistema.
* **O que é:** Uma matriz de adjacência formatada.
* **Conteúdo:** Contém mais de 40 mil linhas, onde cada linha representa um segmento de rua com suas coordenadas de origem $(X, Y, Z)$, destino $(X, Y, Z)$, comprimento plano, variação de altitude ($\Delta Z$), nome oficial da via e o custo final de carbono.

## 3. O Motor Lógico e Navegação

### `estrela.py`
É a inteligência do sistema que roda em tempo real. Não utiliza bibliotecas externas de roteamento, implementando a matemática pura na memória.
* **Geocodificador:** Converte as strings (nomes das ruas fornecidas pelo usuário) nas coordenadas exatas de cruzamento (Nós).
* **Algoritmo A*:** Carrega o CSV em memória como um dicionário (Grafo) bidirecional. Utiliza uma fila de prioridade (`heapq`) para explorar as rotas avaliando o custo de carbono acumulado ($g$) somado à heurística de distância euclidiana ($h$).
* **Navegação (Turn-by-Turn):** Traduz o caminho matemático (lista de coordenadas gerada pelo A*) de volta para texto, agrupando as arestas e imprimindo as instruções passo a passo para o usuário (ex: *"Entre na Rua XV de Novembro"*).

## 4. Ferramentas de Apoio e Debug

Os arquivos abaixo são ferramentas utilitárias criadas para validação de integridade dos dados governamentais:

* **`explorar_mapa.py`:** Um script de topologia. Dado o nome de uma rua, ele busca no grafo todos os cruzamentos validados e retorna a lista de ruas que efetivamente se conectam a ela, evitando erros de "ilhas isoladas" no A*.
* **`ver_grafo.py`:** Usa a biblioteca `matplotlib` para ler o CSV e plotar as arestas em um plano cartesiano, provando visualmente que a extração gerou o mapa correto da cidade.
* **`debug_nomes.py` e `ver_colunas.py`:** Scripts investigativos usados para varrer a tabela de atributos (`.dbf`) do Shapefile e encontrar os identificadores exatos que o IPPUC usou para nomear as colunas (como a `NMVIA`).
