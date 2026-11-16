"""Miniaturas e paginas de PDF como imagem (PyMuPDF)."""

from __future__ import annotations

from pathlib import Path

try:
    import pymupdf as _mu
except ImportError:  # versoes antigas do PyMuPDF
    try:
        import fitz as _mu
    except ImportError:
        _mu = None


def disponivel() -> bool:
    return _mu is not None


def paginas(pdf: Path) -> int:
    """Numero de paginas; ValueError se nao for um PDF legivel e sem senha."""
    if _mu is None:
        raise ValueError("Visualizacao indisponivel: instale `pymupdf`.")
    try:
        with _mu.open(str(pdf)) as doc:
            if doc.needs_pass:
                raise ValueError("O PDF esta protegido por senha.")
            return doc.page_count
    except ValueError:
        raise
    except Exception:
        raise ValueError("Nao foi possivel ler o PDF.") from None


def renderizar(pdf: Path, pagina: int, largura: int) -> bytes:
    """Imagem JPEG da pagina `pagina` (0 = primeira) com `largura` px."""
    if _mu is None:
        raise ValueError("Visualizacao indisponivel: instale `pymupdf`.")
    try:
        with _mu.open(str(pdf)) as doc:
            if doc.needs_pass:
                raise ValueError("O PDF esta protegido por senha.")
            if not 0 <= pagina < doc.page_count:
                raise ValueError("Pagina inexistente.")
            pg = doc[pagina]
            zoom = largura / max(pg.rect.width, 1)
            pix = pg.get_pixmap(matrix=_mu.Matrix(zoom, zoom), alpha=False)
            return pix.tobytes("jpeg", jpg_quality=82)
    except ValueError:
        raise
    except Exception:
        raise ValueError("Nao foi possivel exibir a pagina.") from None
