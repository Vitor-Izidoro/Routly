"""ALT dirigido e BOA* (Hernández et al., algoritmo 3).

Grafos: {no: [(vizinho, distancia_m, emissao_g), ...]}.
Custos finitos e não negativos; grafo reverso preserva o custo original.
"""
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import inf, isfinite


@dataclass
class Rota:
    nos: list
    distancia: float
    emissao: float


def validar_grafo(grafo):
    for arestas in grafo.values():
        for v, d, e in arestas:
            if v not in grafo or not all(isfinite(c) and c >= 0 for c in (d, e)):
                raise ValueError('O grafo exige nós existentes e custos finitos não negativos.')


def inverter_grafo(grafo):
    reverso = {u: [] for u in grafo}
    for u, arestas in grafo.items():
        for v, d, e in arestas:
            reverso[v].append((u, d, e))
    return reverso


def distancias_dijkstra(grafo, inicio, indice):
    dist = {inicio: 0.0}
    ordem = count()
    fila = [(0.0, next(ordem), inicio)]
    while fila:
        custo, _, u = heappop(fila)
        if custo != dist[u]:
            continue
        for aresta in grafo[u]:
            v, peso = aresta[0], aresta[indice]
            novo = custo + peso
            if novo < dist.get(v, inf):
                dist[v] = novo
                heappush(fila, (novo, next(ordem), v))
    return dist


class IndiceALT:
    """Pré-processamento reutilizável para o mesmo grafo e a mesma métrica.

    Copia a adjacência para impedir que mutações invalidem as tabelas.
    Seleção determinística de landmarks por afastamento na métrica do grafo.
    """
    def __init__(self, grafo, modo='emissao', quantidade=4):
        if modo not in ('distancia', 'emissao') or quantidade < 1:
            raise ValueError('Informe modo distancia/emissao e ao menos um landmark.')
        validar_grafo(grafo)
        self.grafo = {u: tuple(arestas) for u, arestas in grafo.items()}
        self.indice = 1 if modo == 'distancia' else 2
        reverso = inverter_grafo(self.grafo)
        self.tabelas = []
        restantes = list(self.grafo)
        proximidade = dict.fromkeys(restantes, inf)
        for _ in range(min(quantidade, len(restantes))):
            marco = max(restantes, key=lambda u: proximidade[u])
            restantes.remove(marco)
            ida = distancias_dijkstra(self.grafo, marco, self.indice)
            volta = distancias_dijkstra(reverso, marco, self.indice)
            self.tabelas.append((ida, volta))
            for u in restantes:
                proximidade[u] = min(proximidade[u], ida.get(u, inf), volta.get(u, inf))

    def heuristica(self, u, destino):
        limite = 0.0
        for ida, volta in self.tabelas:
            if destino in ida and u in ida:
                limite = max(limite, ida[destino] - ida[u])
            if u in volta and destino in volta:
                limite = max(limite, volta[u] - volta[destino])
        return limite

    def buscar(self, inicio, destino):
        if inicio not in self.grafo or destino not in self.grafo:
            return None
        ordem = count()
        inicial = (inicio, 0.0, 0.0, None)
        fila = [(self.heuristica(inicio, destino), 0.0, next(ordem), inicial)]
        melhores = {inicio: 0.0}
        while fila:
            _, custo, _, label = heappop(fila)
            u, d, e, _ = label
            if custo != melhores[u]:
                continue
            if u == destino:
                return reconstruir(label)
            for v, cd, ce in self.grafo[u]:
                novo = custo + (cd if self.indice == 1 else ce)
                if novo < melhores.get(v, inf):
                    melhores[v] = novo
                    filho = (v, d + cd, e + ce, label)
                    heappush(fila, (novo + self.heuristica(v, destino), novo, next(ordem), filho))
        return None


def reconstruir(label):
    _, d, e, _ = label
    nos = []
    while label is not None:
        nos.append(label[0])
        label = label[3]
    return Rota(nos[::-1], d, e)


def boa_estrela(grafo, inicio, destino):
    """Fronteira completa, com uma rota por par de custos não dominado.

    OPEN lexicográfico (f_distância, f_emissão); poda O(1) por g2 mínimo.
    Dois Dijkstras reversos fornecem heurísticas consistentes por objetivo.
    Não há truncamento da fronteira nem aproximação epsilon.
    """
    validar_grafo(grafo)
    if inicio not in grafo or destino not in grafo:
        return []
    reverso = inverter_grafo(grafo)
    hd = distancias_dijkstra(reverso, destino, 1)
    he = distancias_dijkstra(reverso, destino, 2)
    if inicio not in hd:
        return []
    ordem = count()
    fila = [(hd[inicio], he[inicio], next(ordem), (inicio, 0.0, 0.0, None))]
    minimo_e = {}
    solucoes = []
    while fila:
        _, fe, _, label = heappop(fila)
        u, d, e, _ = label
        if e >= minimo_e.get(u, inf) or fe >= minimo_e.get(destino, inf):
            continue
        minimo_e[u] = e
        if u == destino:
            solucoes.append(reconstruir(label))
            continue
        for v, cd, ce in grafo[u]:
            if v not in hd:
                continue
            nd, ne = d + cd, e + ce
            f2 = ne + he[v]
            if ne >= minimo_e.get(v, inf) or f2 >= minimo_e.get(destino, inf):
                continue
            heappush(fila, (nd + hd[v], f2, next(ordem), (v, nd, ne, label)))
    return solucoes
