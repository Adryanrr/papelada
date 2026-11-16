#!/usr/bin/env python3
"""Gera os SVGs do icone do Papelada (conceitos, principal e variantes).

Uso: python assets/build_icons.py   (depois: python assets/render_icons.py)
Tudo e vetor puro: edite as cores/formas aqui e rode de novo.
"""
from pathlib import Path

KIT = Path(__file__).resolve().parent / "icon-kit"

# Formas locais de uma folha (origem no centro). A quina superior direita e cortada.
FOLHA = ("M-154,-240 H100 L190,-150 V204 Q190,240 154,240 H-154 Q-190,240 -190,204 "
         "V-204 Q-190,-240 -154,-240 Z")
DOBRA = "M100,-240 V-186 Q100,-150 136,-150 H190 Z"

TEAL, AMBAR = "#2B3A4A", "#F59E0B"  # TEAL: nome historico, agora e o azul-ardosia
PAPEL = "#FFFDF7"


def svg(corpo: str, defs: str = "", fundo: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">'
            f'<defs>{defs}</defs>{fundo}{corpo}</svg>\n')


def fundo(c0: str, c1: str, uid: str, raio: int = 0) -> tuple[str, str]:
    defs = (f'<linearGradient id="{uid}-bg" x1="0.15" y1="0" x2="0.85" y2="1">'
            f'<stop offset="0" stop-color="{c0}"/><stop offset="1" stop-color="{c1}"/></linearGradient>')
    return defs, f'<rect width="1024" height="1024" rx="{raio}" fill="url(#{uid}-bg)"/>'


def sombra(uid: str, cor: str = "#1B2430", op: float = 0.28) -> str:
    return (f'<filter id="{uid}-sh" x="-25%" y="-20%" width="150%" height="150%">'
            f'<feDropShadow dx="0" dy="16" stdDeviation="15" flood-color="{cor}" flood-opacity="{op}"/></filter>')


def pilha(p: dict, uid: str, sombras: bool = True, linhas: bool = True, borda: str = "") -> str:
    """Conceito A: tres folhas em leque; a da frente tem a dobra e linhas de texto."""
    f = f' filter="url(#{uid}-sh)"' if sombras else ""
    contorno = f' stroke="{borda}" stroke-width="5"' if borda else ""
    texto = (f'<rect x="-130" y="-70" width="250" height="28" rx="14" fill="{p["linha"]}"/>'
             f'<rect x="-130" y="-14" width="260" height="28" rx="14" fill="{p["linha"]}"/>'
             f'<rect x="-130" y="42" width="170" height="28" rx="14" fill="{AMBAR}"/>') if linhas else ""
    return (f'<g transform="translate(512 516) scale(1.12)">'
            f'<g transform="rotate(-13) translate(-34 10)"{f}><path d="{FOLHA}" fill="{p["tras"]}"/></g>'
            f'<g transform="rotate(-5) translate(-8 4)"{f}><path d="{FOLHA}" fill="{p["meio"]}"/></g>'
            f'<g transform="rotate(5) translate(22 0)"{f}><path d="{FOLHA}" fill="{p["frente"]}"{contorno}/>'
            f'<path d="{DOBRA}" fill="{AMBAR}"/>{texto}</g></g>')


def principal(p: dict, uid: str, plano: bool = False, raio: int = 0) -> str:
    defs, bg = fundo(p["bg0"], p["bg1"] if not plano else p["bg0"], uid, raio)
    if not plano:
        defs += sombra(uid)
    return svg(pilha(p, uid, sombras=not plano, borda=p.get("borda", "")), defs, bg)


PRIMARIA = dict(bg0="#FFFFFF", bg1="#E9E6DC", tras="#CBD3DC", meio="#8E9CAC", frente=TEAL, linha=PAPEL)
CLARA = dict(bg0="#FBF3E4", bg1="#EFE0C4", tras="#D9CDB6", meio="#9AA3AE", frente=TEAL, linha=PAPEL)
ESCURA = dict(bg0="#1E2631", bg1="#0E1218", tras="#3A4656", meio="#6B7B8F", frente="#F4F6F9", linha=TEAL,
              borda="#E2E8F0")


def monocromatico(tinta: str = "#1F2933") -> str:
    """Uma tinta so, sobre transparencia: folha da frente cheia, as de tras em contorno."""
    uid = "mono"
    defs = (f'<mask id="{uid}-m" maskUnits="userSpaceOnUse" x="-400" y="-400" width="800" height="800">'
            f'<rect x="-400" y="-400" width="800" height="800" fill="#fff"/>'
            f'<g transform="rotate(5) translate(22 0)"><path d="{FOLHA}" fill="#000" stroke="#000" stroke-width="44"/></g></mask>'
            f'<mask id="{uid}-f" maskUnits="userSpaceOnUse" x="-300" y="-300" width="600" height="600">'
            f'<rect x="-300" y="-300" width="600" height="600" fill="#fff"/>'
            f'<path d="{DOBRA}" fill="#000"/>'
            f'<rect x="-130" y="-70" width="250" height="28" rx="14" fill="#000"/>'
            f'<rect x="-130" y="-14" width="260" height="28" rx="14" fill="#000"/>'
            f'<rect x="-130" y="42" width="170" height="28" rx="14" fill="#000"/></mask>')
    corpo = (f'<g transform="translate(512 516) scale(1.12)">'
             f'<g mask="url(#{uid}-m)" fill="none" stroke="{tinta}" stroke-width="26" stroke-linejoin="round">'
             f'<g transform="rotate(-13) translate(-34 10)"><path d="{FOLHA}"/></g>'
             f'<g transform="rotate(-5) translate(-8 4)"><path d="{FOLHA}"/></g></g>'
             f'<g transform="rotate(5) translate(22 0)"><path d="{FOLHA}" fill="{tinta}" mask="url(#{uid}-f)"/>'
             f'<path d="{DOBRA}" fill="{tinta}" transform="translate(139 -179) scale(.55) translate(-139 179)"/></g></g>')
    return svg(corpo, defs)


