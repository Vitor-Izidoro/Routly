"""Routly — menu principal (CLI central).

    python main.py               menu interativo
    python main.py --opcao 3.6   executa uma opção diretamente (ex.: pipeline completo)

O ETL do IPPUC está em etl_ippuc.py; o roteamento, em executar.py; as
comprovações científicas, em experimentos/comprovacao_cientifica.py.
"""
import argparse
from pathlib import Path
import shlex
import sys
import warnings
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
CSV_GRAFO = BASE / 'grafo_curitiba_carbono.csv'
SAIDA = BASE / 'resultados_validacao'
ORIGEM_PADRAO = 'R. AMADEU ASSAD YASSIM'
DESTINO_PADRAO = 'R. GEN. LUIZ CARLOS PEREIRA TOURINHO'


class Voltar(Exception):
    """Usuário pediu para voltar ao menu anterior."""


# ------------------------------------------------------------------ entrada

def perguntar(texto, padrao=None, opcoes=None, tipo=str):
    """input() com padrão, validação e 'v' para voltar."""
    sufixo = f' [{padrao}]' if padrao not in (None, '') else ''
    while True:
        resposta = input(f'{texto}{sufixo}: ').strip()
        if resposta.lower() == 'v':
            raise Voltar
        if not resposta and padrao is not None:
            resposta = str(padrao)
        if opcoes and resposta not in opcoes:
            print(f'  Opção inválida. Escolha entre: {", ".join(opcoes)} (ou v para voltar).')
            continue
        try:
            return tipo(resposta)
        except ValueError:
            print('  Valor inválido, tente novamente.')


def confirmar(texto, padrao='s'):
    return perguntar(f'{texto} (s/n)', padrao, ['s', 'n', 'S', 'N']).lower() == 's'


def status(caminho):
    return '[OK]' if Path(caminho).exists() else '[AUSENTE]'


def exigir_grafo():
    if CSV_GRAFO.exists():
        return True
    print('\n[!] grafo_curitiba_carbono.csv ausente. Gere-o pela opção 1.1 antes de continuar.')
    return False


# ----------------------------------------------------------- [1] ETL / mapas

def opcao_1_1():
    from etl_ippuc import CAMINHO_CURVAS, CAMINHO_RUAS, executar_etl
    print(f'\nShapefile de ruas:   {status(CAMINHO_RUAS)} {CAMINHO_RUAS}')
    print(f'Shapefile de curvas: {status(CAMINHO_CURVAS)} {CAMINHO_CURVAS}')
    if CSV_GRAFO.exists() and not confirmar('O grafo já existe. Forçar a recriação a partir dos Shapefiles?', 'n'):
        print('Grafo existente mantido.')
        return
    executar_etl()


def _escolher_par():
    origem = perguntar('Rua de origem (nome exato)', ORIGEM_PADRAO)
    destino = perguntar('Rua de destino (nome exato)', DESTINO_PADRAO)
    return origem, destino


def _escolher_cenario_carga(padrao='3'):
    from experimentos.comprovacao_cientifica import CENARIOS_CARGA
    nomes = list(CENARIOS_CARGA)
    for i, nome in enumerate(nomes, 1):
        print(f'  {i}. {nome} ({CENARIOS_CARGA[nome]:,.0f} kg adicionais)'.replace(',', '.'))
    return nomes[int(perguntar('Cenário de carga', padrao, [str(i) for i in range(1, len(nomes) + 1)])) - 1]


def opcao_1_2():
    if not exigir_grafo():
        return
    from mapa import gerar_mapa_rotas
    origem, destino = _escolher_par()
    cenario = _escolher_cenario_carga()
    gerar_mapa_rotas(origem, destino, cenario, SAIDA / 'mapa_rotas.html', abrir=confirmar('Abrir no navegador?'))


def opcao_1_3():
    if not exigir_grafo():
        return
    from mapa import explorar_cruzamentos
    explorar_cruzamentos(perguntar('Rua (nome exato)', 'R. JOÃO CHEDE').upper(), limite=50)


