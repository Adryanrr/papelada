"""Proteger um PDF com senha e remover a senha."""

from __future__ import annotations

import secrets
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions as Perm


def _ler(pdf: Path) -> PdfReader:
    if pdf.suffix.lower() != ".pdf" or not pdf.is_file():
        raise ValueError("Escolha um arquivo PDF.")
    try:
        return PdfReader(str(pdf))
    except Exception:
        raise ValueError("Não foi possível ler o PDF (arquivo corrompido? tente Reparar).") from None


def proteger(pdf: Path, saida: Path, senha: str = "", sem_imprimir: bool = False, sem_copiar: bool = False,
             sem_editar: bool = False) -> dict:
    """Pede a senha para abrir (AES-256). As opcoes 'sem_*' travam a permissao correspondente."""
    senha = str(senha or "")
    if len(senha) < 4:
        raise ValueError("Use uma senha com pelo menos 4 caracteres.")
    reader = _ler(pdf)
    if reader.is_encrypted:
        raise ValueError("O PDF já tem senha. Desbloqueie primeiro.")
    writer = PdfWriter(clone_from=reader)
    perm = Perm.PRINT | Perm.PRINT_TO_REPRESENTATION | Perm.MODIFY | Perm.EXTRACT | Perm.ADD_OR_MODIFY | \
        Perm.EXTRACT_TEXT_AND_GRAPHICS | Perm.FILL_FORM_FIELDS | Perm.ASSEMBLE_DOC
    if sem_imprimir:
        perm &= ~(Perm.PRINT | Perm.PRINT_TO_REPRESENTATION)
    if sem_copiar:
        perm &= ~(Perm.EXTRACT | Perm.EXTRACT_TEXT_AND_GRAPHICS)
    if sem_editar:
        perm &= ~(Perm.MODIFY | Perm.ADD_OR_MODIFY | Perm.ASSEMBLE_DOC | Perm.FILL_FORM_FIELDS)
    restrito = sem_imprimir or sem_copiar or sem_editar
    # com restricoes, a senha de "dono" e aleatoria: so quem criou o PDF as muda, regravando o original
    writer.encrypt(user_password=senha, owner_password=secrets.token_urlsafe(18) if restrito else senha,
                   permissions_flag=perm, algorithm="AES-256")
    with open(saida, "wb") as f:
        writer.write(f)
    return {"info": "protegido com senha" + (" e restrições" if restrito else "")}


def desbloquear(pdf: Path, saida: Path, senha: str = "") -> dict:
    """Grava uma copia sem senha. Precisa da senha de abertura quando o PDF a exige."""
    reader = _ler(pdf)
    if not reader.is_encrypted:
        raise ValueError("Este PDF não tem senha nem restrições.")
    if not reader.decrypt(str(senha or "")):
        raise ValueError("Senha incorreta.")
    writer = PdfWriter(clone_from=reader)
    with open(saida, "wb") as f:
        writer.write(f)
    return {"info": "senha e restrições removidas"}
