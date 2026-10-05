"""Mapas do Routly: exploração de cruzamentos e mapa interativo (Leaflet) de rotas.

O grafo está em SIRGAS 2000 / UTM 22S (metros). A conversão para latitude e
longitude usa as fórmulas inversas de Transverse Mercator (Snyder, 1987), com
o elipsoide GRS80, sem depender de pyproj.
"""
import json
import math
from pathlib import Path
import webbrowser

import pandas as pd

BASE = Path(__file__).resolve().parent
CSV_GRAFO = BASE / 'grafo_curitiba_carbono.csv'
SAIDA = BASE / 'resultados_validacao'


def ruas_que_cruzam(df, rua_alvo):
    """Ruas que compartilham ao menos um nó (esquina) com `rua_alvo`."""
    da_rua = df[df['nome_rua'] == rua_alvo]
    nos_da_rua = set(zip(da_rua['origem_x'], da_rua['origem_y']))
    nos_da_rua.update(zip(da_rua['destino_x'], da_rua['destino_y']))
    outras = df[df['nome_rua'] != rua_alvo]
    cruza = (pd.Series(list(zip(outras['origem_x'], outras['origem_y'])), index=outras.index).isin(nos_da_rua)
             | pd.Series(list(zip(outras['destino_x'], outras['destino_y'])), index=outras.index).isin(nos_da_rua))
    return set(outras.loc[cruza, 'nome_rua'])


def explorar_cruzamentos(rua_alvo="R. JOÃO CHEDE", caminho=CSV_GRAFO, limite=15):
    print("Carregando o mapa para análise...")
    df = pd.read_csv(caminho)
    print(f"\nBuscando todas as ruas que cruzam com a: {rua_alvo}...")
    ruas_conectadas = ruas_que_cruzam(df, rua_alvo)
    print(f"\nSucesso! Achamos {len(ruas_conectadas)} ruas que cruzam com a {rua_alvo}:")
    for rua in sorted(ruas_conectadas)[:limite]:
        print(f" -> {rua}")
    return ruas_conectadas


def utm_para_latlon(leste, norte, zona=22, sul=True):
    """SIRGAS 2000 / UTM → (latitude, longitude) em graus decimais."""
    a, f, k0 = 6378137.0, 1 / 298.257222101, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    x = leste - 500000.0
    y = norte - (10000000.0 if sul else 0.0)
    mu = y / k0 / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
            + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
            + (151 * e1**3 / 96) * math.sin(6 * mu) + (1097 * e1**4 / 512) * math.sin(8 * mu))
    sen, cos, tan = math.sin(phi1), math.cos(phi1), math.tan(phi1)
    c1, t1 = ep2 * cos**2, tan**2
    n1 = a / math.sqrt(1 - e2 * sen**2)
    r1 = a * (1 - e2) / (1 - e2 * sen**2) ** 1.5
    d = x / (n1 * k0)
    lat = phi1 - (n1 * tan / r1) * (d**2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
                                    + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2) * d**6 / 720)
    lon = (d - (1 + 2 * t1 + c1) * d**3 / 6
           + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * d**5 / 120) / cos
    return math.degrees(lat), (zona * 6 - 183) + math.degrees(lon)


_MODELO_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Routly — mapa de rotas</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #mapa { height: 100%; margin: 0; font-family: Georgia, serif; }
  .painel { position: absolute; top: 12px; right: 12px; z-index: 1000; background: #fcfcfb;
            color: #0b0b0b; padding: 10px 14px; border-radius: 8px; max-width: 340px;
            box-shadow: 0 1px 6px rgba(0,0,0,.25); font-size: 13px; line-height: 1.45; }
  .painel h1 { font-size: 15px; margin: 0 0 6px; }
  .linha { display: inline-block; width: 22px; height: 0; border-top: 4px solid; vertical-align: middle; margin-right: 6px; }
