"""Identificação física do HDDT1; não contém uma equação de consumo.

Wang e Rakha (2017), DOI 10.1016/j.trd.2017.06.011,
tabelas 1 e 2 e seção 4.2. Ver docs/CAMINHAO_REFERENCIA.md.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CaminhaoReferencia:
    codigo: str
    fabricante: str
    modelo: str
    ano: int
    motor: str
    potencia_nominal_hp: float
    massa_veicular_kg: float
    cilindrada_l: float
    area_frontal_m2: float
    coef_arrasto: float

    @property
    def descricao(self):
        return f'{self.codigo} — {self.fabricante} {self.modelo} ({self.ano}), {self.motor}'


HDDT1 = CaminhaoReferencia(
    codigo='HDDT1', fabricante='International', modelo='9800 SBA', ano=1997,
    motor='Cummins M11-330', potencia_nominal_hp=330.0,
    massa_veicular_kg=7182.0, cilindrada_l=10.8,
    area_frontal_m2=10.0, coef_arrasto=0.78,
)

# Massa aproximada do laboratório rebocado, não capacidade de carga do trator.
# Não é aplicada automaticamente: a massa adicional da consulta é configurável.
MASSA_MERL_APROX_KG = 45000 * 0.45359237
