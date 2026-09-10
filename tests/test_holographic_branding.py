from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEAL = "assets/images/clearglass-holographic-seal.png"

# Two ways a page may declare the ClearGlass tab logo, both resolving to the
# same seal artwork: straight at the 512px master, or at the sized family
# tools/generate_favicons.py derives from it. The homepage takes the sized
# route so the mark survives being drawn at 16px; every other page still
# points at the master.
TAB_ICON_DECLARATIONS = (
    f'href="/{SEAL}"',
    'href="/favicon.ico"',
)

# What the homepage must name once it opts into the sized family.
SIZED_TAB_ICONS = (
    'href="/favicon.ico"',
    'href="/favicon-32.png"',
    'href="/favicon-16.png"',
    'href="/apple-touch-icon.png"',
)


def test_home_and_blog_feature_the_holographic_seal() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    blog = (ROOT / "blog" / "index.html").read_text(encoding="utf-8")

    assert homepage.count(SEAL) >= 4
    assert 'class="hero-seal"' in homepage
    assert blog.count(f"../{SEAL}") >= 2
    assert 'class="radar-seal"' in blog
    assert "prefers-reduced-motion:reduce" in homepage


def test_every_public_html_page_declares_a_tab_icon() -> None:
    excluded = {"google23RWyXWkoxqgArev8achU8IfVxYC5EIUAYBsuTYKLFM.html"}
    public_pages = [
        page
        for page in ROOT.rglob("*.html")
        if not {"node_modules", ".next"} & set(page.parts) and page.name not in excluded
    ]

    missing = [
        str(page.relative_to(ROOT))
        for page in public_pages
        if not any(
            declaration in page.read_text(encoding="utf-8", errors="ignore")
            for declaration in TAB_ICON_DECLARATIONS
        )
    ]
    assert not missing, f"Public pages without the canonical desktop tab logo: {missing}"


def test_homepage_declares_the_sized_tab_icon_family() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")

    for declaration in SIZED_TAB_ICONS:
        assert declaration in homepage, declaration

    # The 512px master is what made the 16px tab unreadable; keep it out of the
    # homepage's icon slots even though it still carries the visible branding.
    assert f'rel="icon" href="/{SEAL}"' not in homepage


def test_tab_icon_assets_and_manifest_exist() -> None:
    for asset in (
        "logo.png",
        "favicon.ico",
        "favicon-16.png",
        "favicon-32.png",
        "apple-touch-icon.png",
        "safari-pinned-tab.svg",
        "site.webmanifest",
    ):
        assert (ROOT / asset).is_file(), asset



def test_desktop_tab_logo_uses_the_existing_holographic_asset() -> None:
    seal = ROOT / SEAL
    assert seal.is_file()

    manifest = (ROOT / "site.webmanifest").read_text(encoding="utf-8")
    assert '"src": "/assets/images/clearglass-holographic-seal.png"' in manifest
    assert '"sizes": "512x512"' in manifest
