"""Servidor local: a interface web roda no navegador, tudo fica na sua maquina."""

from __future__ import annotations

import argparse
import atexit
import inspect
import itertools
import json
import shutil
import tempfile
import mimetypes
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from . import __version__, batch, convert, export, fsbrowse, images, merge, optimize, pages, preview, remove, security, split, watermark

HOST = "127.0.0.1"
PORTA_PADRAO = 8765
STATIC = Path(__file__).resolve().parent / "static"

# So arquivos gerados nesta sessao podem ser baixados pela rota /download.
_saidas: set[str] = set()
# Previa: arquivos que a interface pode pedir como imagem. `_sessao` guarda a pasta temporaria da ultima
# previa de "Juntar" (arquivos extraidos de .zip/.rar) e some quando outra previa comeca ou o app fecha.
_ids: dict[int, Path] = {}
_prox = itertools.count(1)
_sessao: dict = {"dir": None, "ids": []}
_ao_encerrar: list = []  # chamadas extras ao encerrar (ex.: fechar a janela)
_lock = threading.Lock()


def _registrar(*caminhos) -> None:
    with _lock:
        _saidas.update(str(Path(c).resolve()) for c in caminhos if c)


def _novo_id(caminho: Path) -> int:
    with _lock:
        i = next(_prox)
        _ids[i] = caminho
    return i


def _limpar_sessao() -> None:
    with _lock:
        for i in _sessao["ids"]:
            _ids.pop(i, None)
        _sessao["ids"] = []
        pasta, _sessao["dir"] = _sessao["dir"], None
    if pasta:
        shutil.rmtree(pasta, ignore_errors=True)


atexit.register(_limpar_sessao)


def _api_previa_juntar(p: dict) -> dict:
    """Lista os arquivos na ordem de juncao, com id para pedir miniaturas."""
    _limpar_sessao()
    pasta = tempfile.mkdtemp(prefix="papelada-")
    _sessao["dir"] = pasta
    try:
        r = merge.listar_ordem(_pasta(p), Path(pasta))
    except Exception:
        _limpar_sessao()
        raise
    for item in r["items"]:
        item["id"] = _novo_id(Path(item.pop("path")))
        _sessao["ids"].append(item["id"])
    return {**r, "thumbs": preview.disponivel()}


def _api_previa_imagens(p: dict) -> dict:
    """Imagens na ordem em que virarao paginas, com id para miniaturas."""
    _limpar_sessao()
    pasta = tempfile.mkdtemp(prefix="papelada-")
    _sessao["dir"] = pasta
    try:
        r = images.listar(_pasta(p), Path(pasta))
    except Exception:
        _limpar_sessao()
        raise
    for item in r["items"]:
        item["id"] = _novo_id(Path(item.pop("path")))
        _sessao["ids"].append(item["id"])
    return {**r, "thumbs": True}


def _api_imagens(p: dict) -> dict:
    ordem = p.get("order")
    if ordem is not None and not (isinstance(ordem, list) and all(isinstance(x, str) for x in ordem)):
        raise ValueError("Ordem invalida.")
    r = images.imagens_para_pdf(_pasta(p), str(p.get("name") or ""), p.get("output") or None, ordem,
                                str(p.get("size") or "imagem"), str(p.get("orientation") or "auto"),
                                str(p.get("margin") or "nenhuma"), str(p.get("mode") or "unico"))
    _registrar(*r["outputs"])
    return r


def _api_remover(p: dict) -> dict:
    r = remove.remover_paginas(_pasta(p), str(p.get("value") or ""), p.get("output") or None)
    _registrar(r["output"])
    return r


# Ferramentas de uma chamada so: nome -> (funcao, sufixo do arquivo, extensao ou None para pasta, so um PDF?)
FERRAMENTAS = {
    "rotate": (pages.girar, "_girado", ".pdf", False),
    "organize": (pages.organizar, "_organizado", ".pdf", True),
    "number": (pages.numerar, "_numerado", ".pdf", False),
    "watermark": (watermark.marca_dagua, "_marca-dagua", ".pdf", False),
    "crop": (pages.recortar, "_recortado", ".pdf", False),
    "protect": (security.proteger, "_protegido", ".pdf", False),
    "unlock": (security.desbloquear, "_desbloqueado", ".pdf", False),
    "compress": (optimize.comprimir, "_comprimido", ".pdf", False),
    "repair": (optimize.reparar, "_reparado", ".pdf", False),
    "tojpg": (export.pdf_para_jpg, "_imagens", None, False),
    "tomd": (export.pdf_para_markdown, "", ".md", False),
}


