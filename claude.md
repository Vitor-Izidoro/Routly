Atue como um Engenheiro de Software Sênior e Pesquisador em Otimização Multiobjetivo. Sua tarefa é refatorar a arquitetura de entrada do projeto **Routly** e implementar uma suíte completa de **Validação Científica e Visualização** para comprovação de TCC, inspirada na metodologia de Otimização Multiobjetivo (Fronteira de Pareto / MCDM) do Prof. Dr. Gilberto Reynoso-Meza.

Antes de escrever código, **leia e analise os seguintes arquivos do repositório** para respeitar todas as assinaturas de funções, classes e estruturas de dados existentes:
- `main.py`, `executar.py`, `algoritmos.py`, `estrela.py`, `mapa.py`
- `emissoes.py`, `veiculos.py`, `cenarios_co2.py`, `dados_co2.py`, `vtcpfm.py`
- `experimentos/avaliar_eficacia.py`, `experimentos/validar_conversao_co2.py`
- `tests/` e `validar.sh`

Execute o plano de trabalho abaixo dividido em 3 etapas:

---

### ETAPA 1: Preservação do ETL e Novo `main.py` Interativo (CLI Central)
1. **Separar o ETL do IPPUC:**
   - Mova a lógica atual do `main.py` (que carrega os Shapefiles brutos do IPPUC e gera o `grafo_curitiba_carbono.csv`) para um novo módulo chamado `etl_ippuc.py` (ou mantenha como função isolada), adicionando tratamento de erros amigável (`try/except`) caso os arquivos `.shp` do IPPUC não estejam presentes na máquina, avisando que o usuário pode usar o `grafo_curitiba_carbono.csv` já existente.
2. **Reconstruir o `main.py` como um Menu Principal Interativo e Organizado:**
   - O novo `main.py` deve verificar automaticamente se `grafo_curitiba_carbono.csv` existe (indicando status `[OK]` ou `[AUSENTE]` no cabeçalho do menu).
   - Estruture o menu em categorias claras:

   **[1] Preparação de Dados e Mapas (ETL)**
   - `1.1` Gerar/Recriar Grafo Base a partir dos Shapefiles do IPPUC (verifica se já existe; se não existir ou se o usuário quiser forçar, roda o ETL).
   - `1.2` Gerar/Visualizar Mapa Interativo de Rotas (`mapa.py`).

   **[2] Execução e Roteamento (Todas as opções do `executar.py`)**
   - Incorpore ou exponha em submenus **todas** as funcionalidades, modos de busca (A*, Dijkstra, etc.), escolha de pontos Origem-Destino e cenários de carga/veículos presentes hoje em `executar.py`, `estrela.py` e `cenarios_co2.py`.

   **[3] Comprovações Científicas e Validação (Menu de TCC)**
   - `3.1` Executar Validação VTCPFM / CMEM e Conversão de CO2 (integra os scripts do último commit: `vtcpfm.py`, `experimentos/validar_conversao_co2.py` e `experimentos/avaliar_eficacia.py`).
   - `3.2` Executar Suíte de Testes Automatizados (`pytest` em `tests/`).
   - `3.3` Gerar Análise Multiobjetivo e Fronteira de Pareto (Método Gilberto Meza).
   - `3.4` Gerar Perfil Altimétrico Comparativo (Elevação vs. CO2 Acumulado).
   - `3.5` Executar Simulação de Monte Carlo + Teste Estatístico de Wilcoxon (Validação em Larga Escala).
   - `3.6` **RODAR TUDO (Pipeline Completo de Comprovação)** -> Executa 3.1 a 3.5 e salva todos os gráficos e relatórios na pasta `resultados_validacao/`.

---

### ETAPA 2: Implementação do Módulo de Comprovação Científica (`experimentos/comprovacao_cientifica.py`)
Crie o arquivo `experimentos/comprovacao_cientifica.py` (e adicione `matplotlib`, `scipy` e `numpy` ao `requirements.txt` se necessário). Todos os gráficos devem ter qualidade de publicação acadêmica (300 DPI, fontes legíveis, grid sutil, legendas claras) e ser salvos em `resultados_validacao/`. Implemente as 4 análises abaixo:

