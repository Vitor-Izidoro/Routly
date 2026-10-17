"""Contratos da interface: parâmetros, fila, falhas, cancelamento e acesso a arquivos."""
import json
import io
from contextlib import redirect_stdout
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from interface.catalogo import BASE, catalogo, validar
from interface.servidor import Execucoes, Handler, ThreadingHTTPServer, caminho_seguro
from interface.worker import executar


class CatalogoTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js opcional para as regressões de concorrência do frontend')
    def test_reabertura_e_troca_de_arquivos(self):
        resultado = subprocess.run([shutil.which('node'), '--test', str(BASE / 'tests/frontend/preview.test.cjs')],
                                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_todos_os_modulos_de_teste_estao_disponiveis(self):
        encontrados = {o['arquivo'] for o in catalogo() if 'arquivo' in o}
        self.assertEqual(encontrados, {p.name for p in (BASE / 'tests').glob('test_*.py')})

    def test_rejeita_operacao_parametro_e_valores_invalidos(self):
        casos = [('shell', {}), ('conversao', {'comando': 'dir'}),
                 ('monte_carlo', {'pares': 1}), ('monte_carlo', {'pares': 2.5}),
                 ('monte_carlo', {'pares': float('nan')}), ('pareto', {'boa': 'false'}),
                 ('alt_emissao', {'modelo': 'inexistente'}), ('perfil', {'origem': ''}),
                 ('eficacia', {'velocidades': '0, 30'}), ('eficacia', {'cargas': []})]
        for id, p in casos:
            with self.subTest(id=id, p=p), self.assertRaises(ValueError):
                validar(id, p)

    def test_listas_e_opcoes_do_terminal(self):
        _, p = validar('eficacia', {'cargas': '0, 10000', 'ruido': '', 'cmem': False})
        self.assertEqual(p['cargas'], [0, 10000])
        self.assertEqual(p['ruido'], [])
        self.assertFalse(p['cmem'])

    def test_impede_travessia_de_diretorio(self):
        with tempfile.TemporaryDirectory() as temp:
            raiz = Path(temp) / 'artefatos'; raiz.mkdir()
            (Path(temp) / 'segredo.txt').write_text('privado')
            (raiz / 'ok.txt').write_text('resultado')
            self.assertEqual(caminho_seguro(raiz, 'ok.txt').read_text(), 'resultado')
            for caminho in ('../segredo.txt', str(Path(temp) / 'segredo.txt')):
                with self.assertRaises(FileNotFoundError):
                    caminho_seguro(raiz, caminho)

    def test_worker_propaga_falha_de_pytest(self):
        op, p = validar('testes_todos', {})
        with tempfile.TemporaryDirectory() as temp, patch('pytest.main', return_value=1), self.assertRaises(SystemExit) as erro:
            executar(op, p, Path(temp))
        self.assertEqual(erro.exception.code, 1)

    def test_comparacao_rotas_executa_script_e_exibe_resultados(self):
        import pandas as pd
        op, p = validar('comparacao_rotas', {})
        self.assertEqual(op['grupo'], 'ciencia')
        df = pd.DataFrame([
            (0, 0, 2, 0, 10, 20, 'Subida', 8),
            (0, 0, 1, 0, 6, 4, 'Desvio A', 1),
            (1, 0, 2, 0, 6, 4, 'Desvio B', 1),
            (2, 0, 0, 0, 10, 10, 'Volta', -8),
        ], columns=['origem_x', 'origem_y', 'destino_x', 'destino_y',
                    'distancia_m', 'custo_carbono', 'nome_rua', 'delta_z'])
        saida = io.StringIO()
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(saida), \
                patch('pathlib.Path.is_file', return_value=True), \
                patch('pandas.read_csv', return_value=df), \
                patch('random.choice', side_effect=[(0, 0), (2, 0)]):
            executar(op, p, Path(temp))
        self.assertIn('Rota Mais Curta', saida.getvalue())
        self.assertIn('Rota Mais Ecológica', saida.getvalue())
        self.assertIn('economia de 12.00 g de CO2', saida.getvalue())
        self.assertIn('2.00 metros mais longo', saida.getvalue())

    def test_worker_reutiliza_rota_e_exporta_figura(self):
        import matplotlib.pyplot as plt
        op, p = validar('alt_emissao', {'modelo': 'cmem', 'caminhao': 'hdv-generico'})
        def rota_simulada(modulo, args):
            self.assertEqual(modulo, 'executar')
            self.assertIn('hdv-generico', args)
            self.assertNotIn('--cenario-co2', args)
            plt.figure(); plt.plot([0, 1], [0, 1]); plt.show()
        with tempfile.TemporaryDirectory() as temp, patch('interface.worker.rodar_modulo', side_effect=rota_simulada), patch('pathlib.Path.is_file', return_value=True):
            executar(op, p, Path(temp))
            self.assertTrue((Path(temp) / 'figura_01.png').exists())

    def test_mapa_preserva_segmentos_em_uma_colecao(self):
        import matplotlib.pyplot as plt
        import pandas as pd
        from estrela import plotar_rota_no_mapa
        df = pd.DataFrame({'origem_x':[0, 1], 'origem_y':[0, 2],
                           'destino_x':[1, 3], 'destino_y':[2, 4]})
        with patch.object(plt, 'show'):
            plotar_rota_no_mapa(df, [(0, 0), (1, 2), (3, 4)], 'distancia')
        try:
            eixo = plt.gca()
            self.assertEqual(len(eixo.collections[0].get_segments()), 2)
            self.assertEqual(len(eixo.lines), 1)  # Apenas a rota é uma Line2D.
            self.assertEqual(list(eixo.lines[0].get_xdata()), [0, 1, 3])
        finally:
            plt.close('all')


class FilaTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manager = Execucoes(Path(self.temp.name))

    def tearDown(self):
        self.manager.fechar()
        self.manager.thread.join(timeout=10)
        self.temp.cleanup()

    def esperar(self, id, estados, timeout=10):
        prazo = time.monotonic() + timeout
        while time.monotonic() < prazo:
            job = self.manager.detalhe(id)
            if job['status'] in estados:
                return job
            time.sleep(.03)
        self.fail(f'Execução não chegou ao estado {estados}')

    def test_fila_logs_falhas_e_persistencia(self):
        original = subprocess.Popen
        chamadas = []
        def processo(cmd, **kwargs):
            chamadas.append(cmd)
            codigo = 0 if len(chamadas) == 1 else 2
            return original([sys.executable, '-c', f"print('saída de teste'); raise SystemExit({codigo})"], **kwargs)
        with patch('interface.servidor.subprocess.Popen', side_effect=processo):
            primeiro, segundo = self.manager.criar([{'operacao':'conversao'}, {'operacao':'fisica'}])
            a = self.esperar(primeiro['id'], ['concluido'])
            b = self.esperar(segundo['id'], ['falhou'])
        self.assertIn('saída de teste', a['log'])
        self.assertEqual(b['codigo'], 2)
        self.assertGreaterEqual(b['inicio'], a['fim'])
        self.assertIn('interface.worker', chamadas[0])
        salvo = json.loads((Path(self.temp.name) / segundo['id'] / 'job.json').read_text(encoding='utf-8'))
        self.assertEqual(salvo['status'], 'falhou')

    def test_cancelamento_de_processo_e_de_item_na_fila(self):
        original = subprocess.Popen
        def processo(cmd, **kwargs):
            return original([sys.executable, '-u', '-c', "import time; print('iniciado'); time.sleep(30)"], **kwargs)
        with patch('interface.servidor.subprocess.Popen', side_effect=processo):
            # A restauração do Popen precede taskkill, que também usa subprocess internamente.
            primeiro, segundo = self.manager.criar([{'operacao':'conversao'}, {'operacao':'fisica'}])
            self.esperar(primeiro['id'], ['executando'])
        self.manager.cancelar(segundo['id'])
        self.manager.cancelar(primeiro['id'])
        self.assertEqual(self.manager.detalhe(segundo['id'])['status'], 'cancelado')
        self.assertEqual(self.manager.detalhe(primeiro['id'])['status'], 'cancelado')

    def test_validacao_do_lote_e_atomica(self):
        with self.assertRaises(ValueError):
            self.manager.criar([{'operacao':'conversao'}, {'operacao':'shell'}])
        self.assertEqual(self.manager.listar(), [])


class HttpTest(unittest.TestCase):
    def test_api_arquivos_e_protecao_de_origem(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = Execucoes(Path(temp))
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            server.execucoes = manager
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            url = f'http://127.0.0.1:{server.server_port}'
            try:
                with urlopen(url + '/api/catalogo') as resposta:
                    self.assertEqual(len(json.load(resposta)['grupos']), 5)
                for path in ('/../.git/config', '/biblioteca/../requirements.txt', '/api/execucoes/inexistente'):
                    with self.assertRaises(HTTPError) as erro:
                        urlopen(url + path)
                    self.assertEqual(erro.exception.code, 404)
                request = Request(url + '/api/execucoes', data=b'{"execucoes":[]}', headers={'Content-Type':'application/json', 'Origin':'http://outro-site.test'})
                with self.assertRaises(HTTPError) as erro:
                    urlopen(request)
                self.assertEqual(erro.exception.code, 403)
            finally:
                server.shutdown(); server.server_close(); thread.join(); manager.fechar(); manager.thread.join(5)