# ------------------------------------------------------ [2] roteamento (executar.py)

def rodar_executar(argumentos):
    """Chama executar.main() com a linha de comando montada; erros do argparse não encerram o menu."""
    import executar
    print(f'\n$ python executar.py {shlex.join(argumentos)}')
    with patch.object(sys, 'argv', ['executar.py', *argumentos]):
        try:
            executar.main()
        except SystemExit as saida:
            if saida.code not in (0, None):
                print('[!] Parâmetros rejeitados pelo executar.py (mensagem acima).')


def _parametros_modelo(algoritmo):
    """Pergunta todas as opções do executar.py relevantes ao algoritmo escolhido."""
    from veiculos import MASSA_MERL_APROX_KG
    args = []
    origem, destino = _escolher_par()
    args += ['--origem', origem, '--destino', destino]
    print('\nModelo de emissão:\n  1. VT-CPFM-1 (padrão, Wang e Rakha 2017)\n  2. CMEM simplificado (Lai et al. 2024)'
          '\n  3. Legado (taxa g/km do catálogo canadense)')
    modelo = {'1': 'vtcpfm', '2': 'cmem', '3': 'legado'}[perguntar('Modelo', '1', ['1', '2', '3'])]
    args += ['--modelo-emissao', modelo]
    if modelo == 'vtcpfm':
        print('Conversão de CO₂:\n  1. EPA — 2.697,20 g/L\n  2. Artigo — 2.070 g/L (Wang e Rakha)')
        args += ['--cenario-co2', 'epa' if perguntar('Cenário de CO₂', '1', ['1', '2']) == '1' else 'artigo']
    elif modelo == 'cmem':
        print('Perfil físico:\n  1. HDDT1 (International 9800 SBA)\n  2. HDV genérico (Lai et al. 2024)')
        args += ['--caminhao', 'hddt1' if perguntar('Caminhão', '1', ['1', '2']) == '1' else 'hdv-generico']
    else:
        if confirmar('Informar a taxa de emissão manualmente (g/km)?', 'n'):
            args += ['--taxa-emissao', str(perguntar('Taxa (g/km)', '200', tipo=float))]
        else:
            args += ['--veiculo', perguntar('Marca e modelo do catálogo', 'CHEVROLET CRUZE')]
    if modelo != 'legado':
        print('Massa adicional (reboque + carga):\n  1. Vazio (0 kg)\n'
              f'  2. Meia carga ({MASSA_MERL_APROX_KG / 2:.0f} kg)\n  3. Carregado ({MASSA_MERL_APROX_KG:.0f} kg)'
              '\n  4. Outro valor')
        escolha = perguntar('Carga', '1', ['1', '2', '3', '4'])
        carga = {'1': 0.0, '2': MASSA_MERL_APROX_KG / 2, '3': MASSA_MERL_APROX_KG}.get(escolha)
        if carga is None:
            carga = perguntar('Massa adicional em kg', '0', tipo=float)
        args += ['--carga-kg', f'{carga:g}']
        args += ['--velocidade-kmh', f"{perguntar('Velocidade constante (km/h)', '30', tipo=float):g}"]
    if algoritmo == 'alt':
        args += ['--landmarks', str(perguntar('Número de landmarks do ALT', '4', tipo=int))]
    if algoritmo == 'boa':
        args += ['--rota', str(perguntar('Alternativa de Pareto a detalhar/plotar', '1', tipo=int))]
    if not confirmar('Exibir o mapa da rota (janela matplotlib)?', 'n'):
        args.append('--sem-mapa')
    return args


