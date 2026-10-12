#!/usr/bin/env python3
"""
AetherOS Wolf Brand Identity System -- master asset generator.

ONE MASTER WOLF. Every asset in this identity system derives from the single
geometric wolf head defined below (the WOLF geometry constants). Variants
change only fill treatment / composition / detail level -- never the symbol.

Outputs (relative to this file):
  svg/                 standalone SVG masters + lockups + favicon/app-icon
  png/favicons/        raster favicons 16..512 + favicon.ico
  png/icons/           app icons 128..1024
  png/_qa/             QA contact sheets (internal)
  index.html           brand presentation page

Raster previews use PIL with the exact polygon data used to build the SVG
paths, so what gets QA'd is what ships.
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SVG_DIR = HERE / "svg"
PNG_DIR = HERE / "png"
FAV_DIR = PNG_DIR / "favicons"
ICON_DIR = PNG_DIR / "icons"
QA_DIR = PNG_DIR / "_qa"

for d in (SVG_DIR, FAV_DIR, ICON_DIR, QA_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. COLOR SYSTEM
# ---------------------------------------------------------------------------

CYAN    = "#35E0FF"   # electric cyan   -- gradient head
BLUE    = "#3B82F6"   # electric blue   -- gradient core
VIOLET  = "#8B5CF6"   # violet          -- gradient tail
INK     = "#0A0F1E"   # deep-space navy -- primary ink / dark surfaces
PAPER   = "#F5F8FE"   # light surface
MIDNIGHT= "#070B16"   # pure dark stage
GRAYBG  = "#E7ECF5"

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def mix(c1, c2, t):
    a, b = hex2rgb(c1), hex2rgb(c2)
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))

GRAD_STOPS = ((0.0, CYAN), (0.52, BLUE), (1.0, VIOLET))

def grad_at(t):
    t = max(0.0, min(1.0, t))
    for (p0, c0), (p1, c1) in zip(GRAD_STOPS, GRAD_STOPS[1:]):
        if t <= p1:
            tt = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return mix(c0, c1, tt)
    return hex2rgb(VIOLET)

# ---------------------------------------------------------------------------
# 2. THE MASTER WOLF -- single source of truth
# ---------------------------------------------------------------------------
# Grid: 512 x 512, symmetry axis x = 256. Only the RIGHT half is authored;
# the left half is its programmatic mirror. This guarantees perfect symmetry.

CX = 256.0

SIL_R = [                       # right half, top-center -> clockwise -> chin
    (256.0,  88.0),             # skull dip between ears
    (300.0,  58.0),             # ear inner base
    (344.0,  10.0),             # EAR TIP
    (400.0, 120.0),             # ear outer base
    (388.0, 144.0),             # temple notch
    (474.0, 288.0),             # ruff spike -- single dominant flare / widest
    (396.0, 308.0),             # deep ruff notch
    (424.0, 380.0),             # jaw flick
    (330.0, 376.0),             # jaw cut inward
    (314.0, 420.0),             # muzzle side
    (256.0, 494.0),             # beard tip -- bottom center
]

EYE_R       = [(384.0, 212.0), (306.0, 240.0), (314.0, 268.0), (376.0, 246.0)]
NOSE        = [(256.0, 390.0), (288.0, 424.0), (256.0, 459.0), (224.0, 424.0)]
FOREHEAD    = [(256.0, 132.0), (276.0, 158.0), (256.0, 184.0), (236.0, 158.0)]
EAR_SHADE_R = [(302.0, 62.0), (344.0, 28.0), (368.0, 110.0)]
BRIDGE_R    = [(261.0, 264.0), (289.0, 290.0), (271.0, 388.0), (258.0, 388.0)]
FACE_CORE   = [(256.0, 108.0), (338.0, 232.0), (318.0, 374.0), (194.0, 374.0),
               (174.0, 232.0)]
SHADE_RUFF_R = [(388.0, 144.0), (474.0, 288.0), (396.0, 308.0), (424.0, 380.0),
                (330.0, 376.0), (356.0, 298.0)]

def mirror(pts):
    return [(round(2 * CX - x, 2), round(y, 2)) for x, y in pts]

OUTLINE = mirror(SIL_R)[::-1][:-1] + SIL_R[1:-1]      # closed loop, no dupes

def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

def scale_about(pts, f, cx, cy):
    return [(cx + (x - cx) * f, cy + (y - cy) * f) for x, y in pts]

def fmt(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s

def path_d(pts, close=True):
    s = f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"
    for x, y in pts[1:]:
        s += f"L{fmt(x)} {fmt(y)}"
    return s + ("Z" if close else "")

def poly_attr(pts):
    return " ".join(f"{fmt(x)},{fmt(y)}" for x, y in pts)

def wolf_d(features_scale=1.0, forehead=True):
    """Master path: silhouette + negative-space knockouts (fill evenodd)."""
    parts = [path_d(OUTLINE)]
    eye = scale_about(EYE_R, features_scale, *centroid(EYE_R))
    parts.append(path_d(mirror(eye)))
    parts.append(path_d(eye))
    nose = scale_about(NOSE, min(1.15, features_scale), *centroid(NOSE))
    parts.append(path_d(nose))
    if forehead and features_scale <= 1.0:
        parts.append(path_d(FOREHEAD))
    return " ".join(parts)

WOLF_D_FULL = wolf_d(1.0)           # full-detail master (with forehead mark)

DEFS = f"""  <defs>
  <linearGradient id="aog" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0" stop-color="{CYAN}"/>
    <stop offset="0.52" stop-color="{BLUE}"/>
    <stop offset="1" stop-color="{VIOLET}"/>
  </linearGradient>
  <radialGradient id="aov" cx="0.5" cy="0.56" r="0.62">
    <stop offset="0.72" stop-color="#000010" stop-opacity="0"/>
    <stop offset="1" stop-color="#000010" stop-opacity="0.30"/>
  </radialGradient>
  <linearGradient id="wmg" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0" stop-color="{BLUE}"/>
    <stop offset="1" stop-color="{VIOLET}"/>
  </linearGradient>
  <clipPath id="aoc"><path d="{WOLF_D_FULL}"/></clipPath>
  </defs>"""

WOLF_DETAIL = f"""
    <g clip-path="url(#aoc)">
      <polygon points="{poly_attr(FACE_CORE)}" fill="#FFFFFF" opacity="0.07"/>
      <polygon points="{poly_attr(SHADE_RUFF_R)}" fill="#000010" opacity="0.16"/>
      <polygon points="{poly_attr(mirror(SHADE_RUFF_R))}" fill="#000010" opacity="0.16"/>
      <polygon points="{poly_attr(EAR_SHADE_R)}" fill="#000010" opacity="0.22"/>
      <polygon points="{poly_attr(mirror(EAR_SHADE_R))}" fill="#000010" opacity="0.22"/>
      <polygon points="{poly_attr(BRIDGE_R)}" fill="#FFFFFF" opacity="0.10"/>
      <polygon points="{poly_attr(mirror(BRIDGE_R))}" fill="#FFFFFF" opacity="0.10"/>
      <rect x="-64" y="-64" width="640" height="640" fill="url(#aov)"/>
    </g>"""

def wolf_group(fill="url(#aog)", detail=True, feat_scale=1.0):
    """The master wolf as an embeddable group."""
    d = wolf_d(features_scale=feat_scale, forehead=(feat_scale <= 1.0))
    out = f'<path fill-rule="evenodd" fill="{fill}" d="{d}"/>'
    if detail:
        out += WOLF_DETAIL
    return out

# ---------------------------------------------------------------------------
# 3. WORDMARK -- custom geometric letterforms
# ---------------------------------------------------------------------------
# Skeleton + stroke system. Shared stroke weight (15 units @ cap-height 100),
# square terminals, miter corners: identical construction DNA to the wolf's
# chiseled planes. No external font is used anywhere.

STROKE = 15.0
GAP = 13.0

GLYPHS = {
    "A": dict(w=78, strokes=[[(2, 100), (32, 4), (46, 4), (76, 100)],
                             [(20, 66), (58, 66)]]),
    "e": dict(w=66, strokes=[[(60, 36), (20, 36), (8, 48), (8, 86), (20, 98),
                              (60, 98), (60, 74)],
                             [(8, 72), (60, 72)]]),
    "t": dict(w=50, strokes=[[(30, 2), (30, 96), (44, 96)],
                             [(10, 38), (52, 38)]]),
    "h": dict(w=62, strokes=[[(6, 2), (6, 100)],
                             [(6, 60), (24, 38), (42, 38), (60, 60), (60, 100)]]),
    "r": dict(w=48, strokes=[[(6, 38), (6, 100)],
                             [(6, 58), (22, 38), (44, 38)]]),
    "O": dict(oct=True, w=78),
    "S": dict(w=68, strokes=[[(60, 14), (52, 4), (20, 4), (8, 16), (8, 34),
                              (18, 44), (52, 44), (64, 56), (64, 86),
                              (54, 96), (20, 96), (10, 85)]]),
}

OCT_OUT = [(24, 4), (54, 4), (74, 24), (74, 76), (54, 96), (24, 96), (4, 76), (4, 24)]
OCT_IN  = [(30, 21), (48, 21), (57, 30), (57, 70), (48, 79), (30, 79), (21, 70), (21, 30)]

# Tagline capitals -- same construction rules, used only for the secondary line.
CAPS = {
    **{k: v for k, v in GLYPHS.items() if k in ("A", "O", "S")},
    "I": dict(w=12, strokes=[[(6, 4), (6, 96)]]),
    "P": dict(w=66, strokes=[[(6, 96), (6, 4), (54, 4), (66, 16), (66, 32),
                              (54, 44), (6, 44)]]),
    "E": dict(w=60, strokes=[[(60, 4), (6, 4), (6, 96), (60, 96)],
                             [(6, 50), (48, 50)]]),
    "R": dict(w=68, strokes=[[(6, 96), (6, 4), (54, 4), (66, 16), (66, 32),
                              (54, 44), (6, 44)],
                             [(36, 44), (64, 96)]]),
    "T": dict(w=72, strokes=[[(4, 4), (68, 4)], [(36, 4), (36, 96)]]),
    "N": dict(w=66, strokes=[[(6, 96), (6, 4), (60, 96), (60, 4)]]),
    "G": dict(w=68, strokes=[[(64, 14), (52, 4), (18, 4), (6, 16), (6, 84),
                              (18, 96), (60, 96), (60, 58), (38, 58)]]),
    "Y": dict(w=68, strokes=[[(4, 4), (34, 50), (64, 4)], [(34, 50), (34, 96)]]),
    "M": dict(w=70, strokes=[[(4, 96), (4, 4), (35, 56), (66, 4), (66, 96)]]),
}

def layout_word(word, gap=GAP):
    x, places = 0.0, []
    for ch in word:
        places.append((ch, x))
        x += GLYPHS[ch]["w"] + gap
    return places, x - gap

WORD_PLACES, WORD_W = layout_word("AetherOS")

def wordmark_group(scale=1.0, ink="#0A0F1E", os_ref=None, dx=0.0, dy=0.0):
    """Embeddable custom 'AetherOS'. 'Aether' solid ink; 'OS' gradient accent."""
    os_ref = os_ref or "url(#wmg)"
    els = []
    for i, (ch, xo) in enumerate(WORD_PLACES):
        ref = os_ref if i >= 6 else ink                     # indices 6,7 = O,S
        g = GLYPHS[ch]
        ox = dx + xo * scale
        oy = dy
        if g.get("oct"):
            els.append(
                f'<path transform="translate({fmt(ox)} {fmt(oy)}) scale({scale:g})" '
                f'fill-rule="evenodd" fill="{ref}" '
                f'd="{path_d(OCT_OUT)} {path_d(OCT_IN)}"/>')
        else:
            for st in g["strokes"]:
                pts = [(px, py) for px, py in st]
                els.append(
                    f'<path transform="translate({fmt(ox)} {fmt(oy)}) scale({scale:g})" '
                    f'fill="none" stroke="{ref}" stroke-width="{STROKE:g}" '
                    f'd="{path_d(pts, close=False)}"/>')
    return "".join(els)

TAG_TEXT = "AI OPERATING SYSTEM"

def tagline_units(ls=2.2):
    """Unscaled advance width of the full tagline at a given tracking."""
    x = 0.0
    for raw in TAG_TEXT:
        if raw == " ":
            x += 30 + ls
            continue
        x += CAPS[raw]["w"] + ls
    return x - ls

TAG_UNITS = tagline_units()

def tagline_group(target_width, color="#64748F", ls=2.2, dx=0.0, dy=0.0,
                  opacity=None):
    """Secondary tagline, auto-scaled so its rendered width == target_width.

    dx / dy are FINAL-canvas coordinates (no further scaling applied).
    Returns (group_markup, rendered_height).
    """
    scale = target_width / TAG_UNITS
    sw = STROKE * scale
    x, els = 0.0, []
    op = f' opacity="{opacity}"' if opacity is not None else ""
    for raw in TAG_TEXT:
        if raw == " ":
            x += 30 + ls
            continue
        g = CAPS[raw]
        ox = dx + x * scale
        oy = dy
        if g.get("oct"):
            o = [(px, py) for px, py in OCT_OUT]
            ic = [(px, py) for px, py in OCT_IN]
            els.append(
                f'<path transform="translate({fmt(ox)} {fmt(oy)}) scale({scale:.5f})" '
                f'fill-rule="evenodd" fill="{color}" '
                f'd="{path_d(o)} {path_d(ic)}"/>')
        else:
            for st in g["strokes"]:
                els.append(
                    f'<path transform="translate({fmt(ox)} {fmt(oy)}) scale({scale:.5f})" '
                    f'fill="none" stroke="{color}" stroke-width="{sw:g}" '
                    f'd="{path_d(st, close=False)}"/>')
        x += g["w"] + ls
    return f'<g{op}>{"".join(els)}</g>', 100 * scale

# ---------------------------------------------------------------------------
# 4. LOCKUP BUILDERS (standalone SVG files)
# ---------------------------------------------------------------------------

def svg_wrap(vb_w, vb_h, body, defs=DEFS, px=None):
    w_attr = f' width="{px}" height="{px}"' if px else \
             f' width="{fmt(vb_w)}" height="{fmt(vb_h)}"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {fmt(vb_w)} {fmt(vb_h)}"{w_attr}>'
            f'{defs}{body}</svg>')

def icon_svg(fill="url(#aog)", detail=True):
    return svg_wrap(512, 512, wolf_group(fill=fill, detail=detail))

def horizontal_lockup():
    icon_h = 128.0
    wm_s = 66.0 / 100.0
    ww = WORD_W * wm_s
    gap = 34.0
    H = 128.0
    W = icon_h + gap + ww
    ty = (H - 100.0 * wm_s) / 2 - 2
    body = (
        f'<g transform="scale({icon_h / 512:.5f})">{wolf_group()}</g>'
        f'<g transform="translate({fmt(icon_h + gap)} 0)">'
        f'{wordmark_group(scale=wm_s, ink="#FFFFFF")}</g>'
    )
    return svg_wrap(W, H, body)

def stacked_lockup():
    sw = 168.0
    wm_s = 88.0 / 100.0
    ww = WORD_W * wm_s
    SW = max(sw, ww)
    SH = sw + 44 + 88
    body = (
        f'<g transform="translate({fmt((SW - sw) / 2)} 0) scale({sw / 512:.5f})">'
        f'{wolf_group()}</g>'
        f'<g transform="translate({fmt((SW - ww) / 2)} {fmt(sw + 44)})">'
        f'{wordmark_group(scale=wm_s, ink="#FFFFFF")}</g>'
    )
    return svg_wrap(SW, SH, body)

def full_lockup():
    sw = 168.0
    wm_s = 88.0 / 100.0
    ww = WORD_W * wm_s
    tw = ww * 0.97                       # tagline just inside wordmark width
    gap1, gap2 = 40.0, 26.0
    tg, tg_h = tagline_group(target_width=tw, color="#9FB0D0",
                             dx=((max(sw, ww) - tw) / 2),
                             dy=sw + gap1 + 88 + gap2)
    FW = max(sw, ww)
    FH = sw + gap1 + 88 + gap2 + tg_h
    body = (
        f'<g transform="translate({fmt((FW - sw) / 2)} 0) scale({sw / 512:.5f})">'
        f'{wolf_group()}</g>'
        f'<g transform="translate({fmt((FW - ww) / 2)} {fmt(sw + gap1)})">'
        f'{wordmark_group(scale=wm_s, ink="#FFFFFF")}</g>'
        f'{tg}'
    )
    return svg_wrap(FW, FH, body)

def panel_lockup(bg, fg, tag_color=None):
    """Full lockup presented on a brand surface tile."""
    W, H = 720.0, 480.0
    sw = 176.0
    wm_s = 84.0 / 100.0
    ww = WORD_W * wm_s
    tw = ww * 0.97
    content_h = sw + 38 + 84 + 22 + 100 * (tw / TAG_UNITS)
    y0 = (H - content_h) / 2
    body = (
        f'<rect width="{fmt(W)}" height="{fmt(H)}" rx="28" fill="{bg}"/>' +
        f'<g transform="translate({fmt((W - sw) / 2)} {fmt(y0)}) '
        f'scale({sw / 512:.5f})">{wolf_group()}</g>' +
        f'<g transform="translate({fmt((W - ww) / 2)} {fmt(y0 + sw + 38)})">'
        f'{wordmark_group(scale=wm_s, ink=fg)}</g>' +
        tagline_group(target_width=tw, color=tag_color or fg,
                      dx=(W - tw) / 2,
                      dy=y0 + sw + 38 + 84 + 22,
                      opacity=0.66)[0]
    )
    return svg_wrap(W, H, body)

# ---------------------------------------------------------------------------
# 5. EMIT ALL SVG ASSETS
# ---------------------------------------------------------------------------

def write(p: Path, s: str):
    p.write_text(s, encoding="utf-8")
    print(f"  svg   {p.relative_to(HERE)}")

def emit_svgs():
    print("emitting SVG masters ...")
    # 1 -- Wolf icon only (gradient master)
    write(SVG_DIR / "wolf-icon.svg", icon_svg())
    # 5/6/7 -- Monochrome family (currentColor = themeable)
    write(SVG_DIR / "wolf-mono.svg", icon_svg(fill="currentColor", detail=False))
    write(SVG_DIR / "wolf-white.svg", icon_svg(fill="#FFFFFF", detail=False))
    write(SVG_DIR / "wolf-black.svg", icon_svg(fill="#05080F", detail=False))
    # Wordmark standalone (dark-context ink default)
    wm_vb_w = WORD_W + STROKE + 4
    write(SVG_DIR / "wordmark-aetheros.svg",
          svg_wrap(wm_vb_w, 108,
                   f'<g transform="translate({fmt(STROKE / 2 + 2)} 0)">'
                   f'{wordmark_group(ink="#FFFFFF")}</g>'))
    # 2/3/4 -- Lockups
    write(SVG_DIR / "logo-horizontal.svg", horizontal_lockup())
    write(SVG_DIR / "logo-stacked.svg", stacked_lockup())
    write(SVG_DIR / "logo-full.svg", full_lockup())
    # 8/9 -- Surface presentations
    write(SVG_DIR / "logo-dark-bg.svg", panel_lockup(MIDNIGHT, "#FFFFFF"))
    write(SVG_DIR / "logo-light-bg.svg", panel_lockup(PAPER, INK, tag_color="#5A6B8C"))
    # 10 -- Favicon master (small-size optimized: boosted features, flat fill)
    write(SVG_DIR / "favicon.svg",
          svg_wrap(512, 512, wolf_group(detail=False, feat_scale=1.18)))
    # 11 -- App icon
    app_wolf = (wolf_group(detail=False, feat_scale=1.08)
                .replace('id="aog"', 'id="aog2"'))
    app_defs = DEFS.replace('<clipPath id="aoc">', '<clipPath id="__x__">')
    app_body = (
        '<clipPath id="tile"><rect width="512" height="512" rx="116"/></clipPath>'
        '<linearGradient id="tilebg" x1="0%" y1="0%" x2="0%" y2="100%">'
        '<stop offset="0" stop-color="#121C39"/><stop offset="1" stop-color="#070B16"/>'
        '</linearGradient>'
    )
    write(SVG_DIR / "app-icon.svg",
          f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>{app_defs}{app_body}</defs>
  <g clip-path="url(#tile)"><rect width="512" height="512" fill="url(#tilebg)"/></g>
  <g transform="translate(63.5 67) scale(0.75)">{app_wolf}</g>
</svg>""")

