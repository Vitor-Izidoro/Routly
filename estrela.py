import pandas as pd
import math
import heapq
import matplotlib.pyplot as plt

def carregar_catalogo_veiculos(caminho_dataset):
    print("Carregando catálogo de emissões de veículos do dataset...")
    df_carros = pd.read_csv(caminho_dataset)
    catalogo = {}
    
    # Ajuste os nomes das colunas conforme o seu CSV (Make, Model, CO2 Emissions(g/km))
    for _, row in df_carros.iterrows():
        nome_carro = f"{row.get('Make', '')} {row.get('Model', '')}".upper().strip()
        
        # Pega a emissão, se a coluna exata variar, ajuste o nome aqui:
        emissao = row.get('CO2 Emissions(g/km)', row.get('CO2_EMISSIONS', 200.0))
        catalogo[nome_carro] = float(emissao)
        
    return catalogo



# alterar no futuro para ficar mais otimizado
# o que fazer: separar em funções diferentes, um para o calculo de distancia do caminho e outra para a taxa de emissão de co2
def carregar_grafos_direcionais(caminho_csv, taxa_emissao_g_km):
    
    print(f"Montando grafos multiobjetivo na memória (Base: {taxa_emissao_g_km} g/km)...")
    df = pd.read_csv(caminho_csv)
    grafo_ida = {}
    grafo_volta = {}
    
    for _, row in df.iterrows():
        u = (row['origem_x'], row['origem_y'])
        v = (row['destino_x'], row['destino_y'])
        
        if u not in grafo_ida: 
            grafo_ida[u] = []; grafo_volta[u] = []
        if v not in grafo_ida: 
            grafo_ida[v] = []; grafo_volta[v] = []
            
        # Custo 1: Distância Pura (metros)
        c_dist_ida = row['distancia_m']
        c_dist_volta = row['distancia_m']
        
        # Custo 2: Emissão Real (Gramas de CO2)
        dist_km = row['distancia_m'] / 1000.0
        emissao_base = dist_km * taxa_emissao_g_km
        
        delta_z_ida = row['delta_z']
        c_emissao_ida = emissao_base * (1 + (delta_z_ida * 0.015)) if delta_z_ida > 0 else emissao_base
            
        delta_z_volta = -row['delta_z']
        c_emissao_volta = emissao_base * (1 + (delta_z_volta * 0.015)) if delta_z_volta > 0 else emissao_base
            
        grafo_ida[u].append((v, c_dist_ida, c_emissao_ida))
        grafo_volta[v].append((u, c_dist_ida, c_emissao_ida))
        
        grafo_ida[v].append((u, c_dist_volta, c_emissao_volta))
        grafo_volta[u].append((v, c_dist_volta, c_emissao_volta))
        
    return grafo_ida, grafo_volta

def carregar_indice_ruas(caminho_csv):
    print("Montando índice de ruas...")
    df = pd.read_csv(caminho_csv)
    indice_ruas = {}
    
    for _, row in df.iterrows():
        nome = str(row['nome_rua']).strip()
        if nome not in indice_ruas:
            indice_ruas[nome] = set()
            
        indice_ruas[nome].add((row['origem_x'], row['origem_y']))
        indice_ruas[nome].add((row['destino_x'], row['destino_y']))
        
    return indice_ruas

def pegar_um_no_da_rua(indice_ruas, nome_rua_exato):
    nos = indice_ruas.get(nome_rua_exato)
    if not nos:
        print(f"Erro: Rua '{nome_rua_exato}' não encontrada no índice.")
        return None
    return list(nos)[0]

def heuristica(no_atual, no_objetivo, modo, taxa_emissao_g_km):
    distancia_metros = math.hypot(no_objetivo[0] - no_atual[0], no_objetivo[1] - no_atual[1])
    
    if modo == "distancia":
        return distancia_metros
    elif modo == "emissao":
        distancia_km = distancia_metros / 1000.0
        return distancia_km * taxa_emissao_g_km
    return 0