1. **Otimização Multiobjetivo e Fronteira de Pareto (Abordagem Gilberto Reynoso-Meza):**
   - Implemente uma busca A* ponderada onde o custo da aresta $e$ combina distância normalizada $\hat{d}(e)$ e emissão de $\text{CO}_2$ normalizada $\hat{E}_{\text{CO}_2}(e)$:
     $$C(e) = (1 - \alpha) \cdot \hat{d}(e) + \alpha \cdot \hat{E}_{\text{CO}_2}(e)$$
   - Para um par Origem-Destino representativo de Curitiba (ou escolhido pelo usuário), varie $\alpha$ em pelo menos 11 passos de `0.0` (Rota Mais Curta / Baseline GPS) a `1.0` (Rota Mais Ecológica / Routly).
   - Identifique automaticamente a **Solução de Compromisso (Joelho de Pareto / Knee Point)** (menor distância euclidiana até o Ponto Utopia/Ideal onde Distância e CO2 são mínimos simultaneamente).
   - Gere o gráfico `pareto_fronteira.png` (Eixo X: Distância em km, Eixo Y: Emissões em kg ou g de CO2), destacando o Baseline ($\alpha=0$), o Routly Puro ($\alpha=1$) e o Ponto de Compromisso Ideal, além de exportar uma tabela CSV com o trade-off (% de CO2 economizado vs. % de distância adicional).

2. **Perfil Altimétrico Comparativo (Prova Física Direta):**
   - Para a mesma rota, extraia a sequência de nós/arestas da **Rota Mais Curta ($\alpha=0$)** e da **Rota Ecológica Routly ($\alpha=1$)**.
   - Gere uma figura com 2 subplots empilhados (`perfil_altimetrico_comparativo.png`):
     - **Subplot Superior:** Altitude (m) vs. Distância Acumulada (km) das duas rotas (mostrando a Rota Ecológica contornando os picos de inclinação crítica de Curitiba).
     - **Subplot Inferior:** Emissão de $\text{CO}_2$ Acumulada vs. Distância Acumulada (km) (mostrando o disparo da emissão na rota curta durante as subidas íngremes vs. o crescimento suave na rota Routly).

3. **Simulação de Monte Carlo + Teste Pareado de Wilcoxon (Significância Estatística):**
   - Sorteie $N$ pares Origem-Destino válidos no grafo (padrão $N=100$, configurável) garantindo que exista caminho entre eles.
   - Para cada par, calcule a Rota Mais Curta ($J_1$) e a Rota Ecológica ($J_2$) para os 3 cenários de carga do caminhão (ex: Vazio, Meia Carga, Carregado, conforme `veiculos.py` / `cenarios_co2.py`).
   - Aplique o **Teste de Wilcoxon Signed-Rank** (`scipy.stats.wilcoxon`) comparando as emissões de $J_1$ vs $J_2$ para obter o $p\text{-valor}$ exato.
   - Gere um gráfico de Boxplot (`boxplot_cenarios_carga.png`) mostrando a distribuição da redução percentual de $\text{CO}_2$ (%) nos 3 cenários de peso, anotando o $p\text{-valor}$ e a mediana no gráfico, e salve um relatório resumo em `resultados_validacao/relatorio_estatistico.md`.

4. **Gráfico de Paridade Física (Modelo Routly vs. VTCPFM/CMEM):**
   - Integre com os dados de `vtcpfm.py` / `validacao_cmem.json` para plottar a curva de consumo/emissão em função da inclinação da via (*grade* de -6% a +6%), sobrepondo a curva do modelo do projeto com os pontos da literatura e exibindo no título/legenda o $R^2$ e o erro médio ($MAPE$), salvando em `resultados_validacao/validacao_fisica_grade.png`.

---

### ETAPA 3: Testes e Validação Final
1. Certifique-se de que todos os testes existentes em `tests/` continuam passando (`pytest`).
2. Crie um teste básico para garantir que o menu e as funções de comprovação não possuem erros de importação.
3. Ao finalizar, execute a opção de validação para gerar a pasta `resultados_validacao/` com os primeiros gráficos e me mostre um resumo dos arquivos gerados e das métricas obtidas.