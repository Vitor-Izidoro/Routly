import pandas as pd
import matplotlib.pyplot as plt

print("Carregando o CSV...")
df = pd.read_csv("grafo_curitiba_carbono.csv")

print("Desenhando Curitiba...")
plt.figure(figsize=(10, 10))

# Plota cada aresta como uma linha (isso desenha o mapa da cidade)
plt.plot(
    [df['origem_x'], df['destino_x']], 
    [df['origem_y'], df['destino_y']], 
    color='black', alpha=0.5, linewidth=0.5
)

plt.title("Grafo de Ruas - Curitiba")
plt.axis('equal') # Mantém a proporção real X e Y
plt.show()