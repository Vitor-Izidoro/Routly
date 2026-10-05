"""Comprovação científica do Routly: Pareto, perfil altimétrico, Monte Carlo e paridade física.

Metodologia multiobjetivo inspirada em Reynoso-Meza et al. (MOOD / MCDM):
objetivos J1 = distância e J2 = CO₂ normalizados pelo ponto utopia e pelo
ponto nadir, varredura do peso α e solução de compromisso pela menor
distância euclidiana ao utopia (joelho de Pareto).

Todas as figuras são salvas em 300 DPI em resultados_validacao/.
Uso: python -m experimentos.comprovacao_cientifica --tudo [--pares 100]
"""
import argparse
from dataclasses import dataclass, field
from functools import wraps
import csv
import importlib.util
import json
from heapq import heappop, heappush
from itertools import count
from math import hypot, inf, isfinite
from pathlib import Path
import statistics as st
import subprocess
import sys
from time import perf_counter
import warnings

import matplotlib
import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from scipy import stats

from algoritmos import IndiceALT, boa_estrela, distancias_dijkstra
from emissoes import CaminhaoCMEM, configurar_caminhao, consumo_trecho
from estrela import carregar_grafos_direcionais, carregar_indice_ruas, pegar_um_no_da_rua
from experimentos.avaliar_eficacia import (CSV_GRAFO, comparar_rotas, maior_componente,
                                           pares_aleatorios, tabela_emissao, wilcoxon_pareado)
from veiculos import HDDT1, MASSA_MERL_APROX_KG
from vtcpfm import configurar_vtcpfm, consumo_trecho_vtcpfm

BASE = Path(__file__).resolve().parent.parent
SAIDA = BASE / 'resultados_validacao'
VELOCIDADE_KMH = 30.0
ORIGEM_PADRAO = 'R. AMADEU ASSAD YASSIM'
DESTINO_PADRAO = 'R. GEN. LUIZ CARLOS PEREIRA TOURINHO'
# Massa adicional (reboque + carga) sobre os 7.182 kg do HDDT1; o "carregado"
# é o laboratório rebocado de Wang e Rakha (veiculos.MASSA_MERL_APROX_KG).
CENARIOS_CARGA = {'Vazio': 0.0, 'Meia carga': MASSA_MERL_APROX_KG / 2,
                  'Carregado': MASSA_MERL_APROX_KG}
CARGA_PADRAO = 'Carregado'
EPS_LEXICOGRAFICO = 1e-9  # α=0/1 com desempate pelo outro objetivo: extremos não dominados.

# Paleta categórica validada (skill dataviz) e tintas de texto.
AZUL, LARANJA, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
RAMPA_CARGA = ('#86b6ef', '#2a78d6', '#104281')  # ordinal: vazio → carregado
TINTA, TINTA_2, CINZA = '#0b0b0b', '#52514e', '#a3a29d'
ESTILO = {
    'font.family': 'serif', 'font.size': 10, 'axes.titlesize': 11,
    'axes.labelsize': 10, 'legend.fontsize': 8.5, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
    'axes.grid': True, 'grid.color': '#d9d8d4', 'grid.linewidth': 0.5, 'grid.alpha': 0.8,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': TINTA_2,
    'axes.labelcolor': TINTA, 'xtick.color': TINTA_2, 'ytick.color': TINTA_2,
    'text.color': TINTA, 'legend.frameon': True, 'legend.framealpha': 0.92,
    'legend.edgecolor': '#d9d8d4', 'savefig.dpi': 300, 'savefig.bbox': 'tight',
    'lines.linewidth': 2,
}


# ---------------------------------------------------------------- utilidades

def _br(valor, casas=1):
    """Número no padrão brasileiro (1.234,5)."""
    texto = f'{valor:,.{casas}f}'
    return texto.replace(',', '§').replace('.', ',').replace('§', '.')


def _p_texto(p):
    if p == 0:
        return 'p < 10$^{-300}$'
    if p >= 1e-3:
        return f'p = {_br(p, 4)}'
    mantissa, expoente = f'{p:.2e}'.split('e')
    return f'p = {_br(float(mantissa), 2)} × 10$^{{{int(expoente)}}}$'


def _formatar_eixos(*eixos):
    fmt = FuncFormatter(lambda v, _: f'{v:g}'.replace('.', ','))
    for ax in eixos:
        ax.xaxis.set_major_formatter(fmt)
        ax.yaxis.set_major_formatter(fmt)


def _com_estilo(funcao):
    """Aplica o estilo acadêmico só durante a função, sem alterar o pyplot global."""
    @wraps(funcao)
    def envolvida(*args, **kwargs):
        with matplotlib.rc_context(ESTILO):
            return funcao(*args, **kwargs)
    return envolvida


def _figura(*args, **kwargs):
    return Figure(*args, **kwargs)


def _salvar(fig, caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho)
    print(f'[SALVO] {caminho.relative_to(BASE) if caminho.is_relative_to(BASE) else caminho}')
    return caminho


def _rotulo_carga(nome, carga_kg):
    return f'{nome}\n({_br((HDDT1.massa_veicular_kg + carga_kg) / 1000, 1)} t total)'


def carregar_malha(modelo='vtcpfm', carga_kg=0.0, *, velocidade_kmh=30.0, caminho=CSV_GRAFO,
                   avisos=None, caminhao=None):
    """Igual a avaliar_eficacia.carregar_malha, mas guarda os avisos em `avisos`.

    Os avisos de declividade e de potência acima da nominal entram nos
    relatórios em vez de serem descartados.
    """
    if caminhao is None and modelo == 'cmem':
        caminhao = configurar_caminhao('hddt1')
    with warnings.catch_warnings(record=True) as capturados:
        warnings.simplefilter('always', UserWarning)
        grafo, _ = carregar_grafos_direcionais(caminho, modelo=modelo, caminhao=caminhao,
                                               carga_kg=carga_kg, velocidade_kmh=velocidade_kmh)
    if avisos is not None:
        avisos.extend(str(w.message) for w in capturados)
    return grafo


def altitudes_dos_nos(caminho=CSV_GRAFO):
    import pandas as pd
    df = pd.read_csv(caminho, usecols=['origem_x', 'origem_y', 'origem_z',
                                       'destino_x', 'destino_y', 'destino_z'])
    alt = dict(zip(zip(df.destino_x, df.destino_y), df.destino_z))
    alt.update(zip(zip(df.origem_x, df.origem_y), df.origem_z))
    return alt


def localizar_par(origem=ORIGEM_PADRAO, destino=DESTINO_PADRAO, caminho=CSV_GRAFO):
    indice = carregar_indice_ruas(caminho)
    o, d = pegar_um_no_da_rua(indice, origem.upper()), pegar_um_no_da_rua(indice, destino.upper())
    if o is None or d is None:
        raise ValueError('Rua de origem/destino não encontrada; confira o nome exato no CSV.')
    return o, d


