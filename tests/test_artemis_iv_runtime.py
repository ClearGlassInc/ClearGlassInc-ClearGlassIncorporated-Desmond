"""artemis-iv.html: the tactical-core script must start, and must not invent feed data.

The page was uploaded as a half-merged pair of revisions: one named its state
`state` and called `updateFeedCount()`/`logMission()`/`loadCves()`, the other
named it `S` and called `setFeed()`/`logM()`/`loadNVD()`. 134 references to 22
names had no definition. Reproduced in Chromium on 2026-10-23: the first,
`updateFeedCount()`, threw during start-up, so nothing after it ran (no feed
loaded, no panel renderer, mission log empty), and a timer then threw
`state is not defined` six times.

Making the script run also revives code that had never executed in production,
so the same fix keeps it honest: no feed is marked ONLINE on a timer, no
headline is credited to a named outlet unless GDELT returned it, no uptime is
made up, and the synthetic widgets say they are synthetic.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "artemis-iv.html"

# Every name the engine referenced without defining, as of the upload.
UNDEFINED_AT_UPLOAD = (
    "state", "logMission", "escapeHtml", "setFeed", "updateFeedCount", "NVD_FB",
    "loadCves", "fallbackCves", "syncThreatCves", "geo2canvas", "ACTORS",
    "startThreatMap", "mapAnim", "renderURLhaus", "renderThreatFox", "renderGHSA",
    "loadThreatFox", "loadGHSA", "loadADSB",
)


def _engine() -> str:
    html = PAGE.read_text(encoding="utf-8")
    start = html.index("/* ARTEMIS IV — live open-source intelligence engine")
    js = html[start:html.index("</script>", start)]
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return "\n".join(line for line in js.splitlines() if not line.lstrip().startswith("//"))


def test_every_name_missing_at_upload_is_now_defined_or_gone() -> None:
    code = _engine()
    for name in UNDEFINED_AT_UPLOAD:
        if re.search(rf"(?<![\w$.]){name}\b", code):
            assert re.search(rf"\b(?:function|const|let|var)\s+{name}\b", code), (
                f"{name} is referenced but not defined"
            )


def test_feeds_load_at_start_up() -> None:
    code = _engine()
    # The merge kept runAllFeeds() but lost the call, so no feed ever loaded.
    assert re.search(r"^  runAllFeeds\(\);$", code, re.M)
    assert "function setFeed(key, status, count)" in code


def test_no_feed_is_reported_online_without_data() -> None:
    code = _engine()
    assert "bringFeedOnline" not in code
    assert not re.search(r"status\s*=\s*'ONLINE'", code)
    # Unimplemented feeds say so instead of "fetching…" forever.
    assert "setFeed(k, 'NOT CONNECTED')" in code


def test_no_invented_headlines_or_cve_sets() -> None:
    code = _engine()
    for outlet in ("'WIRED'", "'KREBS'", "'BLEEPCOMP'", "'SECWEEK'"):
        assert outlet not in code
    assert "GDELT_STATIC" not in code and "NVD_FB" not in code


def test_feed_status_card_reports_status_not_made_up_uptime() -> None:
    code = _engine()
    body = re.search(r"function renderFeedUptime\(\) \{(.*?)\n  \}", code, re.S)
    assert body, "renderFeedUptime missing"
    assert "Math.random" not in body.group(1)


def test_synthetic_widgets_are_labelled() -> None:
    html = PAGE.read_text(encoding="utf-8")
    assert "24H THREAT FORECAST · SIMULATED" in html
    assert "CVE SEVERITY · LAST 14D · SIMULATED" in html
    templates = re.search(r"const notifTemplates = \[(.*?)\];", html, re.S)
    assert templates
    titles = re.findall(r"title:'([^']*)'", templates.group(1))
    assert titles and all(t.startswith("Demo · ") for t in titles), titles


def test_data_file_actors_are_mapped_onto_the_renderer_shape() -> None:
    # assets/artemis-iv-data.js uses status/industries; renderThreatPanel calls
    # a.level.toLowerCase(), which threw on the data-file shape.
    assert "level: a.status, sectors: a.industries" in _engine()


def test_page_palette_claims_cmd_k_before_the_control_surface() -> None:
    code = _engine()
    handler = re.search(r"window\.addEventListener\('keydown', \(e\) => \{(.*?)\n  \}, true\);", code, re.S)
    assert handler, "palette shortcut must be a window capture-phase listener"
    assert "e.stopPropagation()" in handler.group(1)
