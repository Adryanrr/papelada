import zipfile
from pathlib import Path

from conftest import faz_pdf, n_paginas
from papelada import merge


def test_ordem_natural_numerada():
    nomes = ["10 - B.pdf", "2 - A.pdf", "7.1.10 - X.pdf", "7.1.2 - X.pdf", "sem numero.pdf"]
    ordenados = sorted(nomes, key=merge.chave_nome)
    assert ordenados == ["2 - A.pdf", "7.1.2 - X.pdf", "7.1.10 - X.pdf", "10 - B.pdf", "sem numero.pdf"]


def test_juntar_pasta_com_subpastas_e_zip(tmp_path):
    raiz = tmp_path / "Empresa"
    faz_pdf(raiz / "2 - b.pdf", 2)
    faz_pdf(raiz / "1 - a.pdf", 1)
    faz_pdf(raiz / "sub" / "3 - c.pdf", 3)
    z = tmp_path / "pacote.zip"
    faz_pdf(tmp_path / "x" / "z.pdf", 4)
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(tmp_path / "x" / "z.pdf", "z.pdf")
    z.rename(raiz / "9 - pacote.zip")

    r = merge.juntar_pasta(raiz)
    assert r["count"] == 4 and r["pages"] == 10
    assert Path(r["output"]).name == "Empresa.pdf"
    assert n_paginas(r["output"]) == 10


def test_nao_sobrescreve_saida_existente(tmp_path):
    raiz = tmp_path / "P"
    faz_pdf(raiz / "a.pdf")
    primeiro = merge.juntar_pasta(raiz)["output"]
    segundo = merge.juntar_pasta(raiz)["output"]
    assert primeiro != segundo and Path(primeiro).exists() and Path(segundo).exists()


def test_pasta_vazia_da_erro_claro(tmp_path):
    (tmp_path / "vazia").mkdir()
    try:
        merge.juntar_pasta(tmp_path / "vazia")
    except ValueError as e:
        assert "Nenhum PDF" in str(e)
    else:
        raise AssertionError("esperava ValueError")


def test_pdf_corrompido_vira_aviso_e_nao_derruba(tmp_path):
    raiz = tmp_path / "P"
    faz_pdf(raiz / "1.pdf", 2)
    (raiz / "2.pdf").write_bytes(b"isto nao e pdf")
    r = merge.juntar_pasta(raiz)
    assert r["pages"] == 2 and any("2.pdf" in a for a in r["avisos"])


def test_lote_gera_um_pdf_por_subpasta(tmp_path):
    faz_pdf(tmp_path / "A" / "1.pdf", 1)
    faz_pdf(tmp_path / "B" / "1.pdf", 2)
    (tmp_path / "C").mkdir()
    r = merge.juntar_lote(tmp_path)
    assert r["total"] == 3 and r["ok"] == 2
    assert {x["nome"]: x["status"] for x in r["resultados"]} == {"A": "ok", "B": "ok", "C": "vazio"}
    # reexecutar nao junta a propria pasta de saida
    assert merge.juntar_lote(tmp_path)["total"] == 3


def test_ordem_personalizada_e_exclusao(tmp_path):
    raiz = tmp_path / "P"
    faz_pdf(raiz / "1 - a.pdf", 1)
    faz_pdf(raiz / "2 - b.pdf", 2)
    faz_pdf(raiz / "3 - c.pdf", 4)
    prev = merge.listar_ordem(raiz)
    assert [i["name"] for i in prev["items"]] == ["1 - a.pdf", "2 - b.pdf", "3 - c.pdf"]
    assert [i["pages"] for i in prev["items"]] == [1, 2, 4] and prev["pages"] == 7
    r = merge.juntar_pasta(raiz, ordem=["3 - c.pdf", "1 - a.pdf"])  # b fica de fora
    assert r["count"] == 2 and r["pages"] == 5 and n_paginas(r["output"]) == 5


def test_ordem_realmente_muda_a_sequencia(tmp_path):
    raiz = tmp_path / "P"
    for nome, w in (("a.pdf", 100), ("b.pdf", 200)):
        from pypdf import PdfWriter
        wr = PdfWriter(); wr.add_blank_page(width=w, height=50)
        (raiz).mkdir(exist_ok=True)
        with open(raiz / nome, "wb") as f:
            wr.write(f)
    from pypdf import PdfReader
    r = merge.juntar_pasta(raiz, ordem=["b.pdf", "a.pdf"])
    assert [float(p.mediabox.width) for p in PdfReader(r["output"]).pages] == [200.0, 100.0]


def test_ordem_em_arquivo_compactado(tmp_path):
    src = tmp_path / "s"
    faz_pdf(src / "a.pdf", 1)
    faz_pdf(src / "b.pdf", 3)
    z = tmp_path / "doc.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(src / "a.pdf", "a.pdf")
        zf.write(src / "b.pdf", "b.pdf")
    assert [i["name"] for i in merge.listar_ordem(z)["items"]] == ["doc.zip/a.pdf", "doc.zip/b.pdf"]
    r = merge.juntar_pasta(z, ordem=["doc.zip/b.pdf"])
    assert r["pages"] == 3


def test_ordem_vazia_ou_desconhecida_da_erro(tmp_path):
    raiz = tmp_path / "P"
    faz_pdf(raiz / "a.pdf")
    for ordem in ([], ["nao-existe.pdf"]):
        try:
            merge.juntar_pasta(raiz, ordem=ordem)
        except ValueError as e:
            assert "Nenhum arquivo" in str(e)
        else:
            raise AssertionError("esperava ValueError")