# ------------------------------------------------------ A* ponderado (J1, J2)

@dataclass
class Trajeto:
    nos: list
    trechos: list  # [(distancia_m, co2_g)] na ordem da rota
    distancia: float
    emissao: float


def limites_heuristica(grafo):
    """(κ, τ): κ = min comprimento/corda e τ = min g CO₂/m sobre todas as arestas.

    Para qualquer caminho u→t: distância ≥ κ·‖u−t‖ e emissão ≥ τ·distância,
    o que torna h admissível e consistente. Só vale para nós (x, y) em metros.
    """
    if not all(isinstance(u, tuple) and len(u) == 2 for u in grafo):
        return None
    kappa, taxa = inf, inf
    for u, arestas in grafo.items():
        for v, d, e in arestas:
            if d <= 0:
                continue
            taxa = min(taxa, e / d)
            corda = hypot(v[0] - u[0], v[1] - u[1])
            if corda > 0:
                kappa = min(kappa, d / corda)
    return (kappa if isfinite(kappa) else 0.0, taxa if isfinite(taxa) else 0.0)


def busca_ponderada(grafo, origem, destino, alpha, escala_d=1.0, escala_e=1.0, limites=None):
    """A* com C(e) = (1−α)·d(e)/escala_d + α·E(e)/escala_e."""
    if not 0 <= alpha <= 1 or escala_d <= 0 or escala_e <= 0:
        raise ValueError('α deve estar em [0, 1] e as escalas devem ser positivas.')
    if origem not in grafo or destino not in grafo:
        return None
    wd, we = (1 - alpha) / escala_d, alpha / escala_e
    fator_h = limites[0] * (wd + we * limites[1]) if limites else 0.0

    def h(u):
        return fator_h * hypot(destino[0] - u[0], destino[1] - u[1]) if fator_h else 0.0

    ordem = count()
    g = {origem: 0.0}
    pai = {origem: None}
    fila = [(h(origem), 0.0, next(ordem), origem)]
    fechados = set()
    while fila:
        _, custo, _, u = heappop(fila)
        if u in fechados or custo > g[u]:
            continue
        fechados.add(u)
        if u == destino:
            nos, trechos = [u], []
            while pai[u] is not None:
                u, d, e = pai[u]
                nos.append(u)
                trechos.append((d, e))
            nos.reverse()
            trechos.reverse()
            return Trajeto(nos, trechos, sum(t[0] for t in trechos), sum(t[1] for t in trechos))
        for v, d, e in grafo[u]:
            novo = custo + wd * d + we * e
            if novo < g.get(v, inf):
                g[v] = novo
                pai[v] = (u, d, e)
                heappush(fila, (novo + h(v), novo, next(ordem), v))
    return None


@dataclass
class ResultadoPareto:
    origem: tuple
    destino: tuple
    carga_kg: float
    solucoes: list           # dicts: alpha, trajeto, métricas
    joelho: int              # índice em solucoes
    utopia: tuple            # (m, g)
    nadir: tuple             # (m, g)
    fronteira_exata: list = field(default_factory=list)  # [(m, g)] do BOA*
    tempo_boa_s: float = 0.0


def analisar_fronteira(grafo, origem, destino, *, passos=21, carga_kg=0.0,
                       incluir_boa=True, limites=None):
    """Varre α em `passos` valores de 0 a 1 e localiza o joelho de Pareto."""
    if passos < 2:
        raise ValueError('Use ao menos dois passos de α.')
    limites = limites if limites is not None else limites_heuristica(grafo)
    curta = busca_ponderada(grafo, origem, destino, EPS_LEXICOGRAFICO, limites=limites)
    eco = busca_ponderada(grafo, origem, destino, 1 - EPS_LEXICOGRAFICO, limites=limites)
    if curta is None or eco is None:
        raise ValueError('Não existe caminho entre origem e destino.')
    utopia = (curta.distancia, eco.emissao)
    nadir = (eco.distancia, curta.emissao)
    escala_d = (nadir[0] - utopia[0]) or utopia[0] or 1.0
    escala_e = (nadir[1] - utopia[1]) or utopia[1] or 1.0
    solucoes = []
    for alpha in np.linspace(0, 1, passos):
        alpha = float(alpha)
        if alpha == 0:
            trajeto = curta
        elif alpha == 1:
            trajeto = eco
        else:
            trajeto = busca_ponderada(grafo, origem, destino, alpha, escala_d, escala_e, limites)
        f1 = (trajeto.distancia - utopia[0]) / escala_d
        f2 = (trajeto.emissao - utopia[1]) / escala_e
        solucoes.append({
            'alpha': alpha, 'trajeto': trajeto, 'f1_norm': f1, 'f2_norm': f2,
            'dist_utopia': hypot(f1, f2),
            'co2_economizado_pct': 100 * (curta.emissao - trajeto.emissao) / curta.emissao,
            'distancia_adicional_pct': 100 * (trajeto.distancia - curta.distancia) / curta.distancia,
        })
    joelho = min(range(len(solucoes)), key=lambda i: (round(solucoes[i]['dist_utopia'], 12), i))
    resultado = ResultadoPareto(origem, destino, carga_kg, solucoes, joelho, utopia, nadir)
    if incluir_boa:
        t = perf_counter()
        resultado.fronteira_exata = [(r.distancia, r.emissao) for r in boa_estrela(grafo, origem, destino)]
        resultado.tempo_boa_s = perf_counter() - t
    return resultado


