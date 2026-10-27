"""Ports of the ingestion context.

They describe what the use case needs from the outside world,
in domain terms, without saying how it is done.
"""

from collections.abc import Iterable, Sequence
from typing import Protocol

from mediscope_ml.ingestion.domain.model import DataSnapshot, EmbeddedChunk, Smpc


class SmpcSource(Protocol):
    """Provides the SmPCs of a data snapshot."""

    @property
    def snapshot(self) -> DataSnapshot: ...

    def fetch(self) -> Iterable[Smpc]:
        """Yield SmPCs one by one (sources may be too large to fit in memory)."""
        ...


class Embedder(Protocol):
    """Turns texts into embedding vectors."""

    def embed(self, texts: Sequence[str]) -> Sequence[tuple[float, ...]]:
        """Return exactly one vector per text, in the same order."""
        ...


class ChunkStore(Protocol):
    """Persists embedded chunks."""

    def save(self, chunks: Sequence[EmbeddedChunk]) -> None:
        """Insert or replace chunks, using `chunk.key` as identity."""
        ...
