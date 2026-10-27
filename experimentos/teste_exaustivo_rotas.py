"""Repete 100 vezes o cálculo do mapa, com terminal e exportação opcional de boxplots.

Usa VT-CPFM, 30 km/h e 11 passos de alpha, como mapa.gerar_mapa_rotas.
É um lote de 100 consultas, não uma enumeração de todos os caminhos da malha.
"""
import argparse
from contextlib import redirect_stdout
import csv
from io import StringIO
from math import fsum
from pathlib import Path
import sys

from experimentos import comprovacao_cientifica as cc
from experimentos.avaliar_eficacia import maior_componente, pares_aleatorios

TOTAL_TESTES = 100
ALTERNATIVAS = ('Mais econômica', 'Compromisso', 'Mais rápida (menor distância)')


def _valores(solucao):
    trajeto = solucao['trajeto']
    return dict(distancia_km=trajeto.distancia / 1000, co2_kg=trajeto.emissao / 1000,
                economia_co2_pct=solucao['co2_economizado_pct'],
                distancia_adicional_pct=solucao['distancia_adicional_pct'])


def _imprimir(nome, valores):
    print(f"  {nome}: {valores['distancia_km']:.3f} km | {valores['co2_kg']:.3f} kg CO₂ | "
          f"economia CO₂ {valores['economia_co2_pct']:.2f}% | "
          f"distância adicional {valores['distancia_adicional_pct']:+.2f}%", flush=True)


def _identificar_ponto(no, ruas_por_no):
    ruas = ' / '.join(sorted(ruas_por_no.get(no, ()))) or 'Rua não identificada'
    return f'{ruas} (X={no[0]:.3f}; Y={no[1]:.3f})'


def executar_teste_exaustivo(cenario='Carregado', semente=42, origem=None, destino=None):
    """Calcula 100 consultas completas e médias aritméticas por alternativa.

    Com origem e destino, repete o mesmo par. Sem eles, sorteia pares na
    maior componente da malha bidirecional, usando uma semente reproduzível.
    Não grava arquivos nem abre mapas. Falhas interrompem o lote, sem reduzir
    silenciosamente o denominador das médias.
    """
    if (origem is None) != (destino is None):
        raise ValueError('Informe origem e destino juntos.')
    if cenario not in cc.CENARIOS_CARGA:
        raise ValueError('Cenário de carga inválido.')
    carga = cc.CENARIOS_CARGA[cenario]
    # Os carregadores legados imprimem diagnósticos; o lote exibe só seus resultados.
    with redirect_stdout(StringIO()):
        grafo = cc.carregar_malha('vtcpfm', carga, velocidade_kmh=cc.VELOCIDADE_KMH)
        if origem is not None:
            par = cc.localizar_par(origem, destino)
            if par[0] == par[1]:
                raise ValueError('Origem e destino devem corresponder a nós diferentes.')
            pares = [par] * TOTAL_TESTES
        else:
            componente = maior_componente(grafo)
            if len(componente) < 2:
                raise ValueError('A malha deve conter ao menos dois nós conectados.')
            pares = pares_aleatorios(componente, TOTAL_TESTES, semente)
        ruas_por_no = {}
        for rua, nos in cc.carregar_indice_ruas(cc.CSV_GRAFO).items():
            for no in nos:
                ruas_por_no.setdefault(no, set()).add(rua)
    limites = cc.limites_heuristica(grafo)
    resultados = []
    for numero, (o, d) in enumerate(pares, 1):
        print(f'Teste {numero:03d}/{TOTAL_TESTES}', flush=True)
        print(f'  Origem: {_identificar_ponto(o, ruas_por_no)}', flush=True)
        print(f'  Destino: {_identificar_ponto(d, ruas_por_no)}', flush=True)
        try:
            resultado = cc.analisar_fronteira(grafo, o, d, passos=11, carga_kg=carga,
                                             incluir_boa=False, limites=limites)
        except ValueError as erro:
            raise ValueError(f'Teste {numero}/{TOTAL_TESTES}: {erro}') from erro
        escolhidas = (resultado.solucoes[-1], resultado.solucoes[resultado.joelho], resultado.solucoes[0])
        rotas = {nome: _valores(s) for nome, s in zip(ALTERNATIVAS, escolhidas)}
        resultados.append(dict(origem=o, destino=d, rotas=rotas,
                               origem_ruas=' / '.join(sorted(ruas_por_no.get(o, ()))),
                               destino_ruas=' / '.join(sorted(ruas_por_no.get(d, ())))))
        for nome, valores in rotas.items():
            _imprimir(nome, valores)
    medias = {nome: {metrica: fsum(r['rotas'][nome][metrica] for r in resultados) / TOTAL_TESTES
                     for metrica in resultados[0]['rotas'][nome]} for nome in ALTERNATIVAS}
    print(f'\nMÉDIAS DOS {TOTAL_TESTES} TESTES', flush=True)
    for nome, valores in medias.items():
        _imprimir(nome, valores)
    return dict(total=TOTAL_TESTES, resultados=resultados, medias=medias,
                cenario=cenario, carga_kg=carga, velocidade_kmh=cc.VELOCIDADE_KMH,
                semente=semente if origem is None else None,
                amostragem='Pares aleatórios' if origem is None else 'Mesmo trajeto')


