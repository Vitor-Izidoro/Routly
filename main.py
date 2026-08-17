import geopandas as gpd
import pandas as pd

def extrair_dados_iniciais():
    caminho_ruas = "../EIXO_RUA_SIRGAS/EIXO_RUA.shp"
    caminho_curvas = "../ALT_CURVA_DE_NIVEL_SIRGAS/ALT_CURVA_DE_NIVEL.shp"

    print("1. Carregando arquivos do IPPUC (isso pode levar alguns segundos)...")
    gdf_ruas = gpd.read_file(caminho_ruas, encoding="latin1")
    gdf_curvas = gpd.read_file(caminho_curvas, encoding="latin1")

    return gdf_ruas, gdf_curvas

def construir_nos_com_elevacao(gdf_ruas, gdf_curvas):
    print("2. Extraindo os nós (cruzamentos) da malha viária...")
    pontos_unicos = set()
    
    for geom in gdf_ruas.geometry:
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            pontos_unicos.add(coords[0])
            pontos_unicos.add(coords[-1])
            
    # Transforma os pontos extraídos em um GeoDataFrame
    df_nos = pd.DataFrame(list(pontos_unicos), columns=['X', 'Y'])
    gdf_nos = gpd.GeoDataFrame(
        df_nos, 
        geometry=gpd.points_from_xy(df_nos.X, df_nos.Y), 
        crs=gdf_ruas.crs
    )
    
    print("3. Calculando a elevação de cada nó (buscando a curva de nível mais próxima)...")
    gdf_nos_z = gpd.sjoin_nearest(
        gdf_nos, 
        gdf_curvas[['ELEVATION', 'geometry']], 
        how='left', 
        distance_col='dist_curva'
    )
    
    gdf_nos_z = gdf_nos_z.drop_duplicates(subset=['X', 'Y']).reset_index(drop=True)
    return gdf_nos_z

def construir_arestas_com_peso(gdf_ruas, gdf_nos_z):
    print("4. Construindo o grafo de rotas e calculando custos de carbono...")
    
    elevacao_map = dict(zip(zip(gdf_nos_z['X'], gdf_nos_z['Y']), gdf_nos_z['ELEVATION']))
    arestas = []
    
    for idx, row in gdf_ruas.iterrows():
        geom = row.geometry
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            
            ponto_origem = coords[0]
            ponto_destino = coords[-1]
            
            z_origem = elevacao_map.get(ponto_origem, 0)
            z_destino = elevacao_map.get(ponto_destino, 0)
            
            distancia_m = geom.length
            delta_z = z_destino - z_origem
            
            k = 5.0 
            if delta_z > 0:
                custo_carbono = distancia_m + (delta_z * k)
            else:
                custo_carbono = distancia_m
                
            # Extraindo a coluna correta do IPPUC para o geocodificador
            nome_rua = str(row.get('NMVIA', 'DESCONHECIDA')).strip().upper()
                
            arestas.append({
                "origem_x": ponto_origem[0], "origem_y": ponto_origem[1], "origem_z": z_origem,
                "destino_x": ponto_destino[0], "destino_y": ponto_destino[1], "destino_z": z_destino,
                "distancia_m": round(distancia_m, 2),
                "delta_z": round(delta_z, 2),
                "custo_carbono": round(custo_carbono, 2),
                "nome_rua": nome_rua
            })
            
    df_arestas = pd.DataFrame(arestas)
    
    # Exporta o grafo limpo
    df_arestas.to_csv("grafo_curitiba_carbono.csv", index=False)
    print("\n[SUCESSO] Grafo exportado com sucesso para 'grafo_curitiba_carbono.csv'!")
    
    return df_arestas

if __name__ == "__main__":
    # Fluxo principal perfeitamente limpo e sequencial
    gdf_ruas_base, gdf_curvas_base = extrair_dados_iniciais()
    gdf_nos_com_z = construir_nos_com_elevacao(gdf_ruas_base, gdf_curvas_base)
    df_grafo_final = construir_arestas_com_peso(gdf_ruas_base, gdf_nos_com_z)