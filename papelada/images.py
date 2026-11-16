"""Imagens (JPG, PNG, ...) para PDF, com tamanho de pagina, orientacao e margem."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from . import preview
from .archive import eh_compactado, extrair
from .common import PASTA_SAIDA_NOME, caminho_livre, nome_seguro, pasta_saida
from .merge import chave_partes

EXT_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"}
TAMANHOS = {"a4": (595.28, 841.89), "carta": (612.0, 792.0)}
MARGENS = {"nenhuma": 0.0, "pequena": 18.0, "grande": 36.0}
LADO_MAX = 1000.0  # no modo "da imagem", a pagina nao passa disso (pontos) no maior lado


def eh_imagem(p: Path) -> bool:
    return p.suffix.lower() in EXT_IMAGEM


def coletar_imagens(alvo: Path, tmp: Path, partes: tuple = (), nivel: int = 0) -> tuple[list, list]:
    """Devolve ([(partes, arquivo)], avisos) com todas as imagens de uma pasta, .zip/.rar... ou imagem."""
    if nivel > 6:
        return [], ["Profundidade maxima de extracao atingida"]
    if alvo.is_file():
        if eh_imagem(alvo):
            return [((alvo.name,), alvo)], []
        if eh_compactado(alvo):
            dest = tmp / f"ext_{len(list(tmp.iterdir()))}"
            extrair(alvo, dest)
            return coletar_imagens(dest, tmp, (alvo.name,), nivel + 1)
        raise ValueError("Escolha uma pasta, um arquivo compactado ou uma imagem.")
    achados: list = []
    avisos: list = []
    for item in sorted(alvo.iterdir(), key=lambda p: p.name.lower()):
        if item.name.startswith(".") or item.name == PASTA_SAIDA_NOME:
            continue
        atual = partes + (item.name,)
        if item.is_dir() or eh_compactado(item):
            try:
                if item.is_dir():
                    sub, av = coletar_imagens(item, tmp, atual, nivel + 1)
                else:
                    dest = tmp / f"ext_{len(list(tmp.iterdir()))}"
                    extrair(item, dest)
                    sub, av = coletar_imagens(dest, tmp, atual, nivel + 1)
            except ValueError as exc:
                avisos.append(str(exc))
                continue
            achados += sub
            avisos += av
        elif eh_imagem(item):
            achados.append((atual, item))
    return achados, avisos


def _ordenadas(alvo: Path, tmp: Path) -> tuple[list, list]:
    achados, avisos = coletar_imagens(alvo, tmp)
    achados.sort(key=lambda a: chave_partes(a[0]))
    return achados, avisos


def listar(alvo: Path, tmp: Path | None = None) -> dict:
    """Imagens na ordem em que virariam paginas. Com `tmp`, cada item traz `path` (arquivo real)."""
    if tmp is None:
        with tempfile.TemporaryDirectory() as t:
            r = listar(alvo, Path(t))
        for i in r["items"]:
            i.pop("path", None)
        return r
    achados, avisos = _ordenadas(alvo, tmp)
    itens = []
    for partes, arq in achados:
        try:
            with Image.open(arq) as im:
                tam = list(ImageOps.exif_transpose(im).size)
        except Exception:
            tam = None
        itens.append({"name": "/".join(partes), "pages": 1, "size": tam, "path": str(arq)})
    return {"path": str(alvo), "count": len(itens), "items": itens, "pages": len(itens), "avisos": avisos}


def _carregar(arq: Path) -> tuple[bytes, int, int, float]:
    """Bytes prontos para inserir (JPEG/PNG), largura, altura em px e dpi."""
    with Image.open(arq) as im:
        dpi = im.info.get("dpi", (96, 96))[0] or 96
        dpi = dpi if dpi >= 36 else 96
        orient = im.getexif().get(0x0112, 1)
        if im.format == "JPEG" and orient in (None, 1) and im.mode in ("RGB", "L"):
            return arq.read_bytes(), im.width, im.height, float(dpi)  # sem recomprimir
        im = ImageOps.exif_transpose(im)
        grafico = im.mode in ("P", "LA", "PA") or "transparency" in im.info or im.mode == "RGBA"
        if im.mode in ("RGBA", "LA", "PA", "P"):
            rgba = im.convert("RGBA")
            fundo = Image.new("RGB", rgba.size, "white")
            fundo.paste(rgba, mask=rgba.split()[3])
            im = fundo
        else:
            im = im.convert("RGB")
        buf = io.BytesIO()
        if grafico:
            im.save(buf, "PNG")
        else:
            im.save(buf, "JPEG", quality=92)
        return buf.getvalue(), im.width, im.height, float(dpi)


def _pagina(doc, dados: bytes, w: int, h: int, dpi: float, tamanho: str, orientacao: str, margem: float):
    if tamanho == "imagem":
        pw, ph = w * 72 / dpi, h * 72 / dpi
        esc = min(1.0, LADO_MAX / max(pw, ph))
        pw, ph = pw * esc, ph * esc
        pg = doc.new_page(width=pw + 2 * margem, height=ph + 2 * margem)
        rect = preview.rect(margem, margem, margem + pw, margem + ph)
    else:
        a, b = TAMANHOS[tamanho]
        paisagem = (w > h) if orientacao == "auto" else orientacao == "paisagem"
        largura, altura = (b, a) if paisagem else (a, b)
        pg = doc.new_page(width=largura, height=altura)
        area_w, area_h = largura - 2 * margem, altura - 2 * margem
        esc = min(area_w / w, area_h / h)
        iw, ih = w * esc, h * esc
        x0, y0 = margem + (area_w - iw) / 2, margem + (area_h - ih) / 2
        rect = preview.rect(x0, y0, x0 + iw, y0 + ih)
    pg.insert_image(rect, stream=dados)


def _gerar(arquivos: list[Path], saida: Path, tamanho: str, orientacao: str, margem: float) -> tuple[int, list[str]]:
    doc = preview.novo_documento()
    avisos: list[str] = []
    for arq in arquivos:
        try:
            dados, w, h, dpi = _carregar(arq)
            _pagina(doc, dados, w, h, dpi, tamanho, orientacao, margem)
        except Exception as exc:
            avisos.append(f"Pulada {arq.name}: {exc}")
    paginas = doc.page_count
    if paginas:
        doc.save(str(saida), garbage=3, deflate=True)
    doc.close()
    return paginas, avisos


def imagens_para_pdf(alvo: Path, nome: str = "", destino: str | None = None, ordem: list[str] | None = None,
                     tamanho: str = "imagem", orientacao: str = "auto", margem: str = "nenhuma",
                     modo: str = "unico") -> dict:
    """Converte imagens em PDF. modo: 'unico' (um PDF com todas) ou 'cada' (um PDF por imagem)."""
    if tamanho not in ("imagem", *TAMANHOS):
        raise ValueError("Tamanho de pagina invalido.")
    if orientacao not in ("auto", "retrato", "paisagem") or margem not in MARGENS or modo not in ("unico", "cada"):
        raise ValueError("Opcao invalida.")
    with tempfile.TemporaryDirectory() as t:
        achados, avisos = _ordenadas(alvo, Path(t))
        if ordem is not None:
            por_nome = {"/".join(p): (p, a) for p, a in achados}
            achados = [por_nome[n] for n in dict.fromkeys(ordem) if n in por_nome]
        if not achados:
            raise ValueError("Nenhuma imagem encontrada." if ordem is None else "Nenhuma imagem selecionada.")
        saida_dir = pasta_saida(alvo.parent, destino)
        m = MARGENS[margem]
        if modo == "unico":
            base = nome or (alvo.stem if alvo.is_file() else alvo.name)
            saida = caminho_livre(saida_dir / f"{nome_seguro(base)}.pdf")
            paginas, av = _gerar([a for _, a in achados], saida, tamanho, orientacao, m)
            if not paginas:
                raise ValueError("Nenhuma imagem pode ser convertida.")
            return {"outputs": [str(saida)], "output": str(saida), "count": paginas, "pages": paginas,
                    "avisos": avisos + av}
        saidas, extra = [], []
        for partes, arq in achados:
            destino_pdf = caminho_livre(saida_dir / f"{nome_seguro(Path(partes[-1]).stem)}.pdf")
            n, av = _gerar([arq], destino_pdf, tamanho, orientacao, m)
            extra += av
            if n:
                saidas.append(str(destino_pdf))
        if not saidas:
            raise ValueError("Nenhuma imagem pode ser convertida.")
        return {"outputs": saidas, "output": str(saida_dir), "count": len(saidas), "pages": len(saidas),
                "avisos": avisos + extra}