# ---------------------------------------------------------------------------
# 6. RASTER EXPORTS (PIL -- same polygons as the SVGs)
# ---------------------------------------------------------------------------

_GRAD_CACHE = {}

def get_gradient(size):
    key = tuple(size)
    if key in _GRAD_CACHE:
        return _GRAD_CACHE[key]
    w, h = size
    base = Image.new("RGB", size)
    px = base.load()
    denom = float(w + h)
    for yy in range(h):
        row_t = yy / denom
        for xx in range(w):
            px[xx, yy] = grad_at(row_t + xx / denom)
    img = base.convert("RGBA")
    _GRAD_CACHE[key] = img
    return img

def render_wolf(size, variant="gradient", bg=None, feat_scale=1.0,
                detail=False, ss=4):
    S = max(16, size * ss)
    mask = Image.new("L", (S, S), 0)
    dr = ImageDraw.Draw(mask)
    k = S / 512.0

    def T(pts):
        return [(x * k, y * k) for x, y in pts]

    dr.polygon(T(OUTLINE), fill=255)
    eye = scale_about(EYE_R, feat_scale, *centroid(EYE_R))
    dr.polygon(T(mirror(eye)), fill=0)
    dr.polygon(T(eye), fill=0)
    nose = scale_about(NOSE, min(1.15, feat_scale), *centroid(NOSE))
    dr.polygon(T(nose), fill=0)
    if detail and feat_scale <= 1.0:
        dr.polygon(T(FOREHEAD), fill=0)

    img = Image.new("RGBA", (S, S),
                    hex2rgb(bg) + (255,) if bg else (0, 0, 0, 0))

    if variant == "gradient":
        art = get_gradient((S, S))
    elif variant == "white":
        art = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    elif variant == "black":
        art = Image.new("RGBA", (S, S), (5, 8, 15, 255))
    else:
        rgb = hex2rgb(variant)
        art = Image.new("RGBA", (S, S), rgb + (255,))
    img.paste(art, (0, 0), mask)

    if detail:
        ov = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        for poly, col, a in (
            (FACE_CORE, (255, 255, 255), 18),
            (SHADE_RUFF_R, (0, 0, 16), 42),
            (mirror(SHADE_RUFF_R), (0, 0, 16), 42),
            (EAR_SHADE_R, (0, 0, 16), 58),
            (mirror(EAR_SHADE_R), (0, 0, 16), 58),
        ):
            tmp = Image.new("L", (S, S), 0)
            ImageDraw.Draw(tmp).polygon(T(poly), fill=a)
            ov.paste(Image.new("RGBA", (S, S), col + (255,)), (0, 0), tmp)
        img = Image.alpha_composite(img, ov)

    if ss > 1:
        img = img.resize((size, size), Image.LANCZOS)
    return img

