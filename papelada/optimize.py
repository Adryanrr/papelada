"""Comprimir e reparar PDFs."""

from __future__ import annotations

import shutil
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from . import pdfio, preview

# (dpi acima do qual a imagem e reduzida, dpi alvo, qualidade JPEG)
NIVEIS = {"baixa": None, "recomendada": (200, 150, 75), "extrema": (130, 96, 50)}


def _tam(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{max(n // 1024, 1)} KB"


def comprimir(pdf: Path, saida: Path, nivel: str = "recomendada") -> dict:
    """Reduz o tamanho: limpa objetos e, nos niveis maiores, reamostra as imagens."""
    nivel = pdfio.escolha(nivel, "Nível", tuple(NIVEIS))
    antes = pdf.stat().st_size
    doc = pdfio.abrir(pdf)
    if NIVEIS[nivel]:
        limiar, alvo, qualidade = NIVEIS[nivel]
        doc.rewrite_images(dpi_threshold=limiar, dpi_target=alvo, quality=qualidade)
    doc.save(str(saida), garbage=4, clean=True, deflate=True, deflate_images=True, deflate_fonts=True, use_objstms=1)
    doc.close()
    depois = saida.stat().st_size
    if depois >= antes:  # nunca entrega um arquivo maior que o original
        shutil.copyfile(pdf, saida)
        return {"info": f"{_tam(antes)}: já estava otimizado, sem ganho", "antes": antes, "depois": antes}
    return {"info": f"{_tam(antes)} → {_tam(depois)} (−{round(100 * (antes - depois) / antes)}%)",
            "antes": antes, "depois": depois}


def reparar(pdf: Path, saida: Path) -> dict:
    """Reconstroi a estrutura de um PDF danificado e grava uma copia integra."""
    if pdf.suffix.lower() != ".pdf" or not pdf.is_file():
        raise ValueError("Escolha um arquivo PDF.")
    mu = preview._exigir()
    try:
        doc = mu.open(str(pdf))
        if doc.needs_pass:
            raise ValueError("O PDF está protegido por senha. Use Desbloquear primeiro.")
        reparado = bool(doc.is_repaired)
        if doc.page_count == 0:
            raise RuntimeError("sem paginas")
        doc.save(str(saida), garbage=4, clean=True, deflate=True)
        doc.close()
        return {"info": "estrutura reconstruída" if reparado else "o arquivo já estava íntegro (regravado)"}
    except ValueError:
        raise
    except Exception:
        pass
    try:  # segunda tentativa, mais tolerante
        reader = PdfReader(str(pdf), strict=False)
        if not len(reader.pages):
            raise RuntimeError("sem paginas")
        writer = PdfWriter(clone_from=reader)
        with open(saida, "wb") as f:
            writer.write(f)
        return {"info": "recuperado em modo tolerante"}
    except Exception:
        raise ValueError("Não foi possível recuperar este PDF.") from None
