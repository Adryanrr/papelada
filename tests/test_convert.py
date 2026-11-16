import pytest

pytest.importorskip("pdf2docx")

from conftest import TEXTO_PDF
from papelada import convert


def test_pdf_com_texto_vira_docx(tmp_path):
    pdf = tmp_path / "t.pdf"
    pdf.write_bytes(TEXTO_PDF)
    r = convert.pdf_para_word(pdf)
    assert r["ok"] == 1
    from docx import Document
    texto = " ".join(p.text for p in Document(r["resultados"][0]["output"]).paragraphs)
    assert "Papelada" in texto


def test_pasta_sem_pdf_da_erro(tmp_path):
    with pytest.raises(ValueError):
        convert.pdf_para_word(tmp_path)
