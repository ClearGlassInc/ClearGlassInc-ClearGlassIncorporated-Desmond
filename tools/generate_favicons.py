#!/usr/bin/env python3
"""Regenerate the site's browser-tab / install icon set from one source image.

Every indexable page links its tab icon to ``/logo.png`` (see the
"Browser Tab Icons" block in each ``<head>``), and the PWA manifests point at
``/icon-192.png`` and ``/icon-512.png``. This script derives that whole family
from a single square-cropped source so the tab, the iOS home screen, and the
installed PWA never drift apart.

Note the site's *visible* logo is ``assets/images/clearglass-logo.png`` — a
different asset. This script deliberately does not touch it.

Usage::

    python3 tools/generate_favicons.py --source path/to/source.png
    python3 tools/generate_favicons.py --source src.png --dry-run

Requires Pillow (``pip install Pillow``); everything else is stdlib.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - dependency guard
    sys.exit("Pillow is required: pip install Pillow")

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# (filename, edge length in px). logo.png is the master the <link rel="icon">
# tags resolve to; the rest are size-specific derivatives.
PNG_TARGETS: list[tuple[str, int]] = [
    ("logo.png", 1024),
    ("icon-512.png", 512),
    ("icon-192.png", 192),
    ("apple-touch-icon.png", 180),
    ("favicon-32.png", 32),
    ("favicon-16.png", 16),
]

# Smallest icon produced; a crop below this leaves nothing usable to scale.
MIN_EDGE = min(edge for _, edge in PNG_TARGETS)

# Windows tiles and legacy browsers read the multi-resolution .ico.
ICO_NAME = "favicon.ico"
ICO_SIZES = [(16, 16), (32, 32), (48, 48)]

MANIFEST = "site.webmanifest"


def square_crop(img: Image.Image, zoom: float = 1.0) -> Image.Image:
    """Center-crop to a square so no resize distorts the artwork.

    ``zoom`` above 1.0 crops tighter about the centre before scaling, trading
    away the artwork's outer margin to keep the central device legible at 16px.

    Raises ValueError if the factor is not finite or crops away so much that
    less than the smallest icon remains -- without this, NaN fails the int()
    conversion and large factors yield a 0x0 crop that dies inside Pillow.
    """
    if not math.isfinite(zoom) or zoom < 1.0:
        raise ValueError(f"zoom must be a finite factor >= 1.0, got {zoom!r}")
    source_edge = min(img.size)
    edge = int(source_edge / zoom)
    if edge < MIN_EDGE:
        raise ValueError(
            f"zoom {zoom:g} crops a {source_edge}px source to {edge}px, "
            f"below the {MIN_EDGE}px smallest icon; use at most "
            f"{source_edge / MIN_EDGE:.1f}"
        )
    left = (img.size[0] - edge) // 2
    top = (img.size[1] - edge) // 2
    return img.crop((left, top, left + edge, top + edge))


def load_source(path: pathlib.Path, circle: bool, zoom: float = 1.0) -> Image.Image:
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        # Flatten onto black in circle mode and white otherwise. Circular icons
        # are cropped to the disc anyway, and these artworks sit on dark fields,
        # so white would ring the edge with a bright halo.
        backdrop = (0, 0, 0, 255) if circle else (255, 255, 255, 255)
        flat = Image.new("RGBA", img.size, backdrop)
        flat.alpha_composite(img)
        img = flat
    return square_crop(img.convert("RGB"), zoom)


def circle_mask(edge: int, supersample: int = 8) -> Image.Image:
    """Antialiased circular alpha mask, drawn large and downsampled.

    Built per output size rather than once on the source: resampling an
    already-masked image softens the disc edge badly at 16px.
    """
    big = edge * supersample
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
    return mask.resize((edge, edge), Image.LANCZOS)


def render(base: Image.Image, edge: int, circle: bool) -> Image.Image:
    out = base.resize((edge, edge), Image.LANCZOS)
    if circle:
        out = out.convert("RGBA")
        out.putalpha(circle_mask(edge))
    return out


def sync_manifest(edge: int, dry_run: bool) -> None:
    """Keep site.webmanifest's declared logo.png size honest."""
    path = REPO_ROOT / MANIFEST
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for icon in data.get("icons", []):
        if icon.get("src", "").lstrip("/") == "logo.png":
            want = f"{edge}x{edge}"
            if icon.get("sizes") != want:
                icon["sizes"] = want
                changed = True
    if not changed:
        return
    print(f"  {MANIFEST} -> logo.png sizes {edge}x{edge}")
    if not dry_run:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        help="Path to the source image (square or better; it is center-cropped).",
    )
    parser.add_argument(
        "--circle",
        action="store_true",
        help="Mask each icon to a circle with a transparent surround, so tabs "
             "render a round badge instead of a square one.",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=1.0,
        metavar="FACTOR",
        help="Crop tighter about the centre before scaling (1.0 = whole image). "
             "Raises legibility at 16px by dropping the outer margin.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be written without touching any file.",
    )
    args = parser.parse_args()

    source = pathlib.Path(args.source)
    if not source.is_absolute():
        source = (REPO_ROOT / source).resolve()
    if not source.exists():
        print(f"source image not found: {source}", file=sys.stderr)
        return 1

    try:
        img = load_source(source, args.circle, args.zoom)
    except ValueError as exc:
        print(f"--zoom: {exc}", file=sys.stderr)
        return 1
    src_edge = img.size[0]
    shape = "circle" if args.circle else "square"
    print(f"source {source.name}: cropped to {src_edge}x{src_edge} "
          f"({shape}, zoom {args.zoom:g})")

    # logo.png has no declared size of its own, so clamp it rather than fake a
    # larger master than the source can support; the manifest then follows it.
    # Every other target's size is quoted in a manifest or a <link> tag, so it
    # must be produced at exactly that size even when that means upscaling.
    master_name, master_default = PNG_TARGETS[0]
    master_edge = min(master_default, src_edge)

    for name, edge in PNG_TARGETS:
        if name == master_name:
            edge = master_edge
        out = REPO_ROOT / name
        print(f"  {name} -> {edge}x{edge}")
        if not args.dry_run:
            render(img, edge, args.circle).save(out, "PNG", optimize=True)

    ico = REPO_ROOT / ICO_NAME
    print(f"  {ICO_NAME} -> {', '.join(f'{w}x{h}' for w, h in ICO_SIZES)}")
    if not args.dry_run:
        render(img, 48, args.circle).save(ico, "ICO", sizes=ICO_SIZES)

    sync_manifest(master_edge, args.dry_run)

    if args.dry_run:
        print("dry run: nothing written")
    else:
        print("done — bump VERSION in sw.js so cached tabs pick up the new icon")
    return 0


if __name__ == "__main__":
    sys.exit(main())
