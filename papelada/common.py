"""Utilitarios compartilhados."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

PASTA_SAIDA_NOME = "Papelada_saida"


def normalizar_texto(texto: str) -> str:
    """Remove acentos e pontuacao e padroniza a caixa, para comparar nomes."""
    sem_acentos = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(c for c in sem_acentos if not unicodedata.combining(c))
    termos = re.sub(r"[^a-zA-Z0-9]+", " ", sem_acentos).strip().lower()
    return re.sub(r"\s+", " ", termos)


def nome_seguro(nome: str) -> str:
    """Troca caracteres proibidos em nomes de arquivo (Windows/Linux/macOS)."""
    limpo = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", unicodedata.normalize("NFC", nome)).strip(" .")
    return limpo or "documento"


def pasta_saida(base: Path, destino: str | None) -> Path:
    """Pasta de saida escolhida pelo usuario ou `Papelada_saida` ao lado da entrada."""
    # se o arquivo ja esta dentro de Papelada_saida, grava ali mesmo (sem aninhar outra pasta)
    padrao = base if base.name == PASTA_SAIDA_NOME else base / PASTA_SAIDA_NOME
    saida = Path(destino).expanduser() if destino else padrao
    saida.mkdir(parents=True, exist_ok=True)
    return saida


def caminho_livre(caminho: Path) -> Path:
    """Evita sobrescrever: acrescenta ` (2)`, ` (3)`... quando o arquivo ja existe."""
    if not caminho.exists():
        return caminho
    n = 2
    while True:
        candidato = caminho.with_name(f"{caminho.stem} ({n}){caminho.suffix}")
        if not candidato.exists():
            return candidato
        n += 1
