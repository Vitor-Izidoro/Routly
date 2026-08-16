import pandas as pd
import math
import heapq

def carregar_grafo(caminho_csv):
    print("Montando o grafo na memória...")
    df = pd.read_csv(caminho_csv)
    grafo = {}
    
    for _, row in df.iterrows():
        origem = (row['origem_x'], row['origem_y'])
        destino = (row['destino_x'], row['destino_y'])
        
        if origem not in grafo: grafo[origem] = []
        if destino not in grafo: grafo[destino] = []
        
        grafo[origem].append((destino, row['custo_carbono']))
        
        delta_z_volta = -row['delta_z']
        if delta_z_volta > 0:
            custo_volta = row['distancia_m'] + (delta_z_volta * 5.0)
        else:
            custo_volta = row['distancia_m']
            
        grafo[destino].append((origem, custo_volta))
        
    return grafo

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

# --- NOVA FUNÇÃO SIMPLIFICADA (Pegar um nó qualquer da rua) ---
def pegar_um_no_da_rua(indice_ruas, nome_rua_exato):
    nos = indice_ruas.get(nome_rua_exato)
    if not nos:
        print(f"Erro: Rua '{nome_rua_exato}' não encontrada no índice.")
        return None
    # Retorna a primeira coordenada associada a esta rua
    return list(nos)[0]

def heuristica(no_atual, no_objetivo):
    return math.hypot(no_objetivo[0] - no_atual[0], no_objetivo[1] - no_atual[1])

def a_estrela(grafo, inicio, objetivo):
    open_set = []
    heapq.heappush(open_set, (0, inicio))
    came_from = {}
    
    g_score = {no: float('inf') for no in grafo}
    g_score[inicio] = 0
    
    closed_set = set()
    
    while open_set:
        _, atual = heapq.heappop(open_set)
        
        if atual == objetivo:
            caminho = [atual]
            while atual in came_from:
                atual = came_from[atual]
                caminho.append(atual)
            return caminho[::-1], g_score[objetivo]
            
        if atual in closed_set:
            continue
        closed_set.add(atual)
        
        for vizinho, custo_aresta in grafo[atual]:
            if vizinho in closed_set:
                continue
                
            tentativa_g_score = g_score[atual] + custo_aresta
            
            if tentativa_g_score < g_score[vizinho]:
                came_from[vizinho] = atual
                g_score[vizinho] = tentativa_g_score
                f_score = tentativa_g_score + heuristica(vizinho, objetivo)
                heapq.heappush(open_set, (f_score, vizinho))
                
    return None, float('inf')
def gerar_instrucoes_de_rota(rota_nos, df_arestas):
    """
    Pega a lista matemática de nós (rota_nos) e converte em texto legível.
    Precisamos do DataFrame original (df_arestas) para resgatar o nome da rua 
    que conecta o Nó(A) ao Nó(B).
    """
    print("\n[GERANDO INSTRUÇÕES DE NAVEGAÇÃO...]")
    instrucoes = []
    rua_atual = None
    
    # Vamos iterar pela rota pegando pares de nós (atual e o próximo)
    for i in range(len(rota_nos) - 1):
        no_atual = rota_nos[i]
        proximo_no = rota_nos[i + 1]
        
        # Procura no CSV qual rua conecta exatamente esses dois nós
        # (Lembrando que o grafo funciona nos dois sentidos)
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
            
        # Lógica para imprimir apenas quando mudar de rua!
        if nome_da_rua != rua_atual:
            if rua_atual is None:
                instrucoes.append(f"-> Saia pela: {nome_da_rua}")
            else:
                instrucoes.append(f"-> Entre na: {nome_da_rua}")
            rua_atual = nome_da_rua
            
    return instrucoes

""" #ESTE AQUI NÃO PRINTA O CAMINHO COMPLETO
if __name__ == "__main__":
    caminho_csv = "grafo_curitiba_carbono.csv"
    meu_grafo = carregar_grafo(caminho_csv)
    indice_ruas = carregar_indice_ruas(caminho_csv)
    
    print("\n--- SISTEMA DE ROTAS DE CURITIBA ---")
    
    # Nomes exatos copiados do seu log do debug_nomes.py!
    rua_origem = "R. VER. ANTÔNIO DOMAKOSKI"
    rua_destino = "R. HASDRUBAL BELLEGARD"
    
    print(f"\nBuscando ponto inicial na: {rua_origem}")
    inicio = pegar_um_no_da_rua(indice_ruas, rua_origem)
    
    print(f"Buscando ponto final na: {rua_destino}")
    destino = pegar_um_no_da_rua(indice_ruas, rua_destino)
    
    if inicio and destino:
        print(f"\nCoordenadas carregadas!")
        print(f"  Origem (X,Y): {inicio[0]:.2f}, {inicio[1]:.2f}")
        print(f"  Destino (X,Y): {destino[0]:.2f}, {destino[1]:.2f}")
        
        print("\nExecutando o motor ecológico A*...")
        rota, custo_total = a_estrela(meu_grafo, inicio, destino)
        
        if rota:
            print(f"\n[SUCESSO!] Rota gerada passando por {len(rota)} cruzamentos (nós).")
            print(f"[RESULTADO] Custo total estimado (Distância + Penalidade Z): {custo_total:.2f}")
        else:
            print("\n[AVISO] Caminho impossível (as ruas podem estar em ilhas desconectadas da malha viária).")
            
    """
            
if __name__ == "__main__":
    caminho_csv = "grafo_curitiba_carbono.csv"
    
    print("\nCarregando banco de dados...")
    # Precisamos carregar o DataFrame cru também para buscar os nomes na instrução
    df_arestas = pd.read_csv(caminho_csv)
    
    meu_grafo = carregar_grafo(caminho_csv)
    indice_ruas = carregar_indice_ruas(caminho_csv)
    
    print("\n--- SISTEMA DE ROTAS DE CURITIBA ---")
    
    # Nomes exatos do log. Vamos usar ruas próximas!
    rua_origem = "R. JOÃO CHEDE"
    rua_destino = "R. CYRO CORREIA PEREIRA"
    
    print(f"\nBuscando ponto inicial na: {rua_origem}")
    inicio = pegar_um_no_da_rua(indice_ruas, rua_origem)
    
    print(f"Buscando ponto final na: {rua_destino}")
    destino = pegar_um_no_da_rua(indice_ruas, rua_destino)
    
    if inicio and destino:
        print("\nExecutando o motor ecológico A*...")
        rota, custo_total = a_estrela(meu_grafo, inicio, destino)
        
        if rota:
            print(f"\n[SUCESSO!] Rota gerada passando por {len(rota)} cruzamentos (nós).")
            print(f"[RESULTADO] Custo total estimado: {custo_total:.2f}")
            
            # --- CHAMA A FUNÇÃO DE TEXTO AQUI ---
            instrucoes = gerar_instrucoes_de_rota(rota, df_arestas)
            print("\n--- PASSO A PASSO DA ROTA ---")
            for passo in instrucoes:
                print(passo)
            print("-> [CHEGOU AO DESTINO]")
            
        else:
            print("\n[AVISO] Caminho impossível.")