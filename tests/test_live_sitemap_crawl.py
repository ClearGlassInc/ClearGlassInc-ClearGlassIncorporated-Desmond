from pathlib import Path

import pytest

from scripts import live_sitemap_crawl as crawler


def test_sitemap_urls_combines_and_deduplicates_files(tmp_path: Path) -> None:
    body = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://www.clearglassinc.com/</loc></url></urlset>"""
    (tmp_path / "sitemap.xml").write_text(body, encoding="utf-8")
    (tmp_path / "sitemap-extra.xml").write_text(body, encoding="utf-8")
    assert crawler.sitemap_urls(tmp_path) == ["https://www.clearglassinc.com/"]


def test_sitemap_urls_rejects_noncanonical_origin(tmp_path: Path) -> None:
    (tmp_path / "sitemap.xml").write_text(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url>'
        '<loc>http://example.com/</loc></url></urlset>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-canonical"):
        crawler.sitemap_urls(tmp_path)


def test_product_catalog_urls_includes_noindex_product_surfaces(tmp_path: Path) -> None:
    (tmp_path / "operator.html").write_text("<meta name='robots' content='noindex'>", encoding="utf-8")
    (tmp_path / "index.html").write_text(
        '<a class="catalog-card featured" href="operator.html#status">Operator</a>'
        '<a class="cg-catalog-card" href="operator.html">Duplicate</a>',
        encoding="utf-8",
    )

    assert crawler.product_catalog_urls(tmp_path) == [
        "https://www.clearglassinc.com/operator.html"
    ]


def test_product_catalog_urls_rejects_missing_target(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<a class="catalog-card" href="missing.html">Missing</a>', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="target does not exist"):
        crawler.product_catalog_urls(tmp_path)


def test_production_urls_combines_sitemap_and_catalog(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<a class="catalog-card" href="product.html">Product</a>', encoding="utf-8"
    )
    (tmp_path / "product.html").write_text("product", encoding="utf-8")
    (tmp_path / "sitemap.xml").write_text(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url>'
        '<loc>https://www.clearglassinc.com/</loc></url></urlset>',
        encoding="utf-8",
    )

    assert crawler.production_urls(tmp_path) == [
        "https://www.clearglassinc.com/",
        "https://www.clearglassinc.com/product.html",
    ]


def test_result_requires_2xx_html_on_canonical_host() -> None:
    assert crawler.Result(
        "https://www.clearglassinc.com/", 200, "https://www.clearglassinc.com/", "text/html; charset=utf-8", None
    ).healthy
    assert not crawler.Result(
        "https://www.clearglassinc.com/", 200, "https://example.com/", "text/html", None
    ).healthy
    assert not crawler.Result(
        "https://www.clearglassinc.com/", 404, "https://www.clearglassinc.com/", "text/html", "not found"
    ).healthy