def exportar_boxplots(resultado, pasta):
    """Exporta os valores individuais (300 linhas) e boxplots, sem recalcular rotas."""
    from matplotlib.figure import Figure
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    metricas = [('distancia_km', 'Distância percorrida', 'km', 20),
                ('co2_kg', 'Emissão estimada de CO₂', 'kg CO₂', 30),
                ('economia_co2_pct', 'Economia de CO₂ versus a mais curta', '%', 20),
                ('distancia_adicional_pct', 'Distância adicional versus a mais curta', '%', 20)]
    linhas = []
    for numero, teste in enumerate(resultado['resultados'], 1):
        for nome in ALTERNATIVAS:
            linhas.append(dict(teste=numero, rota=nome, origem_ruas=teste['origem_ruas'],
                               destino_ruas=teste['destino_ruas'],
                               origem_x=teste['origem'][0], origem_y=teste['origem'][1],
                               destino_x=teste['destino'][0], destino_y=teste['destino'][1],
                               **teste['rotas'][nome], cenario=resultado['cenario'],
                               carga_kg=resultado['carga_kg'], modelo='vtcpfm',
                               velocidade_kmh=resultado['velocidade_kmh'],
                               amostragem=resultado['amostragem'], semente=resultado['semente']))
    csv_path = pasta / 'rotas_100_testes.csv'
    with csv_path.open('w', newline='', encoding='utf-8-sig') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)

    fig = Figure(figsize=(12, 9), facecolor='#fcfcfa')
    cores = ('#35795c', '#47a3a0', '#d1884e')
    for ax, (metrica, titulo, unidade, limite) in zip(fig.subplots(2, 2).flat, metricas):
        dados = [[teste['rotas'][nome][metrica] for teste in resultado['resultados']]
                 for nome in ALTERNATIVAS]
        caixas = ax.boxplot(dados, widths=.5, patch_artist=True, showmeans=True,
                           showfliers=True, whis=1.5,
                           medianprops={'color': '#162d27', 'linewidth': 1.8},
                           meanprops={'marker': 'D', 'markerfacecolor': '#fff2bd',
                                      'markeredgecolor': '#162d27', 'markersize': 5},
                           flierprops={'marker': 'o', 'markersize': 3, 'alpha': .5})
        for caixa, cor in zip(caixas['boxes'], cores):
            caixa.set_facecolor(cor)
            caixa.set_alpha(.65)
        ax.set_xticks([1, 2, 3], ['Mais econômica', 'Compromisso', 'Mais rápida\n(menor distância)'])
        ax.set_title(titulo, fontsize=11, loc='left', pad=12)
        ax.set_ylabel(unidade)
        ax.set_ylim(0, limite)
        ax.set_yticks(range(0, limite + 1, 5))
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(labelsize=9)
    fig.suptitle(f"Comparação das três rotas · {resultado['total']} testes", fontsize=17, y=.97)
    semente = f" · semente {resultado['semente']}" if resultado['semente'] is not None else ''
    carga_texto = f"{resultado['carga_kg']:,.0f}".replace(',', '.')
    fig.text(.5, .925, f"VT-CPFM · {resultado['cenario']} ({carga_texto} kg adicionais) · "
             f"{resultado['velocidade_kmh']:g} km/h · {resultado['amostragem']}{semente}",
             ha='center', fontsize=10, color='#53625b')
    fig.text(.06, .075, 'Cada caixa reúne os 100 valores individuais da alternativa, sem usar as médias como amostra.\n'
             'Caixa: percentis 25–75 · linha: mediana · losango: média · hastes: até 1,5 × intervalo interquartil · pontos: valores além das hastes.\n'
             'Os três grupos usam os mesmos pares origem–destino. Na rota mais curta, os percentuais são zero por definição.\n'
             'Mais rápida pressupõe velocidade constante. Repetir o mesmo trajeto produz caixas sem dispersão.\n'
             'Valores fora dos limites exibidos continuam incluídos nas estatísticas e estão disponíveis no CSV.',
             fontsize=8.5, linespacing=1.6, color='#53625b')
    fig.tight_layout(rect=(.025, .16, .99, .90), h_pad=2.5, w_pad=2)
    png_path, svg_path = pasta / 'boxplots_rotas.png', pasta / 'boxplots_rotas.svg'
    fig.savefig(png_path, dpi=180)
    fig.savefig(svg_path)
    for caminho in (csv_path, png_path, svg_path):
        print(f'[SALVO] {caminho}', flush=True)
    return csv_path, png_path, svg_path


def main(argv=None):
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--carga', choices=list(cc.CENARIOS_CARGA), default='Carregado')
    parser.add_argument('--semente', type=int, default=42)
    parser.add_argument('--origem', help='Com --destino, repete o mesmo trajeto 100 vezes.')
    parser.add_argument('--destino')
    parser.add_argument('--boxplots', action='store_true', help='Exporta CSV e boxplots das três rotas.')
    parser.add_argument('--saida', type=Path, default=cc.SAIDA / 'teste_exaustivo_rotas')
    args = parser.parse_args(argv)
    if (args.origem is None) != (args.destino is None):
        parser.error('Informe --origem e --destino juntos.')
    resultado = executar_teste_exaustivo(args.carga, args.semente, args.origem, args.destino)
    if args.boxplots:
        exportar_boxplots(resultado, args.saida)


if __name__ == '__main__':
    main()
