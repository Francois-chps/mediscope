"""SmPC ingestion domain model.

Pure Python: no I/O, no framework. Names follow the glossary defined in #3.
"""

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from mediscope_ml.ingestion.domain.chunking import split_text


_CIS_PATTERN = re.compile(r"\d{8}")


class DomainError(ValueError):
    """Base class for domain rule violations."""


class InvalidCisCodeError(DomainError):
    """Raised when a CIS code is not made of exactly 8 digits."""


class InvalidSmpcError(DomainError):
    """Raised when an SmPC breaks one of its invariants."""


class InvalidChunkingPolicyError(DomainError):
    """Raised when chunk size or overlap are inconsistent."""


@dataclass(frozen=True, slots=True)
class CisCode:
    """Identifier of a specialty in the BDPM (Code Identifiant de Spécialité)."""

    value: str

    def __post_init__(self) -> None:
        if not _CIS_PATTERN.fullmatch(self.value):
            raise InvalidCisCodeError(f"CIS code must be 8 digits, got {self.value!r}")

    def __str__(self) -> str:
        return self.value


class SectionCode(StrEnum):
    """Numbered sections of SmPC chapter 4 (clinical particulars)."""

    INDICATIONS = "4.1"
    POSOLOGY = "4.2"
    CONTRAINDICATIONS = "4.3"
    WARNINGS = "4.4"
    INTERACTIONS = "4.5"
    PREGNANCY = "4.6"
    DRIVING = "4.7"
    ADVERSE_EFFECTS = "4.8"
    OVERDOSE = "4.9"

    @property
    def is_ingested(self) -> bool:
        """Whether this section is part of the v1 ingestion scope."""
        return self in INGESTED_SECTIONS


INGESTED_SECTIONS = frozenset(
    {
        SectionCode.INDICATIONS,
        SectionCode.POSOLOGY,
        SectionCode.CONTRAINDICATIONS,
        SectionCode.WARNINGS,
        SectionCode.INTERACTIONS,
        SectionCode.PREGNANCY,
        SectionCode.ADVERSE_EFFECTS,
    }
)


@dataclass(frozen=True, slots=True)
class SmpcSection:
    """A numbered section of an SmPC and its text."""

    code: SectionCode
    text: str


@dataclass(frozen=True, slots=True)
class DataSnapshot:
    """The dated export the knowledge base is built from."""

    source: str
    exported_on: date


@dataclass(frozen=True, slots=True)
class ChunkingPolicy:
    """How sections are split before embedding. Sizes are in characters.

    Defaults fit 512-token embedding models (~4 characters per token in French).
    """

    max_chars: int = 1500
    overlap_chars: int = 150

    def __post_init__(self) -> None:
        if self.max_chars <= 0 or not 0 <= self.overlap_chars < self.max_chars:
            raise InvalidChunkingPolicyError(
                "Expected 0 <= overlap < max and max > 0, "
                f"got max={self.max_chars}, overlap={self.overlap_chars}"
            )


DEFAULT_CHUNKING = ChunkingPolicy()


@dataclass(frozen=True, slots=True)
class Chunk:
    """Unit of text to embed, traceable to its specialty, section and dates."""

    cis_code: CisCode
    section_code: SectionCode
    index: int
    text: str
    smpc_revised_on: date
    snapshot: DataSnapshot

    @property
    def key(self) -> str:
        """Stable identifier: re-ingesting the same chunk overwrites it."""
        return f"{self.cis_code}:{self.section_code}:{self.index}"


@dataclass(frozen=True, slots=True, eq=False)
class Smpc:
    """Summary of Product Characteristics of a specialty.

    Aggregate root, identified by its CIS code.
    """

    cis_code: CisCode
    revised_on: date
    sections: tuple[SmpcSection, ...]

    def __post_init__(self) -> None:
        codes = [section.code for section in self.sections]
        if len(codes) != len(set(codes)):
            raise InvalidSmpcError(f"SmPC {self.cis_code} has duplicate sections")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Smpc) and other.cis_code == self.cis_code

    def __hash__(self) -> int:
        return hash(self.cis_code)

    def to_chunks(
        self,
        snapshot: DataSnapshot,
        policy: ChunkingPolicy = DEFAULT_CHUNKING,
    ) -> list[Chunk]:
        """Chunks of every in-scope section; long sections become overlapping windows."""
        return [
            Chunk(
                cis_code=self.cis_code,
                section_code=section.code,
                index=index,
                text=piece,
                smpc_revised_on=self.revised_on,
                snapshot=snapshot,
            )
            for section in self.sections
            if section.code.is_ingested
            for index, piece in enumerate(
                split_text(section.text, policy.max_chars, policy.overlap_chars)
            )
        ]


@dataclass(frozen=True, slots=True)
class EmbeddedChunk:
    """A chunk paired with its embedding vector, ready to be stored."""

    chunk: Chunk
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.vector:
            raise DomainError(f"Chunk {self.chunk.key} has an empty embedding")
