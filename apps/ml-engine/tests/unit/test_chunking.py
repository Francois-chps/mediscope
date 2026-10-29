from mediscope_ml.ingestion.domain.chunking import split_text
from datetime import date

import pytest

from mediscope_ml.ingestion.domain.model import (
    ChunkingPolicy,
    CisCode,
    DataSnapshot,
    InvalidChunkingPolicyError,
    SectionCode,
    Smpc,
    SmpcSection,
)

SENTENCES = [f"Sentence {i:02d} is here." for i in range(20)]  # 20 chars each
TEXT = " ".join(SENTENCES)


def test_short_text_is_a_single_chunk() -> None:
    assert split_text("  Short   text. ", 100, 10) == ["Short text."]


def test_empty_text_gives_no_chunk() -> None:
    assert split_text("   ", 100, 10) == []


def test_no_chunk_exceeds_max_chars() -> None:
    assert all(len(chunk) <= 100 for chunk in split_text(TEXT, 100, 30))


def test_consecutive_chunks_overlap() -> None:
    chunks = split_text(TEXT, 100, 30)

    assert len(chunks) > 1
    for previous, following in zip(chunks, chunks[1:], strict=False):
        assert following.startswith(previous[-20:])  # last sentence carried over


def test_without_overlap_chunks_rebuild_the_text() -> None:
    assert " ".join(split_text(TEXT, 100, 0)) == TEXT


def test_every_sentence_is_kept() -> None:
    chunks = split_text(TEXT, 100, 30)

    assert all(any(sentence in chunk for chunk in chunks) for sentence in SENTENCES)


def test_sentence_without_punctuation_is_cut_on_words() -> None:
    text = " ".join(["word"] * 50)

    chunks = split_text(text, 30, 0)

    assert all(len(chunk) <= 30 for chunk in chunks)
    assert " ".join(chunks) == text


def test_word_longer_than_window_is_sliced() -> None:
    assert split_text("a" * 25, 10, 0) == ["a" * 10, "a" * 10, "a" * 5]


@pytest.mark.parametrize(("max_chars", "overlap"), [(0, 0), (100, 100), (100, -1)])
def test_invalid_chunking_policy_is_rejected(max_chars: int, overlap: int) -> None:
    with pytest.raises(InvalidChunkingPolicyError):
        ChunkingPolicy(max_chars=max_chars, overlap_chars=overlap)


def test_long_section_is_split_into_indexed_chunks() -> None:
    smpc = Smpc(
        cis_code=CisCode("60000001"),
        revised_on=date(2021, 1, 1),
        sections=(SmpcSection(code=SectionCode.ADVERSE_EFFECTS, text=TEXT),),
    )
    snapshot = DataSnapshot(source="BDPM", exported_on=date(2022, 4, 15))

    chunks = smpc.to_chunks(snapshot, ChunkingPolicy(max_chars=100, overlap_chars=30))

    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert len({chunk.key for chunk in chunks}) == len(chunks) > 1
    assert chunks[0].key == "60000001:4.8:0"
