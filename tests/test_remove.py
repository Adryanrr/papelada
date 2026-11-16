import pytest
from pypdf import PdfReader

from conftest import faz_pdf, n_paginas
from papelada import remove


def test_remove_paginas_e_nomeia_saida(tmp_path):
    pdf = faz_pdf(tmp_path / "doc.pdf", 6)
    r = remove.remover_paginas(pdf, "2, 4-5")
    assert (r["removed"], r["remaining"], r["total"]) == (3, 3, 6)
    assert r["output"].endswith("doc_sem-paginas.pdf") and n_paginas(r["output"]) == 3


def test_mantem_as_paginas_certas(tmp_path):
    from pypdf import PdfWriter
    w = PdfWriter()
    for largura in (100, 200, 300):
        w.add_blank_page(width=largura, height=50)
    pdf = tmp_path / "x.pdf"
    with open(pdf, "wb") as f:
        w.write(f)
    r = remove.remover_paginas(pdf, "2")
    assert [float(p.mediabox.width) for p in PdfReader(r["output"]).pages] == [100.0, 300.0]


@pytest.mark.parametrize("valor", ["", "0", "9", "abc", "3-1"])
def test_valores_invalidos(tmp_path, valor):
    pdf = faz_pdf(tmp_path / "d.pdf", 3)
    with pytest.raises(ValueError):
        remove.remover_paginas(pdf, valor)


def test_nao_deixa_remover_tudo(tmp_path):
    pdf = faz_pdf(tmp_path / "d.pdf", 2)
    with pytest.raises(ValueError, match="todas"):
        remove.remover_paginas(pdf, "1-2")


def test_arquivo_invalido(tmp_path):
    (tmp_path / "x.txt").write_text("x")
    with pytest.raises(ValueError):
        remove.remover_paginas(tmp_path / "x.txt", "1")
    ruim = tmp_path / "r.pdf"
    ruim.write_bytes(b"nao e pdf")
    with pytest.raises(ValueError, match="corrompido"):
        remove.remover_paginas(ruim, "1")
