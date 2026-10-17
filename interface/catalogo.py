"""Catálogo compartilhado pela API, formulários e executor. Sem dependências científicas."""
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
GRUPOS = [
    dict(id='testes', nome='Testes automatizados', descricao='Verifique os algoritmos, as equações e a consistência do sistema.', icone='check'),
    dict(id='modelos', nome='Validação de modelos', descricao='Investigue unidades, fatores de CO₂ e a concordância entre os modelos físicos.', icone='leaf'),
    dict(id='ciencia', nome='Análises científicas', descricao='Compare objetivos, relevo e economia de emissões com experimentos reproduzíveis.', icone='chart'),
    dict(id='rotas', nome='Roteamento', descricao='Explore caminhos com ALT, BOA* e NBA*, usando os mesmos motores do terminal.', icone='route'),
    dict(id='dados', nome='Dados e mapas', descricao='Prepare a malha de Curitiba e inspecione ruas, cruzamentos e mapas.', icone='map'),
]


def campo(id, nome, tipo='number', padrao=None, **extras):
    return dict(id=id, nome=nome, tipo=tipo, padrao=padrao, **extras)


ORIGEM = campo('origem', 'Rua de origem', 'text', 'R. AMADEU ASSAD YASSIM')
DESTINO = campo('destino', 'Rua de destino', 'text', 'R. GEN. LUIZ CARLOS PEREIRA TOURINHO')
CARGA = campo('carga', 'Cenário de carga', 'select', 'Carregado', opcoes=['Vazio', 'Meia carga', 'Carregado'])
PARES = campo('pares', 'Pares origem–destino', padrao=100, min=2, inteiro=True)
SEMENTE = campo('semente', 'Semente aleatória', padrao=42, min=0, inteiro=True)
PASSOS = campo('passos', 'Passos de α', padrao=21, min=11, inteiro=True)
BOA = campo('boa', 'Calcular fronteira exata BOA* (pode ser demorado)', 'checkbox', True)
LANDMARKS = campo('landmarks', 'Landmarks', padrao=4, min=1, inteiro=True)
ROTA_CAMPOS = [ORIGEM, DESTINO,
    campo('modelo', 'Modelo de emissão', 'select', 'vtcpfm', opcoes=['vtcpfm', 'cmem', 'legado']),
    campo('cenario_co2', 'Conversão de CO₂', 'select', 'epa', opcoes=['epa', 'artigo'], quando={'modelo': 'vtcpfm'}),
    campo('caminhao', 'Perfil físico', 'select', 'hddt1', opcoes=['hddt1', 'hdv-generico'], quando={'modelo': 'cmem'}),
    campo('carga_kg', 'Reboque + carga (kg)', padrao=0, min=0),
    campo('velocidade', 'Velocidade (km/h)', padrao=30, min=0.01),
    campo('fonte_legado', 'Emissão no modelo legado', 'select', 'taxa', opcoes=['taxa', 'catalogo'], quando={'modelo': 'legado'}),
    campo('taxa', 'Taxa manual (g/km)', padrao=200, min=0.01, quando={'modelo': 'legado', 'fonte_legado': 'taxa'}),
    campo('veiculo', 'Marca e modelo do catálogo', 'text', 'CHEVROLET CRUZE', quando={'modelo': 'legado', 'fonte_legado': 'catalogo'}),
    campo('mapa', 'Gerar imagem da rota', 'checkbox', True)]


def operacao(id, grupo, nome, descricao, campos=(), **extras):
    return dict(id=id, grupo=grupo, nome=nome, descricao=descricao, campos=list(campos), **extras)


