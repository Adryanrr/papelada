"""Ferramentas que mexem nas paginas: girar, organizar, recortar e numerar."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops

from . import pdfio, preview

POSICOES = ("inferior-centro", "inferior-direita", "inferior-esquerda",
            "superior-centro", "superior-direita", "superior-esquerda")
FORMATOS = ("{n}", "Página {n}", "Página {n} de {total}", "{n}/{total}", "- {n} -")
MM = 72 / 25.4


def girar(pdf: Path, saida: Path, graus: int = 90, paginas: str = "") -> dict:
    graus = int(pdfio.escolha(int(graus) if str(graus).lstrip("-").isdigit() else -1, "Giro", (90, 180, 270)))
    doc = pdfio.abrir(pdf)
    sel = pdfio.selecionar(paginas, doc.page_count)
    for i in sel:
        doc[i].set_rotation((doc[i].rotation + graus) % 360)
    pdfio.salvar(doc, saida)
    return {"info": f"{len(sel)} página(s) girada(s) em {graus}°"}


def organizar(pdf: Path, saida: Path, pages: list | None = None) -> dict:
    """`pages`: lista na ordem final, cada item {'p': indice 0-based, 'rot': graus a somar}."""
    if not pages or not isinstance(pages, list):
        raise ValueError("Nenhuma página selecionada.")
    doc = pdfio.abrir(pdf)
    total = doc.page_count
    ordem, giros = [], {}
    for item in pages:
        try:
            p, rot = int(item["p"]), int(item.get("rot", 0)) % 360
        except (KeyError, TypeError, ValueError):
            raise ValueError("Lista de páginas inválida.") from None
        if not 0 <= p < total or rot % 90:
            raise ValueError("Lista de páginas inválida.")
        ordem.append(p)
        giros[p] = rot
    if len(set(ordem)) != len(ordem):
        raise ValueError("Páginas repetidas não são suportadas.")
    for p, rot in giros.items():
        if rot:
            doc[p].set_rotation((doc[p].rotation + rot) % 360)
    doc.select(ordem)
    pdfio.salvar(doc, saida)
    return {"info": f"{len(ordem)} de {total} página(s) mantida(s)"}


def _caixa_conteudo(page, folga_pt: float):
    """Retangulo (na visao do usuario) que envolve o que nao e branco, ou None se a pagina e vazia."""
    pix = page.get_pixmap(dpi=50, alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    caixa = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).convert("L").point(
        lambda v: 255 if v > 12 else 0).getbbox()
    if not caixa:
        return None
    esc_x, esc_y = page.rect.width / pix.width, page.rect.height / pix.height
    mu = preview._exigir()
    r = mu.Rect(caixa[0] * esc_x - folga_pt, caixa[1] * esc_y - folga_pt,
                caixa[2] * esc_x + folga_pt, caixa[3] * esc_y + folga_pt)
    return r & page.rect


def recortar(pdf: Path, saida: Path, modo: str = "auto", folga: float = 5, cima: float = 0, direita: float = 0,
             baixo: float = 0, esquerda: float = 0, paginas: str = "") -> dict:
    """Recorta paginas: 'auto' tira as bordas em branco; 'margens' tira os mm informados de cada lado."""
    modo = pdfio.escolha(modo, "Modo", ("auto", "margens"))
    folga = pdfio.decimal(folga, "Folga", 0, 50, 5) * MM
    lados = [pdfio.decimal(v, n, 0, 500, 0) * MM for v, n in
             ((cima, "Cima"), (direita, "Direita"), (baixo, "Baixo"), (esquerda, "Esquerda"))]
    if modo == "margens" and not any(lados):
        raise ValueError("Informe pelo menos uma margem para cortar.")
    mu = preview._exigir()
    doc = pdfio.abrir(pdf)
    feitas = 0
    for i in pdfio.selecionar(paginas, doc.page_count):
        page = doc[i]
        W, H = page.rect.width, page.rect.height
        if modo == "auto":
            visual = _caixa_conteudo(page, folga)
        else:
            visual = mu.Rect(lados[3], lados[0], W - lados[1], H - lados[2])
        if not visual or visual.width < 10 or visual.height < 10:
            continue
        real = (visual * page.derotation_matrix).normalize()
        page.set_cropbox(mu.Rect(real.x0 + page.cropbox.x0, real.y0 + page.cropbox.y0,
                                 real.x1 + page.cropbox.x0, real.y1 + page.cropbox.y0))
        feitas += 1
    if not feitas:
        raise ValueError("Nada para recortar com essas opções.")
    pdfio.salvar(doc, saida)
    return {"info": f"{feitas} página(s) recortada(s)"}


def numerar(pdf: Path, saida: Path, posicao: str = "inferior-centro", formato: str = "{n}", inicio: int = 1,
            de: int = 1, tamanho: float = 10, margem: float = 8, cor: str = "#000000") -> dict:
    posicao = pdfio.escolha(posicao, "Posição", POSICOES)
    formato = pdfio.escolha(formato, "Formato", FORMATOS)
    inicio = pdfio.inteiro(inicio, "Número inicial", 0, 99999, 1)
    de = pdfio.inteiro(de, "Começar na página", 1, 99999, 1)
    tamanho = pdfio.decimal(tamanho, "Tamanho", 6, 72, 10)
    margem_pt = pdfio.decimal(margem, "Margem", 2, 100, 8) * MM
    rgb = pdfio.cor(cor)
    doc = pdfio.abrir(pdf)
    total = doc.page_count
    if de > total:
        raise ValueError(f"O PDF tem só {total} página(s).")
    vert, horiz = posicao.split("-")
    mu = preview._exigir()
    for i in range(de - 1, total):
        page = doc[i]
        n = inicio + (i - (de - 1))
        texto = formato.replace("{n}", str(n)).replace("{total}", str(inicio + total - de))
        largura = mu.get_text_length(texto, "helv", tamanho)
        W, H = page.rect.width, page.rect.height
        x = {"esquerda": margem_pt + largura / 2, "centro": W / 2, "direita": W - margem_pt - largura / 2}[horiz]
        y = H - margem_pt - tamanho * 0.35 if vert == "inferior" else margem_pt + tamanho * 0.65
        pdfio.texto_na_pagina(page, x, y, texto, tamanho, rgb)
    pdfio.salvar(doc, saida)
    return {"info": f"{total - de + 1} página(s) numerada(s)"}
