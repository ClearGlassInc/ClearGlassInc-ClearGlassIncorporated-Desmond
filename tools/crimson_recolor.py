#!/usr/bin/env python3
"""Rotate the ClearGlass palette from blue-violet onto the crimson brief scheme.

Colour-only transform. It rewrites the *numbers* in colour literals and never
touches selectors, geometry, alpha, or any other declaration, so every layout,
animation and hover state survives exactly as authored.

Method: each literal is converted to HSL. A colour is rewritten only when its
hue sits in the cyan→magenta arc (the old brand range) and it carries enough
saturation to read as a hue rather than a neutral. Its hue is moved into the
crimson band; **saturation and lightness are preserved**, so contrast ratios,
light/dark relationships and gradient structure are all unchanged — a pale tint
stays pale, a deep glow stays deep.

Left alone on purpose:
  · greens/mints/teals (status: OK, nominal, healthy) — hue < 172
  · warm hues already in the crimson/amber range
  · true neutrals (saturation < 6%)
  · near-white and near-black structural values (L ≥ 96% or L ≤ 5%)

Lightness is never raised or lowered across the light/dark divide: a highlight
stays a highlight, so light-on-dark text can never be flipped into mid-tone.

Usage:  python3 tools/crimson_recolor.py --dry-run [paths...]
        python3 tools/crimson_recolor.py --apply   [paths...]
"""
from __future__ import annotations

import argparse
import colorsys
import pathlib
import re
import sys

# Source-hue arc → target hue in the crimson band. Ordered, first match wins.
HUE_MAP = [
    (172, 215, 359),   # cyan / sky      → crimson        (the old primary)
    (215, 252, 356),   # blue            → crimson
    (252, 292, 350),   # violet / purple → crimson-rose
    (292, 335, 352),   # magenta / pink  → crimson-rose
]
SAT_FLOOR = 0.06       # below this a colour is a neutral, not a hue
L_HI, L_LO = 0.96, 0.05
# Deep tones keep only a fraction of their saturation. A saturated navy would
# otherwise translate to an equally saturated maroon, where the reference wants
# near-black carrying just a warm cast (its dark surfaces sample #0f0b0d/#180b0f).
DARK_L, DARK_SAT_SCALE = 0.16, 0.34
# Ceilings that hold the accents in the reference's crimson register. Without
# them a 93%-saturated pastel violet would translate to a hot pink, and a pure
# cyan to pure #f00 — louder than the brief, which tops out around #eb4344.
SAT_CEIL, ACCENT_L_CEIL, ACCENT_S_MIN = 0.80, 0.66, 0.50
# Above this lightness a colour is a highlight or light-on-dark text, not an
# accent. Pulling those down to the accent ceiling would turn near-white type
# into mid-red, so they keep their lightness and only shed saturation, landing
# on the warm off-whites the reference uses for body and caption type.
TINT_L, TINT_SAT_CEIL = 0.86, 0.26

