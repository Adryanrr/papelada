"""Converter PDF em Word (.docx)."""

from __future__ import annotations

from pathlib import Path

from .common import caminho_livre, nome_seguro, pasta_saida


def pdf_para_word(alvo: Path, destino: str | None = None) -> dict:
    """Converte um PDF, ou todos os PDFs de uma pasta, em .docx.

    Funciona com PDFs que tem texto selecionavel. PDFs escaneados (so imagem) precisam de OCR antes.
    """
    try:
        from pdf2docx import Converter
    except ImportError:
        raise ValueError("Conversao para Word indisponivel: instale com `pip install pdf2docx`.") from None

    if alvo.is_dir():
        pdfs = sorted(p for p in alvo.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
        base = alvo
    elif alvo.suffix.lower() == ".pdf" and alvo.is_file():
        pdfs, base = [alvo], alvo.parent
    else:
        raise ValueError("Escolha um PDF ou uma pasta com PDFs.")
    if not pdfs:
        raise ValueError("Nenhum PDF encontrado.")

    saida = pasta_saida(base, destino)
    resultados = []
    for pdf in pdfs:
        docx = caminho_livre(saida / f"{nome_seguro(pdf.stem)}.docx")
        try:
            conv = Converter(str(pdf))
            try:
                conv.convert(str(docx))
            finally:
                conv.close()
            resultados.append({"nome": pdf.name, "status": "ok", "output": str(docx)})
        except Exception as exc:
            resultados.append({"nome": pdf.name, "status": "erro", "output": None, "erro": str(exc)})
    return {"output": str(saida), "total": len(pdfs),
            "ok": sum(r["status"] == "ok" for r in resultados), "resultados": resultados}
