"""Interface de terminal para ALT, BOA* e a implementação legada NBA*."""
import argparse
from pathlib import Path
from time import perf_counter
import math
import pandas as pd
from algoritmos import IndiceALT, boa_estrela
from emissoes import CaminhaoCMEM, validar_cenario
from estrela import (carregar_catalogo_veiculos, carregar_grafos_direcionais,
                     carregar_indice_ruas, pegar_um_no_da_rua,
                     gerar_instrucoes_de_rota, plotar_rota_no_mapa, nba_estrela)

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--algoritmo', choices=['alt', 'boa', 'nba'])
    parser.add_argument('--modo', choices=['distancia', 'emissao'], default='emissao')
    parser.add_argument('--origem', default='R. AMADEU ASSAD YASSIM')
    parser.add_argument('--destino', default='R. GEN. LUIZ CARLOS PEREIRA TOURINHO')
    parser.add_argument('--veiculo', help='Marca/modelo do catálogo, somente no modelo legado.')
    parser.add_argument('--modelo-emissao', choices=['cmem', 'legado'], default='cmem')
    parser.add_argument('--carga-kg', type=float, default=0.0)
    parser.add_argument('--velocidade-kmh', type=float, default=30.0)
    parser.add_argument('--taxa-emissao', type=float)
    parser.add_argument('--landmarks', type=int, default=4)
    parser.add_argument('--rota', type=int, help='Número da alternativa BOA* (começa em 1).')
    parser.add_argument('--sem-mapa', action='store_true')
    args = parser.parse_args()
    interativo = args.algoritmo is None
    if interativo:
        print('\nMAPA DE CARBONO — CURITIBA\n1. ALT: menor distância\n2. ALT: menor emissão\n3. BOA*: alternativas distância × emissão')
        escolha = input('Escolha [3]: ').strip() or '3'
        if escolha not in ('1', '2', '3'):
            parser.error('Escolha 1, 2 ou 3.')
        args.algoritmo = 'boa' if escolha == '3' else 'alt'
        args.modo = 'distancia' if escolha == '1' else 'emissao'
        args.origem = input(f'Rua de origem [{args.origem}]: ').strip() or args.origem
        args.destino = input(f'Rua de destino [{args.destino}]: ').strip() or args.destino
    if args.landmarks < 1:
        parser.error('--landmarks deve ser positivo.')
    if args.modelo_emissao == 'cmem' and (args.taxa_emissao is not None or args.veiculo):
        parser.error('--taxa-emissao e --veiculo exigem --modelo-emissao legado.')
    if interativo and args.modelo_emissao == 'cmem':
        print('Caminhão pesado de referência: 13.000 kg vazio. Velocidade é uma hipótese constante.')
        try:
            args.carga_kg = float(input(f'Carga em kg [{args.carga_kg:g}]: ').strip() or args.carga_kg)
            args.velocidade_kmh = float(input(f'Velocidade em km/h [{args.velocidade_kmh:g}]: ').strip() or args.velocidade_kmh)
        except ValueError:
            parser.error('Carga e velocidade devem ser números.')
    try:
        validar_cenario(args.carga_kg, args.velocidade_kmh)
    except ValueError as erro:
        parser.error(str(erro))
    taxa = args.taxa_emissao
    if args.modelo_emissao == 'legado' and taxa is None:
        catalogo_path = BASE / 'CO2 Emissions_Canada.csv'
        catalogo = carregar_catalogo_veiculos(catalogo_path) if catalogo_path.exists() else {}
        taxa = catalogo.get((args.veiculo or 'CHEVROLET CRUZE').upper())
        if taxa is None:
            taxa = 200.0
            print('[CONFIG] Catálogo/veículo indisponível: taxa de exemplo de 200 g/km. Use --taxa-emissao para alterar.')
    if args.modelo_emissao == 'legado' and (not math.isfinite(taxa) or taxa <= 0):
        parser.error('A taxa de emissão deve ser finita e maior que zero.')
    caminho = BASE / 'grafo_curitiba_carbono.csv'
    if not caminho.exists():
        parser.error('Grafo ausente. Disponibilize os shapefiles e execute main.py antes.')
    caminhao = CaminhaoCMEM()
    if args.modelo_emissao == 'cmem':
        print(f'[CONFIG] CMEM simplificado | massa total {caminhao.massa_vazia_kg + args.carga_kg:g} kg | '
              f'{args.velocidade_kmh:g} km/h | diesel de referência')
        print('[CONFIG] Cenário teórico sem calibração local; altitude por extremidades, sem tráfego/paradas.')
    try:
        grafo, reverso = carregar_grafos_direcionais(
            caminho, taxa, modelo=args.modelo_emissao, caminhao=caminhao,
            carga_kg=args.carga_kg, velocidade_kmh=args.velocidade_kmh)
    except ValueError as erro:
        parser.error(str(erro))
    ruas = carregar_indice_ruas(caminho)
    inicio = pegar_um_no_da_rua(ruas, args.origem.upper())
    destino = pegar_um_no_da_rua(ruas, args.destino.upper())
    if inicio is None or destino is None:
        parser.error('Confira os nomes exatos das ruas no CSV.')
    print(f'\n{args.algoritmo.upper()} | {len(grafo)} nós | modelo {args.modelo_emissao}')
    if args.algoritmo == 'alt':
        t = perf_counter()
        indice = IndiceALT(grafo, args.modo, args.landmarks)
        print(f'Pré-processamento ALT: {perf_counter() - t:.3f} s')
        t = perf_counter()
        resultado = indice.buscar(inicio, destino)
        print(f'Consulta ALT: {perf_counter() - t:.3f} s')
        alternativas = [resultado] if resultado else []
    elif args.algoritmo == 'boa':
        print('Calculando a fronteira completa de Pareto...')
        t = perf_counter()
        alternativas = boa_estrela(grafo, inicio, destino)
        print(f'BOA* (inclui heurísticas reversas): {perf_counter() - t:.3f} s')
    else:
        # A heurística antiga por g/km não é admissível para o novo custo.
        # h=0 na emissão CMEM reduz a busca legada à busca bidirecional por g.
        taxa_heuristica = 0.0 if args.modelo_emissao == 'cmem' else taxa
        nos, custo = nba_estrela(grafo, reverso, inicio, destino, args.modo, taxa_heuristica)
        if not nos:
            print('Não existe caminho entre os nós selecionados.')
            return
        print(f'NBA* legado: custo {custo:.2f} ({args.modo})')
        for passo in gerar_instrucoes_de_rota(nos, pd.read_csv(caminho)):
            print(passo)
        if not args.sem_mapa:
            plotar_rota_no_mapa(pd.read_csv(caminho), nos, args.modo)
        return
    if not alternativas:
        print('Não existe caminho entre os nós selecionados.')
        return
    print('\nRota | Distância (km) | CO₂ estimado (g)' + (' | Diesel estimado (L)' if args.modelo_emissao == 'cmem' else ''))
    for i, rota in enumerate(alternativas, 1):
        combustivel = f' | {rota.emissao / caminhao.fator_co2_g_l:20.3f}' if args.modelo_emissao == 'cmem' else ''
        print(f'{i:4} | {rota.distancia / 1000:14.3f} | {rota.emissao:16.2f}{combustivel}')
    numero = 1 if args.rota is None else args.rota
    if interativo and len(alternativas) > 1:
        try:
            numero = int(input('Alternativa para visualizar [1]: ').strip() or '1')
        except ValueError:
            parser.error('Informe um número inteiro de alternativa.')
    if not 1 <= numero <= len(alternativas):
        parser.error(f'--rota deve estar entre 1 e {len(alternativas)}.')
    rota = alternativas[numero - 1]
    print(f'\nRota selecionada: {numero} ({len(rota.nos)} nós)')
    df = pd.read_csv(caminho)
    for passo in gerar_instrucoes_de_rota(rota.nos, df):
        print(passo)
    print('-> [CHEGOU AO DESTINO]')
    if not args.sem_mapa:
        plotar_rota_no_mapa(df, rota.nos, 'pareto' if args.algoritmo == 'boa' else args.modo)


if __name__ == '__main__':
    main()
