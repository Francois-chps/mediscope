"""Pure parsing helpers for BDPM SmPC HTML documents."""

import re
from datetime import date, datetime

from selectolax.lexbor import LexborHTMLParser

from mediscope_ml.ingestion.domain.model import SectionCode


def _cp1252_char(byte: int) -> str:
    try:
        return bytes([byte]).decode("cp1252")
    except UnicodeDecodeError:  # 5 bytes are undefined in cp1252: keep them as-is
        return chr(byte)


# Upstream text was cp1252 decoded as latin-1: U+0080-U+009F stand for cp1252 bytes.
_C1_TO_CP1252 = {code: _cp1252_char(code) for code in range(0x80, 0xA0)}
# Main anchors only: sub-anchors such as "Rcp_4_2_PosoAdmin_1" contain "_".
_MAIN_ANCHOR = re.compile(r'<[aA]\s[^>]*?name="(Rcp[A-Za-z]+)"')
_REVISION_DATE = re.compile(r'class="DateNotif"[^>]*>.*?(\d{2}/\d{2}/\d{4})', re.DOTALL)

ANCHOR_TO_SECTION: dict[str, SectionCode] = {
    # Modern and legacy anchor families (see ADR-002)
    "RcpIndicTherap": SectionCode.INDICATIONS,
    "RcpPosoAdmin": SectionCode.POSOLOGY,
    "RcpContreindications": SectionCode.CONTRAINDICATIONS,
    "RcpContreIndic": SectionCode.CONTRAINDICATIONS,
    "RcpMisesEnGarde": SectionCode.WARNINGS,
    "RcpInteractionsMed": SectionCode.INTERACTIONS,
    "RcpInteractions": SectionCode.INTERACTIONS,
    "RcpFertGrossAllait": SectionCode.PREGNANCY,
    "RcpGrossAllait": SectionCode.PREGNANCY,
    "RcpConduite": SectionCode.DRIVING,
    "RcpEffetsIndesirables": SectionCode.ADVERSE_EFFECTS,
    "RcpSurdosage": SectionCode.OVERDOSE,
}


def fix_mojibake(html: str) -> str:
    return html.translate(_C1_TO_CP1252)


def parse_revision_date(html: str) -> date | None:
    match = _REVISION_DATE.search(html)
    return datetime.strptime(match[1], "%d/%m/%Y").date() if match else None


def split_sections(html: str) -> dict[SectionCode, str]:
    """Cut the document at every main anchor and keep mapped, well-placed sections.

    Every main anchor bounds the previous section, even unmapped ones
    (e.g. RcpDonneesPharmaceutiques), so 4.9 never spills into 5.
    An anchor whose text does not start with its section number is misplaced and ignored.
    """
    anchors = list(_MAIN_ANCHOR.finditer(html))
    if not anchors:
        return {}
    ends = [anchor.start() for anchor in anchors[1:]] + [len(html)]

    ends = [anchor.start() for anchor in anchors[1:]] + [len(html)]
    sections: dict[SectionCode, str] = {}
    for anchor, end in zip(anchors, ends, strict=True):
        code = ANCHOR_TO_SECTION.get(anchor[1])
        if code is None or code in sections:
            continue
        text = html_to_text(html[anchor.start() : end])
        if text.startswith(f"{code.value}."):
            sections[code] = text
    return sections


def html_to_text(fragment: str) -> str:
    return " ".join(LexborHTMLParser(fragment).text(separator=" ").split())
