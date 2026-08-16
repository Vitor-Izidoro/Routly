import pandas as pd
import geopandas as gpd

print("--- ANALISANDO O CSV GERADO ---")
df_csv = pd.read_csv("grafo_curitiba_carbono.csv")
nomes_unicos = df_csv['nome_rua'].unique()

print(f"Total de nomes de ruas únicos encontrados no CSV: {len(nomes_unicos)}")
print("Amostra dos 20 primeiros nomes no arquivo:")
for nome in nomes_unicos[:20]:
    print(f" -> {nome}")

print("\n--- BUSCANDO AS COLUNAS REAIS DO SHAPEFILE ---")
gdf_ruas = gpd.read_file("EIXO_RUA_SIRGAS/EIXO_RUA.shp", encoding="latin1")
print("Colunas exatas disponíveis no Shapefile do IPPUC:")
for coluna in gdf_ruas.columns:
    print(f" - {coluna}")