def nba_estrela(grafo_ida, grafo_volta, inicio, destino, modo, taxa_emissao):
    if inicio not in grafo_ida or destino not in grafo_ida:
        return None, float('inf')

    open_F = []
    h_init_F = heuristica(inicio, destino, modo, taxa_emissao)
    heapq.heappush(open_F, (h_init_F, 0, inicio))
    g_F = {inicio: 0}
    came_from_F = {}
    closed_F = set()
    
    open_B = []
    h_init_B = heuristica(destino, inicio, modo, taxa_emissao)
    heapq.heappush(open_B, (h_init_B, 0, destino))
    g_B = {destino: 0}
    came_from_B = {}
    closed_B = set()
    
    best_path_cost = float('inf')
    meeting_node = None
    
    while open_F and open_B:
        f_f, current_g_f, u_f = open_F[0]
        f_b, current_g_b, u_b = open_B[0]
        
        if current_g_f + current_g_b >= best_path_cost:
            break
            
        if len(open_F) < len(open_B):
            _, current_g, u = heapq.heappop(open_F)
            if u in closed_F: continue
            closed_F.add(u)
            
            for v, c_dist, c_emissao in grafo_ida.get(u, []):
                custo = c_dist if modo == "distancia" else c_emissao
                tentative_g = current_g + custo
                
                if v not in g_F or tentative_g < g_F[v]:
                    g_F[v] = tentative_g
                    came_from_F[v] = u
                    h_v = heuristica(v, destino, modo, taxa_emissao)
                    heapq.heappush(open_F, (tentative_g + h_v, tentative_g, v))
                    
                    if v in g_B:
                        if tentative_g + g_B[v] < best_path_cost:
                            best_path_cost = tentative_g + g_B[v]
                            meeting_node = v
        else:
            _, current_g, u = heapq.heappop(open_B)
            if u in closed_B: continue
            closed_B.add(u)
            
            for v, c_dist, c_emissao in grafo_volta.get(u, []):
                custo = c_dist if modo == "distancia" else c_emissao
                tentative_g = current_g + custo
                
                if v not in g_B or tentative_g < g_B[v]:
                    g_B[v] = tentative_g
                    came_from_B[v] = u
                    h_v = heuristica(v, inicio, modo, taxa_emissao)
                    heapq.heappush(open_B, (tentative_g + h_v, tentative_g, v))
                    
                    if v in g_F:
                        if tentative_g + g_F[v] < best_path_cost:
                            best_path_cost = tentative_g + g_F[v]
                            meeting_node = v
                            
    if meeting_node is None:
        return None, float('inf')
        
    path_F = []
    curr = meeting_node
    while curr in came_from_F:
        path_F.append(curr)
        curr = came_from_F[curr]
    path_F.append(inicio)
    path_F.reverse()
    
    path_B = []
    curr = came_from_B.get(meeting_node)
    while curr is not None:
        path_B.append(curr)
        curr = came_from_B.get(curr)
        
    return path_F + path_B, best_path_cost

def gerar_instrucoes_de_rota(rota_nos, df_arestas):
    print("\n[GERANDO INSTRUÇÕES DE NAVEGAÇÃO...]")
    instrucoes = []
    rua_atual = None
    
    for i in range(len(rota_nos) - 1):
        no_atual = rota_nos[i]
        proximo_no = rota_nos[i + 1]
        
        aresta_ida = df_arestas[
            (df_arestas['origem_x'] == no_atual[0]) & 
            (df_arestas['origem_y'] == no_atual[1]) & 
            (df_arestas['destino_x'] == proximo_no[0]) & 
            (df_arestas['destino_y'] == proximo_no[1])
        ]
        
        aresta_volta = df_arestas[
            (df_arestas['destino_x'] == no_atual[0]) & 
            (df_arestas['destino_y'] == no_atual[1]) & 
            (df_arestas['origem_x'] == proximo_no[0]) & 
            (df_arestas['origem_y'] == proximo_no[1])
        ]
        
        if not aresta_ida.empty:
            nome_da_rua = aresta_ida.iloc[0]['nome_rua']
        elif not aresta_volta.empty:
            nome_da_rua = aresta_volta.iloc[0]['nome_rua']
        else:
            nome_da_rua = "RUA DESCONHECIDA"
            
        if nome_da_rua != rua_atual:
            if rua_atual is None:
                instrucoes.append(f"-> Saia pela: {nome_da_rua}")
            else:
                instrucoes.append(f"-> Entre na: {nome_da_rua}")
            rua_atual = nome_da_rua
            
    return instrucoes

