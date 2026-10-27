"""In-memory adapters: no I/O, used for tests and dry runs."""

from collections.abc import Iterable, Sequence

from mediscope_ml.ingestion.domain.model import DataSnapshot, EmbeddedChunk, Smpc


class InMemorySmpcSource:
    def __init__(self, snapshot: DataSnapshot, smpcs: Iterable[Smpc]) -> None:
        self.snapshot = snapshot
        self._smpcs = list(smpcs)

    def fetch(self) -> Iterable[Smpc]:
        yield from self._smpcs


class DeterministicEmbedder:
    """Returns a predictable vector derived from the text length."""

    def __init__(self, dimension: int = 4) -> None:
        self._dimension = dimension
        self.calls = 0

    def embed(self, texts: Sequence[str]) -> Sequence[tuple[float, ...]]:
        self.calls += 1
        return [(float(len(text)),) * self._dimension for text in texts]


class InMemoryChunkStore:
    def __init__(self) -> None:
        self.chunks: dict[str, EmbeddedChunk] = {}

    def save(self, chunks: Sequence[EmbeddedChunk]) -> None:
        for embedded in chunks:
            self.chunks[embedded.chunk.key] = embedded
