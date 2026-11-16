"""Juntar documentos: uma pasta vira um PDF; um lote de subpastas vira um PDF por subpasta."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .archive import eh_compactado, extrair
from .common import PASTA_SAIDA_NOME, caminho_livre, nome_seguro, normalizar_texto, pasta_saida

try:
    from PIL import Image
except ImportError:  # Pillow e opcional: sem ele, imagens sao ignoradas com aviso
    Image = None

EXT_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"}
EXT_SILENCIOSAS = {"", ".ds_store", ".db", ".ini", ".thumbs"}
PROFUNDIDADE_MAX = 6


def chave_nome(nome: str) -> tuple:
    """Ordem natural: numeracao inicial antes dos nomes sem numero.

    "2 - A" vem antes de "10 - B"; "7.1.2" antes de "7.1.10"; "8.1.c" respeita a letra.
    """
    base = Path(nome).stem
    m = re.match(r"^\s*(\d+(?:\.\d+)*)(?:\.([a-zA-Z]))?(?:[\s\-_.]+)?(.*)$", base)
    if m:
        numeros = tuple(int(p) for p in m.group(1).split("."))
        return (0, numeros, (m.group(2) or "").lower(), normalizar_texto(m.group(3)))
    return (1, (), "", normalizar_texto(base))


def chave_partes(partes: tuple) -> tuple:
    """Chave de ordenacao de um arquivo a partir das partes do seu caminho relativo."""
    chaves = [chave_nome(p) for p in partes]
    numeracao = tuple((c[1], c[2]) for c in chaves if c[0] == 0)
    nome = chaves[-1][3]
    if numeracao:
        return (0, numeracao, tuple(nome.split()[:5]), nome, tuple(chaves))
    return (1, tuple(chaves))


def _imagem_para_pdf(imagem: Path, destino: Path) -> bool:
    if Image is None:
        return False
    try:
        Image.open(imagem).convert("RGB").save(destino, "PDF", resolution=150)
        return True
    except Exception:
        return False


def coletar(pasta: Path, tmp: Path, partes: tuple = (), nivel: int = 0) -> tuple[list, list]:
    """Percorre a pasta e devolve ([(partes_do_caminho, pdf)], avisos).

    Extrai arquivos compactados e converte imagens em PDF (em `tmp`).
    """
    if nivel > PROFUNDIDADE_MAX:
        return [], ["Profundidade maxima de extracao atingida"]
    achados: list = []
    avisos: list = []
    try:
        itens = sorted(pasta.iterdir(), key=lambda p: p.name.lower())
    except PermissionError:
        return [], [f"Sem permissao: {pasta}"]

    for item in itens:
        if item.name.startswith(".") or item.name == PASTA_SAIDA_NOME:
            continue
        atual = partes + (item.name,)
        ext = item.suffix.lower()
        if item.is_dir():
            sub, av = coletar(item, tmp, atual, nivel + 1)
        elif ext == ".pdf":
            achados.append((atual, item))
            continue
        elif eh_compactado(item):
            dest = tmp / f"ext_{len(list(tmp.iterdir()))}"
            try:
                extrair(item, dest)
            except ValueError as exc:
                avisos.append(str(exc))
                continue
            sub, av = coletar(dest, tmp, atual, nivel + 1)
        elif ext in EXT_IMAGEM:
            destino = tmp / f"img_{len(list(tmp.iterdir()))}.pdf"
            if _imagem_para_pdf(item, destino):
                achados.append((atual, destino))
            else:
                avisos.append(f"Imagem ignorada: {item.name}" + ("" if Image else " (instale o Pillow)"))
            continue
        else:
            if ext not in EXT_SILENCIOSAS:
                avisos.append(f"Ignorado ({ext}): {item.name}")
            continue
        achados.extend(sub)
        avisos.extend(av)
    return achados, avisos


def coletar_alvo(alvo: Path, tmp: Path) -> tuple[list, list]:
    """Coleta de uma pasta ou de um unico arquivo compactado (zip, rar, 7z...)."""
    if alvo.is_file():
        if not eh_compactado(alvo):
            raise ValueError("Escolha uma pasta ou um arquivo compactado (.zip, .rar, .7z...).")
        dest = tmp / "alvo"
        extrair(alvo, dest)
        return coletar(dest, tmp, (alvo.name,))
    return coletar(alvo, tmp)


def _paginas(pdf: Path) -> int | None:
    try:
        return len(PdfReader(str(pdf)).pages)
    except Exception:
        return None


def aplicar_ordem(achados: list, ordem: list[str]) -> tuple[list, list[str]]:
    """Reordena/filtra `achados` pela lista `ordem` (nomes como em `listar_ordem`).

    Quem nao esta em `ordem` fica de fora; nomes desconhecidos viram aviso.
    """
    por_nome = {"/".join(partes): (partes, pdf) for partes, pdf in achados}
    escolhidos, avisos, vistos = [], [], set()
    for nome in ordem:
        if nome in vistos:
            continue
        vistos.add(nome)
        if nome in por_nome:
            escolhidos.append(por_nome[nome])
        else:
            avisos.append(f"Arquivo nao encontrado, ignorado: {nome}")
    return escolhidos, avisos


def listar_ordem(pasta: Path, tmp: Path | None = None) -> dict:
    """Pre-visualiza a ordem em que os arquivos serao juntados.

    Com `tmp`, os arquivos extraidos/convertidos ficam la (quem chama limpa) e cada item traz
    `path`, o arquivo real, para gerar miniaturas.
    """
    if tmp is None:
        with tempfile.TemporaryDirectory() as t:
            r = listar_ordem(pasta, Path(t))
        for item in r["items"]:
            item.pop("path", None)
        return r
    achados, avisos = coletar_alvo(pasta, tmp)
    achados.sort(key=lambda a: chave_partes(a[0]))
    itens = [{"name": "/".join(partes), "pages": _paginas(pdf), "path": str(pdf)} for partes, pdf in achados]
    return {"path": str(pasta), "count": len(itens), "files": [i["name"] for i in itens],
            "items": itens, "pages": sum(i["pages"] or 0 for i in itens), "avisos": avisos}


def juntar_pdfs(pdfs: list[Path], saida: Path) -> tuple[int, list[str]]:
    """Junta PDFs em `saida`. Retorna (paginas, avisos); PDFs ilegiveis viram aviso."""
    writer = PdfWriter()
    paginas = 0
    avisos: list[str] = []
    for pdf in pdfs:
        try:
            reader = PdfReader(str(pdf))
            if reader.is_encrypted and not reader.decrypt(""):
                raise ValueError("protegido por senha")
            for pagina in reader.pages:
                writer.add_page(pagina)
            paginas += len(reader.pages)
        except Exception as exc:
            avisos.append(f"Pulado {pdf.name}: {exc}")
    saida.parent.mkdir(parents=True, exist_ok=True)
    with open(saida, "wb") as f:
        writer.write(f)
    return paginas, avisos


def juntar_pasta(pasta: Path, nome: str = "", destino: str | None = None,
                 ordem: list[str] | None = None) -> dict:
    """Junta todos os documentos de uma pasta, ou de um arquivo compactado, em um unico PDF."""
    with tempfile.TemporaryDirectory() as t:
        achados, avisos = coletar_alvo(pasta, Path(t))
        if not achados:
            raise ValueError("Nenhum PDF (ou imagem) encontrado.")
        achados.sort(key=lambda a: chave_partes(a[0]))
        if ordem is not None:
            achados, av_ordem = aplicar_ordem(achados, ordem)
            avisos = avisos + av_ordem
            if not achados:
                raise ValueError("Nenhum arquivo selecionado para juntar.")
        saida = caminho_livre(pasta_saida(pasta.parent, destino) / f"{nome_seguro(nome or (pasta.stem if pasta.is_file() else pasta.name))}.pdf")
        paginas, av = juntar_pdfs([p for _, p in achados], saida)
    return {"output": str(saida), "count": len(achados), "pages": paginas, "avisos": avisos + av}


def juntar_lote(pasta: Path, destino: str | None = None) -> dict:
    """Cada subpasta (ou arquivo compactado solto) vira um PDF: ideal para muitas pastas de uma vez."""
    saida_dir = pasta_saida(pasta, destino)
    subpastas = [s for s in sorted(pasta.iterdir(), key=lambda p: p.name.lower())
                 if not s.name.startswith(".") and s.name != PASTA_SAIDA_NOME
                 and (s.is_dir() or (s.is_file() and eh_compactado(s)))]
    resultados = []
    for sub in subpastas:
        try:
            r = juntar_pasta(sub, destino=str(saida_dir))
            resultados.append({"nome": sub.name, "status": "ok", **r})
        except ValueError as exc:
            resultados.append({"nome": sub.name, "status": "vazio", "count": 0, "pages": 0,
                               "output": None, "avisos": [str(exc)]})
        except Exception as exc:
            resultados.append({"nome": sub.name, "status": "erro", "count": 0, "pages": 0,
                               "output": None, "avisos": [str(exc)]})
    return {"path": str(pasta), "output": str(saida_dir), "total": len(resultados),
            "ok": sum(r["status"] == "ok" for r in resultados), "resultados": resultados}
