"""CMEM simplificado para caminhão diesel, em regime estacionário.

Parâmetros HDV: Lai et al. (2024), tabela 2, DOI 10.1016/j.cor.2024.106557.
Adaptação local: potência de tração limitada a zero nas descidas;
perdas internas do motor permanecem. Não é o simulador CMEM completo.
Detalhes, unidades e limitações: docs/MODELO_EMISSOES.md.
"""
from dataclasses import dataclass, fields
import math


@dataclass(frozen=True)
class CaminhaoCMEM:
    massa_vazia_kg: float = 13000.0
    atrito_motor_kj_rev_l: float = 0.17
    rotacao_rev_s: float = 33.0
    cilindrada_l: float = 11.0
    area_frontal_m2: float = 8.2
    coef_arrasto: float = 0.70
    coef_rolamento: float = 0.008
    eficiencia_transmissao: float = 0.4
    eficiencia_motor: float = 0.9
    poder_calorifico_kj_g: float = 45.0
    conversao_combustivel_g_l: float = 737.0
    densidade_ar_kg_m3: float = 1.2041
    gravidade_m_s2: float = 9.81
    # EPA (2025), tabela 2: 10.21 kg CO2/galão americano.
    fator_co2_g_l: float = 10210.0 / 3.785411784

    def __post_init__(self):
        for campo in fields(self):
            valor = getattr(self, campo.name)
            if not math.isfinite(valor) or valor <= 0:
                raise ValueError(f'{campo.name} deve ser finito e positivo.')
        if self.eficiencia_motor > 1 or self.eficiencia_transmissao > 1:
            raise ValueError('Eficiências devem estar no intervalo (0, 1].')


@dataclass(frozen=True)
class ConsumoTrecho:
    combustivel_l: float
    co2_g: float


def validar_cenario(carga_kg, velocidade_kmh):
    if not math.isfinite(carga_kg) or carga_kg < 0:
        raise ValueError('A carga deve ser finita e não negativa.')
    if not math.isfinite(velocidade_kmh) or velocidade_kmh <= 0:
        raise ValueError('A velocidade deve ser finita e positiva.')


def consumo_trecho(distancia_m, delta_z, caminhao=None, *, carga_kg=0.0,
                   velocidade_kmh=30.0):
    """Distância horizontal em m; desnível assinado em m; retorno em L e g.

    Velocidade constante sobre o segmento 3D; aceleração zero. Carga não varia
    ao longo da consulta. Distância zero só é aceita com desnível zero.
    """
    validar_cenario(carga_kg, velocidade_kmh)
    if not math.isfinite(distancia_m) or distancia_m < 0 or not math.isfinite(delta_z):
        raise ValueError('Distância deve ser finita e não negativa; desnível deve ser finito.')
    if distancia_m == 0:
        if delta_z != 0:
            raise ValueError('Trecho com distância zero não pode ter desnível.')
        return ConsumoTrecho(0.0, 0.0)
    p = caminhao or CaminhaoCMEM()
    comprimento = math.hypot(distancia_m, delta_z)
    seno = delta_z / comprimento
    cosseno = distancia_m / comprimento
    v = velocidade_kmh / 3.6
    massa = p.massa_vazia_kg + carga_kg
    forca = (massa * p.gravidade_m_s2 * (seno + p.coef_rolamento * cosseno)
             + 0.5 * p.densidade_ar_kg_m3 * p.coef_arrasto * p.area_frontal_m2 * v**2)
    potencia_tracao_w = max(0.0, forca * v)
    potencia_interna_kw = p.atrito_motor_kj_rev_l * p.rotacao_rev_s * p.cilindrada_l
    potencia_combustivel_kw = (potencia_interna_kw + potencia_tracao_w /
                               (1000 * p.eficiencia_transmissao * p.eficiencia_motor))
    litros = (comprimento / v * potencia_combustivel_kw /
              (p.poder_calorifico_kj_g * p.conversao_combustivel_g_l))
    co2 = litros * p.fator_co2_g_l
    if not math.isfinite(co2):
        raise ValueError('Parâmetros produziram custo não finito.')
    return ConsumoTrecho(litros, co2)


def emissao_legada(distancia_m, delta_z, taxa_emissao_g_km):
    if not math.isfinite(taxa_emissao_g_km) or taxa_emissao_g_km <= 0:
        raise ValueError('A taxa legada deve ser finita e positiva.')
    return distancia_m / 1000 * taxa_emissao_g_km * (1 + 0.015 * max(delta_z, 0))