def exportar_tradeoff(resultado, caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open('w', newline='', encoding='utf-8') as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(['alpha', 'distancia_km', 'co2_kg', 'co2_economizado_pct',
                           'distancia_adicional_pct', 'f1_normalizado', 'f2_normalizado',
                           'distancia_ao_utopia', 'nos_na_rota', 'solucao_de_compromisso'])
        for i, s in enumerate(resultado.solucoes):
            t = s['trajeto']
            escritor.writerow([f"{s['alpha']:.3f}", f'{t.distancia / 1000:.4f}', f'{t.emissao / 1000:.4f}',
                               f"{s['co2_economizado_pct']:.3f}", f"{s['distancia_adicional_pct']:.3f}",
                               f"{s['f1_norm']:.4f}", f"{s['f2_norm']:.4f}", f"{s['dist_utopia']:.4f}",
                               len(t.nos), 'sim' if i == resultado.joelho else 'nao'])
    print(f'[SALVO] {caminho.name}')
    return caminho


@_com_estilo
def plotar_pareto(resultado, caminho, titulo_par=''):
    fig = _figura(figsize=(7.6, 6.0))
    ax = fig.add_subplot()
    if resultado.fronteira_exata:
        fx, fy = zip(*sorted(resultado.fronteira_exata))
        ax.plot([x / 1000 for x in fx], [y / 1000 for y in fy], color=CINZA, linewidth=1,
                marker='o', markersize=2.5, zorder=1,
                label=f'Fronteira exata — BOA* ({len(fx)} soluções não dominadas)')
    unicos = {}
    for s in resultado.solucoes:
        t = s['trajeto']
        unicos.setdefault((round(t.distancia, 6), round(t.emissao, 6)), []).append(s['alpha'])
    pontos = sorted(unicos)
    ax.plot([d / 1000 for d, _ in pontos], [e / 1000 for _, e in pontos], color=AZUL, linewidth=1.2,
            linestyle='--', marker='o', markersize=5, markerfacecolor='white', markeredgewidth=1.4,
            zorder=3, label=f'Soma ponderada A* ({len(resultado.solucoes)} valores de α, '
                            f'{len(pontos)} rotas distintas)')
    base, eco = resultado.solucoes[0], resultado.solucoes[-1]
    joelho = resultado.solucoes[resultado.joelho]
    destaque = [
        (base, 's', LARANJA, 'Baseline GPS — rota mais curta (α = 0)'),
        (eco, 'D', AZUL, 'Routly — rota ecológica (α = 1)'),
        (joelho, '*', AQUA, f"Solução de compromisso — joelho (α = {_br(joelho['alpha'], 2)})"),
    ]
    for s, marcador, cor, rotulo in destaque:
        t = s['trajeto']
        ax.scatter(t.distancia / 1000, t.emissao / 1000, marker=marcador, s=190 if marcador == '*' else 80,
                   color=cor, edgecolor='white', linewidth=1.5, zorder=5, label=rotulo)
    ax.scatter(resultado.utopia[0] / 1000, resultado.utopia[1] / 1000, marker='x', s=60,
               color=TINTA, linewidth=1.6, zorder=5, label='Ponto utopia (mín. distância, mín. CO₂)')
    for s, dx, dy in ((base, 10, 2), (eco, -8, -10), (joelho, 10, 10)):
        t = s['trajeto']
        texto = (f"{_br(t.distancia / 1000, 2)} km · {_br(t.emissao / 1000, 2)} kg CO₂"
                 + (f"\n−{_br(s['co2_economizado_pct'], 1)} % CO₂ · +{_br(s['distancia_adicional_pct'], 1)} % dist."
                    if s is not base else ''))
        ax.annotate(texto, (t.distancia / 1000, t.emissao / 1000), xytext=(dx, dy),
                    textcoords='offset points', fontsize=7.5, color=TINTA_2,
                    ha='right' if dx < 0 else 'left', va='bottom' if dy > 0 else 'top')
    ax.set_xlabel('J₁ — Distância percorrida (km)')
    ax.set_ylabel('J₂ — Emissão de CO₂ (kg)')
    carga = HDDT1.massa_veicular_kg + resultado.carga_kg
    ax.set_title('Fronteira de Pareto: distância × emissão de CO₂\n'
                 f'{titulo_par}HDDT1 com {_br(carga / 1000, 1)} t, {VELOCIDADE_KMH:g} km/h, VT-CPFM',
                 fontsize=10.5)
    ax.margins(x=0.12, y=0.12)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=7.8)
    _formatar_eixos(ax)
    return _salvar(fig, caminho)


# -------------------------------------------------------- perfil altimétrico

def _serie_rota(trajeto, altitudes):
    dist = np.concatenate([[0.0], np.cumsum([d for d, _ in trajeto.trechos])]) / 1000
    co2 = np.concatenate([[0.0], np.cumsum([e for _, e in trajeto.trechos])]) / 1000
    z = np.array([altitudes.get(no, np.nan) for no in trajeto.nos], dtype=float)
    dz = np.diff(z)
    trechos_m = np.array([d for d, _ in trajeto.trechos])
    with np.errstate(divide='ignore', invalid='ignore'):
        rampa = np.where(trechos_m > 0, dz / trechos_m, 0.0)
    return dist, z, co2, rampa


@_com_estilo
def plotar_perfil(curta, eco, altitudes, caminho, limiar_rampa=0.05, titulo_par=''):
    fig = _figura(figsize=(7.2, 6.4))
    ax_z, ax_c = fig.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [1, 1], 'hspace': 0.12})
    resumo = {}
    for nome, trajeto, cor, estilo in (('Rota mais curta (α = 0)', curta, LARANJA, '-'),
                                       ('Routly ecológica (α = 1)', eco, AZUL, '-')):
        dist, z, co2, rampa = _serie_rota(trajeto, altitudes)
        subida = float(np.nansum(np.clip(np.diff(z), 0, None)))
        ingremes = np.flatnonzero(rampa > limiar_rampa)
        resumo[nome] = {'distancia_km': dist[-1], 'co2_kg': co2[-1], 'subida_m': subida,
                        'trechos_ingremes': len(ingremes), 'rampa_max_pct': 100 * float(np.max(rampa, initial=0))}
        ax_z.plot(dist, z, color=cor, linestyle=estilo, linewidth=1.6,
                  label=f'{nome}: {_br(dist[-1], 1)} km, subida acumulada {_br(subida, 0)} m')
        ax_z.scatter(dist[ingremes], z[ingremes], marker='^', s=22, color=cor, edgecolor='white',
                     linewidth=0.6, zorder=4)
        ax_c.plot(dist, co2, color=cor, linestyle=estilo, linewidth=1.8,
                  label=f'{nome}: {_br(co2[-1], 2)} kg CO₂')
        ax_c.scatter(dist[-1], co2[-1], color=cor, s=30, zorder=4, edgecolor='white')
    ax_z.scatter([], [], marker='^', s=22, color=TINTA_2,
                 label=f'Início de trecho com aclive > {limiar_rampa * 100:g} %')
    ax_z.set_ylabel('Altitude (m)')
    baixo, alto = ax_z.get_ylim()
    ax_z.set_ylim(baixo, alto + 0.55 * (alto - baixo))  # espaço livre para a legenda
    ax_z.legend(loc='upper center', ncol=1)
    ax_c.set_ylabel('CO₂ acumulado (kg)')
    ax_c.set_xlabel('Distância acumulada (km)')
    ax_c.legend(loc='upper left')
    economia = 100 * (curta.emissao - eco.emissao) / curta.emissao
    ax_z.set_title('Perfil altimétrico e emissão acumulada\n'
                   f'{titulo_par}Routly emite {_br(economia, 1)} % menos CO₂ com '
                   f'{_br(100 * (eco.distancia - curta.distancia) / curta.distancia, 1)} % mais distância',
                   fontsize=10.5)
    _formatar_eixos(ax_z, ax_c)
    _salvar(fig, caminho)
    return resumo


# -------------------------------------------------------------- Monte Carlo

def _ic_bootstrap_mediana(valores, reamostras=10000, semente=42):
    rng = np.random.default_rng(semente)
    v = np.asarray(valores)
    medianas = np.median(rng.choice(v, size=(reamostras, len(v)), replace=True), axis=1)
    return float(np.percentile(medianas, 2.5)), float(np.percentile(medianas, 97.5))


