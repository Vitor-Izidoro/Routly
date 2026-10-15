import pandas as pd
import networkx as nx
import random

def carregar_grafo(caminho_csv):
    print("Carregando a malha viária de Curitiba...")
    df = pd.read_csv(caminho_csv)
    
    df['origem_id'] = list(zip(df['origem_x'], df['origem_y']))
    df['destino_id'] = list(zip(df['destino_x'], df['destino_y']))
    
    G = nx.from_pandas_edgelist(
        df, 
        source='origem_id', 
        target='destino_id', 
        edge_attr=['distancia_m', 'custo_carbono', 'nome_rua', 'delta_z'], # Adicionado delta_z aqui
        create_using=nx.DiGraph()
    )
    
    print(f"Grafo montado com sucesso: {G.number_of_nodes()} nós e {G.number_of_edges()} arestas.")
    return G, df

def buscar_rota(G, origem, destino, modo='distancia_m'):
    """
    Encontra o menor caminho baseado no modo escolhido ('distancia_m' ou 'custo_carbono').
    """
    try:
        rota = nx.shortest_path(G, source=origem, target=destino, weight=modo)
        
        custo_dist = 0
        custo_co2 = 0
        elevacao_acumulada = 0 # Variável para somar as ladeiras
        ruas_percorridas = []
        
        # Percorre as arestas do caminho encontrado
        for u, v in zip(rota[:-1], rota[1:]):
            aresta = G[u][v]
            custo_dist += aresta['distancia_m']
            custo_co2 += aresta['custo_carbono']
            
            # Pega o ganho de elevação (apenas subidas, ou seja, > 0)
            delta_z = aresta.get('delta_z', 0)
            if delta_z > 0:
                elevacao_acumulada += delta_z
            
            # Pega o nome da rua (trata possíveis valores vazios/NaN)
            nome_rua = aresta.get('nome_rua', 'Desconhecida')
            if pd.isna(nome_rua):
                nome_rua = 'Desconhecida'
                
            if not ruas_percorridas or ruas_percorridas[-1] != str(nome_rua):
                ruas_percorridas.append(str(nome_rua))
        
        return rota, custo_dist, custo_co2, elevacao_acumulada, ruas_percorridas
        
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, 0, 0, 0, []

def executar_testes():
    arquivo_grafo = "grafo_curitiba_carbono.csv"
    
    try:
        G, df_base = carregar_grafo(arquivo_grafo)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{arquivo_grafo}' não encontrado.")
        return

    print("\nFiltrando o grafo para garantir que as rotas são possíveis (Maior Componente)...")
    maior_componente = max(nx.strongly_connected_components(G), key=len)
    G_conexo = G.subgraph(maior_componente)
    nos_validos = list(G_conexo.nodes())

    print("Sorteando pontos pela cidade para encontrar o melhor cenário de teste...")
    
    for tentativa in range(1, 51):
        origem = random.choice(nos_validos)
        destino = random.choice(nos_validos)
        
        if origem == destino:
            continue
            
        rota_curta, dist_curta, co2_curta, elev_curta, ruas_curta = buscar_rota(G_conexo, origem, destino, modo='distancia_m')
        rota_eco, dist_eco, co2_eco, elev_eco, ruas_eco = buscar_rota(G_conexo, origem, destino, modo='custo_carbono')
        
        if rota_curta and rota_eco and rota_curta != rota_eco:
            print(f"\n✅ SUCESSO NA TENTATIVA {tentativa}!")
            print(f"Origem (X,Y) : {origem}")
            print(f"Destino (X,Y): {destino}")
            
            print("\n[A] Rota Mais Curta (Foco em Distância)")
            print(f"  -> {len(rota_curta)} nós percorridos")
            print(f"  -> Distância: {dist_curta:.2f} m")
            print(f"  -> Subida   : +{elev_curta:.2f} m de elevação")
            print(f"  -> Emissão  : {co2_curta:.2f} g CO2")
            print(f"  -> Ruas     : {' -> '.join(ruas_curta)}")
            
            print("\n[B] Rota Mais Ecológica (Foco em CO2)")
            print(f"  -> {len(rota_eco)} nós percorridos")
            print(f"  -> Distância: {dist_eco:.2f} m")
            print(f"  -> Subida   : +{elev_eco:.2f} m de elevação")
            print(f"  -> Emissão  : {co2_eco:.2f} g CO2")
            print(f"  -> Ruas     : {' -> '.join(ruas_eco)}")
            
            print("\n--- TRADE-OFF (O RESULTADO DO TCC) ---")
            economia = co2_curta - co2_eco
            aumento = dist_eco - dist_curta
            diferenca_subida = elev_curta - elev_eco
            
            print(f"A rota ecológica desviou de +{diferenca_subida:.2f} m de subidas.")
            print(f"Isso gerou uma economia de {economia:.2f} g de CO2.")
            print(f"Em contrapartida, o trajeto ficou {aumento:.2f} metros mais longo.")
            break
    else:
        print("\nAs 50 tentativas aleatórias deram rotas idênticas. Execute novamente.")

if __name__ == "__main__":
    executar_testes()