def render_app_icon(size, ss=2):
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    tile = Image.new("RGBA", (S, S))
    tp = tile.load()
    for yy in range(S):
        row = mix("#121C39", "#070B16", yy / S)
        for xx in range(S):
            tp[xx, yy] = row + (255,)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, S - 1, S - 1], radius=int(S * 0.225), fill=255)
    img.paste(tile, (0, 0), mask)
    ws = int(S * 0.75)
    wolf = render_wolf(ws, variant="gradient", feat_scale=1.08, ss=1)
    k = S / 512.0
    off_x = (S - ws) // 2
    off_y = off_x + round(3.5 * k)
    img.alpha_composite(wolf, (off_x, off_y))
    return img.resize((size, size), Image.LANCZOS)

def emit_rasters():
    print("rasterizing favicons / icons ...")
    fav_sizes = [16, 24, 32, 48, 64, 96, 128, 256, 512]
    for s in fav_sizes:
        img = render_wolf(s, "gradient", feat_scale=1.18)
        img.save(FAV_DIR / f"favicon_{s}.png")
        print(f"  png   png/favicons/favicon_{s}.png")
    base = render_wolf(48, "gradient", feat_scale=1.18)
    base.save(HERE.parent / "favicon.ico",
              sizes=[(16, 16), (32, 32), (48, 48)])
    print("  ico   ../favicon.ico")

    for s in (128, 256, 512, 1024):
        render_app_icon(s).save(ICON_DIR / f"app_icon_{s}.png")
        print(f"  png   png/icons/app_icon_{s}.png")

    # QA contact sheet ------------------------------------------------------
    def paste_bg(sheet, img, xy, bg):
        cell = Image.new("RGBA", img.size, hex2rgb(bg) + (255,))
        cell.alpha_composite(img)
        sheet.alpha_composite(cell, xy)

    variants = [
        ("master / midnight", "gradient", MIDNIGHT, 1.0, True),
        ("master / black", "gradient", "#000000", 1.0, True),
        ("master / paper", "gradient", PAPER, 1.0, True),
        ("master / gray", "gradient", GRAYBG, 1.0, True),
        ("favicon / black", "gradient", "#000000", 1.18, False),
        ("favicon / navy", "gradient", MIDNIGHT, 1.18, False),
        ("favicon / white", "gradient", "#FFFFFF", 1.18, False),
        ("white wolf / navy", "white", MIDNIGHT, 1.0, False),
        ("black wolf / paper", "black", PAPER, 1.0, False),
    ]
    cell, pad, label_h = 192, 14, 0
    cols = 5
    rows = (len(variants) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * (cell + pad) + pad,
                               rows * (cell + pad) + pad), (18, 22, 34, 255))
    for i, (_name, var, bg, fs, det) in enumerate(variants):
        r, c = divmod(i, cols)
        big = render_wolf(cell, var, bg=bg, feat_scale=fs, detail=det)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + pad)
        paste_bg(sheet, big, (x, y), bg)
        for j, s in enumerate((48, 24, 16)):
            sm = render_wolf(s, var, feat_scale=max(fs, 1.18), detail=False)
            paste_bg(sheet, sm, (x + j * 56, y + cell + 6), bg)
    sheet.convert("RGB").save(QA_DIR / "contact_sheet.png")
    print("  qa    png/_qa/contact_sheet.png")

    # Lockup proportion preview --------------------------------------------
    lw, lh = 1400, 420
    lk = Image.new("RGBA", (lw, lh), hex2rgb(MIDNIGHT) + (255,))
    wolf = render_wolf(300, "gradient", detail=True)
    lk.alpha_composite(wolf, (40, 60))
    d = ImageDraw.Draw(lk)
    sx, sy, sc = 400, 130, 1.05
    for ch, xo in WORD_PLACES:
        g = GLYPHS[ch]
        ox = sx + xo * sc
        if g.get("oct"):
            d.polygon([(ox + px * sc, sy + py * sc) for px, py in OCT_OUT],
                      fill=(255, 255, 255, 255))
            d.polygon([(ox + px * sc, sy + py * sc) for px, py in OCT_IN],
                      fill=hex2rgb(MIDNIGHT))
        else:
            col = (255, 255, 255, 255) if ch not in ("O", "S") else (139, 92, 246, 255)
            for st in g["strokes"]:
                pts = [(ox + px * sc, sy + py * sc) for px, py in st]
                d.line(pts, fill=col, width=int(STROKE * sc), joint="curve")
    lk.convert("RGB").save(QA_DIR / "lockup_preview.png")
    print("  qa    png/_qa/lockup_preview.png")