def pequeno() -> str:
    """Favicon: sem sombras e sem a folha do meio; folhas maiores e linhas grossas."""
    corpo = (f'<g transform="translate(512 522) scale(1.28)">'
             f'<g transform="rotate(-10) translate(-30 8)"><path d="{FOLHA}" fill="#8E9CAC"/></g>'
             f'<g transform="rotate(4) translate(16 0)"><path d="{FOLHA}" fill="{PAPEL}"/>'
             f'<path d="{DOBRA}" fill="{AMBAR}"/>'
             f'<rect x="-130" y="-34" width="250" height="46" rx="23" fill="{TEAL}"/>'
             f'<rect x="-130" y="56" width="170" height="46" rx="23" fill="{AMBAR}"/></g></g>')
    return svg(corpo, "", f'<rect width="1024" height="1024" rx="226" fill="{TEAL}"/>')


def conceito_b() -> str:
    """Conceito B: a folha como mascote, com duas folhas espiando atras."""
    defs, bg = fundo("#FFFFFF", "#E9E6DC", "b")
    defs += sombra("b")
    corpo = ('<g transform="translate(512 540)" filter="url(#b-sh)">'
             '<g transform="rotate(-9) translate(-46 -6)"><rect x="-170" y="-210" width="340" height="420" rx="100" fill="#CBD3DC"/></g>'
             '<g transform="rotate(-3) translate(-20 -2)"><rect x="-170" y="-210" width="340" height="420" rx="100" fill="#8E9CAC"/></g>'
             f'<g transform="rotate(3) translate(14 0)"><rect x="-170" y="-210" width="340" height="420" rx="110" fill="{TEAL}"/>'
             f'<path d="M70,-210 V-160 Q70,-130 100,-130 H170 V-120 Q170,-210 90,-210 Z" fill="{AMBAR}"/>'
             f'<ellipse cx="-62" cy="-10" rx="26" ry="40" fill="{PAPEL}"/><ellipse cx="62" cy="-10" rx="26" ry="40" fill="{PAPEL}"/>'
             f'<path d="M-40,70 Q0,104 40,70" fill="none" stroke="{PAPEL}" stroke-width="16" stroke-linecap="round"/></g></g>')
    return svg(corpo, defs, bg)


def conceito_c() -> str:
    """Conceito C: uma folha cortada na diagonal (separar) que se encaixa (juntar)."""
    defs, bg = fundo("#FFFFFF", "#E9E6DC", "c")
    defs += sombra("c")
    defs += ('<clipPath id="c-a"><polygon points="-400,-400 400,-400 400,-150 -400,150"/></clipPath>'
             '<clipPath id="c-b"><polygon points="-400,150 400,-150 400,400 -400,400"/></clipPath>')
    folha = f'<rect x="-210" y="-260" width="420" height="520" rx="46" fill="{TEAL}"/>'
    corpo = ('<g transform="translate(512 520)">'
             f'<path d="M-232,92 L232,-92" stroke="{AMBAR}" stroke-width="30" stroke-linecap="round"/>'
             f'<g filter="url(#c-sh)"><g transform="translate(-16 -30)"><g clip-path="url(#c-a)">{folha}</g></g>'
             f'<g transform="translate(16 30)"><g clip-path="url(#c-b)">{folha}'
             f'<rect x="-120" y="70" width="230" height="26" rx="13" fill="{PAPEL}"/>'
             f'<rect x="-120" y="124" width="160" height="26" rx="13" fill="{PAPEL}"/></g></g></g></g>')
    return svg(corpo, defs, bg)


def escrever(rel: str, conteudo: str) -> None:
    (KIT / rel).write_text(conteudo, encoding="utf-8")


if __name__ == "__main__":
    escrever("concepts/a-pilha.svg", principal(PRIMARIA, "a"))
    escrever("concepts/b-mascote.svg", conceito_b())
    escrever("concepts/c-corte.svg", conceito_c())
    escrever("master/icon.svg", principal(PRIMARIA, "m"))          # master, primary
    escrever("variants/flat.svg", principal(PRIMARIA, "f", plano=True))
    escrever("variants/light.svg", principal(CLARA, "l"))
    escrever("variants/dark.svg", principal(ESCURA, "d"))
    escrever("variants/monochrome.svg", monocromatico())
    escrever("exports/favicon.svg", pequeno())
    print("SVGs gerados em", KIT)
