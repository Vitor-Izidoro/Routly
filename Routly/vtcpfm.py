"""VT-CPFM-1 convexo HDDT1: Wang e Rakha (2017), equações 3–5.

Parâmetros: seção 3 e tabelas 1, 2 e 4; DOI 10.1016/j.trd.2017.06.011.
Integração por rampa uniforme e velocidade constante: hipótese do Routly.
"""
from dataclasses import dataclass, fields
import math

from emissoes import ConsumoTrecho, validar_cenario
from veiculos import HDDT1
from cenarios_co2 import FATOR_EPA_G_L, selecionar_cenario_co2


@dataclass(frozen=True)
class CaminhaoVTCPFM:
    massa_vazia_kg: float = HDDT1.massa_veicular_kg
    area_frontal_m2: float = HDDT1.area_frontal_m2
    coef_arrasto: float = HDDT1.coef_arrasto
    coef_rolamento: float = 1.25
    c1: float = 0.0328
    c2: float = 4.575
    eficiencia_transmissao: float = 0.94
    densidade_ar_kg_m3: float = 1.2256
    gravidade_m_s2: float = 9.8066
    fator_massa_rotacional: float = 0.1
    alpha0_l_s: float = 1.56e-3
    alpha1_l_s_kw: float = 8.10e-5
    alpha2_l_s_kw2: float = 1.00e-8
    potencia_nominal_kw: float = HDDT1.potencia_nominal_hp * 0.7456998715822702
    # EPA por compatibilidade; configurar_vtcpfm('artigo') seleciona 2070 g/L.
    fator_co2_g_l: float = FATOR_EPA_G_L

    def __post_init__(self):
        for campo in fields(self):
            valor = getattr(self, campo.name)
            if not math.isfinite(valor) or valor <= 0:
                raise ValueError(f'{campo.name} deve ser finito e positivo.')
        if self.eficiencia_transmissao > 1:
            raise ValueError('Eficiência de transmissão deve estar no intervalo (0, 1].')


@dataclass(frozen=True)
class ConsumoTrechoVTCPFM(ConsumoTrecho):
    potencia_kw: float
    potencia_excedida: bool


def configurar_vtcpfm(cenario_co2='epa'):
    """HDDT1 convexo com conversão de CO₂ explicitamente selecionada."""
    cenario = selecionar_cenario_co2(cenario_co2)
    return CaminhaoVTCPFM(fator_co2_g_l=cenario.fator_g_l)


def potencia_instantanea(velocidade_kmh, declividade, altitude_m, caminhao=None,
                        *, carga_kg=0.0, aceleracao_m_s2=0.0):
    """Equações 3 e 4; G é uma razão (0,05 = 5%), H convertido a km.

    Permite repouso para avaliação instantânea. Razão de marcha xi=0 conforme
    o artigo; a API aceita aceleração, mas as arestas usam aceleração zero.
    """
    p = caminhao or CaminhaoVTCPFM()
    valores = (velocidade_kmh, declividade, altitude_m, carga_kg, aceleracao_m_s2)
    if not all(math.isfinite(x) for x in valores) or velocidade_kmh < 0 or carga_kg < 0:
        raise ValueError('Entradas devem ser finitas; velocidade e carga não negativas.')
    ch = 1 - 0.085 * altitude_m / 1000
    if ch <= 0:
        raise ValueError('Altitude fora do domínio da correção aerodinâmica (Ch > 0).')
    massa = p.massa_vazia_kg + carga_kg
    v = velocidade_kmh
    resistencia = (p.densidade_ar_kg_m3 / 25.92 * p.coef_arrasto * ch * p.area_frontal_m2 * v**2
                   + p.gravidade_m_s2 * massa * p.coef_rolamento / 1000 * (p.c1 * v + p.c2)
                   + p.gravidade_m_s2 * massa * declividade)
    potencia = (resistencia + (1 + p.fator_massa_rotacional) * massa * aceleracao_m_s2) * v / (3600 * p.eficiencia_transmissao)
    if not math.isfinite(potencia):
        raise ValueError('Parâmetros produziram potência não finita.')
    return potencia


def vazao_combustivel(potencia_kw, caminhao=None):
    """Equação 5, tabela 4: litros/s; potência negativa mantém alpha0."""
    if not math.isfinite(potencia_kw):
        raise ValueError('Potência deve ser finita.')
    p = caminhao or CaminhaoVTCPFM()
    potencia = max(0.0, potencia_kw)
    vazao = p.alpha0_l_s + p.alpha1_l_s_kw * potencia + p.alpha2_l_s_kw2 * potencia**2
    if not math.isfinite(vazao):
        raise ValueError('Parâmetros produziram vazão não finita.')
    return vazao


def consumo_trecho_vtcpfm(distancia_m, delta_z, caminhao=None, *, altitude_m,
                          carga_kg=0.0, velocidade_kmh=30.0):
    """Integra vazão constante em L e g usando comprimento 3D/velocidade.

    Distância horizontal e desnível em m; altitude média da aresta em m.
    A potência não é recortada: sinaliza cenários acima da potência nominal.
    """
    validar_cenario(carga_kg, velocidade_kmh)
    if not math.isfinite(distancia_m) or distancia_m < 0 or not math.isfinite(delta_z):
        raise ValueError('Distância deve ser finita e não negativa; desnível deve ser finito.')
    if distancia_m == 0 and delta_z != 0:
        raise ValueError('Trecho com distância zero não pode ter desnível.')
    p = caminhao or CaminhaoVTCPFM()
    potencia = potencia_instantanea(velocidade_kmh, delta_z / distancia_m if distancia_m else 0,
                                   altitude_m, p, carga_kg=carga_kg)
    if distancia_m == 0:
        return ConsumoTrechoVTCPFM(0.0, 0.0, 0.0, False)
    tempo_s = math.hypot(distancia_m, delta_z) / (velocidade_kmh / 3.6)
    litros = tempo_s * vazao_combustivel(potencia, p)
    co2 = litros * p.fator_co2_g_l
    if not math.isfinite(co2):
        raise ValueError('Parâmetros produziram custo não finito.')
    return ConsumoTrechoVTCPFM(litros, co2, potencia, potencia > p.potencia_nominal_kw)