def menu_roteamento():
    while True:
        print('\n[2] EXECUÇÃO E ROTEAMENTO (executar.py / estrela.py / algoritmos.py)\n'
              '  2.1 ALT (A* + landmarks) — menor distância\n'
              '  2.2 ALT (A* + landmarks) — menor emissão de CO₂\n'
              '  2.3 BOA* — fronteira de Pareto completa (distância × emissão)\n'
              '  2.4 NBA* bidirecional legado (distância ou emissão)\n'
              '  2.5 Assistente original do executar.py (perguntas passo a passo)\n'
              '  2.6 Linha de comando avançada (argumentos livres do executar.py)\n'
              '  0   Voltar')
        escolha = input('Opção: ').strip()
        if escolha in ('0', 'v', ''):
            return
        if escolha in ('2.1', '2.2', '2.3', '2.4', '2.5', '2.6') and not exigir_grafo():
            continue
        try:
            if escolha == '2.1':
                rodar_executar(['--algoritmo', 'alt', '--modo', 'distancia', *_parametros_modelo('alt')])
            elif escolha == '2.2':
                rodar_executar(['--algoritmo', 'alt', '--modo', 'emissao', *_parametros_modelo('alt')])
            elif escolha == '2.3':
                rodar_executar(['--algoritmo', 'boa', *_parametros_modelo('boa')])
            elif escolha == '2.4':
                modo = 'distancia' if perguntar('Modo: 1. distância  2. emissão', '2', ['1', '2']) == '1' else 'emissao'
                rodar_executar(['--algoritmo', 'nba', '--modo', modo, *_parametros_modelo('nba')])
            elif escolha == '2.5':
                rodar_executar([])
            elif escolha == '2.6':
                print('Exemplo: --algoritmo boa --carga-kg 10000 --velocidade-kmh 30 --rota 2 --sem-mapa')
                rodar_executar(shlex.split(perguntar('Argumentos', '--help')))
            else:
                print('Opção inválida.')
        except Voltar:
            continue


# ------------------------------------------------------ [3] comprovações (TCC)

def _cc():
    from experimentos import comprovacao_cientifica
    return comprovacao_cientifica


def opcao_3_1():
    if exigir_grafo():
        _cc().executar_validacao_modelos(SAIDA)


def opcao_3_2():
    _cc().executar_testes(SAIDA)


def opcao_3_3():
    if not exigir_grafo():
        return
    origem, destino = _escolher_par()
    cenario = _escolher_cenario_carga()
    passos = perguntar('Número de passos de α (≥ 11)', '21', tipo=int)
    r = _cc().executar_pareto_e_perfil(SAIDA, origem, destino, cenario, max(11, passos), perfil=False)['pareto']
    print(f"\nBaseline: {r['baseline_km']:.2f} km, {r['baseline_kg']:.2f} kg | Routly: {r['routly_km']:.2f} km, "
          f"{r['routly_kg']:.2f} kg (−{r['economia_routly_pct']:.2f} % CO₂)\nJoelho α = {r['joelho_alpha']:.2f}: "
          f"−{r['joelho_economia_pct']:.2f} % CO₂ com +{r['joelho_distancia_extra_pct']:.2f} % de distância")


def opcao_3_4():
    if not exigir_grafo():
        return
    origem, destino = _escolher_par()
    cenario = _escolher_cenario_carga()
    perfil = _cc().executar_pareto_e_perfil(SAIDA, origem, destino, cenario, pareto=False)['perfil']
    for nome, d in perfil.items():
        print(f"{nome}: {d['distancia_km']:.2f} km, {d['co2_kg']:.2f} kg CO₂, subida {d['subida_m']:.0f} m")


def opcao_3_5(n_pares=None):
    if not exigir_grafo():
        return
    n = n_pares or perguntar('Número de pares Origem-Destino (N)', '100', tipo=int)
    for nome, s in _cc().executar_monte_carlo(SAIDA, max(2, n)).items():
        print(f"{nome}: redução mediana {s['mediana']:.2f} % | p = {s['p_bicaudal']:.2e}")


def opcao_3_6(n_pares=None):
    if not exigir_grafo():
        return
    n = n_pares or perguntar('Número de pares para o Monte Carlo (N)', '100', tipo=int)
    _cc().rodar_tudo(SAIDA, max(2, n))