def _api_ferramenta(p: dict) -> dict:
    """Roda uma ferramenta de PDF em um arquivo ou numa pasta de PDFs."""
    nome = str(p.get("tool") or "")
    if nome not in FERRAMENTAS:
        raise ValueError("Ferramenta desconhecida.")
    fn, sufixo, ext, so_arquivo = FERRAMENTAS[nome]
    opcoes = p.get("options") or {}
    if not isinstance(opcoes, dict):
        raise ValueError("Opções inválidas.")
    aceitos = set(inspect.signature(fn).parameters) - {"pdf", "saida"}
    desconhecidas = set(opcoes) - aceitos
    if desconhecidas:
        raise ValueError(f"Opção desconhecida: {sorted(desconhecidas)[0]}")
    r = batch.aplicar(_pasta(p), p.get("output") or None, fn, sufixo, ext, so_arquivo, **opcoes)
    _registrar(r["output"], *(x["output"] for x in r["resultados"]))
    return r


def _api_previa_arquivo(p: dict) -> dict:
    """Registra um PDF escolhido pelo usuario para ser visualizado."""
    pdf = _pasta(p)
    if pdf.suffix.lower() != ".pdf" or not pdf.is_file():
        raise ValueError("Escolha um arquivo PDF.")
    return {"id": _novo_id(pdf), "name": pdf.name, "pages": preview.paginas(pdf), "thumbs": preview.disponivel()}


def _pasta(p: dict) -> Path:
    return fsbrowse.resolver(p.get("path"))


def _api_juntar(p: dict) -> dict:
    ordem = p.get("order")
    if ordem is not None and not (isinstance(ordem, list) and all(isinstance(x, str) for x in ordem)):
        raise ValueError("Ordem invalida.")
    r = merge.juntar_pasta(_pasta(p), str(p.get("name") or ""), p.get("output") or None, ordem)
    _registrar(r["output"])
    return r


def _api_lote(p: dict) -> dict:
    r = merge.juntar_lote(_pasta(p), p.get("output") or None)
    _registrar(*(x["output"] for x in r["resultados"]))
    return r


def _api_separar(p: dict) -> dict:
    r = split.separar(_pasta(p), str(p.get("mode") or ""), str(p.get("value") or ""), p.get("output") or None)
    _registrar(*r["files"])
    return r


def _api_word(p: dict) -> dict:
    r = convert.pdf_para_word(_pasta(p), p.get("output") or None)
    _registrar(*(x["output"] for x in r["resultados"]))
    return r


def _api_revelar(p: dict) -> dict:
    """Mostra no Finder/Explorer um arquivo gerado nesta sessao."""
    alvo = Path(str(p.get("path") or "")).resolve()
    with _lock:
        permitido = str(alvo) in _saidas
    if not permitido or not alvo.exists():
        raise ValueError("Arquivo nao encontrado.")
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(alvo)])
    elif os.name == "nt":
        subprocess.Popen(["explorer", f"/select,{alvo}"])
    else:
        subprocess.Popen(["xdg-open", str(alvo.parent)])
    return {"ok": True}


ROTAS = {
    "/api/reveal": _api_revelar,
    "/api/list": lambda p: fsbrowse.listar(_pasta(p)),
    "/api/merge-preview": _api_previa_juntar,
    "/api/preview-file": _api_previa_arquivo,
    "/api/images-preview": _api_previa_imagens,
    "/api/images": _api_imagens,
    "/api/remove-pages": _api_remover,
    "/api/tool": _api_ferramenta,
    "/api/merge": _api_juntar,
    "/api/batch": _api_lote,
    "/api/split": _api_separar,
    "/api/word": _api_word,
}


