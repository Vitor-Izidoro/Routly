"""Regressões do lote: 100 consultas reais, médias, integração e ausência de mapas."""
from contextlib import redirect_stdout
import csv
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimentos import teste_exaustivo_rotas as lote
from interface.catalogo import catalogo, validar
from interface.worker import executar
from interface import worker


class ExaustivoRotasTest(unittest.TestCase):
    def setUp(self):
        # Duas rotas: curta com 10 m/20 g; econômica com 12 m/8 g.
        self.grafo = {(0, 0): [((2, 0), 10, 20), ((1, 0), 6, 4)],
                      (1, 0): [((0, 0), 6, 4), ((2, 0), 6, 4)],
                      (2, 0): [((0, 0), 10, 20), ((1, 0), 6, 4)]}
        self.enterContext(patch.object(lote.cc, 'carregar_indice_ruas', return_value={
            'Rua Inicial': {(0, 0)}, 'Rua Intermediária': {(1, 0)},
            'Rua Final': {(2, 0)}, 'Rua da Esquina': {(2, 0)}}))

    def test_100_consultas_com_medias_e_sem_arquivos(self):
        pares = [((0, 0), (2, 0)), ((0, 0), (1, 0))] * 50
        saida = StringIO()
        original = lote.cc.analisar_fronteira
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(saida), \
                patch.object(lote.cc, 'carregar_malha', return_value=self.grafo), \
                patch.object(lote, 'pares_aleatorios', return_value=pares), \
                patch.object(lote.cc, 'analisar_fronteira', wraps=original) as calcular, \
                patch('mapa.gerar_mapa_rotas') as mapa, patch('webbrowser.open') as navegador, \
                patch('matplotlib.pyplot.savefig') as salvar:
            op, p = validar('exaustivo_rotas', {'boxplots': False})
            executar(op, p, Path(temp))
            self.assertEqual(list(Path(temp).iterdir()), [])
            self.assertEqual(calcular.call_count, 100)
            self.assertTrue(all(c.kwargs['passos'] == 11 and not c.kwargs['incluir_boa']
                                for c in calcular.call_args_list))
            mapa.assert_not_called()
            navegador.assert_not_called()
            salvar.assert_not_called()
        texto = saida.getvalue()
        self.assertEqual(texto.count('Teste '), 100)
        self.assertIn('Teste 100/100', texto)
        self.assertEqual(texto.count('  Origem: Rua Inicial (X=0.000; Y=0.000)'), 100)
        self.assertEqual(texto.count('  Destino: Rua Intermediária (X=1.000; Y=0.000)'), 50)
        self.assertEqual(texto.count('  Destino: Rua Final / Rua da Esquina (X=2.000; Y=0.000)'), 50)
        medias = texto.split('MÉDIAS DOS 100 TESTES')[1]
        self.assertIn('Mais econômica: 0.009 km | 0.006 kg CO₂ | economia CO₂ 30.00% | distância adicional +10.00%', medias)
        self.assertIn('Mais rápida (menor distância): 0.008 km | 0.012 kg CO₂', medias)
        for nome in lote.ALTERNATIVAS:
            self.assertEqual(texto.count(nome + ':'), 101)

    def test_repeticao_do_mesmo_par_recalcula_100_vezes(self):
        with redirect_stdout(StringIO()), patch.object(lote.cc, 'carregar_malha', return_value=self.grafo), \
                patch.object(lote.cc, 'localizar_par', return_value=((0, 0), (2, 0))), \
                patch.object(lote, 'pares_aleatorios') as sortear:
            resultado = lote.executar_teste_exaustivo(origem='A', destino='B')
        sortear.assert_not_called()
        self.assertEqual(resultado['total'], 100)
        self.assertEqual(len(resultado['resultados']), 100)
        self.assertAlmostEqual(resultado['medias']['Mais econômica']['economia_co2_pct'], 60)
        self.assertTrue(all(r['rotas'] == resultado['resultados'][0]['rotas'] for r in resultado['resultados']))

    def test_malha_desconectada_nao_reduz_denominador_silenciosamente(self):
        with redirect_stdout(StringIO()) as saida, \
                patch.object(lote.cc, 'carregar_malha', return_value=self.grafo), \
                patch.object(lote, 'pares_aleatorios', return_value=[((0, 0), (99, 99))] * 100), \
                self.assertRaisesRegex(ValueError, 'Teste 1/100'):
            lote.executar_teste_exaustivo()
        self.assertNotIn('MÉDIAS', saida.getvalue())

    def test_rejeita_par_incompleto_ou_de_mesmo_no(self):
        with self.assertRaisesRegex(ValueError, 'juntos'):
            lote.executar_teste_exaustivo(origem='A')
        with redirect_stdout(StringIO()), patch.object(lote.cc, 'carregar_malha', return_value=self.grafo), \
                patch.object(lote.cc, 'localizar_par', return_value=((0, 0), (0, 0))), \
                self.assertRaisesRegex(ValueError, 'diferentes'):
            lote.executar_teste_exaustivo(origem='A', destino='B')

    def test_sorteio_reproduzivel_na_maior_componente(self):
        from experimentos.avaliar_eficacia import pares_aleatorios
        grafo = {**self.grafo, (99, 99): []}
        with redirect_stdout(StringIO()), patch.object(lote.cc, 'carregar_malha', return_value=grafo):
            resultado = lote.executar_teste_exaustivo(semente=17)
        pares = [(r['origem'], r['destino']) for r in resultado['resultados']]
        self.assertEqual(pares, pares_aleatorios(set(self.grafo), 100, 17))
        self.assertTrue(all(o != d and (99, 99) not in (o, d) for o, d in pares))

    def test_ultima_operacao_da_interface_e_despacho_do_par_fixo(self):
        self.assertEqual(catalogo()[-1]['id'], 'exaustivo_rotas')
        op, p = validar('exaustivo_rotas', {'amostragem': 'Mesmo trajeto', 'origem': 'A', 'destino': 'B', 'boxplots': False})
        self.assertTrue(op['terminal'])
        with tempfile.TemporaryDirectory() as temp, patch.object(lote, 'executar_teste_exaustivo') as rodar:
            executar(op, p, Path(temp))
        rodar.assert_called_once_with('Carregado', 42, 'A', 'B')

    def test_menu_do_terminal_encaminha_cenario_e_semente(self):
        import main
        with redirect_stdout(StringIO()), patch('builtins.input', side_effect=['1', '1', '17']), \
                patch('main.exigir_grafo', return_value=True), \
                patch.object(lote, 'executar_teste_exaustivo') as rodar:
            main.main(['--opcao', '3.7'])
        rodar.assert_called_once_with('Vazio', 17, None, None)

    def test_cabecalho_omite_ruas_padrao_so_no_sorteio(self):
        for modo in ('Pares aleatórios', 'Mesmo trajeto'):
            with self.subTest(modo=modo), tempfile.TemporaryDirectory() as temp:
                caminho = Path(temp) / 'job.json'
                caminho.write_text(json.dumps({'operacao': 'exaustivo_rotas',
                                               'parametros': {'amostragem': modo}}), encoding='utf-8')
                with redirect_stdout(StringIO()) as saida, \
                        patch.object(worker.sys, 'argv', ['worker', str(caminho)]), \
                        patch.object(worker, 'executar'):
                    self.assertEqual(worker.main(), 0)
                parametros = json.loads(saida.getvalue().split('Parâmetros: ')[1].splitlines()[0])
                self.assertEqual('origem' in parametros, modo == 'Mesmo trajeto')
                self.assertEqual('destino' in parametros, modo == 'Mesmo trajeto')

    def test_csv_preserva_300_alternativas_pareadas_e_exporta_boxplots(self):
        pares = [((0, 0), (2, 0)), ((0, 0), (1, 0))] * 50
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(StringIO()), \
                patch.object(lote.cc, 'carregar_malha', return_value=self.grafo), \
                patch.object(lote, 'pares_aleatorios', return_value=pares):
            op, p = validar('exaustivo_rotas', {})
            executar(op, p, Path(temp))
            arquivos = {p.name for p in Path(temp).iterdir()}
            self.assertEqual(arquivos, {'rotas_100_testes.csv', 'boxplots_rotas.png', 'boxplots_rotas.svg'})
            with (Path(temp) / 'rotas_100_testes.csv').open(encoding='utf-8-sig', newline='') as arquivo:
                linhas = list(csv.DictReader(arquivo))
            self.assertEqual(len(linhas), 300)
            for numero in range(1, 101):
                grupo = [linha for linha in linhas if int(linha['teste']) == numero]
                self.assertEqual({r['rota'] for r in grupo}, set(lote.ALTERNATIVAS))
                self.assertEqual({float(r['destino_x']) for r in grupo}, {pares[numero - 1][1][0]})
            self.assertEqual(linhas[0]['origem_ruas'], 'Rua Inicial')
            self.assertEqual(linhas[0]['destino_ruas'], 'Rua Final / Rua da Esquina')
            self.assertEqual(float(linhas[0]['distancia_km']), .012)
            self.assertEqual(float(linhas[0]['economia_co2_pct']), 60)
            self.assertEqual(float(linhas[2]['distancia_adicional_pct']), 0)
            for nome in ('boxplots_rotas.png', 'boxplots_rotas.svg'):
                self.assertGreater((Path(temp) / nome).stat().st_size, 1000)