def _wilcoxon_scipy(j1, j2):
    """Wilcoxon signed-rank pareado (SciPy). Zeros descartados (zero_method='wilcox')."""
    diferencas = np.asarray(j1) - np.asarray(j2)
    nao_nulos = int(np.count_nonzero(diferencas))
    if nao_nulos == 0:
        return {'W': 0.0, 'p_bicaudal': 1.0, 'p_unicaudal': 1.0, 'n_nao_nulos': 0, 'r_efeito': 0.0}
    bi = stats.wilcoxon(j1, j2, zero_method='wilcox', alternative='two-sided')
    uni = stats.wilcoxon(j1, j2, zero_method='wilcox', alternative='greater')
    z, _ = wilcoxon_pareado(diferencas.tolist())
    return {'W': float(bi.statistic), 'p_bicaudal': float(bi.pvalue), 'p_unicaudal': float(uni.pvalue),
            'n_nao_nulos': nao_nulos, 'z': z, 'r_efeito': z / np.sqrt(nao_nulos)}


def monte_carlo(n_pares=100, semente=42, cenarios=None, caminho=CSV_GRAFO, validar_cmem=True):
    """Para cada cenário de carga: J1 (mais curta) × J2 (ecológica) nos mesmos N pares."""
    cenarios = cenarios or CENARIOS_CARGA
    resultados, pares = {}, None
    for nome, carga in cenarios.items():
        t = perf_counter()
        avisos = []
        grafo = carregar_malha('vtcpfm', carga, velocidade_kmh=VELOCIDADE_KMH, caminho=caminho, avisos=avisos)
        if pares is None:
            pares = pares_aleatorios(maior_componente(grafo), n_pares, semente)
        linhas = comparar_rotas(grafo, pares)
        cruzado = None
        if validar_cmem:
            cmem = tabela_emissao(carregar_malha('cmem', carga, velocidade_kmh=VELOCIDADE_KMH, caminho=caminho))
            cruzado = comparar_rotas(grafo, pares, medir_em=cmem)
        resultados[nome] = {'carga_kg': carga, 'linhas': linhas, 'cmem': cruzado, 'avisos': avisos}
        print(f'[MONTE CARLO] {nome}: {len(linhas)} pares em {perf_counter() - t:.1f} s')
    return resultados


def _estatisticas(linhas):
    economia = [r['economia_pct'] for r in linhas]
    j1 = [r['co2_curta_g'] for r in linhas]
    j2 = [r['co2_eco_g'] for r in linhas]
    q1, q3 = np.percentile(economia, [25, 75])
    return {
        'n': len(linhas),
        'identicas': sum(abs(a - b) <= 1e-9 * a for a, b in zip(j1, j2)),
        'mediana': float(np.median(economia)), 'media': st.mean(economia),
        'desvio': st.stdev(economia) if len(economia) > 1 else 0.0,
        'q1': float(q1), 'q3': float(q3), 'max': max(economia),
        'ic95': _ic_bootstrap_mediana(economia),
        'dist_extra_mediana': float(np.median([r['distancia_extra_pct'] for r in linhas])),
        'co2_total_j1_kg': sum(j1) / 1000, 'co2_total_j2_kg': sum(j2) / 1000,
        **_wilcoxon_scipy(j1, j2),
    }


@_com_estilo
def plotar_boxplot(resultados, caminho):
    fig = _figura(figsize=(7.2, 5.0))
    ax = fig.add_subplot()
    nomes = list(resultados)
    dados = [[r['economia_pct'] for r in resultados[n]['linhas']] for n in nomes]
    caixa = ax.boxplot(dados, widths=0.5, patch_artist=True, showfliers=False,
                       medianprops={'color': TINTA, 'linewidth': 1.6},
                       whiskerprops={'color': TINTA_2}, capprops={'color': TINTA_2},
                       boxprops={'edgecolor': TINTA_2, 'linewidth': 0.8})
    rng = np.random.default_rng(7)
    topo = max(max(d) for d in dados)
    for i, (patch, valores, cor) in enumerate(zip(caixa['boxes'], dados, RAMPA_CARGA), start=1):
        patch.set_facecolor(cor)
        patch.set_alpha(0.55)
        ax.scatter(i + rng.uniform(-0.17, 0.17, len(valores)), valores, s=9, color=cor,
                   edgecolor=TINTA_2, linewidth=0.3, alpha=0.85, zorder=3)
        s = _estatisticas(resultados[nomes[i - 1]]['linhas'])
        ax.text(i, topo * 1.06, f"mediana = {_br(s['mediana'], 2)} %\n{_p_texto(s['p_bicaudal'])}",
                ha='center', va='bottom', fontsize=8, color=TINTA)
    ax.set_xticks(range(1, len(nomes) + 1),
                  [_rotulo_carga(n, resultados[n]['carga_kg']) for n in nomes])
    ax.set_ylim(min(0, min(min(d) for d in dados)) - 0.5, topo * 1.25)
    ax.set_ylabel('Redução de CO₂: Routly (J₂) vs. rota mais curta (J₁) (%)')
    n = len(dados[0])
    ax.set_title(f'Monte Carlo com {n} pares O-D por cenário de carga\n'
                 'Teste de Wilcoxon pareado (bicaudal) sobre as emissões de J₁ e J₂', fontsize=10.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g}'.replace('.', ',')))
    return _salvar(fig, caminho)


