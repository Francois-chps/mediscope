import csv
import re
import sys
from datetime import date
from pathlib import Path

import pytest

from mediscope_ml.ingestion.adapters.bdpm.source import BdpmSmpcSource
from mediscope_ml.ingestion.adapters.in_memory import (
    DeterministicEmbedder,
    InMemoryChunkStore,
)
from mediscope_ml.ingestion.application.ingest_smpcs import IngestSmpcs
from mediscope_ml.ingestion.domain.model import (
    INGESTED_SECTIONS,
    DataSnapshot,
    SectionCode,
    Smpc,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "bdpm" / "CIS_RCP_sample.csv"
SNAPSHOT = DataSnapshot(source="BDPM", exported_on=date(2022, 4, 15))
_C1_CONTROL_CHARS = re.compile(r"[\x80-\x9f]")


def _cis_with_anchor(anchor: str) -> str:
    """Find a fixture row by its raw HTML, so tests don't hardcode CIS codes."""
    csv.field_size_limit(sys.maxsize)
    with FIXTURE.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter="\t")
        next(reader)
        return next(cis for cis, html in reader if f'name="{anchor}"' in html)


@pytest.fixture
def source() -> BdpmSmpcSource:
    return BdpmSmpcSource(FIXTURE, SNAPSHOT)


@pytest.fixture
def smpcs(source: BdpmSmpcSource) -> dict[str, Smpc]:
    return {smpc.cis_code.value: smpc for smpc in source.fetch()}


def _codes(smpc: Smpc) -> set[SectionCode]:
    return {section.code for section in smpc.sections}


def test_empty_rows_are_skipped_and_counted(source: BdpmSmpcSource) -> None:
    list(source.fetch())

    assert source.skipped["empty"] == 1


def test_some_smpc_has_all_ingested_sections(smpcs: dict[str, Smpc]) -> None:
    assert any(INGESTED_SECTIONS <= _codes(smpc) for smpc in smpcs.values())


def test_legacy_anchors_are_recognised(smpcs: dict[str, Smpc]) -> None:
    legacy = smpcs[_cis_with_anchor("RcpContreIndic")]

    assert SectionCode.CONTRAINDICATIONS in _codes(legacy)


def test_every_section_starts_with_its_number(smpcs: dict[str, Smpc]) -> None:
    for smpc in smpcs.values():
        for section in smpc.sections:
            assert section.text.startswith(f"{section.code.value}.")


def test_no_mojibake_remains(smpcs: dict[str, Smpc]) -> None:
    for smpc in smpcs.values():
        for section in smpc.sections:
            assert not _C1_CONTROL_CHARS.search(section.text)


def test_revision_dates_precede_snapshot(smpcs: dict[str, Smpc]) -> None:
    assert all(smpc.revised_on <= SNAPSHOT.exported_on for smpc in smpcs.values())


def test_ingests_fixture_end_to_end(source: BdpmSmpcSource) -> None:
    expected_chunks = sum(len(smpc.to_chunks(SNAPSHOT)) for smpc in source.fetch())

    report = IngestSmpcs(
        source, DeterministicEmbedder(), InMemoryChunkStore()
    ).execute()

    assert expected_chunks > 0
    assert report.chunks_stored == expected_chunks
