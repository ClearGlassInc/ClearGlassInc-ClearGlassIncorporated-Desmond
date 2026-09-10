# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import pytest

pytest.importorskip("PIL")

from PIL import Image  # noqa: E402

from tools.generate_favicons import (  # noqa: E402
    MIN_EDGE,
    PNG_TARGETS,
    circle_mask,
    render,
    square_crop,
)


def square(edge: int = 512) -> Image.Image:
    return Image.new("RGB", (edge, edge), (10, 20, 40))


# ── square_crop ───────────────────────────────────────────────────────────────

def test_zoom_one_keeps_the_whole_square():
    assert square_crop(square(512), 1.0).size == (512, 512)


def test_zoom_crops_about_the_centre():
    cropped = square_crop(square(512), 1.6)
    assert cropped.size == (320, 320)


def test_oblong_source_is_squared():
    assert square_crop(Image.new("RGB", (800, 500))).size == (500, 500)


@pytest.mark.parametrize("zoom", [float("nan"), float("inf"), float("-inf"), 0.5, 0.0])
def test_non_finite_or_under_one_zoom_is_rejected(zoom):
    # NaN used to reach int() and large factors produced a 0x0 crop that died
    # inside Pillow; both must surface as a controlled ValueError instead.
    with pytest.raises(ValueError):
        square_crop(square(512), zoom)


def test_zoom_that_crops_below_the_smallest_icon_is_rejected():
    with pytest.raises(ValueError, match="smallest icon"):
        square_crop(square(512), 512 / (MIN_EDGE - 1))


def test_largest_usable_zoom_is_accepted():
    edge = square_crop(square(512), 512 / MIN_EDGE).size[0]
    assert edge == MIN_EDGE


# ── render / circle_mask ──────────────────────────────────────────────────────

def test_square_render_has_no_alpha():
    assert render(square(512), 32, circle=False).mode == "RGB"


def test_circle_render_is_transparent_at_the_corners():
    out = render(square(512), 32, circle=True)
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((16, 16))[3] == 255


def test_circle_mask_is_opaque_at_centre_and_clear_at_corner():
    mask = circle_mask(16)
    assert mask.size == (16, 16)
    assert mask.getpixel((8, 8)) == 255
    assert mask.getpixel((0, 0)) == 0


# ── target table ──────────────────────────────────────────────────────────────

def test_logo_is_the_master_target():
    assert PNG_TARGETS[0][0] == "logo.png"


def test_min_edge_matches_the_smallest_declared_target():
    assert MIN_EDGE == min(edge for _, edge in PNG_TARGETS)