def exportar_monte_carlo(resultados, pasta, semente, n_pares):
    pasta = Path(pasta)
    with (pasta / 'monte_carlo_resultados.csv').open('w', newline='', encoding='utf-8') as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(['cenario', 'carga_kg', 'medido_em', 'origem_x', 'origem_y', 'destino_x',
                           'destino_y', 'distancia_j1_m', 'distancia_j2_m', 'co2_j1_g', 'co2_j2_g',
                           'reducao_co2_pct', 'distancia_extra_pct'])
        for nome, r in resultados.items():
            for medido, linhas in (('VT-CPFM', r['linhas']), ('CMEM', r['cmem'] or [])):
                for l in linhas:
                    escritor.writerow([nome, f"{r['carga_kg']:.2f}", medido, *l['origem'], *l['destino'],
                                       f"{l['distancia_curta_m']:.2f}", f"{l['distancia_eco_m']:.2f}",
                                       f"{l['co2_curta_g']:.3f}", f"{l['co2_eco_g']:.3f}",
                                       f"{l['economia_pct']:.4f}", f"{l['distancia_extra_pct']:.4f}"])
    linhas_md = [
        '# Relatório estatístico — Monte Carlo + Wilcoxon signed-rank', '',
        f'- Pares Origem-Destino: **{n_pares}**, sorteados na maior componente conexa da malha '
        f'(semente {semente}); os mesmos pares em todos os cenários (delineamento pareado).',
        f'- Veículo: {HDDT1.descricao}, massa base {HDDT1.massa_veicular_kg:g} kg; '
        f'velocidade constante {VELOCIDADE_KMH:g} km/h; modelo VT-CPFM-1 (Wang e Rakha, 2017); fator CO₂ EPA.',
        '- J₁: rota de menor distância (ALT). J₂: rota de menor emissão (ALT, ótimo exato).',
        '- H₀: a mediana das diferenças CO₂(J₁) − CO₂(J₂) é zero. H₁ (bicaudal): é diferente de zero. '
        'Também é reportado o p unicaudal (H₁: J₁ > J₂).',
        '- Teste: `scipy.stats.wilcoxon` (zero_method="wilcox": pares com rotas de mesmo custo são '
        'descartados; o SciPy usa a distribuição exata quando n ≤ 50 sem empates e a aproximação normal '
        'nos demais casos). Efeito r = z/√n. IC 95 % da mediana por bootstrap (10.000 reamostras).', '',
        '## Resultado principal (rota escolhida e medida pelo VT-CPFM)', '',
        '| Cenário | Massa total (t) | n | Rotas iguais | Redução mediana (%) | IC 95 % mediana | '
        'Média ± DP (%) | Q1–Q3 (%) | Distância extra mediana (%) | W | p bicaudal | p unicaudal | r |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for nome, r in resultados.items():
        s = _estatisticas(r['linhas'])
        linhas_md.append(
            f"| {nome} | {(HDDT1.massa_veicular_kg + r['carga_kg']) / 1000:.1f} | {s['n']} | {s['identicas']} | "
            f"{s['mediana']:.2f} | [{s['ic95'][0]:.2f}; {s['ic95'][1]:.2f}] | {s['media']:.2f} ± {s['desvio']:.2f} | "
            f"{s['q1']:.2f}–{s['q3']:.2f} | {s['dist_extra_mediana']:.2f} | {s['W']:.0f} | "
            f"{s['p_bicaudal']:.3e} | {s['p_unicaudal']:.3e} | {s.get('r_efeito', 0):.2f} |")
    if all(r['cmem'] for r in resultados.values()):
        linhas_md += ['', '## Validação cruzada (rota escolhida pelo VT-CPFM, medida pelo CMEM)', '',
                      'Aqui o sinal da diferença **não** é garantido pela otimização: o CMEM (Lai et al., 2024) '
                      'é um modelo físico independente. Uma economia significativa indica que o ganho não é '
                      'artefato do modelo usado na busca.', '',
                      '| Cenário | n | Redução mediana (%) | Média (%) | Pares com piora | W | p bicaudal |',
                      '|---|---|---|---|---|---|---|']
        for nome, r in resultados.items():
            s = _estatisticas(r['cmem'])
            piora = sum(l['economia_pct'] < 0 for l in r['cmem'])
            linhas_md.append(f"| {nome} | {s['n']} | {s['mediana']:.2f} | {s['media']:.2f} | {piora} | "
                             f"{s['W']:.0f} | {s['p_bicaudal']:.3e} |")
    linhas_md += ['', '## Leitura e limitações', '',
                  '- Como J₂ é o ótimo exato de emissão no mesmo modelo, CO₂(J₂) ≤ CO₂(J₁) em todo par; o teste '
                  'quantifica se a redução é sistemática na população de viagens, não se o algoritmo "acerta" '
                  'o sinal. A validação cruzada acima é a evidência que não depende dessa garantia.',
                  *[f'- Aviso do modelo no cenário {nome}: {a}' for nome, r in resultados.items()
                    for a in r.get('avisos', [])],
                  '- Velocidade constante, sem tráfego, paradas ou semáforos; altitude por extremidade de aresta '
                  '(curvas de nível IPPUC); ruas tratadas como bidirecionais.',
                  '- Figura: `boxplot_cenarios_carga.png`. Dados por par: `monte_carlo_resultados.csv`.']
    (pasta / 'relatorio_estatistico.md').write_text('\n'.join(linhas_md) + '\n', encoding='utf-8')
    print('[SALVO] relatorio_estatistico.md, monte_carlo_resultados.csv')


# ---------------------------------------------------- paridade física (grade)

@_com_estilo
def validacao_fisica(pasta, rampas_pct=None, altitude_m=910.0):
    """VT-CPFM (modelo do Routly) × CMEM com parâmetros de Lai et al. (2024).

    Referência independente: mesma física de estrada, formulação de consumo
    distinta (perdas internas do motor + eficiências). Métricas sobre g CO₂/km.
    """
    pasta = Path(pasta)
    rampas_ref = np.arange(-6, 6.01, 1.0) if rampas_pct is None else np.asarray(rampas_pct, float)
    rampas_curva = np.linspace(-6, 6, 121)
    vt, cm = configurar_vtcpfm('epa'), configurar_caminhao('hddt1')

    def g_km(modelo, rampa, carga):
        if modelo == 'vtcpfm':
            return consumo_trecho_vtcpfm(1000, rampa * 10, vt, altitude_m=altitude_m, carga_kg=carga,
                                         velocidade_kmh=VELOCIDADE_KMH).co2_g
        return consumo_trecho(1000, rampa * 10, cm, carga_kg=carga, velocidade_kmh=VELOCIDADE_KMH).co2_g

    pontos, pred, ref = [], [], []
    metricas_por_carga = {}
    fig = _figura(figsize=(7.2, 5.0))
    ax = fig.add_subplot()
    for (nome, carga), cor, marcador in zip(CENARIOS_CARGA.items(), RAMPA_CARGA, ('o', 's', '^')):
        curva = [g_km('vtcpfm', r, carga) / 1000 for r in rampas_curva]
        ax.plot(rampas_curva, curva, color=cor, linewidth=2, zorder=2)
        p_c, r_c = [], []
        for rampa in rampas_ref:
            a, b = g_km('vtcpfm', rampa, carga), g_km('cmem', rampa, carga)
            pontos.append({'cenario': nome, 'carga_kg': carga, 'rampa_pct': float(rampa),
                           'co2_g_km_routly_vtcpfm': a, 'co2_g_km_referencia_cmem': b})
            p_c.append(a)
            r_c.append(b)
        pred += p_c
        ref += r_c
        metricas_por_carga[nome] = _metricas(p_c, r_c)
        ax.scatter(rampas_ref, [b / 1000 for b in r_c], marker=marcador, s=34, facecolor='white',
                   edgecolor=cor, linewidth=1.5, zorder=3)
    m = _metricas(pred, ref)
    legenda = [Line2D([], [], color=TINTA_2, linewidth=2, label='Routly — VT-CPFM-1 (Wang e Rakha, 2017)'),
               Line2D([], [], color=TINTA_2, marker='o', linestyle='', markerfacecolor='white',
                      label='Referência — CMEM, parâmetros de Lai et al. (2024)')]
    legenda += [Line2D([], [], color=cor, marker=mk, markerfacecolor='white', linewidth=2,
                       label=_rotulo_carga(n, c).replace('\n', ' '))
                for (n, c), cor, mk in zip(CENARIOS_CARGA.items(), RAMPA_CARGA, ('o', 's', '^'))]
    ax.legend(handles=legenda, loc='upper left')
    ax.axvline(0, color=CINZA, linewidth=0.8, zorder=1)
    ax.set_xlabel('Declividade da via, grade (%)')
    ax.set_ylabel('Emissão de CO₂ (kg/km)')
    ax.set_title('Paridade física: modelo Routly × referência CMEM\n'
                 f"R² = {_br(m['r2'], 3)} · MAPE = {_br(m['mape'], 1)} % · "
                 f'{VELOCIDADE_KMH:g} km/h, altitude {altitude_m:g} m', fontsize=10.5)
    _formatar_eixos(ax)
    _salvar(fig, pasta / 'validacao_fisica_grade.png')
    dados = {
        'descricao': 'Pontos de referência para a paridade física do modelo do Routly em função da declividade.',
        'referencia': 'CMEM simplificado (emissoes.py), parâmetros HDV de Lai et al. (2024), '
                      'DOI 10.1016/j.cor.2024.106557, com perfil físico HDDT1. Valores calculados, '
                      'não medições de campo.',
        'modelo_routly': 'VT-CPFM-1 convexo HDDT1, Wang e Rakha (2017), DOI 10.1016/j.trd.2017.06.011.',
        'condicoes': {'velocidade_kmh': VELOCIDADE_KMH, 'altitude_m': altitude_m,
                      'fator_co2_g_l': vt.fator_co2_g_l, 'massa_base_kg': HDDT1.massa_veicular_kg},
        'metricas_globais': m, 'metricas_por_cenario': metricas_por_carga, 'pontos': pontos,
    }
    (pasta / 'paridade_fisica_grade.json').write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                                                     encoding='utf-8')
    print('[SALVO] paridade_fisica_grade.json')
    return dados