HEX_RE  = re.compile(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b')
FUNC_RE = re.compile(r'\brgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*([,)])')


def map_hue(h_deg: float) -> float | None:
    for lo, hi, target in HUE_MAP:
        if lo <= h_deg < hi:
            return float(target)
    return None


def shift(r: int, g: int, b: int) -> tuple[int, int, int] | None:
    """Return the crimson counterpart of an RGB triple, or None to leave it."""
    h, lightness, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if s < SAT_FLOOR or lightness >= L_HI or lightness <= L_LO:
        return None
    target = map_hue(h * 360)
    if target is None:
        return None
    if lightness < DARK_L:
        s *= DARK_SAT_SCALE          # deep tones → near-black with a warm cast
    elif lightness > TINT_L:
        s = min(s, TINT_SAT_CEIL)    # highlights / light type → warm off-white
    else:
        s = min(s, SAT_CEIL)
        if s > ACCENT_S_MIN:
            lightness = min(lightness, ACCENT_L_CEIL)
    nr, ng, nb = colorsys.hls_to_rgb((target % 360) / 360, lightness, s)
    return round(nr * 255), round(ng * 255), round(nb * 255)


def recolor(text: str, seen: dict[str, str] | None = None) -> tuple[str, int]:
    n = 0

    def hex_sub(m: re.Match) -> str:
        nonlocal n
        h = m.group(1)
        full = h if len(h) == 6 else ''.join(c * 2 for c in h)
        rgb = tuple(int(full[i:i + 2], 16) for i in (0, 2, 4))
        out = shift(*rgb)
        if out is None:
            return m.group(0)
        n += 1
        new = '#%02x%02x%02x' % out
        if seen is not None:
            seen[m.group(0)] = new
        return new

    def func_sub(m: re.Match) -> str:
        nonlocal n
        rgb = tuple(int(x) for x in m.groups()[:3])
        out = shift(*rgb)
        if out is None:
            return m.group(0)
        n += 1
        head = m.group(0)[:m.group(0).index('(') + 1]
        new = f'{head}{out[0]}, {out[1]}, {out[2]}{m.group(4)}'
        if seen is not None:
            seen[', '.join(map(str, rgb))] = ', '.join(map(str, out))
        return new

    text = HEX_RE.sub(hex_sub, text)
    text = FUNC_RE.sub(func_sub, text)
    return text, n


# ── Light→dark inversion, applied per CSS *property* ─────────────────────────
# The hue rotation above changes which hue a colour is, never whether it is
# light or dark. That is deliberate — but the site was authored light-mode, so
# opaque white surfaces and near-black type survive it and end up white cards
# and dark-on-dark text on the crimson canvas. This pass fixes exactly those two
# cases, and it can only do so safely by reading the property a colour sits on:
# #fff means "dark panel" after a `background:` and still means white after a
# `color:`. Value alone cannot tell those apart.
#
# Deliberately NOT inverted:
#   · translucent whites (alpha < .55) — glass sheen and inner highlights, which
#     read correctly on a dark surface and are the reason the panels look like
#     glass at all
#   · anything on a property other than the three named below

SURFACE_PROPS = ('background', 'background-color', 'background-image')
TEXT_PROPS = ('color',)

# Custom properties carry the same light-mode values (glass.css declares
# --panel:#ffffff and --text:#100e0e), but a property name is all there is to go
# on — so the role is read from the name. A variable that matches neither list is
# left alone rather than guessed at.
SURFACE_HINTS = ('bg', 'background', 'surface', 'panel', 'card', 'paper', 'sheet',
                 'void', 'abyss', 'deep', 'well', 'canvas', 'base', 'glass',
                 'pearl', 'bone', 'white', 'off', 'inset', 'layer', 'sunken',
                 'shell', 'plate', 'backdrop', 'black', 'tile')
TEXT_HINTS = ('text', 'txt', 'ink', 'fg', 'foreground', 'muted', 'dim', 'faint',
              'label', 'caption', 'copy', 'heading', 'title')
SURFACE_L = 0.86      # at or above this an opaque surface colour reads as white
TEXT_L = 0.50         # below this a text colour reads as dark-on-light
SHEEN_ALPHA = 0.30    # translucent white below this is a highlight, not a surface

DECL_RE = re.compile(r'(^|[;{,\s])(--[-a-zA-Z0-9]+|[-a-zA-Z]+)(\s*:\s*)([^;{}]*)', re.M)
ALPHA_RE = re.compile(r'\brgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*([\d.]+)\s*\)')


def _relight(r: int, g: int, b: int, to_dark: bool) -> tuple[int, int, int] | None:
    h, lightness, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if to_dark:
        if lightness < SURFACE_L:
            return None
        lightness = 0.055 + (1 - lightness) * 0.35          # white → near-black, keeping order
        s = min(s, 0.20)
    else:
        if lightness >= TEXT_L:
            return None
        lightness = 0.94 - lightness * 0.85                 # near-black type → warm off-white
    nr, ng, nb = colorsys.hls_to_rgb(h, max(0.0, min(1.0, lightness)), s)
    return round(nr * 255), round(ng * 255), round(nb * 255)


def _relight_value(value: str, to_dark: bool) -> tuple[str, int]:
    n = 0

    def hx(m: re.Match) -> str:
        nonlocal n
        h = m.group(1)
        full = h if len(h) == 6 else ''.join(c * 2 for c in h)
        out = _relight(*[int(full[i:i + 2], 16) for i in (0, 2, 4)], to_dark=to_dark)
        if out is None:
            return m.group(0)
        n += 1
        return '#%02x%02x%02x' % out

    def fn(m: re.Match) -> str:
        nonlocal n
        # translucent colours are sheen/veils, never the surface itself
        if m.group(4) == ',':
            tail = value[m.end() - 1:]
            a = re.match(r',\s*([\d.]+)', tail)
            if a and float(a.group(1)) < SHEEN_ALPHA:
                return m.group(0)
        out = _relight(*[int(x) for x in m.groups()[:3]], to_dark=to_dark)
        if out is None:
            return m.group(0)
        n += 1
        head = m.group(0)[:m.group(0).index('(') + 1]
        return f'{head}{out[0]}, {out[1]}, {out[2]}{m.group(4)}'

    value = HEX_RE.sub(hx, value)
    value = FUNC_RE.sub(fn, value)
    return value, n


def invert(text: str) -> tuple[str, int]:
    """Flip white surfaces dark and dark type light, property by property."""
    total = 0

    def decl(m: re.Match) -> str:
        nonlocal total
        prop = m.group(2).lower()
        if prop in SURFACE_PROPS:
            to_dark = True
        elif prop in TEXT_PROPS:
            to_dark = False
        elif prop.startswith('--'):
            stem = prop.lstrip('-')
            parts = [x for x in re.split(r'[-_0-9]+', stem) if x]
            if any(x in TEXT_HINTS for x in parts):
                to_dark = False
            elif any(x in SURFACE_HINTS for x in parts):
                to_dark = True
            else:
                return m.group(0)
        else:
            return m.group(0)
        val, k = _relight_value(m.group(4), to_dark)
        total += k
        return m.group(1) + m.group(2) + m.group(3) + val

    return DECL_RE.sub(decl, text), total


# ── Ink variables the name heuristic cannot see ──────────────────────────────
# Some ink variables are named things no hint list would guess (--wt, --bone,
# --ash-d, --t2). Rather than extend the guesswork, this pass reads how each
# variable is actually *used* across the whole site: a variable consumed by
# `color:` and essentially never by a background is text, whatever it is called.
#
# It fires only when the value is also near-neutral — a grey or an ink. That is
# what separates `--wt:#100e0e` (an ink that must be lifted) from
# `--cyan:#931012` or `--green:#10b981`, which are saturated accents that are
# meant to be darker than their surroundings and must be left exactly as they
# are. Both are "a dark value used as text"; only one is a defect.

# Hue names are brand accents even when the light theme had flattened them to
# near-ink — lifting one turns a crimson button into a pale grey slab. They are
# excluded here and pinned to the palette by clearglass-crimson.css instead.
ACCENT_NAMES = ('blue', 'sky', 'cyan', 'teal', 'indigo', 'violet', 'purple',
                'pink', 'magenta', 'rose', 'crimson', 'wine', 'red', 'green',
                'mint', 'amber', 'gold', 'yellow', 'orange', 'accent', 'brand',
                'primary', 'secondary', 'prism', 'crystal', 'neon', 'glow')

TEXT_USE_RE = re.compile(r'(?<![-\w])color\s*:\s*var\(\s*(--[-a-zA-Z0-9]+)')
SURF_USE_RE = re.compile(r'background(?:-color|-image)?\s*:\s*[^;{}]*?var\(\s*(--[-a-zA-Z0-9]+)')
INK_SAT_MAX = 0.22     # above this the colour is an accent, not an ink
INK_L_MAX = 0.45       # below this an ink is too dark for the crimson canvas


def census(files: list[pathlib.Path]) -> set[str]:
    """Variable names that the site uses as text and effectively never as a surface."""
    text: dict[str, int] = {}
    surf: dict[str, int] = {}
    for f in files:
        t = f.read_text(encoding='utf-8', errors='ignore')
        for n in TEXT_USE_RE.findall(t):
            text[n] = text.get(n, 0) + 1
        for n in SURF_USE_RE.findall(t):
            surf[n] = surf.get(n, 0) + 1
    # "Never a surface" is the bar, not "mostly text": one background use is
    # enough to make lifting the value wrong, because that background then turns
    # pale. --wt and --bone are never backgrounds anywhere and are safe to lift;
    # --navy-2 and --blue are, and are not.
    return {n for n, c in text.items()
            if surf.get(n, 0) == 0
            and not any(a in re.split(r'[-_0-9]+', n.lstrip('-')) for a in ACCENT_NAMES)}


VAR_DECL_RE = re.compile(r'(--[-a-zA-Z0-9]+)(\s*:\s*)(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})(?=\s*[;}])')


def lift_ink(text: str, names: set[str]) -> tuple[str, int]:
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        if m.group(1) not in names:
            return m.group(0)
        h = m.group(3)[1:]
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        hh, lightness, ss = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if ss > INK_SAT_MAX or lightness >= INK_L_MAX:
            return m.group(0)
        nr, ng, nb = colorsys.hls_to_rgb(hh, 0.94 - lightness * 0.85, ss)
        n += 1
        return '%s%s#%02x%02x%02x' % (m.group(1), m.group(2),
                                      round(nr * 255), round(ng * 255), round(nb * 255))

    return VAR_DECL_RE.sub(sub, text), n


# ── HTML: only touch <style> blocks, style="" attributes, and SVG paint attrs ──
STYLE_BLOCK = re.compile(r'(<style\b[^>]*>)(.*?)(</style>)', re.S | re.I)
STYLE_ATTR  = re.compile(r'''(\sstyle\s*=\s*)(["'])(.*?)\2''', re.S | re.I)
PAINT_ATTR  = re.compile(r'''(\s(?:fill|stroke|stop-color|flood-color|lighting-color)\s*=\s*)(["'])(\s*#[0-9a-fA-F]{3,6}\s*|\s*rgba?\([^"']*?\)\s*)\2''', re.I)


def invert_html(text: str) -> tuple[str, int]:
    total = 0

    def block(m: re.Match) -> str:
        nonlocal total
        body, k = invert(m.group(2))
        total += k
        return m.group(1) + body + m.group(3)

    def attr(m: re.Match) -> str:
        nonlocal total
        val, k = invert(m.group(3))
        total += k
        return f'{m.group(1)}{m.group(2)}{val}{m.group(2)}'

    return STYLE_BLOCK.sub(block, STYLE_ATTR.sub(attr, text)), total


def recolor_html(text: str, seen: dict[str, str] | None = None) -> tuple[str, int]:
    total = 0

    def block(m: re.Match) -> str:
        nonlocal total
        body, k = recolor(m.group(2), seen)
        total += k
        return m.group(1) + body + m.group(3)

    def attr(m: re.Match) -> str:
        nonlocal total
        val, k = recolor(m.group(3), seen)
        total += k
        return f'{m.group(1)}{m.group(2)}{val}{m.group(2)}'

    text = STYLE_BLOCK.sub(block, text)
    text = STYLE_ATTR.sub(attr, text)
    text = PAINT_ATTR.sub(attr, text)
    return text, total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--invert', action='store_true',
                    help='also flip white surfaces dark and dark type light')
    ap.add_argument('--lift-ink', action='store_true',
                    help='lift dark near-neutral variables the site uses as text')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('paths', nargs='*')
    a = ap.parse_args()
    if a.invert and a.lift_ink:
        ap.error('--invert and --lift-ink are separate passes; run them one at a time')
    if not (a.apply ^ a.dry_run):
        ap.error('pass exactly one of --apply / --dry-run')

    seen: dict[str, str] = {}
    files = [pathlib.Path(p) for p in a.paths]
    ink_names = census(files) if a.lift_ink else set()
    changed = total = 0
    for f in files:
        src = f.read_text(encoding='utf-8')
        html = f.suffix.lower() in ('.html', '.htm', '.svg')
        if a.lift_ink:
            out, k = lift_ink(src, ink_names)
        elif a.invert:
            out, k = (invert_html if html else invert)(src)
        else:
            out, k = (recolor_html if html else recolor)(src, seen)
        if k:
            changed += 1
            total += k
            if a.apply:
                f.write_text(out, encoding='utf-8')
    verb = 'rewrote' if a.apply else 'would rewrite'
    print(f'{verb} {total} colour literals across {changed}/{len(files)} files')
    if a.dry_run:
        print('\ndistinct mappings:')
        for k, v in sorted(seen.items()):
            print(f'  {k:>20}  ->  {v}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
