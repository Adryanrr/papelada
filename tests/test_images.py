import zipfile
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from conftest import n_paginas
from papelada import images, preview
from test_server import post, url  # noqa: F401

pytestmark = pytest.mark.skipif(not preview.disponivel(), reason="PyMuPDF ausente")


def img(caminho: Path, tam=(400, 200), cor="red", fmt=None, **kw):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", tam, cor).save(caminho, fmt, **kw)
    return caminho


def paginas(pdf):
    return [(round(float(p.mediabox.width)), round(float(p.mediabox.height))) for p in PdfReader(str(pdf)).pages]


def test_pasta_vira_um_pdf_na_ordem_natural(tmp_path):
    pasta = tmp_path / "Fotos"
    img(pasta / "10.jpg", (100, 100))
    img(pasta / "2.png", (300, 100))
    img(pasta / "1.jpg", (200, 100))
    r = images.imagens_para_pdf(pasta, tamanho="imagem")
    assert Path(r["output"]).name == "Fotos.pdf" and r["pages"] == 3
    assert [w for w, _ in paginas(r["output"])] == [150, 225, 75]  # 1.jpg, 2.png, 10.jpg (96 dpi -> pontos)


def test_a4_retrato_e_orientacao_automatica(tmp_path):
    pasta = tmp_path / "P"
    img(pasta / "a-larga.jpg", (800, 400))
    img(pasta / "b-alta.jpg", (400, 800))
    r = images.imagens_para_pdf(pasta, tamanho="a4", orientacao="auto")
    assert paginas(r["output"]) == [(842, 595), (595, 842)]
    r2 = images.imagens_para_pdf(pasta, nome="forcado", tamanho="a4", orientacao="retrato")
    assert paginas(r2["output"]) == [(595, 842), (595, 842)]


def test_carta_paisagem_e_margem(tmp_path):
    pasta = tmp_path / "P"
    img(pasta / "a.jpg", (500, 500))
    r = images.imagens_para_pdf(pasta, tamanho="carta", orientacao="paisagem", margem="grande")
    assert paginas(r["output"]) == [(792, 612)]
    r = images.imagens_para_pdf(pasta, nome="m", tamanho="imagem", margem="pequena")
    assert paginas(r["output"])[0][0] == round(500 * 72 / 96 + 36)  # imagem + 2 margens de 18 pt


def test_um_pdf_por_imagem(tmp_path):
    pasta = tmp_path / "P"
    img(pasta / "x.jpg")
    img(pasta / "y.png")
    r = images.imagens_para_pdf(pasta, modo="cada")
    assert sorted(Path(o).name for o in r["outputs"]) == ["x.pdf", "y.pdf"]
    assert all(n_paginas(o) == 1 for o in r["outputs"])


def test_ordem_e_exclusao_personalizadas(tmp_path):
    pasta = tmp_path / "P"
    img(pasta / "a.jpg", (100, 100))
    img(pasta / "b.jpg", (200, 100))
    img(pasta / "c.jpg", (300, 100))
    r = images.imagens_para_pdf(pasta, ordem=["c.jpg", "a.jpg"])
    assert [w for w, _ in paginas(r["output"])] == [225, 75]
    with pytest.raises(ValueError, match="selecionada"):
        images.imagens_para_pdf(pasta, ordem=[])


def test_zip_e_imagem_unica_e_transparencia(tmp_path):
    src = img(tmp_path / "s" / "a.png", (50, 50))
    Image.new("RGBA", (40, 40), (255, 0, 0, 0)).save(tmp_path / "s" / "t.png")
    z = tmp_path / "fotos.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(src, "a.png")
        zf.write(tmp_path / "s" / "t.png", "t.png")
    assert images.imagens_para_pdf(z)["pages"] == 2
    assert images.imagens_para_pdf(src, nome="solo")["pages"] == 1


def test_exif_gira_a_pagina(tmp_path):
    arq = tmp_path / "P" / "foto.jpg"
    arq.parent.mkdir()
    im = Image.new("RGB", (400, 200), "blue")
    ex = im.getexif()
    ex[0x0112] = 6  # rotacionar 90 graus: fica 200 x 400
    im.save(arq, exif=ex)
    assert images.listar(arq.parent)["items"][0]["size"] == [200, 400]
    r = images.imagens_para_pdf(arq.parent, tamanho="a4", orientacao="auto")
    assert paginas(r["output"]) == [(595, 842)]


def test_erros(tmp_path):
    vazio = tmp_path / "v"
    vazio.mkdir()
    with pytest.raises(ValueError, match="Nenhuma imagem"):
        images.imagens_para_pdf(vazio)
    with pytest.raises(ValueError):
        images.imagens_para_pdf(vazio, tamanho="a0")
    (tmp_path / "x.txt").write_text("x")
    with pytest.raises(ValueError):
        images.imagens_para_pdf(tmp_path / "x.txt")


def test_api_miniatura_de_imagem_e_remover(url, tmp_path):  # noqa: F811
    pasta = tmp_path / "P"
    img(pasta / "a.jpg")
    status, r = post(url, "/api/images-preview", {"path": str(pasta)})
    assert status == 200 and r["items"][0]["size"] == [400, 200] and "path" not in r["items"][0]
    import urllib.request
    jpg = urllib.request.urlopen(f"{url}/thumb?id={r['items'][0]['id']}&w=120").read()
    assert jpg[:3] == b"\xff\xd8\xff"
    status, g = post(url, "/api/images", {"path": str(pasta), "size": "a4"})
    assert status == 200 and g["pages"] == 1
    from conftest import faz_pdf
    pdf = faz_pdf(tmp_path / "d.pdf", 3)
    status, rm = post(url, "/api/remove-pages", {"path": str(pdf), "value": "1"})
    assert status == 200 and rm["remaining"] == 2
    status, _ = post(url, "/api/remove-pages", {"path": str(pdf), "value": "1-3"})
    assert status == 400
