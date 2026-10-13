"""Um processo por execução: reutiliza os motores do terminal e exporta figuras."""
import json
import math
import os
from pathlib import Path
import runpy
import sys
import traceback
from unittest.mock import patch

from interface.catalogo import BASE, validar


def serializar(valor):
    if hasattr(valor, 'item'):
        valor = valor.item()
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    if isinstance(valor, dict):
        return {str(k): serializar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [serializar(v) for v in valor]
    if isinstance(valor, Path):
        return str(valor)
    return valor


def rodar_modulo(modulo, argumentos):
    with patch.object(sys, 'argv', [modulo, *map(str, argumentos)]):
        runpy.run_module(modulo, run_name='__main__')


def executar(op, p, pasta):
    id = op['id']
    if id == 'testes_todos' or id.startswith('teste_'):
        import pytest
        alvo = str(BASE / 'tests' / op['arquivo']) if 'arquivo' in op else str(BASE / 'tests')
        print(f'$ python -m pytest {alvo} -v', flush=True)
        raise SystemExit(int(pytest.main([alvo, '-v', '-p', 'no:cacheprovider', '--color=no'])))
    if id == 'unittest':
        rodar_modulo('unittest', ['discover', '-s', 'tests', '-v'])
        return
    import matplotlib
    matplotlib.use('Agg', force=True)
    import matplotlib.pyplot as plt
    contador = 0

    def salvar_figuras(*args, **kwargs):
        nonlocal contador
        for numero in plt.get_fignums():
            contador += 1
            caminho = pasta / f'figura_{contador:02}.png'
            plt.figure(numero).savefig(caminho, dpi=150, bbox_inches='tight')
            print(f'[FIGURA] {caminho.name}', flush=True)
        plt.close('all')

    with patch.object(plt, 'show', salvar_figuras):
        if op.get('grafo') and not (BASE / 'grafo_curitiba_carbono.csv').is_file():
            raise FileNotFoundError('Grafo ausente. Gere o grafo do IPPUC e copie o CSV para a raiz do projeto.')
        if id in ('alt_distancia', 'alt_emissao', 'boa', 'nba'):
            algoritmo = 'alt' if id.startswith('alt_') else id
            args = ['--algoritmo', algoritmo, '--modo', 'distancia' if id == 'alt_distancia' else p.get('modo', 'emissao'),
                    '--origem', p['origem'], '--destino', p['destino'], '--modelo-emissao', p['modelo'],
                    '--carga-kg', p['carga_kg'], '--velocidade-kmh', p['velocidade']]
            if p['modelo'] == 'vtcpfm':
                args += ['--cenario-co2', p['cenario_co2']]
            elif p['modelo'] == 'cmem':
                args += ['--caminhao', p['caminhao']]
            else:
                args += ['--taxa-emissao', p['taxa']] if p['fonte_legado'] == 'taxa' else ['--veiculo', p['veiculo']]
            if algoritmo == 'alt':
                args += ['--landmarks', p['landmarks']]
            if algoritmo == 'boa':
                args += ['--rota', p['rota']]
            if not p['mapa']:
                args += ['--sem-mapa']
            rodar_modulo('executar', args)
        elif id == 'conversao':
            from experimentos.validar_conversao_co2 import main
            raise SystemExit(main(['--saida', str(pasta)]))
        elif id == 'eficacia':
            args = ['--saida', pasta, '--pares', p['pares'], '--semente', p['semente'], '--landmarks', p['landmarks'],
                    '--cargas', *p['cargas'], '--velocidades', *p['velocidades'], '--ruido-m', *p['ruido']]
            if not p['cmem']:
                args += ['--sem-cmem']
            rodar_modulo('experimentos.avaliar_eficacia', args)
        elif id == 'mapa':
            from mapa import gerar_mapa_rotas
            gerar_mapa_rotas(p['origem'], p['destino'], p['carga'], pasta / 'mapa_rotas.html', abrir=False)
        elif id == 'cruzamentos':
            from mapa import explorar_cruzamentos
            explorar_cruzamentos(p['rua'].upper(), limite=50)
        elif id == 'grafo':
            rodar_modulo('ver_grafo', [])
        elif id in ('colunas', 'nomes', 'etl'):
            from etl_ippuc import CAMINHO_RUAS, CAMINHO_CURVAS, executar_etl
            if id == 'etl':
                if not executar_etl(saida=pasta / 'grafo_curitiba_carbono.csv'):
                    raise RuntimeError('Não foi possível gerar o grafo. Confira os shapefiles e o log acima.')
                print('Grafo exportado. Para usá-lo nas rotas, copie o CSV para a raiz do projeto.')
            else:
                import pandas as pd
                import geopandas as gpd
                if id == 'nomes':
                    df = pd.read_csv(BASE / 'grafo_curitiba_carbono.csv')
                    nomes = df['nome_rua'].dropna().unique()
                    print(f'Total de nomes únicos: {len(nomes)}\nAmostra:')
                    print('\n'.join(map(str, nomes[:20])))
                df = gpd.read_file(CAMINHO_RUAS, encoding='latin1')
                print('Colunas disponíveis:', list(df.columns))
                print(df.head().to_string())
        else:
            from experimentos import comprovacao_cientifica as cc
            if id == 'fisica':
                resultado = cc.validacao_fisica(pasta)
            elif id == 'cmem':
                resultado = cc.reproduzir_registro_cmem(pasta)
            elif id == 'modelos':
                resultado = cc.executar_validacao_modelos(pasta, p['pares'])
            elif id in ('pareto', 'perfil'):
                resultado = cc.executar_pareto_e_perfil(pasta, p['origem'], p['destino'], p['carga'],
                    p.get('passos', 21), p.get('boa', False), perfil=id == 'perfil', pareto=id == 'pareto')
            elif id == 'monte_carlo':
                resultado = cc.executar_monte_carlo(pasta, p['pares'], p['semente'])
            elif id == 'pipeline':
                resultado = cc.rodar_tudo(pasta, p['pares'], p['semente'], p['origem'], p['destino'])
            else:
                raise ValueError('Operação não implementada.')
            resumo = json.dumps(serializar(resultado), ensure_ascii=False, indent=2, allow_nan=False)
            (pasta / 'metricas.json').write_text(resumo, encoding='utf-8')
            print('\n[RESULTADOS]\n' + resumo)
            if id == 'cmem' and resultado['passaram'] != resultado['total']:
                raise RuntimeError('Há divergências no registro CMEM. Consulte o relatório.')
            modelos = resultado.get('modelos', resultado) if id in ('pipeline', 'modelos') else None
            if modelos is not None:
                if 'conversao' not in modelos:
                    raise RuntimeError('A validação de conversão não foi concluída. Consulte o log.')
                registro = modelos['registro_cmem']
                if registro['passaram'] != registro['total'] or not all(v['passou'] for v in modelos['conversao']['verificacoes_unidades']):
                    raise RuntimeError('Há verificações reprovadas na validação dos modelos.')
            if id == 'pipeline' and not resultado['testes_ok']:
                raise RuntimeError('O pipeline terminou com falhas nos testes automatizados.')
        salvar_figuras()


def main():
    os.environ['MPLBACKEND'] = 'Agg'
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    job_path = Path(sys.argv[1]).resolve()
    job = json.loads(job_path.read_text(encoding='utf-8'))
    op, parametros = validar(job['operacao'], job['parametros'])
    pasta = job_path.parent / 'artefatos'
    pasta.mkdir(exist_ok=True)
    print(f'ROUTLY · {op["nome"]}\nParâmetros: {json.dumps(parametros, ensure_ascii=False)}\n', flush=True)
    try:
        executar(op, parametros, pasta)
    except ModuleNotFoundError as erro:
        print(f'\nDependência ausente: {erro.name}. Instale com: python -m pip install -r requirements.txt', flush=True)
        return 1
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
