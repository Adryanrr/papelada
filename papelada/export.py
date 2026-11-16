"""Exportar PDF para imagens (JPG/PNG) e Markdown."""

from __future__ import annotations

from pathlib import Path

from . import pdfio


def pdf_para_jpg(pdf: Path, saida: Path, modo: str = "paginas", formato: str = "jpg", dpi: int = 150,
                 paginas: str = "") -> dict:
    """`saida` e uma pasta. 'paginas': renderiza cada pagina; 'imagens': extrai as imagens embutidas."""
    modo = pdfio.escolha(modo, "Modo", ("paginas", "imagens"))
    formato = pdfio.escolha(formato, "Formato", ("jpg", "png"))
    dpi = pdfio.inteiro(dpi, "Resolução", 36, 600, 150)
    doc = pdfio.abrir(pdf)
    sel = pdfio.selecionar(paginas, doc.page_count)
    largura = len(str(doc.page_count))
    nome = saida.name.rsplit("_imagens", 1)[0]
    arquivos: list[str] = []
    if modo == "paginas":
        for i in sel:
            alvo = saida / f"{nome}_p{i + 1:0{largura}d}.{formato}"
            pix = doc[i].get_pixmap(dpi=dpi, alpha=False)
            pix.save(str(alvo), jpg_quality=90) if formato == "jpg" else pix.save(str(alvo))
            arquivos.append(str(alvo))
    else:
        vistos: set[int] = set()
        for i in sel:
            for k, info in enumerate(doc[i].get_images(full=True), 1):
                xref = info[0]
                if xref in vistos:
                    continue
                vistos.add(xref)
                try:
                    img = doc.extract_image(xref)
                except Exception:
                    continue
                if not img or min(img.get("width", 0), img.get("height", 0)) < 16:
                    continue  # ignora enfeites minusculos
                alvo = saida / f"{nome}_p{i + 1:0{largura}d}_img{k}.{img['ext']}"
                alvo.write_bytes(img["image"])
                arquivos.append(str(alvo))
    doc.close()
    if not arquivos:
        raise ValueError("Nenhuma imagem encontrada neste PDF." if modo == "imagens" else "Nenhuma página para converter.")
    return {"info": f"{len(arquivos)} {'imagem(ns) extraída(s)' if modo == 'imagens' else 'página(s) convertida(s)'}",
            "arquivos": len(arquivos)}


def pdf_para_markdown(pdf: Path, saida: Path, paginas: str = "") -> dict:
    """Texto do PDF em Markdown (titulos, listas, tabelas simples). PDFs so de imagem saem vazios."""
    try:
        import pymupdf4llm
    except ImportError:
        raise ValueError("Conversão para Markdown indisponível: instale `pymupdf4llm`.") from None
    doc = pdfio.abrir(pdf)
    sel = pdfio.selecionar(paginas, doc.page_count)
    try:
        texto = pymupdf4llm.to_markdown(doc, pages=sel)
    except Exception as exc:
        raise ValueError(f"Não foi possível converter: {exc}") from None
    finally:
        doc.close()
    if not texto.strip():
        raise ValueError("Não há texto neste PDF (é só imagem). É preciso OCR.")
    saida.write_text(texto, encoding="utf-8")
    return {"info": f"{len(sel)} página(s), {len(texto.split())} palavra(s)"}
