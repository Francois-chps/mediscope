"""Use case: ingest the SmPCs of a data snapshot into the chunk store."""

from dataclasses import dataclass

from mediscope_ml.ingestion.domain.model import EmbeddedChunk
from mediscope_ml.ingestion.domain.ports import ChunkStore, Embedder, SmpcSource


@dataclass(frozen=True, slots=True)
class IngestionReport:
    smpcs_read: int
    chunks_stored: int


class IngestSmpcs:
    def __init__(
        self, source: SmpcSource, embedder: Embedder, store: ChunkStore
    ) -> None:
        self._source = source
        self._embedder = embedder
        self._store = store

    def execute(self) -> IngestionReport:
        snapshot = self._source.snapshot
        smpcs_read = 0
        chunks_stored = 0

        for smpc in self._source.fetch():
            smpcs_read += 1
            chunks = smpc.to_chunks(snapshot)
            if not chunks:
                continue

            vectors = self._embedder.embed([chunk.text for chunk in chunks])
            self._store.save(
                [
                    EmbeddedChunk(chunk=chunk, vector=tuple(vector))
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ]
            )
            chunks_stored += len(chunks)

        return IngestionReport(smpcs_read=smpcs_read, chunks_stored=chunks_stored)
