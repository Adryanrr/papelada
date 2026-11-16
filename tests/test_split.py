import pytest

from conftest import faz_pdf, n_paginas
from papelada import split


def test_parse_intervalos():
    assert split.parse_intervalos("1-3, 5, 8-", 10) == [(1, 3), (5, 5), (8, 10)]


@pytest.mark.parametrize("texto", ["0", "3-1", "11", "abc", ""])
def test_parse_intervalos_invalidos(texto):
    with pytest.raises(ValueError):
        split.parse_intervalos(texto, 10)


def test_cada_pagina(tmp_path):
    p = faz_pdf(tmp_path / "doc.pdf", 3)
    r = split.separar(p, "cada")
    assert len(r["files"]) == 3 and all(n_paginas(f) == 1 for f in r["files"])


def test_intervalos_e_blocos_e_extrair(tmp_path):
    p = faz_pdf(tmp_path / "doc.pdf", 10)
    assert [n_paginas(f) for f in split.separar(p, "intervalos", "1-3, 5")["files"]] == [3, 1]
    assert [n_paginas(f) for f in split.separar(p, "blocos", "4")["files"]] == [4, 4, 2]
    assert [n_paginas(f) for f in split.separar(p, "extrair", "1-2, 9-10")["files"]] == [4]


def test_rejeita_nao_pdf_e_modo_invalido(tmp_path):
    p = faz_pdf(tmp_path / "doc.pdf", 2)
    with pytest.raises(ValueError):
        split.separar(tmp_path / "nada.txt", "cada")
    with pytest.raises(ValueError):
        split.separar(p, "xyz")
    with pytest.raises(ValueError):
        split.separar(p, "blocos", "0")


def test_pdf_corrompido_da_erro_claro(tmp_path):
    ruim = tmp_path / "ruim.pdf"
    ruim.write_bytes(b"nao sou um pdf")
    with pytest.raises(ValueError, match="corrompido"):
        split.separar(ruim, "cada")
