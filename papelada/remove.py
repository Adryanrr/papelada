"""Remover paginas de um PDF."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .common import caminho_livre, nome_seguro, pasta_saida
from .split import parse_intervalos


def remover_paginas(pdf: Path, valor: str, destino: str | None = None) -> dict:
    """Grava uma copia de `pdf` sem as paginas de `valor` (ex.: '2, 5-7')."""
    if pdf.suffix.lower() != ".pdf" or not pdf.is_file():
        raise ValueError("Escolha um arquivo PDF.")
    try:
        reader = PdfReader(str(pdf))
    except Exception:
        raise ValueError("Nao foi possivel ler o PDF (arquivo corrompido?).") from None
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("O PDF esta protegido por senha.")
    total = len(reader.pages)
    fora = {p for ini, fim in parse_intervalos(valor, total) for p in range(ini, fim + 1)}
    if len(fora) >= total:
        raise ValueError("Nao da para remover todas as paginas do PDF.")
    writer = PdfWriter()
    for i in range(1, total + 1):
        if i not in fora:
            writer.add_page(reader.pages[i - 1])
    saida = caminho_livre(pasta_saida(pdf.parent, destino) / f"{nome_seguro(pdf.stem)}_sem-paginas.pdf")
    with open(saida, "wb") as f:
        writer.write(f)
    return {"output": str(saida), "removed": len(fora), "remaining": total - len(fora), "total": total}
