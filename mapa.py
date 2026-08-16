import pandas as pd

print("Carregando o mapa para análise...")
df = pd.read_csv("grafo_curitiba_carbono.csv")

# Vamos investigar a malha ao redor da João Chede
rua_alvo = "R. JOÃO CHEDE"
print(f"\nBuscando todas as ruas que cruzam com a: {rua_alvo}...")

# 1. Pega todas as coordenadas (X, Y) que pertencem à João Chede
nos_da_rua = set(zip(df[df['nome_rua'] == rua_alvo]['origem_x'], df[df['nome_rua'] == rua_alvo]['origem_y']))
nos_da_rua.update(zip(df[df['nome_rua'] == rua_alvo]['destino_x'], df[df['nome_rua'] == rua_alvo]['destino_y']))

# 2. Varre o mapa inteiro procurando outras ruas que usem essas mesmas coordenadas
ruas_conectadas = set()
for _, row in df.iterrows():
    if row['nome_rua'] != rua_alvo:
        origem = (row['origem_x'], row['origem_y'])
        destino = (row['destino_x'], row['destino_y'])
        
        # Se a esquina bater, temos um cruzamento!
        if origem in nos_da_rua or destino in nos_da_rua:
            ruas_conectadas.add(row['nome_rua'])

print(f"\nSucesso! Achamos {len(ruas_conectadas)} ruas que cruzam com a {rua_alvo}:")
for rua in list(ruas_conectadas)[:15]:  # Mostra as 15 primeiras
    print(f" -> {rua}")