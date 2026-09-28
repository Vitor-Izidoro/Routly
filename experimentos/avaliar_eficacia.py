"""Avaliação da eficácia: rota mais curta × rota de menor emissão em Curitiba.

Compara, em pares origem-destino aleatórios da maior componente conectada,
a rota ALT por distância (o que um GPS comum faria) com a rota ALT por
emissão. Camadas descritas em experimentos/README.md:
  1. economia de CO₂ por carga, velocidade, faixa de distância e relevo;
  2. validação cruzada: rota escolhida por VT-CPFM medida com CMEM;
  3. sensibilidade: rota escolhida com altitudes ruidosas, medida na malha original.

Uso: python experimentos/avaliar_eficacia.py --pares 300 --cargas 0 10000 20000
"""
import argparse
import csv
import math
import random
import statistics as st
import sys
import tempfile
import warnings
from pathlib import Path
from time import perf_counter

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import pandas as pd  # noqa: E402
from algoritmos import IndiceALT, distancias_dijkstra  # noqa: E402
from emissoes import configurar_caminhao  # noqa: E402
from estrela import carregar_grafos_direcionais  # noqa: E402

CSV_GRAFO = BASE / 'grafo_curitiba_carbono.csv'
FAIXAS_KM = ((0, 3, 'curta (<3 km)'), (3, 8, 'média (3–8 km)'), (8, math.inf, 'longa (>8 km)'))


