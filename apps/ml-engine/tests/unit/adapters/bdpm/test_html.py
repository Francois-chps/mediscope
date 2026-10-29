from datetime import date

import pytest

from mediscope_ml.ingestion.adapters.bdpm.html import (
    ANCHOR_TO_SECTION,
    fix_mojibake,
    parse_revision_date,
    split_sections,
)
from mediscope_ml.ingestion.domain.model import SectionCode


def _heading(anchor: str, title: str, body: str = "") -> str:
    return f'<p class="AmmAnnexeTitre2"><a name="{anchor}"></a>{title}</p><p>{body}</p>'


def test_fix_mojibake_restores_typographic_apostrophe() -> None:
    assert fix_mojibake("L\x92AUTORISATION") == "L\u2019AUTORISATION"


def test_fix_mojibake_keeps_bytes_undefined_in_cp1252() -> None:
    assert fix_mojibake("a\x81b") == "a\x81b"


def test_parse_revision_date() -> None:
    html = '<p class="DateNotif">ANSM - Mis à jour le : 17/08/2009</p>'
    assert parse_revision_date(html) == date(2009, 8, 17)


def test_parse_revision_date_returns_none_when_missing() -> None:
    assert parse_revision_date("<p>no date</p>") is None


@pytest.mark.parametrize(
    ("modern", "legacy"),
    [
        ("RcpContreindications", "RcpContreIndic"),
        ("RcpInteractionsMed", "RcpInteractions"),
        ("RcpFertGrossAllait", "RcpGrossAllait"),
    ],
)
def test_legacy_anchors_map_to_same_section(modern: str, legacy: str) -> None:
    assert ANCHOR_TO_SECTION[modern] == ANCHOR_TO_SECTION[legacy]


def test_split_sections_extracts_text_per_section() -> None:
    html = _heading("RcpIndicTherap", "4.1. Indications", "Pain.") + _heading(
        "RcpContreIndic", "4.3. Contre-indications", "Allergy."
    )

    assert split_sections(html) == {
        SectionCode.INDICATIONS: "4.1. Indications Pain.",
        SectionCode.CONTRAINDICATIONS: "4.3. Contre-indications Allergy.",
    }


def test_sub_anchors_stay_inside_their_section() -> None:
    html = _heading("RcpPosoAdmin", "4.2. Posologie", "Intro.") + _heading(
        "Rcp_4_2_PosoAdmin_1", "Adultes", "1 g."
    )

    assert (
        split_sections(html)[SectionCode.POSOLOGY]
        == "4.2. Posologie Intro. Adultes 1 g."
    )


def test_unmapped_main_anchor_bounds_previous_section() -> None:
    html = _heading("RcpSurdosage", "4.9. Surdosage", "Rare.") + _heading(
        "RcpPropPharmacologiques", "5. PROPRIETES", "Out of scope."
    )

    assert split_sections(html)[SectionCode.OVERDOSE] == "4.9. Surdosage Rare."


def test_misplaced_anchor_is_ignored() -> None:
    html = _heading("RcpPosoAdmin", "Adulte", "1 g.")

    assert SectionCode.POSOLOGY not in split_sections(html)
