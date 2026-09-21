"""Fatores de CO₂ separados da equação de consumo; fontes e alcance explícitos."""
from dataclasses import dataclass


FATOR_EPA_G_L = 10210.0 / 3.785411784
FATOR_ARTIGO_G_L = 2070.0


@dataclass(frozen=True)
class CenarioCO2:
    nome: str
    descricao: str
    fator_g_l: float
    fonte: str
    alcance: str


EPA = CenarioCO2(
    'epa', 'Aplicação com diesel de referência EPA', FATOR_EPA_G_L,
    'EPA (2025), Emission Factors Hub, tabela 2: 10,21 kg CO₂/galão americano.',
    'Referência de combustão; sem calibração para a mistura de diesel brasileira.',
)
ARTIGO = CenarioCO2(
    'artigo', 'Reprodução do fator empírico de Wang e Rakha', FATOR_ARTIGO_G_L,
    'Wang e Rakha (2017), seção 6.3, equação 9; DOI 10.1016/j.trd.2017.06.011.',
    'Reproduz a conversão do artigo; a rota simulada não reproduz suas medições.',
)


def selecionar_cenario_co2(nome='epa', *, modelo='vtcpfm'):
    """Artigo exige VT-CPFM; legado já recebe emissão em g/km, sem litros."""
    if modelo not in ('vtcpfm', 'cmem'):
        raise ValueError('--cenario-co2 exige --modelo-emissao vtcpfm ou cmem.')
    if nome == 'epa':
        return EPA
    if nome == 'artigo':
        if modelo != 'vtcpfm':
            raise ValueError('--cenario-co2 artigo exige --modelo-emissao vtcpfm.')
        return ARTIGO
    raise ValueError('Cenário de CO₂ deve ser epa ou artigo.')
