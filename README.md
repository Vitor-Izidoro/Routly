# Mapa-De-Carbono: Sistema de Rotas Ecológicas - Curitiba

## 1. Descrição, Contextualização e Escopo do Projeto

**Contextualização:** Sistemas de navegação tradicionais frequentemente calculam a rota mais rápida ou mais curta, ignorando o relevo topográfico. Em cidades com variações de altitude significativas como Curitiba, rotas com aclives severos aumentam exponencialmente o esforço do motor e, consequentemente, a emissão de gases de efeito estufa. 

**Descrição:** Este projeto consiste no desenvolvimento de um motor de roteamento espacial multiobjetivo operando em nível de memória. O sistema cruza os dados oficiais de arruamento e altimetria da cidade de Curitiba com o catálogo de emissões de veículos para calcular rotas personalizadas.

**Escopo:** O sistema permite ao usuário inserir a origem e o destino (via nomes de ruas) e selecionar o veículo que será utilizado. O algoritmo entrega a rota instruída passo a passo (turn-by-turn) otimizando para dois modos à escolha do usuário:
*   **Modo Distância:** O trajeto geometricamente mais curto.
*   **Modo Emissão:** O trajeto com a menor emissão de carbono (evitando aclives severos para veículos a combustão).

---

## 2. Materiais e Métodos

**Materiais (Bases de Dados):**
*   **Dados Geográficos (IPPUC):** Shapefiles oficiais de "Eixos de Rua" e "Curvas de Nível" de Curitiba (Sistema de Coordenadas SIRGAS 2000).
*   **Dados Veiculares:** Dataset `CO2 Emissions_Canada.csv`, fornecendo a taxa de emissão base ($E$) em g/km para diversos modelos e motores reais.

**Métodos (Engenharia e Algoritmos):**
1.  **Pipeline ETL (Extração, Transformação e Carga):** Processamento espacial utilizando as bibliotecas `GeoPandas` e `Shapely` em Python. Os vértices das ruas são cruzados com as curvas de nível utilizando uma R-Tree (`sjoin_nearest`) para interpolação da cota altimétrica ($Z$) em complexidade otimizada.
2.  **Modelagem Matemática do Carbono:** O custo $C$ de uma aresta (rua) no grafo é calculado deterministicamente pela fórmula: 
    $$ C = (d_{km} \times E) \times (1 + (\Delta Z \times k)) $$
    Sendo $d_{km}$ a distância do segmento, $E$ a emissão do veículo (g/km), $\Delta Z$ a variação de altitude, e $k$ a constante de penalidade do motor em aclives.
3.  **Busca de Caminho (NBA*):** Implementação do Algoritmo *New Bidirectional A** (A-Estrela Bidirecional) operando em uma Lista de Adjacência. O espaço de busca explora a malha simultaneamente a partir da origem e do destino, utilizando a distância euclidiana projetada sobre o consumo do veículo como função heurística admissível.

---

## 3. Baseline de Implementação (Artefatos e Logs)

*Nota de Arquitetura:* Por se tratar de um sistema puramente determinístico baseado na Teoria dos Grafos, este projeto não gera "pesos de modelo" (Model Weights) típicos de redes neurais. O conhecimento do sistema reside em sua matriz de adjacência pré-processada e na *Lookup Table* de veículos.

### Estrutura do Repositório
*   **`main.py`:** Script de ETL. Responsável por ler os Shapefiles brutos, criar a topologia matemática e exportar a matriz de adjacência final.
*   **`estrela.py`:** O motor de roteamento em tempo real. Contém o geocodificador (busca flexível de nomes de ruas), a lógica do NBA*, e o sistema de plotagem gráfica via `matplotlib`.
*   **`grafo_curitiba_carbono.csv`:** Artefato gerado pelo `main.py`. Contém mais de 40 mil arestas formatadas com distâncias e deltas de altimetria.
*   **`CO2 Emissions_Canada.csv`:** Tabela estática de emissão de carbono por modelo veicular.
*   **Arquivos de Debug (`explorar_mapa.py`, `debug_nomes.py`, `ver_colunas.py`,`ver_grafo.py`  ):** Scripts utilitários de validação topológica e inspeção de dados.

