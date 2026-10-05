import math
from pathlib import Path
import tempfile
import unittest

from algoritmos import IndiceALT, boa_estrela, distancias_dijkstra
from estrela import carregar_grafos_direcionais
from vtcpfm import (CaminhaoVTCPFM, consumo_trecho_vtcpfm,
                    potencia_instantanea, vazao_combustivel)


class VTCPFMTest(unittest.TestCase):
    def test_potencia_e_consumo_por_calculo_independente(self):
        # 36 km/h, rampa 2%, altitude 1000 m, massa total 17182 kg.
        # Aerodinâmica calculada em m/s (10), independente da forma /25.92.
        resistencia = (.5 * 1.2256 * .78 * .915 * 10 * 10**2
                       + 9.8066 * 17182 * .00125 * (.0328 * 36 + 4.575)
                       + 9.8066 * 17182 * .02)
        potencia = resistencia * 10 / (.94 * 1000)
        litros = (.00156 + .000081 * potencia + .00000001 * potencia**2) * math.hypot(1000, 20) / 10
        r = consumo_trecho_vtcpfm(1000, 20, altitude_m=1000, carga_kg=10000, velocidade_kmh=36)
        self.assertAlmostEqual(r.potencia_kw, potencia)
        self.assertAlmostEqual(r.combustivel_l, litros)
        self.assertAlmostEqual(r.co2_g, litros * 10210 / 3.785411784)

    def test_regimes_aceleracao_e_altitude(self):
        self.assertEqual(vazao_combustivel(-100), .00156)
        self.assertEqual(vazao_combustivel(0), .00156)
        self.assertAlmostEqual(vazao_combustivel(100), .00976)
        self.assertEqual(potencia_instantanea(0, 0, 0), 0)
        base = potencia_instantanea(36, 0, 0)
        self.assertAlmostEqual(potencia_instantanea(36, 0, 0, aceleracao_m_s2=1) - base,
                               1.1 * 7182 * 10 / 940)
        self.assertLess(potencia_instantanea(36, 0, 1000), base)

    def test_relevo_massa_e_potencia_excedida(self):
        descida, plano, subida = [consumo_trecho_vtcpfm(1000, dz, altitude_m=900)
                                  for dz in (-50, 0, 50)]
        self.assertLess(descida.combustivel_l, plano.combustivel_l)
        self.assertLess(plano.combustivel_l, subida.combustivel_l)
        self.assertAlmostEqual(descida.combustivel_l, .00156 * math.hypot(1000, 50) / (30/3.6))
        carregado = consumo_trecho_vtcpfm(1000, 200, altitude_m=900, carga_kg=20000)
        self.assertTrue(carregado.potencia_excedida)
        self.assertGreater(carregado.potencia_kw, CaminhaoVTCPFM().potencia_nominal_kw)
        self.assertGreater(carregado.co2_g, subida.co2_g)
        self.assertEqual(consumo_trecho_vtcpfm(0, 0, altitude_m=0).co2_g, 0)

    def test_entradas_invalidas(self):
        for d, z, h in [(-1, 0, 0), (0, 1, 0), (100, math.nan, 0),
                         (100, 0, math.nan), (100, 0, 12000)]:
            with self.assertRaises(ValueError):
                consumo_trecho_vtcpfm(d, z, altitude_m=h)
        for kwargs in [{'carga_kg': -1}, {'velocidade_kmh': 0}]:
            with self.assertRaises(ValueError):
                consumo_trecho_vtcpfm(100, 0, altitude_m=0, **kwargs)
        for kwargs in [{'alpha2_l_s_kw2': -1e-8}, {'eficiencia_transmissao': 2}]:
            with self.assertRaises(ValueError):
                CaminhaoVTCPFM(**kwargs)

    def test_grafo_direcional_e_buscas(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / 'grafo.csv'
            arquivo.write_text('origem_x,origem_y,origem_z,destino_x,destino_y,destino_z,distancia_m,delta_z\n'
                               '0,0,900,1,0,950,1000,50\n'
                               '1,0,950,2,0,900,1000,-50\n'
                               '0,0,900,2,0,900,2400,0\n')
            grafo, reverso = carregar_grafos_direcionais(arquivo)
            custo = consumo_trecho_vtcpfm(1000, 50, altitude_m=925).co2_g
            self.assertAlmostEqual(grafo[(0, 0)][0][2], custo)
            self.assertEqual(grafo[(0, 0)][0][1:], reverso[(1, 0)][0][1:])
            self.assertGreater(custo, grafo[(1, 0)][0][2])
            for modo, indice in [('distancia', 1), ('emissao', 2)]:
                rota = IndiceALT(grafo, modo).buscar((0, 0), (2, 0))
                esperado = distancias_dijkstra(grafo, (0, 0), indice)[(2, 0)]
                self.assertAlmostEqual(getattr(rota, modo), esperado)
            self.assertEqual(len(boa_estrela(grafo, (0, 0), (2, 0))), 2)
            arquivo.write_text('origem_x,origem_y,destino_x,destino_y,distancia_m,delta_z\n'
                               '0,0,1,0,100,0\n')
            with self.assertRaisesRegex(ValueError, 'origem_z'):
                carregar_grafos_direcionais(arquivo)
