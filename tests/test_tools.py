import random
from pathlib import Path

import pytest
from PIL import Image, ImageChops
from pypdf import PdfReader

from papelada import batch, export, optimize, pages, preview, security, watermark

pytestmark = pytest.mark.skipif(not preview.disponivel(), reason="PyMuPDF ausente")
import pymupdf  # noqa: E402


def pdf_texto(caminho: Path, n=3, w=300, h=400, rot=0, conteudo=True):
    d = pymupdf.open()
    for i in range(n):
        p = d.new_page(width=w, height=h)
        if conteudo:
            p.insert_text((100, 150), f"Pagina {i + 1}", fontsize=18)
            p.draw_rect(pymupdf.Rect(100, 200, 200, 260), fill=(0, 0, 0))
        if rot:
            p.set_rotation(rot)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    d.save(caminho)
    return caminho


def pdf_imagem_pesada(caminho: Path):
    random.seed(1)
    im = Image.new("RGB", (1600, 1600))
    im.putdata([(random.randrange(256), random.randrange(256), random.randrange(256)) for _ in range(1600 * 1600)])
    img = caminho.with_suffix(".png")
    im.save(img)
    d = pymupdf.open()
    p = d.new_page(width=595, height=842)
    p.insert_image(pymupdf.Rect(20, 20, 575, 575), filename=str(img))
    d.save(caminho)
    return caminho


def saida_de(r):
    return Path(r["resultados"][0]["output"])


def escuro(pdf: Path, pagina=0, dpi=72):
    with pymupdf.open(str(pdf)) as d:
        pix = d[pagina].get_pixmap(dpi=dpi, alpha=False)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    return im, im.point(lambda v: 255 if v < 140 else 0).getbbox()


# ---------- girar / organizar ----------
def test_girar_todas_e_selecionadas(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 3)
    r = batch.aplicar(pdf, None, pages.girar, "_g", ".pdf", graus=90)
    assert [p.rotation for p in PdfReader(str(saida_de(r))).pages] == [90, 90, 90]
    r2 = batch.aplicar(pdf, str(tmp_path / "o2"), pages.girar, "_g", ".pdf", graus=180, paginas="2")
    assert [p.rotation for p in PdfReader(str(saida_de(r2))).pages] == [0, 180, 0]


def test_girar_graus_invalidos(tmp_path):
    with pytest.raises(ValueError):
        batch.aplicar(pdf_texto(tmp_path / "a.pdf"), None, pages.girar, "_g", ".pdf", graus=45)


def test_organizar_reordena_remove_e_gira(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 4)
    r = batch.aplicar(pdf, None, pages.organizar, "_o", ".pdf", so_arquivo=True,
                      pages=[{"p": 2, "rot": 0}, {"p": 0, "rot": 90}, {"p": 3, "rot": 0}])
    with pymupdf.open(str(saida_de(r))) as d:
        assert [pg.get_text().strip() for pg in d] == ["Pagina 3", "Pagina 1", "Pagina 4"]
        assert [pg.rotation for pg in d] == [0, 90, 0]


def test_organizar_valida(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 2)
    for ruim in ([], [{"p": 5}], [{"p": 0}, {"p": 0}], [{"p": 0, "rot": 45}], None):
        with pytest.raises(ValueError):
            batch.aplicar(pdf, str(tmp_path / "x"), pages.organizar, "_o", ".pdf", so_arquivo=True, pages=ruim)


# ---------- numerar ----------
def test_numerar_texto_e_posicao(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 3, conteudo=False)
    r = batch.aplicar(pdf, None, pages.numerar, "_n", ".pdf", formato="Página {n} de {total}", inicio=5, de=2)
    with pymupdf.open(str(saida_de(r))) as d:
        assert d[0].get_text().strip() == ""
        assert d[1].get_text().strip() == "Página 5 de 6" and d[2].get_text().strip() == "Página 6 de 6"
    _, bb = escuro(saida_de(r), 1)
    assert bb and bb[1] > 400 * 0.85 and abs((bb[0] + bb[2]) / 2 - 150) < 25  # embaixo, no centro


@pytest.mark.parametrize("rot", [0, 90, 180, 270])
def test_numerar_em_pagina_girada_fica_embaixo_e_legivel(tmp_path, rot):
    pdf = pdf_texto(tmp_path / "a.pdf", 1, rot=rot, conteudo=False)
    r = batch.aplicar(pdf, None, pages.numerar, "_n", ".pdf", formato="{n}", tamanho=20)
    im, bb = escuro(saida_de(r))
    assert bb and bb[1] > im.height * 0.8 and abs((bb[0] + bb[2]) / 2 - im.width / 2) < im.width * 0.1
    # o numero "1" nao pode estar de lado: mais alto que largo
    assert bb[3] - bb[1] > bb[2] - bb[0]


def test_numerar_opcoes_invalidas(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 2)
    for kw in ({"posicao": "meio"}, {"formato": "{x}"}, {"de": 9}, {"tamanho": 1}, {"cor": "zzz"}):
        with pytest.raises(ValueError):
            batch.aplicar(pdf, str(tmp_path / "x"), pages.numerar, "_n", ".pdf", **kw)