def plotar_rota_no_mapa(df_arestas, rota_nos, modo_escolhido):
    print("\nDesenhando o mapa de Curitiba com a rota gerada...")
    plt.figure(figsize=(10, 10))
    
    plt.plot(
        [df_arestas['origem_x'], df_arestas['destino_x']], 
        [df_arestas['origem_y'], df_arestas['destino_y']], 
        color='grey', alpha=0.1, linewidth=0.5
    )
    
    if rota_nos:
        x_rota = [no[0] for no in rota_nos]
        y_rota = [no[1] for no in rota_nos]
        
        cor_rota = 'green' if modo_escolhido == 'emissao' else 'blue'
        plt.plot(x_rota, y_rota, color=cor_rota, linewidth=3, label=f'Melhor Rota ({modo_escolhido.upper()})')
        
        plt.scatter(x_rota[0], y_rota[0], color='green', s=100, label='Início', zorder=5)
        plt.scatter(x_rota[-1], y_rota[-1], color='red', s=100, label='Destino', zorder=5)
        
    plt.title(f"Grafo de Ruas - Curitiba (Otimizado para {modo_escolhido.upper()})")
    plt.axis('equal')
    plt.legend()
    plt.show()

if __name__ == "__main__":
    caminho_csv_rotas = "grafo_curitiba_carbono.csv"
    caminho_csv_carros = "CO2 Emissions_Canada.csv"
    
    # 1. Menu de Configuração
    # Opções de modo: "distancia" ou "emissao"
    modo_escolhido = "emissao" 
    
    # Tente digitar um nome exatamente como está no CSV do Kaggle. 
    # Caso não exista, o fallback de 200.0 g/km será usado.
    carro_escolhido = "CHEVROLET CRUZE" 
    
    catalogo_carros = carregar_catalogo_veiculos(caminho_csv_carros)
    taxa_emissao = catalogo_carros.get(carro_escolhido, 200.0)
    
    print(f"\n[CONFIG] Veículo: {carro_escolhido} | Emissão Base: {taxa_emissao} g/km")
    print(f"[CONFIG] Otimizando rota para: {modo_escolhido.upper()}")
    
    # 2. Carrega Dados
    df_arestas = pd.read_csv(caminho_csv_rotas)
    grafo_ida, grafo_volta = carregar_grafos_direcionais(caminho_csv_rotas, taxa_emissao)
    indice_ruas = carregar_indice_ruas(caminho_csv_rotas)
    
    # 3. Define Origem e Destino
    print("\n--- SISTEMA DE ROTAS DE CURITIBA (NBA*) ---")
    rua_origem = "R. AMADEU ASSAD YASSIM"
    rua_destino = "R. GEN. LUIZ CARLOS PEREIRA TOURINHO"
    
    inicio = pegar_um_no_da_rua(indice_ruas, rua_origem)
    destino = pegar_um_no_da_rua(indice_ruas, rua_destino)
    
    # 4. Executa a Busca
    if inicio and destino:
        print("\nExecutando o motor de roteamento Bidirecional...")
        rota, custo_total = nba_estrela(grafo_ida, grafo_volta, inicio, destino, modo_escolhido, taxa_emissao)
        
        if rota:
            print(f"\n[SUCESSO!] Rota gerada passando por {len(rota)} cruzamentos (nós).")
            
            # Formatação inteligente do print baseada no modo escolhido
            if modo_escolhido == "distancia":
                print(f"[RESULTADO] Distância total estimada: {custo_total:.2f} metros")
            else:
                print(f"[RESULTADO] Emissão total estimada: {custo_total:.2f} gramas de CO2")
            
            instrucoes = gerar_instrucoes_de_rota(rota, df_arestas)
            print("\n--- PASSO A PASSO DA ROTA ---")
            for passo in instrucoes:
                print(passo)
            print("-> [CHEGOU AO DESTINO]")
            
            plotar_rota_no_mapa(df_arestas, rota, modo_escolhido)
            
        else:
            print("\n[AVISO] Caminho impossível.")