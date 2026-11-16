"""Aplica uma operacao a um PDF, ou a todos os PDFs de uma pasta."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .common import PASTA_SAIDA_NOME, caminho_livre, nome_seguro, pasta_saida


def alvos_pdf(alvo: Path) -> tuple[list[Path], Path]:
    """PDFs a processar e a pasta-base da saida."""
    if alvo.is_dir():
        pdfs = sorted((p for p in alvo.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
                       and not p.name.startswith(".")), key=lambda p: p.name.lower())
        if not pdfs:
            raise ValueError("Nenhum PDF encontrado na pasta.")
        return pdfs, alvo
    if alvo.suffix.lower() == ".pdf" and alvo.is_file():
        return [alvo], alvo.parent
    raise ValueError("Escolha um PDF ou uma pasta com PDFs.")


def aplicar(alvo: Path, destino: str | None, fn: Callable[..., dict | None], sufixo: str, ext: str | None = ".pdf",
            so_arquivo: bool = False, **opcoes) -> dict:
    """Roda `fn(pdf, saida, **opcoes)` em cada PDF. `ext=None` significa que a saida e uma pasta."""
    pdfs, base = alvos_pdf(alvo)
    if so_arquivo and len(pdfs) != 1:
        raise ValueError("Esta ferramenta trabalha com um PDF por vez.")
    saida_dir = pasta_saida(base, destino)
    resultados = []
    for pdf in pdfs:
        nome = nome_seguro(pdf.stem)
        if ext is None:
            saida = saida_dir / f"{nome}{sufixo}"
            n = 2
            while saida.exists():
                saida = saida_dir / f"{nome}{sufixo} ({n})"
                n += 1
            saida.mkdir()
        else:
            saida = caminho_livre(saida_dir / f"{nome}{sufixo}{ext}")
        try:
            extra = fn(pdf, saida, **opcoes) or {}
            resultados.append({"nome": pdf.name, "status": "ok", "output": str(saida), **extra})
        except ValueError as exc:
            _limpar(saida)
            resultados.append({"nome": pdf.name, "status": "erro", "output": None, "erro": str(exc)})
        except Exception as exc:
            _limpar(saida)
            resultados.append({"nome": pdf.name, "status": "erro", "output": None, "erro": f"Erro inesperado: {exc}"})
    ok = sum(r["status"] == "ok" for r in resultados)
    if ok == 0 and len(resultados) == 1:
        raise ValueError(resultados[0]["erro"])  # um arquivo so: erro direto, sem tabela de resultados
    return {"output": str(saida_dir), "total": len(resultados), "ok": ok, "resultados": resultados}


def _limpar(saida: Path) -> None:
    try:
        if saida.is_dir():
            import shutil
            shutil.rmtree(saida, ignore_errors=True)
        elif saida.exists():
            saida.unlink()
    except OSError:
        pass


__all__ = ["alvos_pdf", "aplicar", "PASTA_SAIDA_NOME"]