# ---------- marca d'agua ----------
def test_marca_dagua_texto_atras_e_sobre(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 2)
    r = batch.aplicar(pdf, None, watermark.marca_dagua, "_m", ".pdf", texto="CONFIDENCIAL", paginas="1")
    with pymupdf.open(str(saida_de(r))) as d:
        assert "CONFIDENCIAL" in d[0].get_text() and "CONFIDENCIAL" not in d[1].get_text()
    _, bb = escuro(saida_de(r), 0)  # opacidade 30% de cinza: nao deve escurecer a pagina toda
    assert bb is not None


def test_marca_dagua_imagem(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 1, conteudo=False)
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (200, 100), (200, 0, 0, 255)).save(logo)
    r = batch.aplicar(pdf, None, watermark.marca_dagua, "_m", ".pdf", imagem=str(logo), opacidade=100, estilo="horizontal")
    with pymupdf.open(str(saida_de(r))) as d:
        assert len(d[0].get_images()) == 1
        pix = d[0].get_pixmap(dpi=72, alpha=False)
        assert pix.pixel(150, 200)[0] > 150 and pix.pixel(150, 200)[1] < 80  # vermelho no centro


def test_marca_dagua_exige_texto_ou_imagem(tmp_path):
    with pytest.raises(ValueError, match="texto"):
        batch.aplicar(pdf_texto(tmp_path / "a.pdf"), None, watermark.marca_dagua, "_m", ".pdf")


# ---------- recortar ----------
def test_recortar_por_margens_e_auto(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 1)
    r = batch.aplicar(pdf, None, pages.recortar, "_r", ".pdf", modo="margens", cima=10, baixo=10, esquerda=5, direita=5)
    mm = 72 / 25.4
    with pymupdf.open(str(saida_de(r))) as d:
        assert abs(d[0].rect.width - (300 - 10 * mm)) < 0.5 and abs(d[0].rect.height - (400 - 20 * mm)) < 0.5
    r2 = batch.aplicar(pdf, str(tmp_path / "auto"), pages.recortar, "_r", ".pdf", modo="auto", folga=2)
    with pymupdf.open(str(saida_de(r2))) as d:
        assert d[0].rect.width < 160 and d[0].rect.height < 180 and "Pagina 1" in d[0].get_text()


def test_recortar_em_pagina_girada_mantem_conteudo(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 1, rot=90)
    r = batch.aplicar(pdf, None, pages.recortar, "_r", ".pdf", modo="auto", folga=3)
    im, bb = escuro(saida_de(r), dpi=72)
    assert bb and bb[0] <= 12 and bb[1] <= 12 and im.width < 170 and im.height < 170  # conteudo perto da borda (folga de 3 mm)


def test_recortar_validacoes(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 1)
    with pytest.raises(ValueError, match="margem"):
        batch.aplicar(pdf, None, pages.recortar, "_r", ".pdf", modo="margens")
    with pytest.raises(ValueError, match="Nada"):
        batch.aplicar(pdf_texto(tmp_path / "v.pdf", 1, conteudo=False), None, pages.recortar, "_r", ".pdf", modo="auto")


