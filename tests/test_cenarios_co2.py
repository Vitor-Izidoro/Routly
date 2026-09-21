from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import executar
from algoritmos import IndiceALT, boa_estrela
from cenarios_co2 import selecionar_cenario_co2
from estrela import carregar_grafos_direcionais
from vtcpfm import configurar_vtcpfm, consumo_trecho_vtcpfm


class CenariosCO2Test(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.base = Path(self.pasta.name)
        self.arquivo = self.base / 'grafo_curitiba_carbono.csv'
        self.arquivo.write_text(
            'origem_x,origem_y,origem_z,destino_x,destino_y,destino_z,distancia_m,delta_z,nome_rua\n'
            '0,0,900,1,0,950,1000,50,ORIGEM\n'
            '1,0,950,2,0,900,1000,-50,MEIO\n'
            '0,0,900,2,0,900,2400,0,ALTERNATIVA\n'
            '2,0,900,3,0,900,100,0,DESTINO\n')

    def test_conversao_preserva_consumo_e_potencia(self):
        for dz in (-50, 0, 50):
            artigo = consumo_trecho_vtcpfm(1000, dz, configurar_vtcpfm('artigo'), altitude_m=900)
            epa = consumo_trecho_vtcpfm(1000, dz, configurar_vtcpfm('epa'), altitude_m=900)
            self.assertEqual(artigo.combustivel_l, epa.combustivel_l)
            self.assertEqual(artigo.potencia_kw, epa.potencia_kw)
            self.assertAlmostEqual(artigo.co2_g, artigo.combustivel_l * 2070)
            self.assertAlmostEqual(epa.co2_g, epa.combustivel_l * (10210 / 3.785411784))

    def test_conversao_preserva_buscas_e_pareto(self):
        grafos = [carregar_grafos_direcionais(self.arquivo, caminhao=configurar_vtcpfm(c))[0]
                  for c in ('epa', 'artigo')]
        for modo in ('distancia', 'emissao'):
            rotas = [IndiceALT(g, modo).buscar((0, 0), (2, 0)) for g in grafos]
            self.assertEqual(rotas[0].nos, rotas[1].nos)
        fronteiras = [boa_estrela(g, (0, 0), (2, 0)) for g in grafos]
        self.assertEqual(len(fronteiras[0]), 2)
        self.assertEqual([r.nos for r in fronteiras[0]], [r.nos for r in fronteiras[1]])
        for epa, artigo in zip(*fronteiras):
            self.assertEqual(epa.distancia, artigo.distancia)
            self.assertAlmostEqual(artigo.emissao / epa.emissao, 2070 / (10210 / 3.785411784))

    def executar_cli(self, args, respostas=()):
        saida = StringIO()
        with patch.object(executar, 'BASE', self.base), patch('sys.argv', ['estrela.py',
                '--origem', 'ORIGEM', '--destino', 'DESTINO', '--sem-mapa', *args]), \
                patch('builtins.input', side_effect=respostas), redirect_stdout(saida), redirect_stderr(saida):
            executar.main()
        return saida.getvalue()

    def test_cli_padrao_cenarios_e_menu(self):
        self.assertIn('CO₂: epa (2697.20 g/L)', self.executar_cli(['--algoritmo', 'alt']))
        self.assertIn('CO₂: artigo (2070.00 g/L)', self.executar_cli(
            ['--algoritmo', 'alt', '--cenario-co2', 'artigo']))
        # ALT emissão, ruas padrão, cenário artigo, massa e velocidade padrão.
        saida = self.executar_cli([], ['2', '', '', '2', '', ''])
        self.assertIn('CO₂: artigo (2070.00 g/L)', saida)
        self.assertIn('não reproduz suas medições', saida)

    def test_cenarios_incompativeis(self):
        for nome, modelo in [('artigo', 'cmem'), ('epa', 'legado'), ('invalido', 'vtcpfm')]:
            with self.assertRaises(ValueError):
                selecionar_cenario_co2(nome, modelo=modelo)
        for modelo, cenario in [('cmem', 'artigo'), ('legado', 'epa')]:
            with self.assertRaises(SystemExit) as erro:
                self.executar_cli(['--algoritmo', 'alt', '--modelo-emissao', modelo,
                                  '--cenario-co2', cenario])
            self.assertEqual(erro.exception.code, 2)
