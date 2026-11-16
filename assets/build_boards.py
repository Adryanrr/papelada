#!/usr/bin/env python3
"""Pranchas de revisao: comparacao dos conceitos e prancha final das variantes."""
from pathlib import Path

from render_icons import KIT, capturar_html

CSS = ("body{margin:0;font:14px system-ui;color:#e8efed}.t{border-radius:23%;overflow:hidden;display:block}"
       ".c{display:flex;flex-direction:column;align-items:center;gap:8px}.r{display:flex;gap:28px;align-items:flex-end}"
       ".quad{background:conic-gradient(#ccc 25%,#fff 0 50%,#ccc 0 75%,#fff 0) 0 0/16px 16px}")


def tile(path: str, px: int, raio: bool = True) -> str:
    rad = "" if raio else "border-radius:0;"
    return f'<img class="t" style="{rad}width:{px}px;height:{px}px" src="{(KIT / path).as_uri()}">'


def comparacao() -> None:
    itens = [("A · Pilha de folhas (recomendado)", "concepts/a-pilha.svg"),
             ("B · Folha mascote", "concepts/b-mascote.svg"),
             ("C · Folha cortada", "concepts/c-corte.svg")]
    cols = "".join(f'<div class="c">{tile(p, 360)}<div>{n}</div>'
                   f'<div class="r" style="background:#10201e;padding:10px;border-radius:10px">'
                   f'{tile(p, 64)}{tile(p, 32)}{tile(p, 16)}</div></div>' for n, p in itens)
    html = f'<style>{CSS}</style><body style="background:#0f1716;padding:28px"><div class="r" style="align-items:flex-start">{cols}</div>'
    capturar_html(html, KIT / "concepts/comparison.png", 1280, 640)


def final() -> None:
    var = [("Principal", "master/icon.svg"), ("Plana", "variants/flat.svg"), ("Clara", "variants/light.svg"),
           ("Escura", "variants/dark.svg")]
    linhas = ""
    for fundo, cor in (("claro", "#f3f1ea;color:#222"), ("escuro", "#0f1716;color:#e8efed"), ("quadriculado", "")):
        cls = ' class="quad"' if not cor else ""
        estilo = f'style="background:{cor}"' if cor else 'style="color:#222"'
        cels = "".join(f'<div class="c">{tile(p, 160)}<div>{n}</div><div class="r">{tile(p, 64)}{tile(p, 32)}</div></div>'
                       for n, p in var)
        cels += (f'<div class="c"><img style="width:160px;height:160px" src="{(KIT / "variants/monochrome.svg").as_uri()}">'
                 f'<div>Mono</div><div class="r"><img style="width:64px" src="{(KIT / "variants/monochrome.svg").as_uri()}">'
                 f'<img style="width:32px" src="{(KIT / "variants/monochrome.svg").as_uri()}"></div></div>')
        cels += (f'<div class="c">{tile("exports/favicon.svg", 160, False)}<div>Pequena</div><div class="r">'
                 f'<img src="{(KIT / "exports/favicon-32.png").as_uri()}" width="32">'
                 f'<img src="{(KIT / "exports/favicon-16.png").as_uri()}" width="16"></div></div>')
        linhas += f'<div{cls} {estilo}><div class="r" style="padding:22px;align-items:flex-start">{cels}</div></div>'
    html = f'<style>{CSS}</style><body>{linhas}'
    capturar_html(html, KIT / "review/preview.png", 1440, 1000)


if __name__ == "__main__":
    comparacao()
    final()
    print("pranchas geradas")
