import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

print("Carregando o CSV...")
df = pd.read_csv("grafo_curitiba_carbono.csv")

print("Desenhando Curitiba...")
plt.figure(figsize=(10, 10))

# Plota cada aresta como uma linha (isso desenha o mapa da cidade)
segmentos = df[['origem_x', 'origem_y', 'destino_x', 'destino_y']].to_numpy().reshape(-1, 2, 2)
plt.gca().add_collection(LineCollection(segmentos, colors='black', alpha=0.5, linewidths=0.5))
plt.gca().autoscale_view()

plt.title("Grafo de Ruas - Curitiba")
plt.axis('equal') # Mantém a proporção real X e Y
plt.show()
