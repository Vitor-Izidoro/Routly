"""Eficácia na malha real: rota ecológica × rota mais curta (pares fixos, semente 42).

Exige grafo_curitiba_carbono.csv na raiz; sem ele os testes de malha são pulados.
Limites mínimos ficam abaixo do observado (≈3% vazio, ≈10% com 20 t) para
detectar regressões sem falhar por variação de amostra.
"""
import statistics as st
import unittest

from algoritmos import distancias_dijkstra
from experimentos.avaliar_eficacia import (CSV_GRAFO, carregar_malha, comparar_rotas,
                                           maior_componente, pares_aleatorios,
                                           tabela_emissao, wilcoxon_pareado)

PARES = 20
CARGA_PESADA_KG = 20000.0


class EstatisticaTest(unittest.TestCase):
    def test_wilcoxon_simetrico_e_deslocado(self):
        _, p = wilcoxon_pareado([1, -1, 2, -2, 3, -3])
        self.assertGreater(p, 0.9)
        z, p = wilcoxon_pareado(list(range(1, 21)))
        self.assertGreater(z, 0)
        self.assertLess(p, 0.001)
        self.assertEqual(wilcoxon_pareado([0, 0]), (0.0, 1.0))


@unittest.skipUnless(CSV_GRAFO.exists(), 'grafo_curitiba_carbono.csv ausente')
class EficaciaMalhaRealTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vazio = carregar_malha('vtcpfm', 0.0)
        cls.pesado = carregar_malha('vtcpfm', CARGA_PESADA_KG)
        cls.pares = pares_aleatorios(maior_componente(cls.vazio), PARES)
        cls.res_vazio = comparar_rotas(cls.vazio, cls.pares)
        cls.res_pesado = comparar_rotas(cls.pesado, cls.pares)

    def test_todos_os_pares_tem_rota(self):
        self.assertEqual(len(self.res_vazio), PARES)
        self.assertEqual(len(self.res_pesado), PARES)

    def test_rota_ecologica_nunca_emite_mais_nem_e_mais_curta(self):
        for rotulo, resultados in (('vazio', self.res_vazio), ('20 t', self.res_pesado)):
            for r in resultados:
                with self.subTest(carga=rotulo, origem=r['origem'], destino=r['destino']):
                    self.assertLessEqual(r['co2_eco_g'], r['co2_curta_g'] * (1 + 1e-9))
                    self.assertGreaterEqual(r['distancia_eco_m'], r['distancia_curta_m'] - 1e-6)

    def test_economia_media_minima(self):
        self.assertGreater(st.mean(r['economia_pct'] for r in self.res_vazio), 1.5)
        self.assertGreater(st.mean(r['economia_pct'] for r in self.res_pesado), 5.0)

    def test_economia_cresce_com_a_carga(self):
        self.assertGreater(st.mean(r['economia_pct'] for r in self.res_pesado),
                           st.mean(r['economia_pct'] for r in self.res_vazio))

    def test_economia_estatisticamente_significativa(self):
        _, p = wilcoxon_pareado([r['co2_curta_g'] - r['co2_eco_g'] for r in self.res_pesado])
        self.assertLess(p, 0.01)

    def test_alt_emissao_igual_ao_dijkstra_na_malha_real(self):
        for r in self.res_pesado[:3]:
            with self.subTest(origem=r['origem']):
                otimo = distancias_dijkstra(self.pesado, r['origem'], 2)[r['destino']]
                self.assertAlmostEqual(r['co2_eco_g'], otimo, delta=1e-6 * otimo)

    def test_economia_confirmada_por_modelo_independente(self):
        # Rota escolhida pelo VT-CPFM e medida com CMEM: a economia não pode sumir.
        cmem = tabela_emissao(carregar_malha('cmem', CARGA_PESADA_KG))
        resultados = comparar_rotas(self.pesado, self.pares, medir_em=cmem)
        self.assertGreater(st.mean(r['economia_pct'] for r in resultados), 3.0)


if __name__ == '__main__':
    unittest.main()
