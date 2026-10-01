"""The founder credential ledger publishes a designation only with its register.

A protected designation (a licence or a certification mark) is a claim a client
relies on, and its issuer keeps a public register that settles it. The homepage
founder section may name one only when the same section links to that issuer's
register, so a reader can check it. docs/FOUNDER_CREDENTIALS_REGISTER.md lists
the claims held back until that evidence is on file.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOMEPAGE = ROOT / "index.html"
VCARD = ROOT / "assets" / "founder" / "desmond-otieno-odhiambo.vcf"

# Designation pattern -> hosts of the issuer's public register or verification tool.
REGISTERS = {
    r"\bPatent Agent\b": ("oedci.uspto.gov",),
    r"\bTrademark Agent\b": ("cpata-cabamc.ca",),
    r"\b(?:CISSP|CCSP|CSSLP|Certified in Cybersecurity)\b": ("isc2.org",),
    r"\b(?:PMP|CAPM)\b": ("pmi.org",),
    r"\bCEH\b|Certified Ethical Hacker": ("eccouncil.org",),
    r"\bCPIM\b": ("apics.org", "ascm.org"),
    r"\b(?:CISA|CISM|CRISC|CGEIT|CDPSE)\b": ("isaca.org",),
}


def founder_section() -> str:
    source = HOMEPAGE.read_text(encoding="utf-8")
    match = re.search(r'<section[^>]*\bid="founder".*?</section>', source, re.S)
    assert match, "index.html has no #founder section"
    return match.group(0)


def test_each_designation_links_to_its_register() -> None:
    section = founder_section()
    text = re.sub(r"<[^>]+>", " ", section)
    hrefs = re.findall(r'href="([^"]+)"', section)
    missing = [
        f"{pattern} needs a link to {' or '.join(hosts)}"
        for pattern, hosts in REGISTERS.items()
        if re.search(pattern, text)
        and not any(host in href for href in hrefs for host in hosts)
    ]
    assert not missing, "\n".join(missing)


def test_ledger_count_matches_entries() -> None:
    """The count is the no-JavaScript fallback, so it has to be true as written."""
    section = founder_section()
    entries = len(re.findall(r'class="credential-item"', section))
    stated = re.search(r'id="founderLedgerCount"[^>]*>(\d+) entries<', section)
    assert stated, "founderLedgerCount is missing its entry count"
    assert int(stated.group(1)) == entries


def test_vcard_matches_the_published_contact() -> None:
    # Bytes, not read_text: universal newlines would hide a missing CRLF (RFC 2426).
    card = VCARD.read_bytes().decode("utf-8")
    assert card.startswith("BEGIN:VCARD\r\n") and card.rstrip("\r\n").endswith("END:VCARD")
    email = re.search(r"^EMAIL[^:]*:(.+?)\r?$", card, re.M)
    assert email, "vCard has no EMAIL line"
    assert f'href="mailto:{email.group(1)}"' in founder_section()
