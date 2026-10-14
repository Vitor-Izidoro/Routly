"""Servidor HTTP restrito ao computador local, com fila persistente de execuções."""
import argparse
import csv
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import mimetypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
from urllib.parse import quote, unquote, urlparse
import uuid
import webbrowser

from interface.catalogo import BASE, GRUPOS, catalogo, validar

STATIC = Path(__file__).parent / 'static'
RUNS = BASE / '.routly' / 'runs'
EXTENSOES = {'.png', '.jpg', '.jpeg', '.svg', '.html', '.csv', '.json', '.md', '.txt'}


def agora():
    return datetime.now(timezone.utc).isoformat()


def caminho_seguro(raiz, relativo):
    raiz = raiz.resolve()
    caminho = (raiz / relativo).resolve()
    if not caminho.is_relative_to(raiz) or not caminho.is_file():
        raise FileNotFoundError('Arquivo indisponível.')
    return caminho


def artefatos(raiz, prefixo):
    if not raiz.exists():
        return []
    arquivos = []
    for p in sorted(raiz.rglob('*')):
        if p.is_file() and p.suffix.lower() in EXTENSOES and p.resolve().is_relative_to(raiz.resolve()):
            relativo = p.relative_to(raiz).as_posix()
            arquivos.append(dict(nome=relativo, tipo=p.suffix[1:], tamanho=p.stat().st_size,
                                 url=prefixo + quote(relativo)))
    return arquivos