</style></head>
<body><div id="mapa"></div><div class="painel" id="painel"></div>
<script>
const DADOS = __DADOS__;
const mapa = L.map('mapa');
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom: 19, attribution: '&copy; OpenStreetMap | malha viária IPPUC'}).addTo(mapa);
const limites = [];
let html = `<h1>${DADOS.titulo}</h1>`;
for (const r of DADOS.rotas) {
  const linha = L.polyline(r.pontos, {color: r.cor, weight: 5, opacity: .85, dashArray: r.tracejado || null})
    .bindPopup(`<b>${r.nome}</b><br>${r.resumo}`).addTo(mapa);
  limites.push(...r.pontos);
  html += `<div><span class="linha" style="border-color:${r.cor}"></span><b>${r.nome}</b><br>${r.resumo}</div>`;
}
html += `<div style="margin-top:6px;color:#52514e">${DADOS.nota}</div>`;
document.getElementById('painel').innerHTML = html;
L.circleMarker(DADOS.origem, {radius: 8, color: '#0b0b0b', fillColor: '#ffffff', fillOpacity: 1})
  .bindTooltip('Origem', {permanent: true}).addTo(mapa);
L.circleMarker(DADOS.destino, {radius: 8, color: '#ffffff', fillColor: '#0b0b0b', fillOpacity: 1})
  .bindTooltip('Destino', {permanent: true}).addTo(mapa);
mapa.fitBounds(limites, {padding: [30, 30]});
</script></body></html>
"""


def gerar_mapa_rotas(origem, destino, cenario='Carregado', saida=SAIDA / 'mapa_rotas.html', abrir=True):
    """Calcula rota mais curta, joelho de Pareto e rota ecológica e grava um mapa Leaflet."""
    from experimentos.comprovacao_cientifica import (CENARIOS_CARGA, VELOCIDADE_KMH, analisar_fronteira,
                                                     carregar_malha, localizar_par)
    carga = CENARIOS_CARGA[cenario]
    grafo = carregar_malha('vtcpfm', carga, velocidade_kmh=VELOCIDADE_KMH)
    o, d = localizar_par(origem, destino)
    resultado = analisar_fronteira(grafo, o, d, passos=11, carga_kg=carga, incluir_boa=False)
    escolhidas = [(resultado.solucoes[0], 'Rota mais curta — baseline GPS (α = 0)', '#eb6834', None),
                  (resultado.solucoes[resultado.joelho], 'Solução de compromisso (joelho)', '#1baf7a', '8 8'),
                  (resultado.solucoes[-1], 'Routly — rota ecológica (α = 1)', '#2a78d6', None)]
    rotas = []
    for s, nome, cor, tracejado in escolhidas:
        t = s['trajeto']
        rotas.append({'nome': f"{nome}, α = {s['alpha']:.1f}".replace('.', ','), 'cor': cor, 'tracejado': tracejado,
                      'pontos': [utm_para_latlon(x, y) for x, y in t.nos],
                      'resumo': (f'{t.distancia / 1000:.2f} km · {t.emissao / 1000:.2f} kg CO₂ · '
                                 f"{-s['co2_economizado_pct']:+.1f} % CO₂ · "
                                 f"{s['distancia_adicional_pct']:+.1f} % distância").replace('.', ',')})
    dados = {'titulo': f'{origem.title()} → {destino.title()}', 'rotas': rotas,
             'origem': utm_para_latlon(*o), 'destino': utm_para_latlon(*d),
             'nota': f"HDDT1 {cenario.lower()} ({f'{carga:,.0f}'.replace(',', '.')} kg adicionais), "
                     f'{VELOCIDADE_KMH:g} km/h, VT-CPFM. Clique numa rota para ver os detalhes.'}
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(_MODELO_HTML.replace('__DADOS__', json.dumps(dados, ensure_ascii=False)), encoding='utf-8')
    print(f'[MAPA] Mapa interativo salvo em {saida}')
    if abrir:
        webbrowser.open(saida.as_uri())
    return saida


if __name__ == "__main__":
    explorar_cruzamentos()