def _metricas(pred, ref):
    p, r = np.asarray(pred), np.asarray(ref)
    ss_res = float(np.sum((r - p) ** 2))
    ss_tot = float(np.sum((r - r.mean()) ** 2))
    return {'r2': 1 - ss_res / ss_tot if ss_tot else 1.0,
            'mape': float(np.mean(np.abs((p - r) / r)) * 100),
            'pearson': float(np.corrcoef(p, r)[0, 1]) if len(p) > 1 else 1.0}


# ---------------------------------------------------------------- execuções

def _titulo_par(origem, destino):
    return f'{origem.title()} → {destino.title()}\n'


def executar_pareto_e_perfil(pasta=SAIDA, origem=ORIGEM_PADRAO, destino=DESTINO_PADRAO,
                             cenario=CARGA_PADRAO, passos=21, incluir_boa=True, perfil=True, pareto=True):
    pasta = Path(pasta)
    carga = CENARIOS_CARGA[cenario]
    grafo = carregar_malha('vtcpfm', carga, velocidade_kmh=VELOCIDADE_KMH)
    o, d = localizar_par(origem, destino)
    titulo = _titulo_par(origem, destino)
    saida = {}
    if pareto:
        resultado = analisar_fronteira(grafo, o, d, passos=passos, carga_kg=carga, incluir_boa=incluir_boa)
        exportar_tradeoff(resultado, pasta / 'pareto_tradeoff.csv')
        plotar_pareto(resultado, pasta / 'pareto_fronteira.png', titulo)
        curta, eco = resultado.solucoes[0]['trajeto'], resultado.solucoes[-1]['trajeto']
        j = resultado.solucoes[resultado.joelho]
        saida['pareto'] = {
            'baseline_km': curta.distancia / 1000, 'baseline_kg': curta.emissao / 1000,
            'routly_km': eco.distancia / 1000, 'routly_kg': eco.emissao / 1000,
            'economia_routly_pct': resultado.solucoes[-1]['co2_economizado_pct'],
            'distancia_extra_routly_pct': resultado.solucoes[-1]['distancia_adicional_pct'],
            'joelho_alpha': j['alpha'], 'joelho_km': j['trajeto'].distancia / 1000,
            'joelho_kg': j['trajeto'].emissao / 1000, 'joelho_economia_pct': j['co2_economizado_pct'],
            'joelho_distancia_extra_pct': j['distancia_adicional_pct'],
            'rotas_distintas': len({(round(s['trajeto'].distancia, 6), round(s['trajeto'].emissao, 6))
                                    for s in resultado.solucoes}),
            'fronteira_exata': len(resultado.fronteira_exata), 'tempo_boa_s': resultado.tempo_boa_s,
        }
    else:
        limites = limites_heuristica(grafo)
        curta = busca_ponderada(grafo, o, d, EPS_LEXICOGRAFICO, limites=limites)
        eco = busca_ponderada(grafo, o, d, 1 - EPS_LEXICOGRAFICO, limites=limites)
        if curta is None or eco is None:
            raise ValueError('Não existe caminho entre origem e destino.')
    if perfil:
        saida['perfil'] = plotar_perfil(curta, eco, altitudes_dos_nos(),
                                        pasta / 'perfil_altimetrico_comparativo.png', titulo_par=titulo)
    return saida


def executar_monte_carlo(pasta=SAIDA, n_pares=100, semente=42):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    resultados = monte_carlo(n_pares, semente)
    plotar_boxplot(resultados, pasta / 'boxplot_cenarios_carga.png')
    exportar_monte_carlo(resultados, pasta, semente, n_pares)
    return {nome: _estatisticas(r['linhas']) | {'cmem': _estatisticas(r['cmem']) if r['cmem'] else None}
            for nome, r in resultados.items()}


REGISTRO_CMEM = next((c for c in (BASE / 'docs' / 'validacao_cmem.json', BASE / 'validacao_cmem.json')
                      if c.is_file()), BASE / 'docs' / 'validacao_cmem.json')


