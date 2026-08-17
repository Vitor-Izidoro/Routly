import pandas as pd
import math
import heapq
import matplotlib.pyplot as plt

def carregar_grafos_direcionais(caminho_csv):
    print("Montando grafos direcionais (Ida e Volta) na memória para NBA*...")
    df = pd.read_csv(caminho_csv)
    grafo_ida = {}
    grafo_volta = {}
    
    for _, row in df.iterrows():
        u = (row['origem_x'], row['origem_y'])
        v = (row['destino_x'], row['destino_y'])
        
        if u not in grafo_ida: 
            grafo_ida[u] = []
            grafo_volta[u] = []
        if v not in grafo_ida: 
            grafo_ida[v] = []
            grafo_volta[v] = []
            
        c_uv = row['custo_carbono']
        
        delta_z_volta = -row['delta_z']
        if delta_z_volta > 0:
            c_vu = row['distancia_m'] + (delta_z_volta * 5.0)
        else:
            c_vu = row['distancia_m']
            
        # Aresta u -> v
        grafo_ida[u].append((v, c_uv))
        grafo_volta[v].append((u, c_uv))
        
        # Aresta v -> u
        grafo_ida[v].append((u, c_vu))
        grafo_volta[u].append((v, c_vu))
        
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

def heuristica(no_atual, no_objetivo):
    return math.hypot(no_objetivo[0] - no_atual[0], no_objetivo[1] - no_atual[1])

def nba_estrela(grafo_ida, grafo_volta, inicio, destino):
    if inicio not in grafo_ida or destino not in grafo_ida:
        return None, float('inf')

    # Filas de prioridade para a busca Forward (F) e Backward (B)
    open_F = []
    heapq.heappush(open_F, (heuristica(inicio, destino), 0, inicio)) # (f, g, node)
    g_F = {inicio: 0}
    came_from_F = {}
    closed_F = set()
    
    open_B = []
    heapq.heappush(open_B, (heuristica(destino, inicio), 0, destino))
    g_B = {destino: 0}
    came_from_B = {}
    closed_B = set()
    
    best_path_cost = float('inf')
    meeting_node = None
    
    while open_F and open_B:
        f_f, current_g_f, u_f = open_F[0]
        f_b, current_g_b, u_b = open_B[0]
        
        # Condição de parada da busca bidirecional
        if current_g_f + current_g_b >= best_path_cost:
            break
            
        # Expande a menor fronteira para otimizar espaço de busca
        if len(open_F) < len(open_B):
            _, current_g, u = heapq.heappop(open_F)
            if u in closed_F: continue
            closed_F.add(u)
            
            for v, custo in grafo_ida.get(u, []):
                tentative_g = current_g + custo
                if v not in g_F or tentative_g < g_F[v]:
                    g_F[v] = tentative_g
                    came_from_F[v] = u
                    heapq.heappush(open_F, (tentative_g + heuristica(v, destino), tentative_g, v))
                    
                    if v in g_B:
                        if tentative_g + g_B[v] < best_path_cost:
                            best_path_cost = tentative_g + g_B[v]
                            meeting_node = v
        else:
            _, current_g, u = heapq.heappop(open_B)
            if u in closed_B: continue
            closed_B.add(u)
            
            for v, custo in grafo_volta.get(u, []):
                tentative_g = current_g + custo
                if v not in g_B or tentative_g < g_B[v]:
                    g_B[v] = tentative_g
                    came_from_B[v] = u
                    heapq.heappush(open_B, (tentative_g + heuristica(v, inicio), tentative_g, v))
                    
                    if v in g_F:
                        if tentative_g + g_F[v] < best_path_cost:
                            best_path_cost = tentative_g + g_F[v]
                            meeting_node = v
                            
    if meeting_node is None:
        return None, float('inf')
        
    # Reconstruir caminho a partir do meeting_node
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

def plotar_rota_no_mapa(df_arestas, rota_nos):
    print("\nDesenhando o mapa de Curitiba com a rota gerada (Roxa)...")
    plt.figure(figsize=(10, 10))
    
    plt.plot(
        [df_arestas['origem_x'], df_arestas['destino_x']], 
        [df_arestas['origem_y'], df_arestas['destino_y']], 
        color='grey', alpha=0.1, linewidth=0.5
    )
    
    if rota_nos:
        x_rota = [no[0] for no in rota_nos]
        y_rota = [no[1] for no in rota_nos]
        plt.plot(x_rota, y_rota, color='purple', linewidth=3, label='Melhor Rota (NBA*)')
        
        plt.scatter(x_rota[0], y_rota[0], color='green', s=100, label='Início', zorder=5)
        plt.scatter(x_rota[-1], y_rota[-1], color='red', s=100, label='Destino', zorder=5)
        
    plt.title("Grafo de Ruas - Curitiba (Rotas Ecológicas)")
    plt.axis('equal')
    plt.legend()
    plt.show()

if __name__ == "__main__":
    caminho_csv = "grafo_curitiba_carbono.csv"
    
    print("\nCarregando banco de dados...")
    df_arestas = pd.read_csv(caminho_csv)
    
    grafo_ida, grafo_volta = carregar_grafos_direcionais(caminho_csv)
    indice_ruas = carregar_indice_ruas(caminho_csv)
    
    print("\n--- SISTEMA DE ROTAS DE CURITIBA (NBA*) ---")
    
    rua_origem = "R. AMADEU ASSAD YASSIM"
    rua_destino = "R. GEN. LUIZ CARLOS PEREIRA TOURINHO"
    
    print(f"\nBuscando ponto inicial na: {rua_origem}")
    inicio = pegar_um_no_da_rua(indice_ruas, rua_origem)
    
    print(f"Buscando ponto final na: {rua_destino}")
    destino = pegar_um_no_da_rua(indice_ruas, rua_destino)
    
    if inicio and destino:
        print("\nExecutando o motor ecológico Bidirecional (NBA*)...")
        rota, custo_total = nba_estrela(grafo_ida, grafo_volta, inicio, destino)
        
        if rota:
            print(f"\n[SUCESSO!] Rota gerada passando por {len(rota)} cruzamentos (nós).")
            print(f"[RESULTADO] Custo total estimado: {custo_total:.2f}")
            
            instrucoes = gerar_instrucoes_de_rota(rota, df_arestas)
            print("\n--- PASSO A PASSO DA ROTA ---")
            for passo in instrucoes:
                print(passo)
            print("-> [CHEGOU AO DESTINO]")
            
            plotar_rota_no_mapa(df_arestas, rota)
            
        else:
            print("\n[AVISO] Caminho impossível.")