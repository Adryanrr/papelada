# Icone do Papelada

- `master/icon.svg`: arte principal (quadrada, sem cantos arredondados; o sistema aplica a mascara).
- `variants/`: plana, clara, escura e monocromatica (uma tinta, sobre fundo claro).
- `exports/`: PNG 1024/512, favicon (SVG + PNG 16/32/48 renderizados nativamente), `icon.ico` (Windows) e `icon.icns` (macOS).
- Para regenerar: edite `assets/build_icons.py`, depois rode `python assets/build_icons.py` e `python assets/render_icons.py` (requer Chrome/Chromium e Pillow).