def reproduzir_registro_cmem(pasta=SAIDA, registro=REGISTRO_CMEM, tolerancia=1e-9):
    """Recalcula as rotas gravadas em docs/validacao_cmem.json (CMEM hdv-generico).

    Confere hash do grafo, distância, CO₂ e custo Dijkstra de cada consulta, e a
    fronteira do BOA*. Verifica a reprodutibilidade da busca, não a precisão
    física da emissão (ver docs/MODELO_EMISSOES.md).
    """
    import hashlib
    pasta = Path(pasta)
    dados = json.loads(Path(registro).read_text(encoding='utf-8'))
    hash_atual = hashlib.sha256(CSV_GRAFO.read_bytes()).hexdigest()
    caminhao = CaminhaoCMEM(**dados['parametros'])
    o, d = localizar_par(dados['origem'], dados['destino'])
    verificacoes = [{'verificacao': 'SHA-256 do grafo', 'registrado': dados['grafo_sha256'],
                     'obtido': hash_atual, 'passou': hash_atual == dados['grafo_sha256']}]

    def conferir(nome, registrado, obtido):
        verificacoes.append({'verificacao': nome, 'registrado': registrado, 'obtido': obtido,
                             'passou': abs(obtido - registrado) <= tolerancia * max(1.0, abs(registrado))})

    grafos = {}
    for r in dados['resultados']:
        chave = (r['carga_kg'], r['velocidade_kmh'])
        if chave not in grafos:
            grafos[chave] = carregar_malha('cmem', r['carga_kg'], velocidade_kmh=r['velocidade_kmh'],
                                           caminhao=caminhao)
        grafo = grafos[chave]
        rota = IndiceALT(grafo, r['modo'], 4).buscar(o, d)
        dijkstra = distancias_dijkstra(grafo, o, 1 if r['modo'] == 'distancia' else 2)[d]
        rotulo = f"{r['modo']}, {r['carga_kg']:g} kg, {r['velocidade_kmh']:g} km/h"
        conferir(f'Distância (m) — {rotulo}', r['distancia_m'], rota.distancia)
        conferir(f'CO₂ (g) — {rotulo}', r['co2_g'], rota.emissao)
        conferir(f'Custo Dijkstra — {rotulo}', r['custo_dijkstra'], dijkstra)
    if 'boa_carga_zero' in dados:
        b = dados['boa_carga_zero']
        fronteira = boa_estrela(grafos[next(k for k in grafos if k[0] == 0)], o, d)
        conferir('BOA* carga 0: nº de alternativas', b['alternativas'], len(fronteira))
        conferir('BOA* carga 0: extremo de distância (m)', b['extremo_distancia_m'],
                 min(r.distancia for r in fronteira))
        conferir('BOA* carga 0: extremo de emissão (g)', b['extremo_emissao_g'],
                 min(r.emissao for r in fronteira))
    passaram = sum(v['passou'] for v in verificacoes)
    linhas = ['# Reprodução do registro `docs/validacao_cmem.json`', '',
              f"Registro de {dados['data']}: {dados['origem']} → {dados['destino']}, CMEM com o perfil "
              f"histórico `hdv-generico` ({caminhao.massa_vazia_kg:g} kg de massa vazia). "
              f'Tolerância relativa {tolerancia:g}.', '',
              f'**{passaram}/{len(verificacoes)} verificações reproduzidas.**', '',
              '| Verificação | Registrado | Obtido | Resultado |', '|---|---|---|---|']
    for v in verificacoes:
        fmt = (lambda x: f'{x:.6f}') if isinstance(v['obtido'], float) else str
        linhas.append(f"| {v['verificacao']} | {fmt(v['registrado'])} | {fmt(v['obtido'])} | "
                      f"{'OK' if v['passou'] else 'DIVERGE'} |")
    linhas += ['', f"Nota do registro: {dados.get('nota', '')}", '',
               'A igualdade dos custos verifica a busca (ALT = Dijkstra, resultados estáveis), '
               'não a precisão física da estimativa de emissão.']
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / 'reproducao_validacao_cmem.md').write_text('\n'.join(linhas) + '\n', encoding='utf-8')
    print(f'[CMEM] Registro histórico reproduzido: {passaram}/{len(verificacoes)} -> reproducao_validacao_cmem.md')
    return {'passaram': passaram, 'total': len(verificacoes), 'verificacoes': verificacoes}


def executar_validacao_modelos(pasta=SAIDA, pares_eficacia=100):
    """3.1: conversão de CO₂, eficácia (3 camadas), registro CMEM e paridade física por grade."""
    from unittest.mock import patch
    from experimentos import avaliar_eficacia, validar_conversao_co2
    pasta = Path(pasta)
    resumo = {}
    try:
        validar_conversao_co2.main(['--saida', str(pasta / 'conversao_co2')])
        resumo['conversao'] = json.loads((pasta / 'conversao_co2' / 'resumo.json').read_text(encoding='utf-8'))
    except SystemExit as erro:
        print(f'[CO₂] Validação da conversão indisponível (código {erro.code}).')
    print('\n--- Eficácia em 3 camadas (experimentos/avaliar_eficacia.py) ---')
    argumentos = ['avaliar_eficacia.py', '--pares', str(pares_eficacia),
                  '--cargas', *[f'{c:g}' for c in CENARIOS_CARGA.values()],
                  '--saida', str(pasta / 'eficacia')]
    with patch.object(sys, 'argv', argumentos):
        avaliar_eficacia.main()
    with (pasta / 'eficacia' / 'resumo.csv').open(encoding='utf-8') as arquivo:
        resumo['eficacia'] = [l for l in csv.DictReader(arquivo) if not l['cenario'].startswith(' ')]
    print('\n--- Reprodução de docs/validacao_cmem.json ---')
    resumo['registro_cmem'] = reproduzir_registro_cmem(pasta)
    resumo['fisica'] = validacao_fisica(pasta)
    return resumo


def executar_testes(pasta=SAIDA):
    """3.2: pytest em tests/ (unittest como alternativa). Log em testes_automatizados.txt."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    if importlib.util.find_spec('pytest'):
        comando = [sys.executable, '-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider']
    else:
        print('[TESTES] pytest não instalado; usando unittest.')
        comando = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']
    proc = subprocess.run(comando, cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace')
    log = proc.stdout + proc.stderr
    (pasta / 'testes_automatizados.txt').write_text(log, encoding='utf-8')
    print(log.strip().splitlines()[-1] if log.strip() else '(sem saída)')
    return proc.returncode == 0, log


def rodar_tudo(pasta=SAIDA, n_pares=100, semente=42, origem=ORIGEM_PADRAO, destino=DESTINO_PADRAO):
    """3.6: pipeline completo; grava RESUMO.md com as métricas principais."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    if not CSV_GRAFO.exists():
        raise FileNotFoundError('grafo_curitiba_carbono.csv ausente; gere-o pelo menu 1.1.')
    inicio = perf_counter()
    print('\n=== 3.1 Validação VT-CPFM / CMEM e conversão de CO₂ ===')
    modelos = executar_validacao_modelos(pasta)
    print('\n=== 3.2 Testes automatizados ===')
    testes_ok, log = executar_testes(pasta)
    print('\n=== 3.3 + 3.4 Fronteira de Pareto e perfil altimétrico ===')
    rota = executar_pareto_e_perfil(pasta, origem, destino)
    print(f'\n=== 3.5 Monte Carlo ({n_pares} pares) + Wilcoxon ===')
    mc = executar_monte_carlo(pasta, n_pares, semente)
    escrever_resumo(pasta, modelos, testes_ok, log, rota, mc, n_pares, origem, destino,
                    perf_counter() - inicio)
    return {'modelos': modelos, 'testes_ok': testes_ok, 'rota': rota, 'monte_carlo': mc}


