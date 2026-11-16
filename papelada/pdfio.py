"""Ajudantes compartilhados pelas ferramentas de PDF (abrir, validar opcoes, escrever texto)."""

from __future__ import annotations

from pathlib import Path

from . import preview
from .split import parse_intervalos


def abrir(pdf: Path, senha: str = ""):
    """Abre um PDF com PyMuPDF; ValueError em portugues se for invalido ou protegido."""
    mu = preview._exigir()
    if pdf.suffix.lower() != ".pdf" or not pdf.is_file():
        raise ValueError("Escolha um arquivo PDF.")
    try:
        doc = mu.open(str(pdf))
    except Exception:
        raise ValueError("Nao foi possivel ler o PDF (arquivo corrompido? tente Reparar).") from None
    if doc.needs_pass and not (senha and doc.authenticate(senha)):
        doc.close()
        raise ValueError("O PDF esta protegido por senha. Use Desbloquear primeiro.")
    return doc


def salvar(doc, saida: Path) -> None:
    doc.save(str(saida), garbage=3, deflate=True)
    doc.close()


def selecionar(texto: str, total: int) -> list[int]:
    """Indices (0-based) das paginas de 'texto' ('1-3, 5'); vazio = todas."""
    if not str(texto or "").strip():
        return list(range(total))
    vistos: list[int] = []
    for ini, fim in parse_intervalos(str(texto), total):
        vistos += [i - 1 for i in range(ini, fim + 1) if i - 1 not in vistos]
    return sorted(vistos)


def inteiro(valor, nome: str, minimo: int, maximo: int, padrao: int | None = None) -> int:
    if valor in (None, ""):
        if padrao is None:
            raise ValueError(f"Informe {nome}.")
        return padrao
    try:
        n = int(float(valor))
    except (TypeError, ValueError):
        raise ValueError(f"{nome}: informe um numero.") from None
    if not minimo <= n <= maximo:
        raise ValueError(f"{nome}: use um valor entre {minimo} e {maximo}.")
    return n


def decimal(valor, nome: str, minimo: float, maximo: float, padrao: float) -> float:
    if valor in (None, ""):
        return padrao
    try:
        n = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nome}: informe um numero.") from None
    if not minimo <= n <= maximo:
        raise ValueError(f"{nome}: use um valor entre {minimo:g} e {maximo:g}.")
    return n


def escolha(valor, nome: str, validos) -> str:
    if valor not in validos:
        raise ValueError(f"{nome}: opcao invalida.")
    return valor


def cor(hexa: str) -> tuple[float, float, float]:
    h = str(hexa or "#000000").lstrip("#")
    if len(h) != 6:
        raise ValueError("Cor invalida.")
    try:
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        raise ValueError("Cor invalida.") from None


def ponto_real(page, x: float, y: float):
    """Ponto (x, y) na pagina como o usuario a ve -> coordenadas internas da pagina."""
    mu = preview._exigir()
    return mu.Point(x, y) * page.derotation_matrix


def texto_na_pagina(page, x: float, y: float, texto: str, tamanho: float, cor_rgb, angulo: float = 0,
                    opacidade: float = 1.0, sobre: bool = True) -> None:
    """Escreve `texto` centrado em (x, y) vistos pelo usuario, inclinado `angulo` graus (anti-horario),
    mesmo em paginas que ja estao giradas."""
    mu = preview._exigir()
    centro = ponto_real(page, x, y)
    largura = mu.get_text_length(texto, "helv", tamanho)
    origem = mu.Point(centro.x - largura / 2, centro.y + tamanho * 0.35)
    morph = (centro, mu.Matrix((angulo + page.rotation) % 360))
    page.insert_text(origem, texto, fontsize=tamanho, fontname="helv", color=cor_rgb, fill_opacity=opacidade,
                     morph=morph, overlay=sobre)
