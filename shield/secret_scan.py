"""Secret scanner for the Shield tree and its evidence artifacts.

    python3 -m shield.secret_scan PATH [PATH ...]

Exit 1 when anything matches. Findings name the file, line and rule, never the
matched text. Patterns are assembled at runtime so this file does not contain
the markers it looks for (the G01 workflow greps shield/ for them literally).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_B64_KEY = r"[A-Za-z0-9+/]{43}="
# "".join, not "+": the compiler folds "a" + "b" into one constant in the .pyc,
# which would put the literal marker back into shield/__pycache__.
RULES = {
    "pem-private-key": re.compile("".join(("-----BEGIN (?:RSA |EC |OPENSSH |DSA )?", "PRIVATE",
                                           " KEY-----"))),
    "wireguard-private-key-line": re.compile("".join(("Private", r"Key\s*=\s*", _B64_KEY))),
    "private-key-field": re.compile("".join((r"private[_-]?key[\"']?\s*[:=]\s*[\"']?", _B64_KEY)),
                                    re.I),
    "stripe-live-secret": re.compile("".join(("(?:sk|rk)_", "live_", r"[0-9A-Za-z]{8,}"))),
    "stripe-secret-variable": re.compile("".join(("STRIPE_", "SECRET"))),
}
FORBIDDEN_NAMES = {".env"}
FORBIDDEN_SUFFIXES = {".key", ".pem"}
MAX_BYTES = 2_000_000


def scan(paths: list[Path]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for root in paths:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in files:
            if path.name in FORBIDDEN_NAMES or path.suffix in FORBIDDEN_SUFFIXES:
                findings.append({"file": str(path), "line": 0, "rule": "forbidden-file-type"})
                continue
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(text.splitlines(), 1):
                for rule, pattern in RULES.items():
                    if pattern.search(line):
                        findings.append({"file": str(path), "line": number, "rule": rule})
    return findings


def main(argv: list[str]) -> int:
    findings = scan([Path(p) for p in argv])
    print(json.dumps({"findings": findings, "count": len(findings)}, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
