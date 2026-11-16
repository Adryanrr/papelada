import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest

from conftest import faz_pdf, n_paginas
from papelada import archive, merge

FIX = Path(__file__).parent / "fixtures"
tem_bsdtar = bool(shutil.which("bsdtar") or shutil.which("unar") or shutil.which("7zz") or shutil.which("7z"))


def pasta_com_pdfs(base: Path) -> Path:
    faz_pdf(base / "src" / "2 - b.pdf", 2)
    faz_pdf(base / "src" / "1 - a.pdf", 1)
    return base / "src"


def test_zip_direto_gera_pdf(tmp_path):
    src = pasta_com_pdfs(tmp_path)
    z = tmp_path / "doc.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for f in src.iterdir():
            zf.write(f, f.name)
    r = merge.juntar_pasta(z)
    assert Path(r["output"]).name == "doc.pdf" and r["pages"] == 3 and n_paginas(r["output"]) == 3


def test_tar_gz_direto_gera_pdf(tmp_path):
    src = pasta_com_pdfs(tmp_path)
    t = tmp_path / "doc.tar.gz"
    with tarfile.open(t, "w:gz") as tf:
        tf.add(src, arcname="pasta")
    assert merge.juntar_pasta(t)["pages"] == 3


@pytest.mark.skipif(not (shutil.which("7zz") or shutil.which("7z")), reason="precisa do 7-Zip para criar o .7z")
def test_7z_direto_gera_pdf(tmp_path):
    import subprocess
    src = pasta_com_pdfs(tmp_path)
    z = tmp_path / "doc.7z"
    subprocess.run([shutil.which("7zz") or shutil.which("7z"), "a", str(z), str(src / "*")], check=True, capture_output=True)
    assert merge.juntar_pasta(z)["pages"] == 3


@pytest.mark.skipif(not tem_bsdtar, reason="sem ferramenta para rar")
def test_rar_real_e_extraido(tmp_path):
    destino = tmp_path / "out"
    archive.extrair(FIX / "rar5-dups.rar", destino)
    assert len(list(destino.rglob("*.txt"))) >= 1


@pytest.mark.skipif(not tem_bsdtar, reason="sem ferramenta para rar")
def test_rar_sem_pdf_da_erro_de_pdf_e_nao_de_extracao(tmp_path):
    with pytest.raises(ValueError, match="Nenhum PDF"):
        merge.juntar_pasta(FIX / "rar5-dups.rar")


@pytest.mark.skipif(not tem_bsdtar, reason="sem ferramenta para rar")
def test_rar_com_senha_da_erro_claro(tmp_path):
    with pytest.raises(ValueError, match="senha"):
        archive.extrair(FIX / "rar5-psw.rar", tmp_path / "o")


def test_arquivo_que_nao_e_compactado_e_recusado(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("x")
    with pytest.raises(ValueError, match="compactado"):
        merge.juntar_pasta(f)


def test_tar_com_caminho_fora_da_pasta_e_recusado(tmp_path):
    t = tmp_path / "mau.tar"
    (tmp_path / "x.txt").write_text("x")
    with tarfile.open(t, "w") as tf:
        tf.add(tmp_path / "x.txt", arcname="../fora.txt")
    with pytest.raises(ValueError, match="suspeito"):
        archive.extrair(t, tmp_path / "dest")
    assert not (tmp_path / "fora.txt").exists()


def test_lote_inclui_compactado_solto(tmp_path):
    src = pasta_com_pdfs(tmp_path)
    lote = tmp_path / "lote"
    lote.mkdir()
    with zipfile.ZipFile(lote / "empresa.zip", "w") as zf:
        for f in src.iterdir():
            zf.write(f, f.name)
    r = merge.juntar_lote(lote)
    assert r["ok"] == 1 and Path(r["resultados"][0]["output"]).name == "empresa.pdf"
