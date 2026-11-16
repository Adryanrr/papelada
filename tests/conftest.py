import pytest
from pypdf import PdfReader, PdfWriter

TEXTO_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 52>>stream
BT /F1 18 Tf 72 700 Td (Ola Papelada) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
trailer<</Root 1 0 R/Size 6>>
%%EOF
"""


def faz_pdf(caminho, paginas=1):
    w = PdfWriter()
    for _ in range(paginas):
        w.add_blank_page(width=200, height=200)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "wb") as f:
        w.write(f)
    return caminho


def n_paginas(caminho):
    return len(PdfReader(str(caminho)).pages)


@pytest.fixture
def pdf():
    return faz_pdf