OPCOES = {
    '1.1': ('Gerar/Recriar grafo base a partir dos Shapefiles do IPPUC', opcao_1_1),
    '1.2': ('Gerar/Visualizar mapa interativo de rotas (HTML)', opcao_1_2),
    '1.3': ('Explorar cruzamentos de uma rua', opcao_1_3),
    '2': ('Execução e roteamento (submenu)', menu_roteamento),
    '3.1': ('Validação VT-CPFM / CMEM e conversão de CO₂', opcao_3_1),
    '3.2': ('Suíte de testes automatizados (pytest)', opcao_3_2),
    '3.3': ('Análise multiobjetivo e Fronteira de Pareto', opcao_3_3),
    '3.4': ('Perfil altimétrico comparativo (elevação × CO₂ acumulado)', opcao_3_4),
    '3.5': ('Monte Carlo + teste de Wilcoxon', opcao_3_5),
    '3.6': ('RODAR TUDO — pipeline completo de comprovação', opcao_3_6),
}


def cabecalho():
    from dados_co2 import CAMINHO_DATASET
    from etl_ippuc import CAMINHO_RUAS
    return (
        '\n' + '=' * 66 +
        '\n  ROUTLY — Roteamento ecológico multiobjetivo para Curitiba\n' + '=' * 66 +
        f'\n  Grafo base (grafo_curitiba_carbono.csv) ... {status(CSV_GRAFO)}'
        f'\n  Shapefiles IPPUC ......................... {status(CAMINHO_RUAS)}'
        f'\n  Catálogo CO₂ (Kaggle) .................... {status(CAMINHO_DATASET)}'
        f'\n  Resultados (resultados_validacao/) ....... {status(SAIDA)}\n' + '-' * 66)


def menu_principal():
    while True:
        print(cabecalho())
        print('[1] PREPARAÇÃO DE DADOS E MAPAS (ETL)')
        for chave in ('1.1', '1.2', '1.3'):
            print(f'  {chave} {OPCOES[chave][0]}')
        print('[2] EXECUÇÃO E ROTEAMENTO\n  2   Abrir submenu (ALT, BOA*, NBA*, assistente, CLI)')
        print('[3] COMPROVAÇÕES CIENTÍFICAS E VALIDAÇÃO (TCC)')
        for chave in ('3.1', '3.2', '3.3', '3.4', '3.5', '3.6'):
            print(f'  {chave} {OPCOES[chave][0]}')
        print('  0   Sair   (em qualquer pergunta, digite v para voltar)')
        escolha = input('Opção: ').strip()
        if escolha in ('0', 'q', 'sair'):
            print('Até logo!')
            return
        if escolha in ('1', '3'):
            print('Escolha uma subopção, por exemplo 1.1 ou 3.6.')
            continue
        if escolha.startswith('2.'):
            escolha = '2'
        if escolha not in OPCOES:
            print('Opção inválida.')
            continue
        executar_opcao(escolha)


def executar_opcao(chave, **kwargs):
    try:
        with warnings.catch_warnings():
            if chave.startswith('3'):  # avisos de declividade já constam nos relatórios
                warnings.simplefilter('ignore', UserWarning)
            OPCOES[chave][1](**kwargs)
    except Voltar:
        pass
    except (ValueError, FileNotFoundError, OSError) as erro:
        print(f'[ERRO] {erro}')


def main(argv=None):
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--opcao', choices=[k for k in OPCOES if k != '2'],
                        help='Executa uma opção sem abrir o menu.')
    parser.add_argument('--pares', type=int, help='N do Monte Carlo (opções 3.5 e 3.6).')
    args = parser.parse_args(argv)
    try:
        if args.opcao in ('3.5', '3.6'):
            executar_opcao(args.opcao, n_pares=args.pares or 100)
        elif args.opcao:
            executar_opcao(args.opcao)
        else:
            menu_principal()
    except (EOFError, KeyboardInterrupt):
        print('\nEncerrado.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
