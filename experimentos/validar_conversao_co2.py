"""Verificação dimensional e comparação descritiva com o catálogo canadense.

Não valida o consumo físico do caminhão, nem recalibra seus parâmetros.
Executável somente com a biblioteca padrão do Python.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from cenarios_co2 import FATOR_EPA_G_L
from dados_co2 import (CAMINHO_DATASET, FONTE_DATASET, NOTEBOOK_REFERENCIA,
                       URL_DOWNLOAD, garantir_dataset_co2)
from vtcpfm import consumo_trecho_vtcpfm, vazao_combustivel

CONSUMO = 'Fuel Consumption Comb (L/100 km)'
EMISSAO = 'CO2 Emissions(g/km)'
FONTE = FONTE_DATASET


def positivo(valor):
    numero = float(valor)
    if not math.isfinite(numero) or numero <= 0:
        raise ValueError('Valor deve ser finito e maior que zero.')
    return numero


def converter_consumo(consumo_l_100km, fator_g_l=FATOR_EPA_G_L):
    """Retorna (L/km, g CO₂/km); admite consumo zero."""
    consumo = float(consumo_l_100km)
    if not math.isfinite(consumo) or consumo < 0:
        raise ValueError('Consumo deve ser finito e não negativo.')
    fator = positivo(fator_g_l)
    return consumo / 100, consumo / 100 * fator


def verificar_unidades():
    """Casos conhecidos e integração com a conversão usada pelo VT-CPFM."""
    resultados = []

    def conferir(nome, obtido, esperado):
        resultados.append(dict(verificacao=nome, obtido=obtido, esperado=esperado,
                               passou=math.isclose(obtido, esperado, rel_tol=1e-12,
                                                   abs_tol=1e-12)))

    litros, gramas = converter_consumo(10, 2700)
    conferir('10 L/100 km -> 0.1 L/km', litros, 0.1)
    conferir('0.1 L/km x 2700 g/L -> 270 g/km', gramas, 270)
    conferir('Consumo zero -> emissão zero', converter_consumo(0)[1], 0)
    conferir('10.21 kg/gal US -> g/L', FATOR_EPA_G_L, 2697.1966545766954)
    # 36 km/h = 10 m/s: 1 km plano leva 100 s.
    curto = consumo_trecho_vtcpfm(1000, 0, altitude_m=0, velocidade_kmh=36)
    longo = consumo_trecho_vtcpfm(10000, 0, altitude_m=0, velocidade_kmh=36)
    conferir('VT-CPFM: vazão L/s integrada por 100 s', curto.combustivel_l,
             vazao_combustivel(curto.potencia_kw) * 100)
    conferir('VT-CPFM: litros -> gramas', curto.co2_g,
             curto.combustivel_l * FATOR_EPA_G_L)
    conferir('VT-CPFM: 10 km consomem 10 vezes 1 km', longo.combustivel_l,
             curto.combustivel_l * 10)
    conferir('L/100 km -> g/km coincide com trecho de 1 km',
             converter_consumo(curto.combustivel_l * 100)[1], curto.co2_g)
    return resultados


def analisar(caminho):
    detalhes, rejeitados = [], []
    total = diesel = 0
    with Path(caminho).open(encoding='utf-8-sig', newline='') as arquivo:
        leitor = csv.DictReader(arquivo)
        exigidas = {'Fuel Type', CONSUMO, EMISSAO}
        if not exigidas.issubset(leitor.fieldnames or []):
            raise ValueError('Colunas obrigatórias ausentes: ' +
                             ', '.join(sorted(exigidas - set(leitor.fieldnames or []))))
        for linha, registro in enumerate(leitor, start=2):
            total += 1
            if (registro['Fuel Type'] or '').strip().upper() != 'D':
                continue
            diesel += 1
            try:
                consumo = positivo(registro[CONSUMO])
                emissao = positivo(registro[EMISSAO])
                litros, estimada = converter_consumo(consumo)
                fator = emissao / litros
                diferenca = (fator / FATOR_EPA_G_L - 1) * 100
                if not all(map(math.isfinite, (fator, estimada, diferenca))):
                    raise ValueError('Cálculo fora do intervalo numérico finito.')
            except (TypeError, ValueError, OverflowError, ZeroDivisionError) as erro:
                rejeitados.append(dict(linha_csv=linha, motivo=str(erro)))
                continue
            detalhes.append(dict(linha_csv=linha, fabricante=registro.get('Make', ''),
                                 modelo=registro.get('Model', ''), consumo_l_100km=consumo,
                                 consumo_l_km=litros, co2_dataset_g_km=emissao,
                                 co2_epa_g_km=estimada, fator_implicito_g_l=fator,
                                 diferenca_fator_pct=diferenca))
    if not detalhes:
        raise ValueError(f'Nenhum registro diesel válido; diesel={diesel}, inválidos={len(rejeitados)}.')
    fatores = [r['fator_implicito_g_l'] for r in detalhes]
    resumo = dict(registros_total=total, registros_diesel=diesel,
                  registros_validos=len(detalhes), registros_rejeitados=rejeitados,
                  fator_projeto_g_l=FATOR_EPA_G_L,
                  fator_implicito_media_g_l=statistics.mean(fatores),
                  fator_implicito_mediana_g_l=statistics.median(fatores),
                  fator_implicito_min_g_l=min(fatores), fator_implicito_max_g_l=max(fatores),
                  diferenca_media_fator_pct=(statistics.mean(fatores) / FATOR_EPA_G_L - 1) * 100)
    return resumo, detalhes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=CAMINHO_DATASET,
                        help='CSV local; se estiver ausente, será baixado automaticamente do Kaggle.')
    parser.add_argument('--saida', type=Path, default=BASE / 'experimentos/resultados_conversao_co2')
    args = parser.parse_args(argv)
    dataset_baixado = not args.dataset.is_file()
    try:
        dataset = garantir_dataset_co2(args.dataset)
        resumo, detalhes = analisar(dataset)
    except (OSError, ValueError) as erro:
        parser.error(str(erro))
    verificacoes = verificar_unidades()
    resumo.update(fonte=FONTE, notebook_referencia=NOTEBOOK_REFERENCIA,
                  url_download=URL_DOWNLOAD, dataset_baixado=dataset_baixado,
                  dataset=str(dataset.resolve()),
                  sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
                  python=platform.python_version(), verificacoes_unidades=verificacoes,
                  criterio='Comparação descritiva; sem limiar de aprovação empírica.',
                  limitacoes='Não valida consumo do caminhão. Consumo e CO₂ do catálogo '
                  'podem não ser independentes. Valores arredondados e registros repetidos '
                  'são preservados; não se estima significância estatística.')
    args.saida.mkdir(parents=True, exist_ok=True)
    (args.saida / 'resumo.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (args.saida / 'diesel.csv').open('w', encoding='utf-8', newline='') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(detalhes[0]))
        escritor.writeheader()
        escritor.writerows(detalhes)
    passaram = sum(v['passou'] for v in verificacoes)
    relatorio = (
        '# Verificação da conversão de consumo em CO₂\n\n'
        f'Verificações de unidades: {passaram}/{len(verificacoes)} passaram.\n\n'
        f'Registros diesel válidos: {len(detalhes)}; rejeitados: {len(resumo["registros_rejeitados"])}.\n\n'
        f'Fator do projeto: {FATOR_EPA_G_L:.4f} g/L.\n\n'
        f'Fator implícito médio: {resumo["fator_implicito_media_g_l"]:.4f} g/L; '
        f'mediana: {resumo["fator_implicito_mediana_g_l"]:.4f} g/L.\n\n'
        f'Intervalo observado: {min(r["fator_implicito_g_l"] for r in detalhes):.4f}–'
        f'{max(r["fator_implicito_g_l"] for r in detalhes):.4f} g/L.\n\n'
        f'Diferença da média em relação ao projeto: {resumo["diferenca_media_fator_pct"]:+.4f}%.\n\n'
        'A diferença descreve a proximidade dos fatores; não é um teste de equivalência '
        'nem uma aprovação do modelo físico. Nenhum parâmetro foi recalibrado.\n\n'
        + resumo['limitacoes'] + '\n\n'
        f'Fonte do dataset: {FONTE}\n\n'
        f'Notebook de referência: {NOTEBOOK_REFERENCIA}\n\n'
        f'URL de download automático: {URL_DOWNLOAD}\n\n'
        f'SHA-256 do CSV: `{resumo["sha256"]}`\n'
    )
    (args.saida / 'relatorio.md').write_text(relatorio, encoding='utf-8')
    # Terminais Windows antigos não representam CO₂; arquivos seguem em UTF-8.
    encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    print(relatorio.encode(encoding, errors='replace').decode(encoding))
    return 0 if passaram == len(verificacoes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