def catalogo():
    itens = [operacao('testes_todos', 'testes', 'Suíte completa', 'Todos os testes em tests/, com resultados detalhados por caso.', batch=False),
             operacao('unittest', 'testes', 'Suíte unittest', 'Executa a descoberta de testes unittest, como no terminal.', batch=False)]
    nomes = {'algoritmos': 'Algoritmos de busca', 'cenarios_co2': 'Cenários de CO₂',
             'comprovacao': 'Comprovação científica', 'conversao_co2': 'Conversão e unidades',
             'eficacia': 'Eficácia das rotas', 'emissoes': 'Modelo CMEM', 'vtcpfm': 'Modelo VT-CPFM',
             'interface': 'Interface e execução'}
    for arquivo in sorted((BASE / 'tests').glob('test_*.py')):
        chave = arquivo.stem.removeprefix('test_')
        itens.append(operacao('teste_' + chave, 'testes', nomes.get(chave, chave.replace('_', ' ').title()),
                              'Testes de ' + arquivo.name + '.', arquivo=arquivo.name))
    itens += [
        operacao('modelos', 'modelos', 'Validação integrada', 'Conversão, eficácia em três camadas, registro CMEM e paridade física.', [PARES], grafo=True, batch=False),
        operacao('conversao', 'modelos', 'Conversão de CO₂', 'Verifica unidades e compara o fator de emissão com o catálogo canadense.'),
        operacao('fisica', 'modelos', 'Paridade física', 'Compara VT-CPFM e CMEM em uma grade de declividades. Gera gráfico e métricas.'),
        operacao('cmem', 'modelos', 'Reprodução do CMEM', 'Reproduz as verificações registradas em docs/validacao_cmem.json.', grafo=True),
        operacao('eficacia', 'modelos', 'Eficácia em três camadas', 'Economia de CO₂, validação cruzada CMEM e sensibilidade ao ruído de altitude.',
                 [PARES, SEMENTE, LANDMARKS,
                  campo('cargas', 'Cargas (kg, separadas por vírgula)', 'numbers', '0, 10000, 20000', min=0),
                  campo('velocidades', 'Velocidades (km/h)', 'numbers', '30', min=0.01),
                  campo('ruido', 'Desvios de altitude (m; vazio desativa)', 'numbers', '1, 2', min=0, vazio=True),
                  campo('cmem', 'Validar também com CMEM', 'checkbox', True)], grafo=True),
        operacao('comparacao_rotas', 'ciencia', 'Comparação de rotas · subidas e CO₂', 'Compara a rota mais curta com a mais ecológica: distância, subida acumulada, emissões e ruas. Resultados no Terminal.', grafo=True),
        operacao('pareto', 'ciencia', 'Fronteira de Pareto', 'Distância × emissão, solução de compromisso e fronteira exata BOA*.', [ORIGEM, DESTINO, CARGA, PASSOS, BOA], grafo=True),
        operacao('perfil', 'ciencia', 'Perfil altimétrico', 'Elevação e CO₂ acumulado nas rotas mais curta e mais ecológica.', [ORIGEM, DESTINO, CARGA], grafo=True),
        operacao('monte_carlo', 'ciencia', 'Monte Carlo + Wilcoxon', 'Pares aleatórios em três cargas, intervalos de confiança e teste pareado.', [PARES, SEMENTE], grafo=True),
        operacao('pipeline', 'ciencia', 'Comprovação completa', 'Executa o pipeline 3.1 a 3.5 do terminal e gera o relatório consolidado.', [PARES, SEMENTE, ORIGEM, DESTINO], grafo=True, batch=False),
        operacao('alt_distancia', 'rotas', 'ALT · menor distância', 'A* com landmarks para encontrar a rota mais curta.', [*ROTA_CAMPOS, LANDMARKS], grafo=True),
        operacao('alt_emissao', 'rotas', 'ALT · menor emissão', 'A* com landmarks para minimizar o CO₂ estimado.', [*ROTA_CAMPOS, LANDMARKS], grafo=True),
        operacao('boa', 'rotas', 'BOA* · rotas de Pareto', 'Calcula todas as alternativas não dominadas e detalha a rota escolhida.', [*ROTA_CAMPOS, campo('rota', 'Alternativa a visualizar', padrao=1, min=1, inteiro=True)], grafo=True),
        operacao('nba', 'rotas', 'NBA* · bidirecional', 'Executa o algoritmo legado por distância ou emissão.', [*ROTA_CAMPOS, campo('modo', 'Objetivo', 'select', 'emissao', opcoes=['distancia', 'emissao'])], grafo=True),
        operacao('mapa', 'dados', 'Mapa interativo de rotas', 'Sobrepõe rotas curta, ecológica e de compromisso sobre a malha local IPPUC.', [ORIGEM, DESTINO, CARGA], grafo=True),
        operacao('cruzamentos', 'dados', 'Explorar cruzamentos', 'Lista as ruas conectadas à rua informada.', [campo('rua', 'Nome exato da rua', 'text', 'R. JOÃO CHEDE')], grafo=True),
        operacao('grafo', 'dados', 'Visualizar malha viária', 'Desenha as arestas do grafo de Curitiba.', grafo=True),
        operacao('colunas', 'dados', 'Inspecionar shapefile', 'Exibe as colunas e as primeiras linhas da base de ruas do IPPUC.', shapefiles=True),
        operacao('nomes', 'dados', 'Diagnóstico de nomes', 'Lista nomes do grafo e colunas do shapefile.', grafo=True, shapefiles=True),
        operacao('etl', 'dados', 'Gerar grafo do IPPUC', 'Converte os shapefiles em uma nova malha. O CSV gerado fica nos resultados desta execução.', shapefiles=True, batch=False),
    ]
    return itens


def validar(id, parametros):
    op = next((o for o in catalogo() if o['id'] == id), None)
    if op is None:
        raise ValueError('Operação desconhecida.')
    if not isinstance(parametros, dict):
        raise ValueError('Parâmetros inválidos.')
    if set(parametros) - {c['id'] for c in op['campos']}:
        raise ValueError('Parâmetro desconhecido.')
    resultado = {}
    for c in op['campos']:
        v = parametros.get(c['id'], c['padrao'])
        try:
            if c['tipo'] == 'checkbox':
                if not isinstance(v, bool):
                    raise ValueError()
            elif c['tipo'] == 'select':
                if v not in c['opcoes']:
                    raise ValueError()
            elif c['tipo'] in ('number', 'numbers'):
                valores = (v if isinstance(v, list) else str(v).split(',')) if c['tipo'] == 'numbers' else [v]
                if c.get('vazio') and v == '':
                    valores = []
                numeros = [float(n) for n in valores]
                if any(not math.isfinite(n) or n < c.get('min', -math.inf) for n in numeros):
                    raise ValueError()
                if c.get('inteiro') and any(n != int(n) for n in numeros):
                    raise ValueError()
                if c['tipo'] == 'numbers' and not numeros and not c.get('vazio'):
                    raise ValueError()
                v = numeros if c['tipo'] == 'numbers' else int(numeros[0]) if c.get('inteiro') else numeros[0]
            else:
                if not isinstance(v, str) or not v.strip() or len(v) > 250:
                    raise ValueError()
                v = v.strip()
        except (ValueError, TypeError, OverflowError):
            raise ValueError(f'Valor inválido para {c["nome"]}.') from None
        resultado[c['id']] = v
    return op, resultado
