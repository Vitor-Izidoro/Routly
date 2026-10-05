import random
import unittest
from algoritmos import IndiceALT, boa_estrela


def enumerar(grafo, inicio, destino):
    custos = set()
    def visitar(u, vistos, d, e):
        if u == destino:
            custos.add((d, e))
            return
        for v, cd, ce in grafo[u]:
            if v not in vistos:
                visitar(v, vistos | {v}, d + cd, e + ce)
    visitar(inicio, {inicio}, 0, 0)
    return {c for c in custos if not any(x != c and x[0] <= c[0] and x[1] <= c[1] for x in custos)}


class AlgoritmosTest(unittest.TestCase):
    def test_grafos_dirigidos_contra_enumeracao_exaustiva(self):
        rng = random.Random(42)
        for _ in range(60):
            grafo = {u: [] for u in range(6)}
            for u in grafo:
                for v in grafo:
                    if u != v and rng.random() < .3:
                        grafo[u].append((v, rng.randrange(8), rng.randrange(8)))
            esperado = enumerar(grafo, 0, 5)
            with self.subTest(grafo=grafo):
                self.assertEqual({(r.distancia, r.emissao) for r in boa_estrela(grafo, 0, 5)}, esperado)
                for modo, i in [('distancia', 0), ('emissao', 1)]:
                    indice = IndiceALT(grafo, modo, 3)
                    rota = indice.buscar(0, 5)
                    if esperado:
                        self.assertEqual((rota.distancia, rota.emissao)[i], min(c[i] for c in esperado))
                        self.assertEqual(rota.nos[0], 0)
                        self.assertEqual(rota.nos[-1], 5)
                    else:
                        self.assertIsNone(rota)

    def test_empates_ciclos_e_arestas_paralelas(self):
        grafo = {0: [(1, 1, 5), (1, 3, 2), (1, 1, 5), (2, 9, 9)],
                 1: [(0, 0, 0), (2, 1, 1)], 2: [], 3: []}
        self.assertEqual({(r.distancia, r.emissao) for r in boa_estrela(grafo, 0, 2)}, {(2, 6), (4, 3)})
        self.assertEqual(boa_estrela(grafo, 0, 0)[0].nos, [0])
        self.assertEqual(IndiceALT(grafo).buscar(0, 0).emissao, 0)
        self.assertEqual(boa_estrela(grafo, 0, 3), [])
        self.assertIsNone(IndiceALT(grafo).buscar(0, 99))

    def test_custos_invalidos(self):
        for peso in (-1, float('nan'), float('inf')):
            grafo = {0: [(1, peso, 1)], 1: []}
            with self.assertRaises(ValueError):
                IndiceALT(grafo)
            with self.assertRaises(ValueError):
                boa_estrela(grafo, 0, 1)


if __name__ == '__main__':
    unittest.main()
