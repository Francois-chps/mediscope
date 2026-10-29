from collections.abc import Sequence
from datetime import date

import pytest

from mediscope_ml.ingestion.adapters.in_memory import (
    DeterministicEmbedder,
    InMemoryChunkStore,
    InMemorySmpcSource,
)
from mediscope_ml.ingestion.application.ingest_smpcs import IngestionReport, IngestSmpcs
from mediscope_ml.ingestion.domain.model import (
    CisCode,
    DataSnapshot,
    SectionCode,
    Smpc,
    SmpcSection,
)

SNAPSHOT = DataSnapshot(source="iDoc Sante BDPM export", exported_on=date(2022, 4, 15))


def an_smpc(cis: str, *codes: SectionCode) -> Smpc:
    return Smpc(
        cis_code=CisCode(cis),
        revised_on=date(2009, 8, 17),
        sections=tuple(
            SmpcSection(code=code, text=f"Text of {code}") for code in codes
        ),
    )


def ingest(
    *smpcs: Smpc,
    store: InMemoryChunkStore | None = None,
    embedder: DeterministicEmbedder | None = None,
) -> tuple[IngestionReport, InMemoryChunkStore]:
    store = store if store is not None else InMemoryChunkStore()
    use_case = IngestSmpcs(
        source=InMemorySmpcSource(SNAPSHOT, smpcs),
        embedder=embedder if embedder is not None else DeterministicEmbedder(),
        store=store,
    )
    return use_case.execute(), store


def test_stores_one_embedded_chunk_per_ingested_section() -> None:
    _, store = ingest(
        an_smpc("61266250", SectionCode.POSOLOGY, SectionCode.DRIVING),
        an_smpc("12345678", SectionCode.INTERACTIONS),
    )

    assert sorted(store.chunks) == ["12345678:4.5:0", "61266250:4.2:0"]


def test_reports_smpcs_read_and_chunks_stored() -> None:
    report, _ = ingest(
        an_smpc("61266250", SectionCode.POSOLOGY, SectionCode.CONTRAINDICATIONS),
        an_smpc("12345678", SectionCode.OVERDOSE),
    )

    assert report == IngestionReport(smpcs_read=2, chunks_stored=2)


def test_chunks_carry_the_source_snapshot() -> None:
    _, store = ingest(an_smpc("61266250", SectionCode.POSOLOGY))

    assert store.chunks["61266250:4.2:0"].chunk.snapshot == SNAPSHOT


def test_reingesting_does_not_duplicate_chunks() -> None:
    store = InMemoryChunkStore()
    smpc = an_smpc("61266250", SectionCode.POSOLOGY, SectionCode.INDICATIONS)

    ingest(smpc, store=store)
    ingest(smpc, store=store)

    assert len(store.chunks) == 2


def test_does_not_call_embedder_when_nothing_to_ingest() -> None:
    embedder = DeterministicEmbedder()

    ingest(an_smpc("61266250", SectionCode.DRIVING), embedder=embedder)

    assert embedder.calls == 0


class MisbehavingEmbedder:
    """Returns one vector less than requested."""

    def embed(self, texts: Sequence[str]) -> Sequence[tuple[float, ...]]:
        return [(1.0,)] * (len(texts) - 1)


def test_fails_when_embedder_returns_wrong_number_of_vectors() -> None:
    use_case = IngestSmpcs(
        source=InMemorySmpcSource(
            SNAPSHOT,
            [an_smpc("61266250", SectionCode.POSOLOGY, SectionCode.INDICATIONS)],
        ),
        embedder=MisbehavingEmbedder(),
        store=InMemoryChunkStore(),
    )

    with pytest.raises(ValueError):
        use_case.execute()