# ---------------------------------------------------------------------------
# 7. BRAND PRESENTATION PAGE
# ---------------------------------------------------------------------------

CSS = """
:root{--cyan:#35E0FF;--blue:#3B82F6;--violet:#8B5CF6;--ink:#0A0F1E;
--mid:#070B16;--paper:#F5F8FE;--mut:#8CA0C4}
*{margin:0;padding:0;box-sizing:border-box}
body{background:#04060D;color:#E7EEFB;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:64px 32px 120px}
h1{font-size:15px;letter-spacing:.42em;color:var(--mut);text-transform:uppercase;font-weight:600}
h2{font-size:26px;margin:0 0 6px;font-weight:650}
h2 span{background:linear-gradient(90deg,var(--cyan),var(--blue),var(--violet));
-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:#93A5C8;font-size:14px;line-height:1.6;max-width:640px;margin-bottom:34px}
section{margin-top:72px}
.hero{display:flex;gap:48px;align-items:center;justify-content:center;
background:radial-gradient(900px 420px at 50% 0,#0C1730 0%,#04060D 70%);
border:1px solid #14203C;border-radius:24px;padding:72px 40px;margin-top:40px}
.hero img{width:min(430px,80%)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px}
.card{background:#0A1122;border:1px solid #16233F;border-radius:16px;padding:22px;
display:flex;flex-direction:column;align-items:center;gap:16px;min-height:190px;
justify-content:center}
.card.dark{background:#04060D}.card.light{background:var(--paper)}
.card.black{background:#000}.card.gray{background:var(--paper)}
.card img{max-width:82%;max-height:110px}
.card .nm{font-size:11px;color:var(--mut);letter-spacing:.14em;text-transform:uppercase;text-align:center}
.row{display:flex;align-items:center;justify-content:center;gap:28px;flex-wrap:wrap;
background:#0A1122;border:1px solid #16233F;border-radius:16px;padding:26px}
.sw{display:flex;align-items:flex-end;gap:10px}
.sz{text-align:center;font-size:10px;color:var(--mut)}
.bgs{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.tile{border-radius:14px;padding:30px;display:flex;align-items:center;justify-content:center;min-height:170px;border:1px solid rgba(255,255,255,.06)}
.palette{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
.pal{border-radius:14px;padding:18px;height:120px;display:flex;flex-direction:column;justify-content:flex-end;border:1px solid rgba(255,255,255,.08)}
.pal b{font-size:13px}.pal i{font-size:11px;opacity:.75;font-style:normal}
.rules{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.rule{border-radius:14px;padding:22px;font-size:13px;line-height:1.7}
.ok{background:#07131F;border:1px solid #123047}.no{background:#170B12;border:1px solid #3B1230}
.rule h3{font-size:12px;letter-spacing:.18em;text-transform:uppercase;margin-bottom:10px}
.ok h3{color:#39D98A}.no h3{color:#FF6B9D}
.checker{background:repeating-conic-gradient(#2A3350 0% 25%,#1B2340 0% 50%) 0 0/22px 22px}
footer{margin-top:90px;color:#54648A;font-size:12px;text-align:center;line-height:2}
img.wm{filter:none}
"""

