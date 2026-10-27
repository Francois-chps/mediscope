# ADR-001: Hexagonal architecture for the ML engine

- **Status**: Accepted
- **Date**: 2026-10-27
- **Related issue**: #6

## Context

The ML engine relies on technologies that are likely to change:

- the data source (a 2022 BDPM snapshot today, possibly fresh data later, see #3);
- the embedding model and the vector store;
- the LLM provider (hosted API, fine-tuned model, local model).

The business rules, such as which SmPC sections are ingested, chunk
traceability to their sources and idempotent re-ingestion, must stay
stable and be testable without network, database or GPU.

## Decision

Each bounded context (starting with `ingestion`) is split into three layers:

- **domain**: model and ports, written in pure Python with no third-party dependency.
  Ports are `typing.Protocol` interfaces expressed in domain terms
  (`SmpcSource`, `Embedder`, `ChunkStore`).
- **application**: use cases orchestrating the domain through ports
  (`IngestSmpcs`).
- **adapters**: implementations of the ports with concrete technologies,
  plus in-memory adapters used for tests and dry runs.

Dependencies only point inward: adapters depend on application and domain,
application depends on domain, domain depends on nothing.
Concrete adapters are wired in a single composition root (the CLI, #8).
Ports are created only for external dependencies (I/O, network, models),
and their signatures are driven by what the use cases need.

## Consequences

**Positive**

- Unit tests run in milliseconds, with in-memory adapters instead of real infrastructure.
- Changing a data source, model or database means adding an adapter,
  without touching the domain.
- Business rules are explicit and readable in one place.

**Negative**

- More files and one level of indirection compared to a script.
- Adapters must translate external formats (CSV rows, HTML anchors, SQL rows)
  into domain objects.
- Risk of over-abstraction, mitigated by creating ports only for external dependencies.

**Enforcement**

The dependency rule is currently checked during review. An import-linter
contract will be added together with the first third-party dependency (#5).

## Alternatives considered

- **Plain scripts calling libraries directly**: simpler at first, but business
  rules become coupled to polars, the database and the model, and cannot be
  tested without infrastructure.
- **Using LangChain abstractions as ports**: ties the domain to a fast-moving
  framework API. LangChain can still be used inside adapters.