def escrever_resumo(pasta, modelos, testes_ok, log, rota, mc, n_pares, origem, destino, duracao_s):
    p, perfil = rota['pareto'], rota['perfil']
    fis = modelos['fisica']['metricas_globais']
    linhas = ['# Resumo da comprovação científica — Routly', '',
              f'Pipeline completo em {duracao_s:.0f} s. Par representativo: {origem} → {destino} '
              f'(HDDT1 carregado, {VELOCIDADE_KMH:g} km/h).', '',
              '## Arquivos', '']
    for arquivo in sorted(pasta.rglob('*')):
        if arquivo.is_file() and arquivo.name != 'RESUMO.md':
            linhas.append(f'- `{arquivo.relative_to(pasta).as_posix()}`')
    ultima = (log.strip().splitlines() or ['?'])[-1]
    linhas += ['', '## Métricas principais', '',
               f"- **Testes automatizados:** {'aprovados' if testes_ok else 'COM FALHAS'} — {ultima}",
               f"- **Paridade física (VT-CPFM × CMEM, grade −6 % a +6 %):** R² = {fis['r2']:.3f}, "
               f"MAPE = {fis['mape']:.1f} %, Pearson = {fis['pearson']:.3f}"]
    if 'conversao' in modelos:
        c = modelos['conversao']
        unidades = c['verificacoes_unidades']
        linhas.append(f"- **Conversão de CO₂ (diesel, Kaggle):** fator implícito médio "
                      f"{c['fator_implicito_media_g_l']:.1f} g/L vs. projeto (EPA) {c['fator_projeto_g_l']:.1f} g/L "
                      f"({c['diferenca_media_fator_pct']:+.2f} %), n = {c['registros_validos']}; "
                      f"verificações de unidades {sum(v['passou'] for v in unidades)}/{len(unidades)}")
    reg = modelos['registro_cmem']
    linhas.append(f"- **Reprodução de `docs/validacao_cmem.json`:** {reg['passaram']}/{reg['total']} "
                  'verificações idênticas ao registro histórico')
    linhas += [f"- **Pareto:** baseline {p['baseline_km']:.2f} km / {p['baseline_kg']:.2f} kg; Routly "
               f"{p['routly_km']:.2f} km / {p['routly_kg']:.2f} kg (−{p['economia_routly_pct']:.2f} % CO₂, "
               f"+{p['distancia_extra_routly_pct']:.2f} % distância); joelho α = {p['joelho_alpha']:.2f}: "
               f"−{p['joelho_economia_pct']:.2f} % CO₂ com +{p['joelho_distancia_extra_pct']:.2f} % distância; "
               f"{p['rotas_distintas']} rotas distintas na varredura; fronteira exata BOA* com "
               f"{p['fronteira_exata']} soluções ({p['tempo_boa_s']:.2f} s)"]
    for nome, dados in perfil.items():
        linhas.append(f"- **Perfil — {nome}:** {dados['distancia_km']:.2f} km, subida acumulada "
                      f"{dados['subida_m']:.0f} m, {dados['trechos_ingremes']} trechos com aclive > 5 %, "
                      f"rampa máx. {dados['rampa_max_pct']:.1f} %")
    linhas += ['', '### Eficácia em 3 camadas (`eficacia/resumo.csv`)', '',
               '| Cenário | n | Economia média (%) | IC 95 % | Distância extra (%) | Casos negativos | p |',
               '|---|---|---|---|---|---|---|']
    for e in modelos['eficacia']:
        linhas.append(f"| {e['cenario'].replace('|', '·')} | {e['pares']} | {float(e['economia_media_pct']):.2f} | "
                      f"[{float(e['ic95_inf_pct']):.2f}; {float(e['ic95_sup_pct']):.2f}] | "
                      f"{float(e['distancia_extra_media_pct']):.2f} | {e['economia_negativa']} | "
                      f"{float(e['p_valor']):.2e} |")
    linhas += ['', f'### Monte Carlo ({n_pares} pares) — redução de CO₂ de J₂ sobre J₁', '',
               '| Cenário | Mediana (%) | IC 95 % | Média (%) | p (Wilcoxon, bicaudal) | Mediana CMEM (%) | p CMEM |',
               '|---|---|---|---|---|---|---|']
    for nome, s in mc.items():
        c = s['cmem'] or {}
        linhas.append(f"| {nome} | {s['mediana']:.2f} | [{s['ic95'][0]:.2f}; {s['ic95'][1]:.2f}] | "
                      f"{s['media']:.2f} | {s['p_bicaudal']:.2e} | {c.get('mediana', float('nan')):.2f} | "
                      f"{c.get('p_bicaudal', float('nan')):.2e} |")
    (pasta / 'RESUMO.md').write_text('\n'.join(linhas) + '\n', encoding='utf-8')
    print(f'\n[SALVO] RESUMO.md — veja {pasta}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--tudo', action='store_true', help='Pipeline completo (3.1 a 3.5).')
    grupo.add_argument('--modelos', action='store_true', help='3.1 Validação VT-CPFM/CMEM e CO₂.')
    grupo.add_argument('--testes', action='store_true', help='3.2 Testes automatizados.')
    grupo.add_argument('--pareto', action='store_true', help='3.3 Fronteira de Pareto.')
    grupo.add_argument('--perfil', action='store_true', help='3.4 Perfil altimétrico.')
    grupo.add_argument('--monte-carlo', action='store_true', help='3.5 Monte Carlo + Wilcoxon.')
    parser.add_argument('--pares', type=int, default=100)
    parser.add_argument('--semente', type=int, default=42)
    parser.add_argument('--origem', default=ORIGEM_PADRAO)
    parser.add_argument('--destino', default=DESTINO_PADRAO)
    parser.add_argument('--carga', choices=list(CENARIOS_CARGA), default=CARGA_PADRAO)
    parser.add_argument('--passos-alpha', type=int, default=21)
    parser.add_argument('--sem-boa', action='store_true', help='Não calcular a fronteira exata BOA*.')
    parser.add_argument('--saida', type=Path, default=SAIDA)
    args = parser.parse_args(argv)
    if args.pares < 2 or args.passos_alpha < 11:
        parser.error('Use --pares ≥ 2 e --passos-alpha ≥ 11.')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        if args.tudo:
            rodar_tudo(args.saida, args.pares, args.semente, args.origem, args.destino)
        elif args.modelos:
            executar_validacao_modelos(args.saida)
        elif args.testes:
            return 0 if executar_testes(args.saida)[0] else 1
        elif args.monte_carlo:
            executar_monte_carlo(args.saida, args.pares, args.semente)
        else:
            executar_pareto_e_perfil(args.saida, args.origem, args.destino, args.carga, args.passos_alpha,
                                     not args.sem_boa, perfil=args.perfil, pareto=args.pareto)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
