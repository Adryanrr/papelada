"""Navegacao de pastas para o seletor da interface."""

from __future__ import annotations

import os
import string
from pathlib import Path

from .archive import eh_compactado


def resolver(valor: str | None) -> Path:
    pasta = (Path(valor).expanduser() if valor else Path.home()).resolve()
    if not pasta.exists():
        raise ValueError(f"Caminho nao encontrado: {pasta}")
    return pasta


def atalhos() -> list[dict]:
    """Pastas comuns do usuario que existem de fato."""
    home = Path.home()
    nomes = [("Início", home), ("Área de Trabalho", home / "Desktop"), ("Documentos", home / "Documents"),
             ("Downloads", home / "Downloads")]
    return [{"name": n, "path": str(p)} for n, p in nomes if p.is_dir()]


def listar(pasta: Path) -> dict:
    """Lista subpastas e PDFs de `pasta` (e as unidades, no Windows)."""
    if not pasta.is_dir():
        pasta = pasta.parent
    try:
        itens = sorted(pasta.iterdir(), key=lambda p: p.name.lower())
    except PermissionError as exc:
        raise ValueError(f"Sem permissao para abrir: {pasta}") from exc
    visiveis = [i for i in itens if not i.name.startswith(".")]
    drives = ([f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
              if os.name == "nt" else [])
    return {
        "path": str(pasta),
        "parent": str(pasta.parent) if pasta.parent != pasta else "",
        "home": str(Path.home()),
        "shortcuts": atalhos(),
        "drives": drives,
        "dirs": [{"name": i.name, "path": str(i)} for i in visiveis if i.is_dir()],
        "archives": [{"name": i.name, "path": str(i)} for i in visiveis if i.is_file() and eh_compactado(i)],
        "pdfs": [{"name": i.name, "path": str(i)} for i in visiveis
                 if i.is_file() and i.suffix.lower() == ".pdf"],
    }
