"""Obtenção reproduzível do catálogo canadense usado nas validações de CO₂."""
import csv
from io import BytesIO, StringIO
import os
from pathlib import Path
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile


BASE = Path(__file__).resolve().parent
NOME_DATASET = 'CO2 Emissions_Canada.csv'
CAMINHO_DATASET = BASE / NOME_DATASET
ID_DATASET_KAGGLE = 'debajyotipodder/co2-emission-by-vehicles'
FONTE_DATASET = f'https://www.kaggle.com/datasets/{ID_DATASET_KAGGLE}'
NOTEBOOK_REFERENCIA = 'https://www.kaggle.com/code/muizah/c02-emission'
URL_DOWNLOAD = f'https://www.kaggle.com/api/v1/datasets/download/{ID_DATASET_KAGGLE}'
COLUNAS_OBRIGATORIAS = {
    'Fuel Type',
    'Fuel Consumption Comb (L/100 km)',
    'CO2 Emissions(g/km)',
}
LIMITE_DOWNLOAD_BYTES = 20 * 1024 * 1024


def _baixar_zip(url):
    requisicao = Request(url, headers={'User-Agent': 'Routly/1.0 (validacao-cientifica)'})
    try:
        with urlopen(requisicao, timeout=60) as resposta:
            tamanho = resposta.headers.get('Content-Length')
            if tamanho and int(tamanho) > LIMITE_DOWNLOAD_BYTES:
                raise ValueError('O arquivo informado pelo Kaggle excede o limite de 20 MB.')
            conteudo = resposta.read(LIMITE_DOWNLOAD_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as erro:
        raise ValueError(f'Não foi possível baixar o dataset público do Kaggle: {erro}') from erro
    if len(conteudo) > LIMITE_DOWNLOAD_BYTES:
        raise ValueError('O download do Kaggle excedeu o limite de 20 MB.')
    return conteudo


def _extrair_csv(conteudo_zip):
    try:
        with ZipFile(BytesIO(conteudo_zip)) as arquivo_zip:
            candidatos = [item for item in arquivo_zip.infolist()
                           if not item.is_dir() and Path(item.filename).name == NOME_DATASET]
            if len(candidatos) != 1:
                raise ValueError(f'O pacote do Kaggle deve conter exatamente um {NOME_DATASET}.')
            if candidatos[0].file_size > LIMITE_DOWNLOAD_BYTES:
                raise ValueError('O CSV descompactado excede o limite de 20 MB.')
            conteudo_csv = arquivo_zip.read(candidatos[0])
    except BadZipFile as erro:
        raise ValueError('O Kaggle não retornou um pacote ZIP válido.') from erro

    try:
        texto = conteudo_csv.decode('utf-8-sig')
    except UnicodeDecodeError as erro:
        raise ValueError('O CSV baixado não está codificado em UTF-8.') from erro
    leitor = csv.DictReader(StringIO(texto))
    ausentes = COLUNAS_OBRIGATORIAS - set(leitor.fieldnames or [])
    if ausentes:
        raise ValueError('O CSV baixado não possui as colunas esperadas: ' +
                         ', '.join(sorted(ausentes)))
    return conteudo_csv


def baixar_dataset_co2(caminho=CAMINHO_DATASET, *, url=URL_DOWNLOAD):
    """Baixa e grava atomicamente o CSV público, sem extrair outros arquivos."""
    destino = Path(caminho)
    conteudo_csv = _extrair_csv(_baixar_zip(url))
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=destino.parent, prefix=f'.{destino.name}.',
                                         suffix='.tmp', delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo_csv)
        os.replace(temporario, destino)
    finally:
        if temporario is not None and temporario.exists():
            temporario.unlink()
    return destino


def garantir_dataset_co2(caminho=CAMINHO_DATASET):
    """Retorna o CSV existente ou faz seu download automático quando ausente."""
    destino = Path(caminho)
    if destino.is_file():
        return destino
    print(f'[DADOS] {NOME_DATASET} ausente; baixando o dataset público do Kaggle...')
    resultado = baixar_dataset_co2(destino)
    print(f'[DADOS] Dataset salvo em {resultado}.')
    return resultado
