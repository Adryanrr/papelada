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


def _exigir():
    if _mu is None:
        raise ValueError("Recurso indisponivel: instale `pymupdf`.")
    return _mu


def rect(x0: float, y0: float, x1: float, y1: float):
    return _exigir().Rect(x0, y0, x1, y1)


def novo_documento():
    return _exigir().open()


def _eh_imagem(p: Path) -> bool:
    return p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"}


def _miniatura_imagem(arq: Path, largura: int) -> bytes:
    import io

    from PIL import Image, ImageOps
    try:
        with Image.open(arq) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((largura, largura * 4))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=82)
            return buf.getvalue()
    except Exception:
        raise ValueError("Nao foi possivel exibir a imagem.") from None


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
    """Imagem JPEG da pagina `pagina` (0 = primeira) com `largura` px (ou da propria imagem)."""
    if _eh_imagem(pdf):
        return _miniatura_imagem(pdf, largura)
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
