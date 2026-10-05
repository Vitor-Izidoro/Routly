"""ETL do IPPUC: Shapefiles de eixos de rua + curvas de nível → grafo_curitiba_carbono.csv.

Lógica original do main.py, preservada. GeoPandas só é importado quando o
ETL roda, para que o restante do Routly funcione apenas com o CSV pronto.
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent


def _localizar(relativo):
    """Pasta-irmã do projeto (caminho original '../') ou dentro dele (.gitignore)."""
    candidatos = [BASE.parent / relativo, BASE / relativo]
    return next((c for c in candidatos if c.is_file()), candidatos[0])


CAMINHO_RUAS = _localizar('EIXO_RUA_SIRGAS/EIXO_RUA.shp')
CAMINHO_CURVAS = _localizar('ALT_CURVA_DE_NIVEL_SIRGAS/ALT_CURVA_DE_NIVEL.shp')
CSV_GRAFO = BASE / 'grafo_curitiba_carbono.csv'


def extrair_dados_iniciais(caminho_ruas=CAMINHO_RUAS, caminho_curvas=CAMINHO_CURVAS):
    import geopandas as gpd

    print("1. Carregando arquivos do IPPUC (isso pode levar alguns segundos)...")
    gdf_ruas = gpd.read_file(caminho_ruas, encoding="latin1")
    gdf_curvas = gpd.read_file(caminho_curvas, encoding="latin1")

    return gdf_ruas, gdf_curvas

def construir_nos_com_elevacao(gdf_ruas, gdf_curvas):
    import geopandas as gpd

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

def construir_arestas_com_peso(gdf_ruas, gdf_nos_z, saida=CSV_GRAFO):
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
    df_arestas.to_csv(saida, index=False)
    print(f"\n[SUCESSO] Grafo exportado com sucesso para '{Path(saida).name}'!")

    return df_arestas


def executar_etl(caminho_ruas=CAMINHO_RUAS, caminho_curvas=CAMINHO_CURVAS, saida=CSV_GRAFO):
    """Roda o ETL completo; devolve True em caso de sucesso e nunca propaga erros."""
    ausentes = [str(c) for c in (caminho_ruas, caminho_curvas) if not Path(c).is_file()]
    if ausentes:
        print('[ETL] Shapefiles do IPPUC não encontrados:\n  ' + '\n  '.join(ausentes))
        print('[ETL] Baixe-os em https://ippuc.org.br/geodownloads/geo.htm (projeção SIRGAS)'
              ' e extraia as pastas EIXO_RUA_SIRGAS/ e ALT_CURVA_DE_NIVEL_SIRGAS/ ao lado do projeto.')
        if Path(saida).is_file():
            print(f"[ETL] O grafo já existente '{Path(saida).name}' continua disponível para uso.")
        return False
    try:
        gdf_ruas, gdf_curvas = extrair_dados_iniciais(caminho_ruas, caminho_curvas)
        gdf_nos_z = construir_nos_com_elevacao(gdf_ruas, gdf_curvas)
        construir_arestas_com_peso(gdf_ruas, gdf_nos_z, saida)
    except ImportError as erro:
        print(f'[ETL] Dependência ausente ({erro.name}). Instale com: pip install geopandas')
    except Exception as erro:  # Leitura de shapefile pode falhar de muitas formas (fiona/pyogrio).
        print(f'[ETL] Falha ao processar os Shapefiles: {type(erro).__name__}: {erro}')
    else:
        return True
    if Path(saida).is_file():
        print(f"[ETL] Use o grafo já existente '{Path(saida).name}'.")
    return False


if __name__ == "__main__":
    raise SystemExit(0 if executar_etl() else 1)
