import geopandas as gpd

print("Lendo shapefile de ruas...")
gdf_ruas = gpd.read_file("EIXO_RUA_SIRGAS/EIXO_RUA.shp", encoding="latin1")

# Imprime todas as colunas disponíveis no banco de dados da rua
print("\nColunas disponíveis:")
print(list(gdf_ruas.columns))

# Mostra as 5 primeiras ruas completas para a gente ver como os nomes estão formatados
print("\nExemplo dos dados:")
print(gdf_ruas.head())