# ---------- seguranca ----------
def test_proteger_e_desbloquear(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf", 2)
    r = batch.aplicar(pdf, None, security.proteger, "_p", ".pdf", senha="segredo", sem_copiar=True)
    prot = saida_de(r)
    assert PdfReader(str(prot)).is_encrypted
    with pytest.raises(ValueError, match="incorreta"):
        batch.aplicar(prot, str(tmp_path / "x"), security.desbloquear, "_d", ".pdf", senha="errada")
    r2 = batch.aplicar(prot, str(tmp_path / "y"), security.desbloquear, "_d", ".pdf", senha="segredo")
    assert not PdfReader(str(saida_de(r2))).is_encrypted and len(PdfReader(str(saida_de(r2))).pages) == 2


def test_proteger_validacoes(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf")
    with pytest.raises(ValueError, match="4"):
        batch.aplicar(pdf, None, security.proteger, "_p", ".pdf", senha="ab")
    with pytest.raises(ValueError, match="não tem senha"):
        batch.aplicar(pdf, str(tmp_path / "x"), security.desbloquear, "_d", ".pdf")


def test_ferramentas_recusam_pdf_com_senha_e_orientam(tmp_path):
    pdf = pdf_texto(tmp_path / "a.pdf")
    prot = saida_de(batch.aplicar(pdf, None, security.proteger, "_p", ".pdf", senha="segredo"))
    with pytest.raises(ValueError, match="Desbloquear"):
        batch.aplicar(prot, str(tmp_path / "x"), pages.girar, "_g", ".pdf")


# ---------- comprimir / reparar ----------
def test_comprimir_reduz_e_nunca_aumenta(tmp_path):
    pdf = pdf_imagem_pesada(tmp_path / "pesado.pdf")
    r = batch.aplicar(pdf, None, optimize.comprimir, "_c", ".pdf", nivel="extrema")
    item = r["resultados"][0]
    assert item["depois"] < item["antes"] * 0.6 and "−" in item["info"]
    leve = pdf_texto(tmp_path / "leve.pdf", 1)
    r2 = batch.aplicar(leve, str(tmp_path / "o2"), optimize.comprimir, "_c", ".pdf", nivel="baixa")
    assert saida_de(r2).stat().st_size <= leve.stat().st_size


def test_reparar_pdf_danificado(tmp_path):
    bom = pdf_texto(tmp_path / "bom.pdf", 3)
    dados = bom.read_bytes()
    ruim = tmp_path / "ruim.pdf"
    ruim.write_bytes(dados[: dados.rindex(b"startxref")])  # tira o final (xref/trailer)
    r = batch.aplicar(ruim, None, optimize.reparar, "_r", ".pdf")
    with pymupdf.open(str(saida_de(r))) as d:
        assert d.page_count == 3
    lixo = tmp_path / "lixo.pdf"
    lixo.write_bytes(b"isto nao e um pdf")
    with pytest.raises(ValueError, match="recuperar"):
        batch.aplicar(lixo, str(tmp_path / "x"), optimize.reparar, "_r", ".pdf")


# ---------- exportar ----------
def test_pdf_para_jpg_paginas_e_imagens(tmp_path):
    pdf = pdf_texto(tmp_path / "doc.pdf", 3)
    r = batch.aplicar(pdf, None, export.pdf_para_jpg, "_imagens", None, dpi=72)
    pasta = Path(r["resultados"][0]["output"])
    assert pasta.is_dir() and sorted(p.name for p in pasta.iterdir()) == ["doc_p1.jpg", "doc_p2.jpg", "doc_p3.jpg"]
    assert Image.open(pasta / "doc_p1.jpg").size == (300, 400)
    pesado = pdf_imagem_pesada(tmp_path / "foto.pdf")
    r2 = batch.aplicar(pesado, None, export.pdf_para_jpg, "_imagens", None, modo="imagens")
    assert len(list(Path(r2["resultados"][0]["output"]).iterdir())) == 1
    with pytest.raises(ValueError, match="Nenhuma imagem"):
        batch.aplicar(pdf, str(tmp_path / "z"), export.pdf_para_jpg, "_imagens", None, modo="imagens")


def test_pdf_para_markdown(tmp_path):
    d = pymupdf.open()
    p = d.new_page()
    p.insert_text((72, 100), "Titulo grande", fontsize=24)
    p.insert_text((72, 140), "corpo do texto", fontsize=11)
    d.save(tmp_path / "t.pdf")
    r = batch.aplicar(tmp_path / "t.pdf", None, export.pdf_para_markdown, "", ".md")
    md = saida_de(r).read_text(encoding="utf-8")
    assert md.startswith("#") and "Titulo grande" in md and "corpo do texto" in md
    with pytest.raises(ValueError, match="OCR"):
        batch.aplicar(pdf_texto(tmp_path / "v.pdf", 1, conteudo=False), str(tmp_path / "o"), export.pdf_para_markdown, "", ".md")


# ---------- lote ----------
def test_lote_em_pasta_continua_apos_erro(tmp_path):
    pasta = tmp_path / "docs"
    pdf_texto(pasta / "a.pdf", 1)
    pdf_texto(pasta / "b.pdf", 1)
    (pasta / "c.pdf").write_bytes(b"corrompido")
    r = batch.aplicar(pasta, None, pages.girar, "_g", ".pdf")
    assert (r["total"], r["ok"]) == (3, 2)
    assert {x["nome"]: x["status"] for x in r["resultados"]} == {"a.pdf": "ok", "b.pdf": "ok", "c.pdf": "erro"}
    # re-executar nao reprocessa a pasta de saida
    assert batch.aplicar(pasta, None, pages.girar, "_g", ".pdf")["total"] == 3


# ---------- API ----------
def test_api_tool_valida_e_executa(tmp_path):
    import json
    import threading
    import urllib.error
    import urllib.request

    from papelada import server
    srv = server.criar_servidor(8920)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(corpo):
        req = urllib.request.Request(base + "/api/tool", json.dumps(corpo).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    try:
        pdf = pdf_texto(tmp_path / "a.pdf", 2)
        status, r = post({"tool": "rotate", "path": str(pdf), "options": {"graus": "90", "paginas": ""}})
        assert status == 200 and r["ok"] == 1 and Path(r["resultados"][0]["output"]).name == "a_girado.pdf"
        assert post({"tool": "nao-existe", "path": str(pdf)})[0] == 400
        status, r = post({"tool": "rotate", "path": str(pdf), "options": {"x": 1}})
        assert status == 400 and "desconhecida" in r["error"]
        pasta = tmp_path / "dois"
        pdf_texto(pasta / "x.pdf", 1)
        pdf_texto(pasta / "y.pdf", 1)
        assert post({"tool": "organize", "path": str(pasta), "options": {"pages": [{"p": 0}]}})[0] == 400  # so um PDF por vez
        status, r = post({"tool": "compress", "path": str(pdf), "options": {"nivel": "recomendada"}})
        assert status == 200 and r["resultados"][0]["info"]
    finally:
        srv.shutdown()
        srv.server_close()