def build_index():
    print("building index.html ...")

    def card(src, name, cls="", extra_style=""):
        c = f"card {cls}".strip()
        st = f' style="{extra_style}"' if extra_style else ""
        return (f'<div class="{c}"><img src="{src}" alt="{name}"{st}>'
                f'<div class="nm">{name}</div></div>')

    fav_row = "".join(
        f'<div class="sz"><img src="png/favicons/favicon_{s}.png" width="{s}" '
        f'height="{s}" alt=""><br>{s}px</div>'
        for s in (16, 24, 32, 48, 64, 96, 128, 256))

    svg_ladder = "".join(
        f'<div class="sz"><img src="svg/wolf-icon.svg" width="{s}" height="{s}" '
        f'alt=""><br>{s}px</div>'
        for s in (16, 32, 64, 128, 256, 512))

    bg_tiles = ""
    for bg, cls, name in (("#000000", "", "Black"), ("#070B16", "", "Dark Navy"),
                          ("#FFFFFF", "", "White"), ("#E7ECF5", "", "Light Gray")):
        style = f'background:{bg};' + ("color:#0A0F1E;" if bg in ("#FFFFFF", "#E7ECF5") else "")
        bg_tiles += (f'<div class="tile {cls}" style="{style}">'
                     f'<img src="svg/wolf-icon.svg" width="120" alt=""></div>')
    bg_tiles += ('<div class="tile checker">'
                 '<img src="svg/wolf-icon.svg" width="120" alt=""></div>')

    pal = "".join(
        f'<div class="pal" style="background:linear-gradient(135deg,{c1},{c2})">'
        f'<b>{n}</b><i>{h}</i></div>'
        for n, h, c1, c2 in (
            ("Electric Cyan", CYAN, CYAN, CYAN), ("Electric Blue", BLUE, BLUE, BLUE),
            ("Violet", VIOLET, VIOLET, VIOLET), ("Deep-Space Navy", INK, "#182440", INK),
            ("Signature Gradient", "—", CYAN, VIOLET)))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AetherOS — Wolf Brand Identity System</title>
