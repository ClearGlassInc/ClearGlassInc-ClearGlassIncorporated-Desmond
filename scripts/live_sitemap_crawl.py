#!/usr/bin/env python3
"""Bounded, read-only production crawl of every locally declared sitemap URL."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
import ssl
import sys
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HOST = "www.clearglassinc.com"
USER_AGENT = "ClearGlass-Reliability-Crawler/1.0"
CATALOG_LINK_CLASSES = frozenset({"catalog-card", "cg-catalog-card"})


class _CatalogParser(HTMLParser):
    """Collect the product links rendered by the homepage catalog cards."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        href = attributes.get("href")
        if href and classes.intersection(CATALOG_LINK_CLASSES):
            self.hrefs.append(href)


@dataclass(frozen=True)
class Result:
    url: str
    status: int | None
    final_url: str | None
    content_type: str | None
    error: str | None

    @property
    def healthy(self) -> bool:
        return (
            self.error is None
            and self.status is not None
            and 200 <= self.status < 300
            and self.final_url is not None
            and self.final_url.startswith(f"https://{EXPECTED_HOST}/")
            and (self.content_type or "").split(";", 1)[0] in {"text/html", "application/xhtml+xml"}
        )


def sitemap_urls(root: Path = ROOT) -> list[str]:
    """Return the unique HTTPS URLs declared by every checked-in sitemap."""

    urls: set[str] = set()
    sitemap_files = sorted(root.glob("sitemap*.xml"))
    if not sitemap_files:
        raise ValueError("no sitemap*.xml files found")
    for path in sitemap_files:
        document = ET.parse(path).getroot()
        for node in document.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            url = (node.text or "").strip()
            if not url.startswith(f"https://{EXPECTED_HOST}/"):
                raise ValueError(f"non-canonical sitemap URL in {path.name}: {url!r}")
            urls.add(url)
    return sorted(urls)


def product_catalog_urls(root: Path = ROOT) -> list[str]:
    """Return canonical URLs for every homepage product card.

    Catalog-only operator surfaces can intentionally be ``noindex`` and therefore
    absent from the sitemap. They still need a production availability check.
    """

    index_path = root / "index.html"
    parser = _CatalogParser()
    parser.feed(index_path.read_text(encoding="utf-8"))
    if not parser.hrefs:
        raise ValueError("no product catalog links found in index.html")

    urls: set[str] = set()
    for href in parser.hrefs:
        relative, _fragment = urldefrag(href)
        url = urljoin(f"https://{EXPECTED_HOST}/", relative)
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != EXPECTED_HOST:
            raise ValueError(f"non-canonical product catalog URL: {href!r}")
        local_path = root / parsed.path.lstrip("/")
        if not local_path.is_file():
            raise ValueError(f"product catalog target does not exist: {href!r}")
        urls.add(url)
    return sorted(urls)


def production_urls(root: Path = ROOT) -> list[str]:
    """Combine indexable routes with every product surface without duplicates."""

    return sorted(set(sitemap_urls(root)).union(product_catalog_urls(root)))


def fetch(url: str, timeout: float) -> Result:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            # Read one byte so connection/body failures are surfaced without downloading whole pages.
            response.read(1)
            return Result(url, response.status, response.geturl(), response.headers.get("Content-Type"), None)
    except HTTPError as exc:
        return Result(url, exc.code, exc.geturl(), exc.headers.get("Content-Type"), str(exc))
    except (URLError, TimeoutError, OSError) as exc:
        return Result(url, None, None, None, str(exc))


def crawl(urls: list[str], *, timeout: float = 15, workers: int = 8) -> list[Result]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda url: fetch(url, timeout), urls))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("live-sitemap-crawl.json"))
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.timeout <= 0 or not 1 <= args.workers <= 16:
        parser.error("timeout must be positive and workers must be between 1 and 16")

    try:
        results = crawl(production_urls(), timeout=args.timeout, workers=args.workers)
    except (ET.ParseError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = {
        "summary": {
            "checked": len(results),
            "healthy": sum(result.healthy for result in results),
            "failed": sum(not result.healthy for result in results),
        },
        "results": [asdict(result) | {"healthy": result.healthy} for result in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    for result in results:
        if not result.healthy:
            print(f"FAIL {result.url}: status={result.status} final={result.final_url} error={result.error}")
    return 1 if payload["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
