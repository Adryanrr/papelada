# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller packaging/papelada.spec   (gera dist/Papelada[.exe] ou dist/Papelada.app)
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

AQUI = Path(SPECPATH)
RAIZ = AQUI.parent

datas = [(str(RAIZ / "papelada" / "static"), "papelada/static")]
binaries, hidden = [], []
for pacote in ("pdf2docx", "fitz", "pymupdf", "pymupdf4llm", "pymupdf_layout", "webview", "cryptography"):
    try:
        d, b, h = collect_all(pacote)
    except Exception:
        continue
    datas += d
    binaries += b
    hidden += h

icone = {"darwin": "icon.icns", "win32": "icon.ico"}.get(sys.platform)
icone = str(AQUI / icone) if icone else None

a = Analysis([str(AQUI / "entry.py")], pathex=[str(RAIZ)], datas=datas, binaries=binaries,
             hiddenimports=hidden, excludes=["tkinter", "matplotlib", "pytest"])
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    # macOS: .app (sem janela de terminal); o botao "Encerrar" da interface fecha o servidor
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Papelada", console=False, icon=icone)
    coll = COLLECT(exe, a.binaries, a.datas, name="Papelada")
    app = BUNDLE(coll, name="Papelada.app", icon=icone, bundle_identifier="dev.papelada.app")
else:
    # Windows: .exe unico sem janela de console (a interface abre em janela propria).
    # Linux: binario unico com console; abre no navegador.
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Papelada", console=(sys.platform != "win32"), icon=icone)
