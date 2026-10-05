"""Menu principal, ETL e comprovação científica: importações, corretude e geração de figuras."""
from contextlib import redirect_stdout
import importlib
from io import StringIO
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from algoritmos import distancias_dijkstra
from experimentos import comprovacao_cientifica as cc
from experimentos.avaliar_eficacia import wilcoxon_pareado


def grade_aleatoria(lado=6, semente=1):
    """Malha (x, y) em metros com arestas nos dois sentidos e custos de emissão variados."""
    rng = random.Random(semente)
    grafo = {(x * 100.0, y * 100.0): [] for x in range(lado) for y in range(lado)}
    for (x, y) in list(grafo):
        for dx, dy in ((100.0, 0.0), (0.0, 100.0)):
            v = (x + dx, y + dy)
            if v in grafo:
                d = 100.0 * rng.uniform(1.0, 1.4)  # comprimento ≥ corda, como no IPPUC
                grafo[(x, y)].append((v, d, d * rng.uniform(0.5, 3.0)))
                grafo[v].append(((x, y), d, d * rng.uniform(0.5, 3.0)))
    return grafo


class ImportacoesTest(unittest.TestCase):
    def test_modulos_do_menu_importam(self):
        for nome in ('main', 'etl_ippuc', 'mapa', 'executar', 'experimentos.comprovacao_cientifica',
                     'experimentos.avaliar_eficacia', 'experimentos.validar_conversao_co2'):
            with self.subTest(modulo=nome):
                importlib.import_module(nome)

    def test_opcoes_do_menu_existem(self):
        import main
        self.assertEqual(set(main.OPCOES), {'1.1', '1.2', '1.3', '2', '3.1', '3.2', '3.3', '3.4', '3.5', '3.6'})
        self.assertTrue(all(callable(funcao) for _, funcao in main.OPCOES.values()))


class MenuTest(unittest.TestCase):
    def rodar(self, respostas, argv=()):
        import main
        saida = StringIO()
        with patch('builtins.input', side_effect=respostas), redirect_stdout(saida):
            main.main(list(argv))
        return saida.getvalue()

    def test_sair_e_opcao_invalida(self):
        saida = self.rodar(['9', '1', '0'])
        self.assertIn('Grafo base', saida)
        self.assertIn('Opção inválida', saida)
        self.assertIn('Até logo', saida)

    def test_voltar_em_pergunta_nao_encerra_o_menu(self):
        saida = self.rodar(['3.3', 'v', '0'] if Path(cc.CSV_GRAFO).exists() else ['0'])
        self.assertIn('Até logo', saida)

    def test_fim_da_entrada_encerra(self):
        self.assertIn('Encerrado', self.rodar(EOFError))  # Ctrl+Z/Ctrl+D no terminal

    def test_perguntar_valida_opcoes(self):
        import main
        with patch('builtins.input', side_effect=['x', '2']), redirect_stdout(StringIO()):
            self.assertEqual(main.perguntar('?', '1', ['1', '2']), '2')
        with patch('builtins.input', side_effect=['v']), self.assertRaises(main.Voltar):
            main.perguntar('?')


class ETLTest(unittest.TestCase):
    def test_shapefiles_ausentes_nao_propagam_erro(self):
        from etl_ippuc import executar_etl
        with tempfile.TemporaryDirectory() as pasta, redirect_stdout(StringIO()) as saida:
            ok = executar_etl(Path(pasta) / 'a.shp', Path(pasta) / 'b.shp', Path(pasta) / 'g.csv')
        self.assertFalse(ok)
        self.assertIn('não encontrados', saida.getvalue())