<style>{CSS}</style>
</head>
<body><div class="wrap">

<h1>AetherOS · Brand Identity · v1.0</h1>

<div class="hero">
  <img src="svg/logo-full.svg" alt="AetherOS full lockup">
</div>

<section>
  <h2>The <span>Master Wolf</span></h2>
  <p class="sub">One symbol. Every asset below is derived from this single
  geometric wolf head — ears, brow planes, cheek ruff spikes, muzzle bridge,
  negative-space eyes and nose. Nothing else may ever stand beside it.</p>
  <div class="row"><img src="svg/wolf-icon.svg" width="360" alt="master wolf"></div>
</section>

<section>
  <h2>Logo <span>Configurations</span></h2>
  <p class="sub">Eleven canonical configurations. All derive from the master
  wolf; no secondary symbol exists.</p>
  <div class="grid">
    {card('svg/wolf-icon.svg', '01 · Wolf Icon Only')}
    {card('svg/logo-horizontal.svg', '02 · Wolf + AetherOS Horizontal', '', 'max-width:95%')}
    {card('svg/logo-stacked.svg', '03 · Wolf Above AetherOS')}
    {card('svg/logo-full.svg', '04 · Wolf + AetherOS + Tagline', '', 'max-width:95%')}
    {card('svg/wolf-mono.svg', '05 · Monochrome Wolf', 'light', 'color:#0A0F1E')}
    {card('svg/wolf-white.svg', '06 · White Wolf', 'dark')}
    {card('svg/wolf-black.svg', '07 · Black Wolf', 'gray')}
    {card('svg/logo-dark-bg.svg', '08 · Dark Background Version', '', 'max-width:95%')}
    {card('svg/logo-light-bg.svg', '09 · Light Background Version', '', 'max-width:95%')}
    {card('svg/favicon.svg', '10 · Favicon Master')}
    {card('png/icons/app_icon_256.png', '11 · App Icon')}
  </div>
