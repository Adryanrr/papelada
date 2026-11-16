"""Separar um PDF em varios arquivos."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .common import caminho_livre, nome_seguro, pasta_saida


def parse_intervalos(texto: str, total: int) -> list[tuple[int, int]]:
    """'1-3, 5, 8-' -> [(1, 3), (5, 5), (8, total)] (paginas comecam em 1)."""
    saida: list[tuple[int, int]] = []
    for parte in texto.replace(";", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            if "-" in parte:
                a, b = (x.strip() for x in parte.split("-", 1))
                ini, fim = int(a or 1), int(b or total)
            else:
                ini = fim = int(parte)
        except ValueError:
            raise ValueError(f"Intervalo invalido: '{parte}'") from None
        if ini < 1 or fim > total or ini > fim:
            raise ValueError(f"Intervalo fora do documento ({total} paginas): '{parte}'")
        saida.append((ini, fim))
    if not saida:
        raise ValueError("Informe ao menos um intervalo de paginas, ex.: 1-3, 5, 8-10")
    return saida


def _gravar(reader: PdfReader, ini: int, fim: int, caminho: Path) -> str:
    w = PdfWriter()
    for i in range(ini - 1, fim):
        w.add_page(reader.pages[i])
    caminho = caminho_livre(caminho)
    with open(caminho, "wb") as f:
        w.write(f)
    return str(caminho)


def separar(pdf: Path, modo: str, valor: str = "", destino: str | None = None) -> dict:
    """Modos: 'cada' (1 arquivo por pagina), 'intervalos' (1 arquivo por intervalo),
    'blocos' (valor = paginas por arquivo) e 'extrair' (um so arquivo com os intervalos)."""
    if pdf.suffix.lower() != ".pdf" or not pdf.is_file():
        raise ValueError("Escolha um arquivo PDF.")
    try:
        reader = PdfReader(str(pdf))
    except Exception:
        raise ValueError("Nao foi possivel ler o PDF (arquivo corrompido?).") from None
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("O PDF esta protegido por senha.")
    total = len(reader.pages)
    saida = pasta_saida(pdf.parent, destino)
    base = nome_seguro(pdf.stem)
    largura = len(str(total))

    if modo == "cada":
        fatias = [(i, i) for i in range(1, total + 1)]
    elif modo == "blocos":
        try:
            n = int(valor)
        except ValueError:
            raise ValueError("Informe quantas paginas por arquivo.") from None
        if n < 1:
            raise ValueError("Paginas por arquivo deve ser pelo menos 1.")
        fatias = [(i, min(i + n - 1, total)) for i in range(1, total + 1, n)]
    elif modo == "intervalos":
        fatias = parse_intervalos(valor, total)
    elif modo == "extrair":
        paginas = [p for ini, fim in parse_intervalos(valor, total) for p in range(ini, fim + 1)]
        w = PdfWriter()
        for p in paginas:
            w.add_page(reader.pages[p - 1])
        arq = caminho_livre(saida / f"{base}_selecao.pdf")
        with open(arq, "wb") as f:
            w.write(f)
        return {"output": str(saida), "files": [str(arq)], "total_pages": total}
    else:
        raise ValueError(f"Modo desconhecido: {modo}")

    arquivos = []
    for ini, fim in fatias:
        rotulo = f"{ini:0{largura}d}" if ini == fim else f"{ini:0{largura}d}-{fim:0{largura}d}"
        arquivos.append(_gravar(reader, ini, fim, saida / f"{base}_p{rotulo}.pdf"))
    return {"output": str(saida), "files": arquivos, "total_pages": total}