### Reprodução e Acesso aos Dados
Os dados primários para execução deste baseline ultrapassam o limite de repositórios padrão devido à resolução do Shapefile. 
*   **Bases oficiais:** Podem ser baixadas no Portal do IPPUC (https://ippuc.org.br/geodownloads/geo.htm). É obrigatória a escolha da projeção **SIRGAS**.
*   **Base congelada do projeto:** Disponível no drive do grupo (https://drive.google.com/file/d/1G_TyDlhXrZ-uHM17ONIaw-5KRDzijHaS/view?usp=sharing).

---

## 4. Cronograma de Execução

| Etapa | Descrição da Atividade | Status |
| :--- | :--- | :--- |
| **Fase 1** | Pesquisa de viabilidade e obtenção dos dados primários (IPPUC e Kaggle). | Concluído |
| **Fase 2** | Construção do pipeline ETL (`main.py`) e interpolação espacial (R-Tree). | Concluído |
| **Fase 3** | Implementação do algoritmo Bidirecional (NBA*) e geocodificador de texto. | Concluído |
| **Fase 4** | Refatoração estrutural para sistema Multiobjetivo (Distância vs Emissão). | Concluído |
| **Fase 5** | Testes de consistência topológica (identificação e tratamento de ilhas). | Em Andamento |
| **Fase 6** | Embasamento em artigos cíentificos sobre caminhões para desenvolver uma nova fórmula única de emissão de carbono. | Em Andamento |
| **Fase 7** | Substituir o dataset de emissão de carbono de carros para especializar o algoritmo em rotas para caminhões. | A iniciar |
| **Fase 8** | Análise de resultados, validação matemática das rotas e geração de logs. | A Iniciar |
| **Fase 9** | Redação do documento final, formatação acadêmica e defesa. | A Iniciar |
---
## Exemplo de funcionamento
**Entrada no Código:**
```python
carro_escolhido = "CHEVROLET CRUZE" 
print("\n--- SISTEMA DE ROTAS DE CURITIBA (NBA*) ---")
rua_origem = "R. AMADEU ASSAD YASSIM"
rua_destino = "R. GEN. LUIZ CARLOS PEREIRA TOURINHO"
```
### Saida no terminal

```plaintext

--- SISTEMA DE ROTAS DE CURITIBA (NBA*) ---

Executando o motor de roteamento Bidirecional...

[SUCESSO!] Rota gerada passando por 240 cruzamentos (nós).
[RESULTADO] Emissão total estimada: 4888.73 gramas de CO2

[GERANDO INSTRUÇÕES DE NAVEGAÇÃO...]

--- PASSO A PASSO DA ROTA ---
-> Saia pela: R. PURÚS
-> Entre na: R. GUSTAVO RATTMAN
-> Entre na: R. FAGUNDES VARELA
-> Entre na: R. AUGUSTO STRESSER
-> Entre na: R. FLÁVIO DALLEGRAVE
-> Entre na: R. ZEILA MOURA DOS SANTOS
-> Entre na: AV. PRES. AFFONSO CAMARGO
-> Entre na: VIADUTO DO CAPANEMA
-> Entre na: AV. DR. DARIO LOPES DOS SANTOS
-> Entre na: R. CONS. LAURINDO
-> Entre na: R. CHILE
-> Entre na: AV. MAL. FLORIANO PEIXOTO
-> Entre na: AV. PRES. KENNEDY
-> Entre na: AV. REPÚBLICA ARGENTINA
-> Entre na: AV. WINSTON CHURCHILL
-> Entre na: ROD. BR-476
-> Entre na: R. NICOLA PELLANDA
-> Entre na: R. STELLA ANTONIASSI GROCHEWSKI
-> Entre na: R. MARIANO SNAK
-> Entre na: R. BRASÍLIO PERY MOREIRA
-> Entre na: ROD. BR-476
-> Entre na: ROD. BR-116 - RÉGIS BITTENCOURT
-> Entre na: R. VER. ANGELO BURBELLO
-> Entre na: ESTR. DEL. BRUNO DE ALMEIDA
-> Entre na: R. JÚLIO PEREIRA SOBRINHO
-> Entre na: R. EMANOEL ERNESTO BERTOLDI
-> Entre na: R. CRESCÊNCIA BERTHOLDI
-> Entre na: R. LUCAS CARVALHO
-> Entre na: R. GEN. LUIZ CARLOS PEREIRA TOURINHO
-> [CHEGOU AO DESTINO]

Desenhando o mapa de Curitiba com a rota gerada...

```

<img width="1636" height="909" alt="image" src="https://github.com/user-attachments/assets/a4cc73b6-55cd-46d9-8636-ff2d370405e3" />

    



