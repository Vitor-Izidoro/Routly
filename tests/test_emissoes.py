import math
from pathlib import Path
import tempfile
import unittest
from emissoes import CaminhaoCMEM, consumo_trecho
from estrela import carregar_grafos_direcionais
from algoritmos import IndiceALT, boa_estrela


class EmissoesTest(unittest.TestCase):
    def test_referencia_plana_por_equacao_independente(self):
        # 1 km horizontal a 36 km/h: tempo=100s, v=10m/s, massa=13000kg.
        energia_kj = 100 * (0.17 * 33 * 11 +
                           (13000 * 9.81 * 0.008 + 0.5 * 1.2041 * 0.7 * 8.2 * 100)
                           * 10 / (1000 * 0.4 * 0.9))
        litros = energia_kj / (45 * 737)
        r = consumo_trecho(1000, 0, velocidade_kmh=36)
        self.assertAlmostEqual(r.combustivel_l, litros)
        self.assertAlmostEqual(r.co2_g, litros * 10210 / 3.785411784)

    def test_relevo_carga_e_descida_sem_credito(self):
        descida, plano, subida = [consumo_trecho(1000, z).co2_g for z in (-50, 0, 50)]
        self.assertLess(descida, plano)
        self.assertLess(plano, subida)
        self.assertGreater(consumo_trecho(1000, 50, carga_kg=10000).co2_g, subida)
        p = CaminhaoCMEM()
        r = consumo_trecho(1000, -100, velocidade_kmh=36)
        piso_l = math.hypot(1000,100)/10 * (.17*33*11)/(45*737)
        self.assertAlmostEqual(r.combustivel_l, piso_l)
        self.assertGreater(r.co2_g, 0)
        self.assertEqual(consumo_trecho(0,0).co2_g, 0)

    def test_segmentacao_preserva_custo_em_rampa_uniforme(self):
        for dz in (-80, 0, 80):
            inteiro = consumo_trecho(1000, dz, carga_kg=5000).co2_g
            partes = 10 * consumo_trecho(100, dz/10, carga_kg=5000).co2_g
            self.assertAlmostEqual(inteiro, partes)

    def test_entradas_invalidas(self):
        for args in [(-1,0), (0,1), (100,float('nan')), (float('inf'),1)]:
            with self.assertRaises(ValueError):
                consumo_trecho(*args)
        for kwargs in [{'carga_kg':-1}, {'velocidade_kmh':0}, {'velocidade_kmh':float('inf')}]:
            with self.assertRaises(ValueError):
                consumo_trecho(100,0,**kwargs)
        with self.assertRaises(ValueError):
            CaminhaoCMEM(eficiencia_motor=2)

    def test_grafo_reverso_e_comparacao_legada(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta)/'grafo.csv'
            arquivo.write_text('origem_x,origem_y,destino_x,destino_y,distancia_m,delta_z\n0,0,100,0,100,5\n')
            g, r = carregar_grafos_direcionais(arquivo)
            self.assertGreater(g[(0,0)][0][2], g[(100,0)][0][2])
            self.assertEqual(g[(0,0)][0][1:], r[(100,0)][0][1:])
            antigo,_ = carregar_grafos_direcionais(arquivo,200,modelo='legado')
            self.assertAlmostEqual(antigo[(0,0)][0][2],21.5)

    def test_cmem_pode_preferir_caminho_mais_longo(self):
        # A rota curta sobe 50m e desce; a alternativa plana tem 2.4km.
        g = {0: [(1,1000,consumo_trecho(1000,50).co2_g),
                 (2,1200,consumo_trecho(1200,0).co2_g)],
             1: [(3,1000,consumo_trecho(1000,-50).co2_g)],
             2: [(3,1200,consumo_trecho(1200,0).co2_g)], 3: []}
        self.assertEqual(IndiceALT(g,'distancia').buscar(0,3).nos,[0,1,3])
        self.assertEqual(IndiceALT(g,'emissao').buscar(0,3).nos,[0,2,3])
        self.assertEqual(len(boa_estrela(g,0,3)),2)