class Execucoes:
    def __init__(self, raiz=RUNS):
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.jobs = {}
        self.processo = None
        self.fechando = False
        self.sinal = threading.Event()
        for arquivo in self.raiz.glob('*/job.json'):
            try:
                job = json.loads(arquivo.read_text(encoding='utf-8'))
                if job['status'] in ('fila', 'executando'):
                    job.update(status='interrompido', fim=agora())
                self.jobs[job['id']] = job
                self.salvar(job)
            except (OSError, ValueError, KeyError):
                continue
        self.thread = threading.Thread(target=self._fila, daemon=True)
        self.thread.start()

    def salvar(self, job):
        pasta = self.raiz / job['id']
        pasta.mkdir(exist_ok=True)
        temp = pasta / 'job.tmp'
        temp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(pasta / 'job.json')

    def criar(self, pedidos):
        if not isinstance(pedidos, list) or not 1 <= len(pedidos) <= 40:
            raise ValueError('Selecione entre 1 e 40 execuções.')
        validados = []
        for pedido in pedidos:
            if not isinstance(pedido, dict):
                raise ValueError('Pedido inválido.')
            validados.append(validar(pedido.get('operacao'), pedido.get('parametros', {})))
        novos = []
        with self.lock:
            if self.fechando:
                raise ValueError('Servidor em encerramento.')
            if sum(j['status'] in ('fila', 'executando') for j in self.jobs.values()) + len(validados) > 100:
                raise ValueError('A fila está cheia. Aguarde as execuções atuais.')
            for op, p in validados:
                job = dict(id=uuid.uuid4().hex, operacao=op['id'], nome=op['nome'], grupo=op['grupo'],
                           parametros=p, status='fila', criado=agora(), inicio=None, fim=None, codigo=None)
                self.salvar(job)
                self.jobs[job['id']] = job
                novos.append(dict(job))
            self.sinal.set()
        return novos

    def listar(self):
        with self.lock:
            return [dict(j) for j in sorted(self.jobs.values(), key=lambda j: j['criado'], reverse=True)]

    def detalhe(self, id):
        with self.lock:
            if id not in self.jobs:
                raise FileNotFoundError('Execução não encontrada.')
            job = dict(self.jobs[id])
        pasta = self.raiz / id
        log = pasta / 'terminal.txt'
        # A tela recebe até 256 KiB; o arquivo para download contém o log inteiro.
        if log.exists():
            with log.open('rb') as arquivo:
                arquivo.seek(max(0, log.stat().st_size - 262144))
                job['log'] = arquivo.read().decode('utf-8', errors='replace')
        else:
            job['log'] = ''
        job['artefatos'] = artefatos(pasta / 'artefatos', f'/arquivos/{id}/')
        job['log_url'] = f'/logs/{id}'
        return job

    def cancelar(self, id):
        with self.lock:
            if id not in self.jobs:
                raise FileNotFoundError('Execução não encontrada.')
            job = self.jobs[id]
            if job['status'] not in ('fila', 'executando'):
                return
            ativo = job['status'] == 'executando'
            job.update(status='cancelado', fim=agora())
            self.salvar(job)
            if ativo and self.processo and self.processo.poll() is None:
                if os.name == 'nt':
                    try:
                        subprocess.run(['taskkill', '/PID', str(self.processo.pid), '/T', '/F'],
                                       capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                    finally:
                        # Alguns ambientes restringem taskkill; o handle do processo
                        # criado por este servidor ainda permite encerrá-lo diretamente.
                        if self.processo.poll() is None:
                            self.processo.kill()
                else:
                    try:
                        os.killpg(self.processo.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass

    def _fila(self):
        while not self.fechando:
            self.sinal.wait()
            if self.fechando:
                return
            with self.lock:
                job = next((j for j in self.jobs.values() if j['status'] == 'fila'), None)
                if job is None:
                    self.sinal.clear()
                    continue
                pasta = self.raiz / job['id']
                job.update(status='executando', inicio=agora())
                self.salvar(job)
                log = (pasta / 'terminal.txt').open('wb')
                env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1', MPLBACKEND='Agg')
                try:
                    self.processo = subprocess.Popen(
                        [sys.executable, '-u', '-m', 'interface.worker', str(pasta / 'job.json')],
                        cwd=BASE, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                        start_new_session=os.name != 'nt')
                except OSError as erro:
                    log.write(str(erro).encode('utf-8'))
                    log.close()
                    job.update(status='falhou', fim=agora(), codigo=-1)
                    self.salvar(job)
                    continue
            codigo = self.processo.wait()
            log.close()
            with self.lock:
                if job['status'] != 'cancelado':
                    job.update(status='concluido' if codigo == 0 else 'falhou', fim=agora())
                job['codigo'] = codigo
                self.salvar(job)
                self.processo = None

    def fechar(self):
        with self.lock:
            self.fechando = True
            for job in self.jobs.values():
                if job['status'] in ('fila', 'executando'):
                    self.cancelar(job['id'])
            self.sinal.set()


def ambiente():
    def shp(relativo):
        return any((base / relativo).is_file() for base in (BASE, BASE.parent))
    return dict(grafo=(BASE / 'grafo_curitiba_carbono.csv').is_file(),
                catalogo=(BASE / 'CO2 Emissions_Canada.csv').is_file(),
                ruas=shp('EIXO_RUA_SIRGAS/EIXO_RUA.shp'),
                curvas=shp('ALT_CURVA_DE_NIVEL_SIRGAS/ALT_CURVA_DE_NIVEL.shp'),
                dependencias={m: importlib.util.find_spec(m) is not None for m in ('pytest', 'pandas', 'numpy', 'scipy', 'matplotlib', 'geopandas')})


class Handler(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        pass

    def responder(self, dados, status=200, tipo='application/json; charset=utf-8'):
        conteudo = json.dumps(dados, ensure_ascii=False).encode('utf-8') if tipo.startswith('application/json') else dados
        self.send_response(status)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(conteudo)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.end_headers()
        self.wfile.write(conteudo)

    def local(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.local():
            return self.responder({'erro': 'Acesso somente pelo endereço local.'}, 403)
        url = urlparse(self.path)
        caminho = unquote(url.path)
        try:
            if caminho == '/api/catalogo':
                return self.responder(dict(grupos=GRUPOS, operacoes=catalogo(), ambiente=ambiente()))
            if caminho == '/api/execucoes':
                return self.responder(self.server.execucoes.listar())
            if caminho.startswith('/api/execucoes/'):
                return self.responder(self.server.execucoes.detalhe(caminho.rsplit('/', 1)[-1]))
            if caminho == '/api/biblioteca':
                return self.responder(artefatos(BASE / 'resultados_validacao', '/biblioteca/'))
            if caminho.startswith('/arquivos/'):
                _, _, id, relativo = caminho.split('/', 3)
                if id not in self.server.execucoes.jobs:
                    raise FileNotFoundError()
                arquivo = caminho_seguro(self.server.execucoes.raiz / id / 'artefatos', relativo)
                if arquivo.suffix.lower() not in EXTENSOES:
                    raise FileNotFoundError()
            elif caminho.startswith('/biblioteca/'):
                arquivo = caminho_seguro(BASE / 'resultados_validacao', caminho.removeprefix('/biblioteca/'))
                if arquivo.suffix.lower() not in EXTENSOES:
                    raise FileNotFoundError()
            elif caminho.startswith('/logs/'):
                id = caminho.rsplit('/', 1)[-1]
                if id not in self.server.execucoes.jobs:
                    raise FileNotFoundError()
                arquivo = caminho_seguro(self.server.execucoes.raiz / id, 'terminal.txt')
            else:
                arquivo = caminho_seguro(STATIC, 'index.html' if caminho == '/' else caminho.lstrip('/'))
            if url.query == 'preview' and arquivo.suffix == '.csv':
                with arquivo.open(encoding='utf-8-sig', newline='') as entrada:
                    reader = csv.reader(entrada)
                    linhas = []
                    for i, linha in enumerate(reader):
                        if i >= 201:
                            break
                        linhas.append(linha)
                return self.responder(dict(linhas=linhas[:201], limitado=len(linhas) == 201))
            tipo = mimetypes.guess_type(arquivo.name)[0] or 'application/octet-stream'
            if arquivo.suffix in ('.md', '.txt', '.csv'):
                tipo = 'text/plain'
            if tipo.startswith('text/') or tipo in ('application/javascript', 'application/json'):
                tipo += '; charset=utf-8'
            # JSON de artefatos é enviado como bytes, sem serialização dupla.
            if tipo.startswith('application/json'):
                tipo = 'text/plain; charset=utf-8'
            return self.responder(arquivo.read_bytes(), tipo=tipo)
        except (FileNotFoundError, ValueError):
            self.responder({'erro': 'Arquivo ou execução não encontrado.'}, 404)
        except OSError as erro:
            self.responder({'erro': str(erro)}, 500)

    def do_POST(self):
        origem = self.headers.get('Origin')
        if not self.local() or (origem and origem != f'http://{self.headers.get("Host")}'):
            return self.responder({'erro': 'Origem não permitida.'}, 403)
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.responder({'erro': 'Use JSON.'}, 415)
        try:
            tamanho = int(self.headers.get('Content-Length', '0'))
            if not 0 < tamanho <= 65536:
                raise ValueError('Tamanho de pedido inválido.')
            dados = json.loads(self.rfile.read(tamanho))
            if not isinstance(dados, dict):
                raise ValueError('Pedido inválido.')
            if self.path == '/api/execucoes':
                return self.responder(self.server.execucoes.criar(dados.get('execucoes')), 201)
            if self.path.startswith('/api/cancelar/'):
                self.server.execucoes.cancelar(self.path.rsplit('/', 1)[-1])
                return self.responder({'ok': True})
            self.responder({'erro': 'Operação desconhecida.'}, 404)
        except (ValueError, TypeError) as erro:
            self.responder({'erro': str(erro)}, 400)
        except FileNotFoundError as erro:
            self.responder({'erro': str(erro)}, 404)


def main():
    parser = argparse.ArgumentParser(description='Interface local do Routly')
    parser.add_argument('--porta', type=int, default=8765)
    parser.add_argument('--sem-abrir', action='store_true')
    args = parser.parse_args()
    try:
        servidor = ThreadingHTTPServer(('127.0.0.1', args.porta), Handler)
    except OSError as erro:
        parser.exit(1, f'Não foi possível abrir a porta {args.porta}: {erro}\nUse --porta com outro número.\n')
    servidor.execucoes = Execucoes()
    url = f'http://127.0.0.1:{servidor.server_port}'
    print(f'Routly disponível em {url}\nCtrl+C encerra o servidor e as execuções ativas.', flush=True)
    if not args.sem_abrir:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.execucoes.fechar()
        servidor.server_close()


if __name__ == '__main__':
    main()