def carregar_malha(modelo='vtcpfm', carga_kg=0.0, velocidade_kmh=30.0, caminho=CSV_GRAFO):
    """Grafo de ida sem avisos nem mensagens de progresso do carregador."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        caminhao = configurar_caminhao('hddt1') if modelo == 'cmem' else None
        grafo, _ = carregar_grafos_direcionais(caminho, modelo=modelo, caminhao=caminhao,
                                               carga_kg=carga_kg, velocidade_kmh=velocidade_kmh)
    return grafo


def maior_componente(grafo):
    """Malha tratada como bidirecional: alcance por Dijkstra equivale à componente."""
    vistos, maior = set(), set()
    for no in grafo:
        if no not in vistos:
            comp = set(distancias_dijkstra(grafo, no, 1))
            vistos |= comp
            if len(comp) > len(maior):
                maior = comp
    return maior


def pares_aleatorios(nos, quantidade, semente=42):
    rnd = random.Random(semente)
    ordenados = sorted(nos)
    return [tuple(rnd.sample(ordenados, 2)) for _ in range(quantidade)]


def tabela_emissao(grafo):
    """Menor emissão entre arestas paralelas u→v, para medir rotas em outro modelo."""
    custos = {}
    for u, arestas in grafo.items():
        for v, _, e in arestas:
            custos[u, v] = min(e, custos.get((u, v), math.inf))
    return custos


def emissao_da_rota(nos, custos):
    return sum(custos[u, v] for u, v in zip(nos, nos[1:]))


def subida_por_km(nos, altitudes):
    """Desnível positivo acumulado (m) por km de rota, para classificar o relevo."""
    subida = sum(max(0.0, altitudes[v] - altitudes[u]) for u, v in zip(nos, nos[1:]))
    distancia = sum(math.dist(u, v) for u, v in zip(nos, nos[1:]))
    return subida / (distancia / 1000) if distancia else 0.0


def comparar_rotas(grafo, pares, landmarks=8, medir_em=None):
    """Para cada par: rota curta × rota ecológica escolhidas em `grafo`.

    `medir_em` (tabela_emissao de outro grafo) mede as duas rotas em outro modelo
    ou em outra malha; sem ele, usa as emissões do próprio grafo de escolha.
    """
    curta, eco = IndiceALT(grafo, 'distancia', landmarks), IndiceALT(grafo, 'emissao', landmarks)
    resultados = []
    for origem, destino in pares:
        rc, re_ = curta.buscar(origem, destino), eco.buscar(origem, destino)
        if rc is None or re_ is None:
            continue
        ec, ee = ((emissao_da_rota(rc.nos, medir_em), emissao_da_rota(re_.nos, medir_em))
                  if medir_em else (rc.emissao, re_.emissao))
        resultados.append({
            'origem': origem, 'destino': destino,
            'distancia_curta_m': rc.distancia, 'distancia_eco_m': re_.distancia,
            'co2_curta_g': ec, 'co2_eco_g': ee,
            'economia_g': ec - ee,
            'economia_pct': 100 * (ec - ee) / ec if ec else 0.0,
            'distancia_extra_pct': 100 * (re_.distancia - rc.distancia) / rc.distancia if rc.distancia else 0.0,
            'rotas_iguais': rc.nos == re_.nos,
            'nos_curta': rc.nos,
        })
    return resultados


def wilcoxon_pareado(diferencas):
    """Wilcoxon de postos sinalizados, aproximação normal bilateral (sem scipy).

    Zeros descartados; postos médios em empates; correção de empates na variância.
    """
    d = [x for x in diferencas if x != 0]
    n = len(d)
    if n == 0:
        return 0.0, 1.0
    ordem = sorted(range(n), key=lambda i: abs(d[i]))
    postos, i, correcao = [0.0] * n, 0, 0.0
    while i < n:
        j = i
        while j + 1 < n and abs(d[ordem[j + 1]]) == abs(d[ordem[i]]):
            j += 1
        for k in range(i, j + 1):
            postos[ordem[k]] = (i + j) / 2 + 1
        t = j - i + 1
        correcao += t ** 3 - t
        i = j + 1
    w_mais = sum(p for p, x in zip(postos, d) if x > 0)
    media = n * (n + 1) / 4
    desvio = math.sqrt(n * (n + 1) * (2 * n + 1) / 24 - correcao / 48)
    z = (w_mais - media) / desvio if desvio else 0.0
    return z, math.erfc(abs(z) / math.sqrt(2))


def ic_bootstrap(valores, reamostras=2000, semente=42):
    """Intervalo de confiança de 95% da média por bootstrap percentil."""
    rnd = random.Random(semente)
    medias = sorted(st.mean(rnd.choices(valores, k=len(valores))) for _ in range(reamostras))
    return medias[int(0.025 * reamostras)], medias[int(0.975 * reamostras) - 1]


def resumir(rotulo, resultados):
    econ = [r['economia_pct'] for r in resultados]
    if not econ:
        return {'cenario': rotulo, 'pares': 0}
    z, p = wilcoxon_pareado([r['co2_curta_g'] - r['co2_eco_g'] for r in resultados])
    ic = ic_bootstrap(econ) if len(econ) > 1 else (econ[0], econ[0])
    return {
        'cenario': rotulo, 'pares': len(econ),
        'economia_media_pct': st.mean(econ), 'ic95_inf_pct': ic[0], 'ic95_sup_pct': ic[1],
        'economia_mediana_pct': st.median(econ), 'economia_max_pct': max(econ),
        'economia_media_g': st.mean(r['economia_g'] for r in resultados),
        'distancia_extra_media_pct': st.mean(r['distancia_extra_pct'] for r in resultados),
        'rotas_iguais': sum(r['rotas_iguais'] for r in resultados),
        'economia_negativa': sum(x < -1e-9 for x in econ),
        'wilcoxon_z': z, 'p_valor': p,
    }


def imprimir(resumo):
    if not resumo['pares']:
        print(f"{resumo['cenario']}: sem pares.")
        return
    print(f"{resumo['cenario']:<62} n={resumo['pares']:<4} "
          f"economia {resumo['economia_media_pct']:6.2f}% "
          f"[IC95 {resumo['ic95_inf_pct']:.2f}–{resumo['ic95_sup_pct']:.2f}] "
          f"mediana {resumo['economia_mediana_pct']:6.2f}% | "
          f"+dist {resumo['distancia_extra_media_pct']:5.2f}% | "
          f"negativos {resumo['economia_negativa']} | p={resumo['p_valor']:.2g}", flush=True)


def malha_com_ruido(caminho, desvio_m, semente):
    """CSV temporário com ruído gaussiano por nó (mesmo nó, mesmo ruído)."""
    df = pd.read_csv(caminho)
    rnd = random.Random(semente)
    ruido = {}
    def z(x, y, base):
        chave = (x, y)
        if chave not in ruido:
            ruido[chave] = rnd.gauss(0, desvio_m)
        return base + ruido[chave]
    df['origem_z'] = [z(x, y, b) for x, y, b in zip(df.origem_x, df.origem_y, df.origem_z)]
    df['destino_z'] = [z(x, y, b) for x, y, b in zip(df.destino_x, df.destino_y, df.destino_z)]
    # Trechos de distância zero precisam manter desnível zero para passar na validação.
    df['delta_z'] = (df.destino_z - df.origem_z).where(df.distancia_m > 0, 0.0)
    arquivo = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8')
    df.to_csv(arquivo.name, index=False)
    arquivo.close()
    return Path(arquivo.name)


def salvar_csv(caminho, linhas):
    if not linhas:
        return
    campos = [c for c in linhas[0] if c != 'nos_curta']
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        escritor = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        escritor.writeheader()
        escritor.writerows(linhas)


def gerar_graficos(saida, por_carga):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, eixo = plt.subplots(figsize=(8, 5))
    for rotulo, resultados in por_carga.items():
        eixo.hist([r['economia_pct'] for r in resultados], bins=30, alpha=0.5, label=rotulo)
    eixo.set_xlabel('Economia de CO₂ da rota ecológica (%)')
    eixo.set_ylabel('Pares origem-destino')
    eixo.set_title('Rota ecológica × rota mais curta — Curitiba')
    eixo.legend()
    fig.tight_layout()
    fig.savefig(saida / 'histograma_economia.png', dpi=150)
    plt.close(fig)
    fig, eixo = plt.subplots(figsize=(8, 5))
    for rotulo, resultados in por_carga.items():
        eixo.scatter([r['distancia_extra_pct'] for r in resultados],
                     [r['economia_pct'] for r in resultados], s=10, alpha=0.6, label=rotulo)
    eixo.set_xlabel('Distância extra da rota ecológica (%)')
    eixo.set_ylabel('Economia de CO₂ (%)')
    eixo.set_title('Custo em distância × ganho em emissão')
    eixo.legend()
    fig.tight_layout()
    fig.savefig(saida / 'distancia_x_economia.png', dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--pares', type=int, default=300)
    parser.add_argument('--semente', type=int, default=42)
    parser.add_argument('--cargas', type=float, nargs='+', default=[0.0, 10000.0, 20000.0])
    parser.add_argument('--velocidades', type=float, nargs='+', default=[30.0])
    parser.add_argument('--landmarks', type=int, default=8)
    parser.add_argument('--ruido-m', type=float, nargs='*', default=[1.0, 2.0],
                        help='Desvios-padrão (m) do ruído de altitude; vazio desliga a camada 3.')
    parser.add_argument('--sem-cmem', action='store_true', help='Desliga a validação cruzada (camada 2).')
    parser.add_argument('--sem-graficos', action='store_true')
    parser.add_argument('--saida', type=Path, default=BASE / 'experimentos' / 'resultados')
    args = parser.parse_args()
    if not CSV_GRAFO.exists():
        parser.error('Grafo ausente. Disponibilize grafo_curitiba_carbono.csv (gerado por main.py).')
    args.saida.mkdir(parents=True, exist_ok=True)
    inicio = perf_counter()

    base = carregar_malha()
    componente = maior_componente(base)
    pares = pares_aleatorios(componente, args.pares, args.semente)
    altitudes = {}
    df = pd.read_csv(CSV_GRAFO)
    for x, y, zv in zip(df.origem_x, df.origem_y, df.origem_z):
        altitudes[x, y] = zv
    for x, y, zv in zip(df.destino_x, df.destino_y, df.destino_z):
        altitudes[x, y] = zv
    print(f'Malha: {len(base)} nós, maior componente {len(componente)}. '
          f'{len(pares)} pares, semente {args.semente}.\n', flush=True)

    resumos, detalhados, por_carga = [], [], {}
    print('== Camada 1: economia de CO₂ (VT-CPFM) ==', flush=True)
    for v in args.velocidades:
        for carga in args.cargas:
            rotulo = f'VT-CPFM | {carga:g} kg | {v:g} km/h'
            grafo = carregar_malha('vtcpfm', carga, v)
            resultados = comparar_rotas(grafo, pares, args.landmarks)
            por_carga[f'{carga:g} kg, {v:g} km/h'] = resultados
            resumos.append(resumir(rotulo, resultados))
            imprimir(resumos[-1])
            for r in resultados:
                detalhados.append({'cenario': rotulo, **r})
            # Recortes por faixa de distância e por relevo (mediana da subida por km).
            for minimo, maximo, nome in FAIXAS_KM:
                recorte = [r for r in resultados if minimo <= r['distancia_curta_m'] / 1000 < maximo]
                resumos.append(resumir(f'  {rotulo} | {nome}', recorte))
                imprimir(resumos[-1])
            relevo = [subida_por_km(r['nos_curta'], altitudes) for r in resultados]
            limite = st.median(relevo)
            for nome, cond in (('relevo plano', lambda s: s <= limite), ('relevo acidentado', lambda s: s > limite)):
                recorte = [r for r, s in zip(resultados, relevo) if cond(s)]
                resumos.append(resumir(f'  {rotulo} | {nome} (limite {limite:.1f} m/km)', recorte))
                imprimir(resumos[-1])

    carga_ref, v_ref = max(args.cargas), args.velocidades[0]
    if not args.sem_cmem:
        print('\n== Camada 2: rota escolhida por VT-CPFM, medida com CMEM ==', flush=True)
        for carga in args.cargas:
            escolha = carregar_malha('vtcpfm', carga, v_ref)
            medida = tabela_emissao(carregar_malha('cmem', carga, v_ref))
            resumos.append(resumir(f'VT-CPFM→CMEM | {carga:g} kg | {v_ref:g} km/h',
                                   comparar_rotas(escolha, pares, args.landmarks, medida)))
            imprimir(resumos[-1])

    if args.ruido_m:
        print(f'\n== Camada 3: altitudes com ruído, medida na malha original ({carga_ref:g} kg) ==', flush=True)
        verdade = tabela_emissao(carregar_malha('vtcpfm', carga_ref, v_ref))
        for desvio in args.ruido_m:
            arquivo = malha_com_ruido(CSV_GRAFO, desvio, args.semente)
            try:
                ruidosa = carregar_malha('vtcpfm', carga_ref, v_ref, arquivo)
            finally:
                arquivo.unlink(missing_ok=True)
            resumos.append(resumir(f'Ruído ±{desvio:g} m | {carga_ref:g} kg | {v_ref:g} km/h',
                                   comparar_rotas(ruidosa, pares, args.landmarks, verdade)))
            imprimir(resumos[-1])

    salvar_csv(args.saida / 'resumo.csv', resumos)
    salvar_csv(args.saida / 'pares.csv', detalhados)
    if not args.sem_graficos:
        gerar_graficos(args.saida, por_carga)
    print(f'\nResultados em {args.saida} ({perf_counter() - inicio:.0f} s).')


if __name__ == '__main__':
    main()