class BuscaPonderadaTest(unittest.TestCase):
    def test_extremos_iguais_ao_dijkstra(self):
        grafo = grade_aleatoria()
        o, d = (0.0, 0.0), (500.0, 500.0)
        limites = cc.limites_heuristica(grafo)
        for alpha, indice in ((0.0, 1), (1.0, 2)):
            rota = cc.busca_ponderada(grafo, o, d, alpha, limites=limites)
            otimo = distancias_dijkstra(grafo, o, indice)[d]
            self.assertAlmostEqual(rota.distancia if indice == 1 else rota.emissao, otimo)
            self.assertEqual((rota.nos[0], rota.nos[-1]), (o, d))
            self.assertAlmostEqual(rota.distancia, sum(t[0] for t in rota.trechos))

    def test_heuristica_nao_altera_o_otimo(self):
        for semente in range(5):
            grafo = grade_aleatoria(semente=semente)
            limites = cc.limites_heuristica(grafo)
            for alpha in (0.1, 0.5, 0.9):
                com = cc.busca_ponderada(grafo, (0.0, 0.0), (500.0, 300.0), alpha, 300, 900, limites)
                sem = cc.busca_ponderada(grafo, (0.0, 0.0), (500.0, 300.0), alpha, 300, 900, None)
                custo = lambda r: (1 - alpha) * r.distancia / 300 + alpha * r.emissao / 900
                self.assertAlmostEqual(custo(com), custo(sem))

    def test_entradas_invalidas_e_sem_caminho(self):
        grafo = {(0.0, 0.0): [], (1.0, 0.0): []}
        self.assertIsNone(cc.busca_ponderada(grafo, (0.0, 0.0), (1.0, 0.0), 0.5))
        with self.assertRaises(ValueError):
            cc.busca_ponderada(grafo, (0.0, 0.0), (1.0, 0.0), 1.5)

    def test_fronteira_e_joelho(self):
        r = cc.analisar_fronteira(grade_aleatoria(), (0.0, 0.0), (500.0, 500.0), passos=11)
        self.assertEqual(len(r.solucoes), 11)
        base, eco = r.solucoes[0]['trajeto'], r.solucoes[-1]['trajeto']
        self.assertLessEqual(base.distancia, eco.distancia)
        self.assertGreaterEqual(base.emissao, eco.emissao)
        joelho = r.solucoes[r.joelho]
        self.assertEqual(joelho['dist_utopia'], min(s['dist_utopia'] for s in r.solucoes))
        exatos = {(round(a, 6), round(b, 6)) for a, b in r.fronteira_exata}
        for s in r.solucoes:  # soluções suportadas pertencem à fronteira exata do BOA*
            self.assertIn((round(s['trajeto'].distancia, 6), round(s['trajeto'].emissao, 6)), exatos)


class EstatisticaEFigurasTest(unittest.TestCase):
    def test_wilcoxon_scipy_consistente_com_implementacao_propria(self):
        rng = random.Random(3)
        j2 = [rng.uniform(100, 200) for _ in range(60)]
        j1 = [x + rng.gauss(5, 10) for x in j2]
        s = cc._wilcoxon_scipy(j1, j2)
        _, p = wilcoxon_pareado([a - b for a, b in zip(j1, j2)])
        self.assertAlmostEqual(s['p_bicaudal'], p, delta=0.02)
        self.assertEqual(cc._wilcoxon_scipy([1, 2], [1, 2])['p_bicaudal'], 1.0)

    def test_utm_curitiba(self):
        from mapa import utm_para_latlon
        lat, lon = utm_para_latlon(673000, 7181000)
        self.assertAlmostEqual(lat, -25.478, places=2)
        self.assertAlmostEqual(lon, -49.279, places=2)

    def test_figuras_e_relatorios_em_grafo_sintetico(self):
        grafo = grade_aleatoria()
        altitudes = {no: 900 + no[0] / 50 for no in grafo}
        r = cc.analisar_fronteira(grafo, (0.0, 0.0), (500.0, 500.0), passos=11)
        linhas = [{'origem': (0, 0), 'destino': (1, 1), 'distancia_curta_m': 1000, 'distancia_eco_m': 1100,
                   'co2_curta_g': 100 + i, 'co2_eco_g': 95, 'economia_pct': (5 + i) / (100 + i) * 100,
                   'distancia_extra_pct': 10.0} for i in range(12)]
        mc = {n: {'carga_kg': c, 'linhas': linhas, 'cmem': linhas, 'avisos': []}
              for n, c in cc.CENARIOS_CARGA.items()}
        with tempfile.TemporaryDirectory() as pasta, redirect_stdout(StringIO()):
            pasta = Path(pasta)
            cc.plotar_pareto(r, pasta / 'p.png')
            cc.exportar_tradeoff(r, pasta / 't.csv')
            cc.plotar_perfil(r.solucoes[0]['trajeto'], r.solucoes[-1]['trajeto'], altitudes, pasta / 'a.png')
            cc.plotar_boxplot(mc, pasta / 'b.png')
            cc.exportar_monte_carlo(mc, pasta, 42, 12)
            dados = cc.validacao_fisica(pasta)
            for nome in ('p.png', 't.csv', 'a.png', 'b.png', 'validacao_fisica_grade.png',
                         'paridade_fisica_grade.json', 'relatorio_estatistico.md', 'monte_carlo_resultados.csv'):
                self.assertGreater((pasta / nome).stat().st_size, 0, nome)
        self.assertGreater(dados['metricas_globais']['r2'], 0.9)


@unittest.skipUnless(cc.CSV_GRAFO.exists() and cc.REGISTRO_CMEM.exists(),
                     'grafo ou docs/validacao_cmem.json ausente')
class RegistroCMEMTest(unittest.TestCase):
    def test_registro_historico_reproduzido(self):
        with tempfile.TemporaryDirectory() as pasta, redirect_stdout(StringIO()):
            resultado = cc.reproduzir_registro_cmem(Path(pasta))
        falhas = [v['verificacao'] for v in resultado['verificacoes'] if not v['passou']]
        self.assertEqual(falhas, [])


if __name__ == '__main__':
    unittest.main()
