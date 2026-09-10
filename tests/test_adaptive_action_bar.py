"""Static regression gates for the adaptive Artemis action architecture."""

from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class _ActionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_bar = False
        self.actions: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        classes = values.get("class", "").split()
        if tag == "div" and "adaptive-action-bar" in classes:
            self.in_bar = True
        elif self.in_bar and tag == "a":
            self.actions.append(values)

    def handle_endtag(self, tag: str) -> None:
        if self.in_bar and tag == "div":
            self.in_bar = False


def test_artemis_actions_keep_routes_and_priority_metadata() -> None:
    parser = _ActionParser()
    parser.feed((ROOT / "artemis-self-evolving-platform.html").read_text(encoding="utf-8"))

    assert [action["href"] for action in parser.actions] == [
        "CLEARGLASSINC_ARTEMIS_SELF_EVOLVING_PLATFORM_BLUEPRINT.md",
        "#architecture",
        "#loop",
        "tools/windows/ultimate-windows-gpu-advanced-graphics-optimization.ps1",
    ]
    assert [action["data-action-priority"] for action in parser.actions] == [
        "primary",
        "secondary",
        "secondary",
        "overflow",
    ]


def test_overflow_primitive_has_accessibility_and_container_guards() -> None:
    script = (ROOT / "adaptive-action-bar.js").read_text(encoding="utf-8")
    styles = (ROOT / "adaptive-action-bar.css").read_text(encoding="utf-8")

    for behavior in (
        "ResizeObserver",
        'aria-haspopup", "menu',
        'aria-expanded',
        'aria-controls',
        'event.key === "Escape"',
        'event.key === "ArrowDown"',
        'document.addEventListener("pointerdown"',
        "more.focus()",
    ):
        assert behavior in script

    for guard in (
        "container: actionbar / inline-size",
        "max-width: 100%",
        "min-width: 0",
        "min-height: 44px",
        "prefers-reduced-motion: reduce",
        "--z-dropdown: 60",
    ):
        assert guard in styles
