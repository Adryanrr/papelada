import json
import threading
import urllib.error
import urllib.request

import pytest

from conftest import faz_pdf
from papelada import server


@pytest.fixture
def url():
    srv = server.criar_servidor(8900)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def post(url, rota, corpo, headers=None):
    req = urllib.request.Request(url + rota, json.dumps(corpo).encode(),
                                 {"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_index_e_icone(url):
    assert b"Papelada" in urllib.request.urlopen(url + "/").read()


def test_fluxo_juntar_e_baixar(url, tmp_path):
    faz_pdf(tmp_path / "P" / "a.pdf", 2)
    status, r = post(url, "/api/merge", {"path": str(tmp_path / "P")})
    assert status == 200 and r["pages"] == 2
    baixado = urllib.request.urlopen(f"{url}/download?path={urllib.request.quote(r['output'])}").read()
    assert baixado.startswith(b"%PDF")


def test_download_so_de_arquivos_gerados(url, tmp_path):
    segredo = tmp_path / "segredo.txt"
    segredo.write_text("x")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(f"{url}/download?path={urllib.request.quote(str(segredo))}")
    assert e.value.code == 404


def test_bloqueia_origem_estranha(url):
    status, _ = post(url, "/api/list", {}, {"Origin": "http://evil.example"})
    assert status == 403


def test_erro_de_validacao_vira_400(url, tmp_path):
    status, r = post(url, "/api/merge", {"path": str(tmp_path / "nao-existe")})
    assert status == 400 and "error" in r


def test_reveal_recusa_arquivo_fora_das_saidas(url, tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("x")
    status, r = post(url, "/api/reveal", {"path": str(f)})
    assert status == 400 and "error" in r


def test_list_traz_atalhos_e_tipos(url, tmp_path):
    faz_pdf(tmp_path / "a.pdf")
    (tmp_path / "pasta").mkdir()
    (tmp_path / "x.rar").write_bytes(b"x")
    status, r = post(url, "/api/list", {"path": str(tmp_path)})
    assert status == 200 and r["shortcuts"]
    assert [d["name"] for d in r["dirs"]] == ["pasta"]
    assert [d["name"] for d in r["pdfs"]] == ["a.pdf"] and [d["name"] for d in r["archives"]] == ["x.rar"]
