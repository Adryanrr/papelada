"""Marca d'agua de texto ou imagem."""

from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image

from . import pdfio, preview

POSICOES = {"centro": 0.5, "superior": 0.15, "inferior": 0.85}


def _imagem_pronta(arq: Path, largura_pt: float, angulo: float, opacidade: float):
    """PNG com transparencia, ja girado (angulo visual + giro da pagina), e tamanho em pontos."""
    try:
        with Image.open(arq) as im:
            im = im.convert("RGBA")
            alvo_w = max(int(largura_pt * 2), 8)
            im = im.resize((alvo_w, max(int(im.height * alvo_w / im.width), 1)))
    except Exception:
        raise ValueError("Não foi possível abrir a imagem da marca d'água.") from None
    alfa = im.getchannel("A").point(lambda v: int(v * opacidade))
    im.putalpha(alfa)
    return im.rotate(angulo, expand=True, resample=Image.BICUBIC)


def marca_dagua(pdf: Path, saida: Path, texto: str = "", imagem: str = "", estilo: str = "diagonal",
                posicao: str = "centro", tamanho: float = 0, opacidade: float = 30, cor: str = "#808080",
                camada: str = "sobre", escala: float = 50, paginas: str = "") -> dict:
    texto = str(texto or "").strip()
    if not texto and not imagem:
        raise ValueError("Informe o texto ou uma imagem para a marca d'água.")
    estilo = pdfio.escolha(estilo, "Estilo", ("diagonal", "horizontal"))
    pos_y = POSICOES[pdfio.escolha(posicao, "Posição", tuple(POSICOES))]
    camada = pdfio.escolha(camada, "Camada", ("sobre", "atras"))
    op = pdfio.decimal(opacidade, "Opacidade", 5, 100, 30) / 100
    tam = pdfio.decimal(tamanho, "Tamanho", 0, 400, 0)
    esc = pdfio.decimal(escala, "Escala", 5, 100, 50) / 100
    rgb = pdfio.cor(cor)
    arq = Path(imagem).expanduser() if imagem else None
    if arq is not None and not arq.is_file():
        raise ValueError("Imagem da marca d'água não encontrada.")
    mu = preview._exigir()
    doc = pdfio.abrir(pdf)
    sel = pdfio.selecionar(paginas, doc.page_count)
    angulo = 45 if estilo == "diagonal" else 0
    for i in sel:
        page = doc[i]
        W, H = page.rect.width, page.rect.height
        cx, cy = W / 2, H * pos_y
        if texto:
            alvo = (math.hypot(W, H) * 0.62) if angulo else W * 0.7
            fonte = tam or max(8.0, min(alvo / max(mu.get_text_length(texto, "helv", 1), 0.01), 200.0))
            pdfio.texto_na_pagina(page, cx, cy, texto, fonte, rgb, angulo, op, camada == "sobre")
        else:
            im = _imagem_pronta(arq, W * esc, (angulo + page.rotation) % 360, op)
            buf = io.BytesIO()
            im.save(buf, "PNG")
            centro = pdfio.ponto_real(page, cx, cy)
            w, h = im.width / 2, im.height / 2
            page.insert_image(mu.Rect(centro.x - w / 2, centro.y - h / 2, centro.x + w / 2, centro.y + h / 2),
                              stream=buf.getvalue(), overlay=camada == "sobre")
    pdfio.salvar(doc, saida)
    return {"info": f"marca d'água em {len(sel)} página(s)"}