class Handler(BaseHTTPRequestHandler):
    server_version = f"Papelada/{__version__}"

    def _host_ok(self) -> bool:
        """Barra paginas de outros sites (DNS rebinding / CSRF) falando com o servidor local."""
        porta = self.server.server_address[1]
        validos = {f"{HOST}:{porta}", f"localhost:{porta}"}
        if self.headers.get("Host") not in validos:
            return False
        origem = self.headers.get("Origin")
        return origem is None or origem in {f"http://{h}" for h in validos}

    def do_GET(self):
        if not self._host_ok():
            return self._json({"error": "Acesso negado."}, 403)
        rota = urlparse(self.path)
        if rota.path == "/":
            return self._arquivo(STATIC / "index.html")
        if rota.path.startswith("/static/"):
            alvo = (STATIC / rota.path[len("/static/"):]).resolve()
            if STATIC.resolve() in alvo.parents and alvo.is_file():
                return self._arquivo(alvo)
        if rota.path == "/thumb":
            return self._miniatura(parse_qs(rota.query))
        if rota.path == "/download":
            alvo = Path(parse_qs(rota.query).get("path", [""])[0]).resolve()
            with _lock:
                permitido = str(alvo) in _saidas
            if permitido and alvo.is_file():
                return self._arquivo(alvo, anexo=True)
        self._json({"error": "Nao encontrado."}, 404)

    def do_POST(self):
        if not self._host_ok():
            return self._json({"error": "Acesso negado."}, 403)
        if self.path == "/api/quit":
            self._json({"ok": True})
            _limpar_sessao()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            for fn in _ao_encerrar:
                threading.Thread(target=fn, daemon=True).start()
            return
        acao = ROTAS.get(self.path)
        if acao is None:
            return self._json({"error": "Nao encontrado."}, 404)
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
            corpo = json.loads(self.rfile.read(tamanho) or b"{}")
            self._json(acao(corpo))
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:  # erro inesperado: nao derruba o servidor
            self._json({"error": f"Erro interno: {exc}"}, 500)

    def _miniatura(self, q: dict):
        try:
            i, pag = int(q.get("id", [""])[0]), int(q.get("p", ["0"])[0])
            larg = min(max(int(q.get("w", ["240"])[0]), 60), 1800)
        except ValueError:
            return self._json({"error": "Pedido invalido."}, 400)
        with _lock:
            pdf = _ids.get(i)
        if pdf is None or not pdf.is_file():
            return self._json({"error": "Nao encontrado."}, 404)
        try:
            img = preview.renderizar(pdf, pag, larg)
        except ValueError as exc:
            return self._json({"error": str(exc)}, 422)
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(img)))
        self.send_header("Cache-Control", "private, max-age=600")
        self.end_headers()
        self.wfile.write(img)

    def _json(self, dados, status: int = 200):
        bruto = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(bruto)))
        self.end_headers()
        self.wfile.write(bruto)

    def _arquivo(self, caminho: Path, anexo: bool = False):
        tipo = mimetypes.guess_type(caminho.name)[0] or "application/octet-stream"
        if tipo.startswith("text/"):
            tipo += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(caminho.stat().st_size))
        if anexo:
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(caminho.name)}")
        self.end_headers()
        with open(caminho, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)

    def log_message(self, *args):
        return


def criar_servidor(porta: int = PORTA_PADRAO) -> ThreadingHTTPServer:
    """Usa a porta pedida ou a proxima livre (ate +20)."""
    for p in range(porta, porta + 21):
        try:
            return ThreadingHTTPServer((HOST, p), Handler)
        except OSError:
            continue
    raise OSError(f"Nenhuma porta livre entre {porta} e {porta + 20}.")


def _abrir_janela(servidor: ThreadingHTTPServer, url: str) -> bool:
    """Abre a interface numa janela propria (pywebview). False se indisponivel."""
    try:
        import webview
    except Exception:
        return False
    janela = webview.create_window("Papelada", url, width=920, height=760, min_size=(560, 520))
    _ao_encerrar.append(janela.destroy)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    webview.start()  # bloqueia ate a janela fechar
    servidor.shutdown()
    return True


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="papelada", description="Juntar, separar e converter PDFs.")
    ap.add_argument("--port", type=int, default=PORTA_PADRAO)
    ap.add_argument("--browser", action="store_true", help="usar o navegador em vez da janela propria")
    ap.add_argument("--no-browser", action="store_true", help="nao abrir nada (so o servidor)")
    ap.add_argument("--version", action="version", version=f"Papelada {__version__}")
    args = ap.parse_args(argv)
    for nome in ("stdout", "stderr"):  # app sem console: bibliotecas que imprimem nao podem quebrar
        if getattr(sys, nome) is None:
            setattr(sys, nome, open(os.devnull, "w"))

    servidor = criar_servidor(args.port)
    url = f"http://{HOST}:{servidor.server_address[1]}"
    print(f"Papelada {__version__} em {url}")
    try:
        if args.no_browser or args.browser or not _abrir_janela(servidor, url):
            if not args.no_browser:
                webbrowser.open(url)
            servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
