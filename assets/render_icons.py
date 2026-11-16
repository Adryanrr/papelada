#!/usr/bin/env python3
"""Renderiza os PNGs/ICO/ICNS a partir dos SVGs com o Chrome/Chromium em modo headless.

Uso: .venv/bin/python assets/render_icons.py   (requer Chrome ou Chromium e Pillow)
Cada tamanho e renderizado nativamente (sem reduzir um PNG maior).
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

KIT = Path(__file__).resolve().parent / "icon-kit"
RAIZ = Path(__file__).resolve().parent.parent


def achar_chrome() -> str:
    candidatos = [os.environ.get("CHROME", ""),
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    candidatos += [shutil.which(n) or "" for n in ("google-chrome", "chromium", "chromium-browser", "chrome")]
    for c in candidatos:
        if c and Path(c).exists():
            return c
    raise SystemExit("Chrome/Chromium nao encontrado. Defina CHROME=/caminho/do/chrome")


def capturar_html(html: str, saida: Path, largura: int, altura: int, transparente: bool = False) -> None:
    with tempfile.TemporaryDirectory() as t:
        pagina = Path(t) / "p.html"
        pagina.write_text(html, encoding="utf-8")
        cmd = [achar_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
               f"--user-data-dir={t}/perfil", f"--window-size={largura},{altura}",
               f"--screenshot={saida}", "--force-device-scale-factor=1"]
        if transparente:
            cmd.append("--default-background-color=00000000")
        subprocess.run(cmd + [pagina.as_uri()], check=True, capture_output=True, timeout=60)


def svg_para_png(svg: Path, tamanho: int, saida: Path) -> None:
    """Renderiza o SVG em `tamanho` px (nativo) e recorta o canto superior esquerdo."""
    lado = max(tamanho, 300)
    html = (f'<style>html,body{{margin:0;background:transparent}}img{{display:block;width:{tamanho}px;'
            f'height:{tamanho}px}}</style><img src="{svg.as_uri()}">')
    bruto = saida.with_suffix(".raw.png")
    capturar_html(html, bruto, lado, lado, transparente=True)
    Image.open(bruto).convert("RGBA").crop((0, 0, tamanho, tamanho)).save(saida)
    bruto.unlink()


if __name__ == "__main__":
    ex, va = KIT / "exports", KIT / "variants"
    for t in (1024, 512):
        svg_para_png(KIT / "master/icon.svg", t, ex / f"app-icon-{t}.png")
    svg_para_png(va / "light.svg", 512, va / "light-512.png")
    svg_para_png(va / "dark.svg", 512, va / "dark-512.png")
    svg_para_png(va / "monochrome.svg", 512, va / "monochrome-512.png")
    for t in (16, 32, 48):
        svg_para_png(ex / "favicon.svg", t, ex / f"favicon-{t}.png")
    svg_para_png(KIT / "master/icon.svg", 256, ex / "app-icon-256.png")

    # ICO: camadas grandes do icone principal, pequenas do favicon (nativas)
    camadas = [Image.open(ex / f"favicon-{t}.png") for t in (16, 32, 48)]
    camadas += [Image.open(ex / "app-icon-256.png")]
    camadas[-1].save(ex / "icon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
                     append_images=camadas[:-1])

    # ICNS (macOS): iconset renderizado nativamente + iconutil
    if shutil.which("iconutil"):
        with tempfile.TemporaryDirectory() as t:
            iset = Path(t) / "icon.iconset"
            iset.mkdir()
            for base in (16, 32, 128, 256, 512):
                svg_para_png(KIT / "master/icon.svg", base, iset / f"icon_{base}x{base}.png")
                svg_para_png(KIT / "master/icon.svg", base * 2, iset / f"icon_{base}x{base}@2x.png")
            subprocess.run(["iconutil", "-c", "icns", str(iset), "-o", str(ex / "icon.icns")], check=True)

    # copia para onde o app e o empacotamento usam
    shutil.copy(KIT / "master/icon.svg", RAIZ / "papelada/static/icon.svg")
    shutil.copy(ex / "favicon.svg", RAIZ / "papelada/static/icon-small.svg")
    (RAIZ / "packaging").mkdir(exist_ok=True)
    for nome in ("icon.ico", "icon.icns", "app-icon-256.png"):
        if (ex / nome).exists():
            shutil.copy(ex / nome, RAIZ / "packaging" / nome.replace("app-icon-256", "icon"))
    print("PNG/ICO/ICNS gerados")
