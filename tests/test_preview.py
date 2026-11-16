import urllib.error
import urllib.request
import zipfile

import pytest

from conftest import faz_pdf
from papelada import merge, preview
from test_server import post, url  # noqa: F401  (fixture reutilizada)

pytestmark = pytest.mark.skipif(not preview.disponivel(), reason="PyMuPDF ausente")


def test_renderizar_devolve_jpeg_e_conta_paginas(tmp_path):
    pdf = faz_pdf(tmp_path / "a.pdf", 3)
    assert preview.paginas(pdf) == 3
    img = preview.renderizar(pdf, 1, 200)
    assert img[:3] == b"\xff\xd8\xff"


def test_pagina_inexistente_e_pdf_invalido(tmp_path):
    pdf = faz_pdf(tmp_path / "a.pdf", 1)
    with pytest.raises(ValueError):
        preview.renderizar(pdf, 5, 200)
    ruim = tmp_path / "x.pdf"
    ruim.write_bytes(b"nao e pdf")
    with pytest.raises(ValueError):
        preview.paginas(ruim)


def test_paginas_de_item_dentro_de_zip(tmp_path):
    src = faz_pdf(tmp_path / "s" / "a.pdf", 4)
    z = tmp_path / "d.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(src, "a.pdf")
    assert merge.listar_ordem(z)["items"][0]["pages"] == 4


def test_miniatura_pela_api(url, tmp_path):  # noqa: F811
    faz_pdf(tmp_path / "P" / "a.pdf", 2)
    status, r = post(url, "/api/merge-preview", {"path": str(tmp_path / "P")})
    assert status == 200 and r["thumbs"] and "path" not in r["items"][0]
    item = r["items"][0]
    img = urllib.request.urlopen(f"{url}/thumb?id={item['id']}&p=1&w=160").read()
    assert img[:3] == b"\xff\xd8\xff"
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(f"{url}/thumb?id=999999&p=0")
    assert e.value.code == 404


def test_preview_file_so_aceita_pdf(url, tmp_path):  # noqa: F811
    pdf = faz_pdf(tmp_path / "a.pdf", 3)
    status, r = post(url, "/api/preview-file", {"path": str(pdf)})
    assert status == 200 and r["pages"] == 3
    (tmp_path / "x.txt").write_text("x")
    status, _ = post(url, "/api/preview-file", {"path": str(tmp_path / "x.txt")})
    assert status == 400