</section>

<section>
  <h2>Color <span>System</span></h2>
  <p class="sub">One coherent gradient — electric cyan through electric blue
  into violet. Flat, enterprise-grade, no neon glow, no metal, no cartoon.</p>
  <div class="palette">{pal}</div>
</section>

<section>
  <h2>Scale <span>Ladder</span></h2>
  <p class="sub">True raster favicon renders at every size. At 16px the wolf
  keeps its ears, eyes and snout — never a blob.</p>
  <div class="row">{fav_row}</div>
  <p class="sub" style="margin-top:18px">SVG vector ladder:</p>
  <div class="row">{svg_ladder}</div>
</section>

<section>
  <h2>Background <span>Tolerance</span></h2>
  <div class="bgs">{bg_tiles}</div>
</section>

<section>
  <h2>Usage <span>Rules</span></h2>
  <div class="rules">
    <div class="rule ok"><h3>Always</h3>
      Wolf first — the symbol identifies the brand alone.<br>
      Clear space ≥ 25% of wolf height on all sides.<br>
      Minimum size: 16px (favicon), 24px (inline), 88px (lockup).<br>
      Use the exact gradient stops; never rotate or skew the wolf.<br>
      Mono contexts: pure white or pure black wolf only.
    </div>
    <div class="rule no"><h3>Never</h3>
      Do not replace the wolf with an abstract “A”.<br>
      Do not add a second competing symbol beside it.<br>
      Do not outline, shadow, bevel, animate parts, or add glow.<br>
      Do not recolor outside the defined palette.<br>
      Do not place the wolf on low-contrast mid-tone backgrounds.
    </div>
  </div>
</section>

<footer>
  AETHEROS · AI OPERATING SYSTEM<br>
  One wolf. One wordmark. One brand. One visual language.
</footer>

</div></body></html>
"""
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print("  html  index.html")

if __name__ == "__main__":
    emit_svgs()
    emit_rasters()
    build_index()
    print("done.")
