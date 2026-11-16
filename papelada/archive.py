"""Descompactar arquivos: zip/tar nativos; rar, 7z e outros via ferramentas do sistema."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

EXT_ARQUIVO = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".tbz2", ".txz", ".cab", ".iso"}
_NATIVOS_TAR = {".tar", ".gz", ".tgz", ".bz2", ".xz", ".tbz2", ".txz"}

# Ferramentas externas, em ordem de preferencia. bsdtar (libarchive) ja vem no macOS e o `tar.exe`
# do Windows 10/11 tambem e bsdtar: le rar e 7z sem instalar nada.
_FERRAMENTAS = ["bsdtar", "unar", "7zz", "7z", "7za", "unrar"] + (["tar"] if sys.platform in ("darwin", "win32") else [])

DICA_INSTALAR = ("Para abrir .rar/.7z instale uma destas ferramentas: 7-Zip, unar ou bsdtar "
                 "(Linux: `sudo apt install libarchive-tools` ou `unar`).")


def eh_compactado(caminho: Path) -> bool:
    nome = caminho.name.lower()
    return caminho.suffix.lower() in EXT_ARQUIVO or nome.endswith((".tar.gz", ".tar.bz2", ".tar.xz"))


def _comando(exe: str, arquivo: Path, destino: Path) -> list[str]:
    base = Path(exe).stem.lower()
    if base == "unar":
        return [exe, "-o", str(destino), "-force-overwrite", "-quiet", str(arquivo)]
    if base in ("7zz", "7z", "7za"):
        return [exe, "x", "-y", f"-o{destino}", str(arquivo)]
    if base == "unrar":
        return [exe, "x", "-y", str(arquivo), str(destino) + os.sep]
    return [exe, "-xf", str(arquivo), "-C", str(destino)]  # bsdtar / tar


def _extrair_tar(arquivo: Path, destino: Path) -> None:
    with tarfile.open(arquivo) as tf:
        raiz = destino.resolve()
        for m in tf.getmembers():  # barra caminhos fora da pasta e links perigosos
            alvo = (destino / m.name).resolve()
            if raiz not in alvo.parents and alvo != raiz or m.issym() or m.islnk() or m.isdev():
                raise ValueError(f"Caminho suspeito no arquivo: {m.name}")
        tf.extractall(destino, members=tf.getmembers())


def extrair(arquivo: Path, destino: Path) -> None:
    """Extrai `arquivo` em `destino`. Levanta ValueError com mensagem em portugues se falhar."""
    destino.mkdir(parents=True, exist_ok=True)
    ext = arquivo.suffix.lower()
    try:
        if ext == ".zip":
            with zipfile.ZipFile(arquivo) as zf:
                if any(i.flag_bits & 0x1 for i in zf.infolist()):
                    raise ValueError("O arquivo .zip esta protegido por senha.")
                zf.extractall(destino)
            return
        if ext in _NATIVOS_TAR and tarfile.is_tarfile(arquivo):
            _extrair_tar(arquivo, destino)
            return
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Nao foi possivel abrir {arquivo.name}: {exc}") from None

    ferramentas = [(n, shutil.which(n)) for n in _FERRAMENTAS]
    ferramentas = [(n, p) for n, p in ferramentas if p]
    if not ferramentas:
        raise ValueError(f"Nenhuma ferramenta para abrir {arquivo.name}. {DICA_INSTALAR}")
    for _, exe in ferramentas:
        try:
            r = subprocess.run(_comando(exe, arquivo, destino), capture_output=True, timeout=600)
        except Exception:
            continue
        if r.returncode == 0 and any(destino.iterdir()):
            return
    raise ValueError(f"Nao foi possivel abrir {arquivo.name}: protegido por senha, corrompido ou formato nao suportado.")
