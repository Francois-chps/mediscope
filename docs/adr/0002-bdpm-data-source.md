# ADR-002: BDPM SmPC export as data source

- Status: Accepted
- Date: <today>

## Context
MediScope answers drug questions from official French SmPCs. The BDPM (ANSM)
publishes them as a single export, `CIS_RCP.csv` (~1 GB, 15,649 rows).
Profiling the full file showed:

- Tab-separated UTF-8 with quoted multiline HTML; no malformed row, no duplicate CIS.
- 3,603 rows have an empty HTML body; every non-empty row has a revision date
  (`ANSM - Mis à jour le : dd/mm/yyyy`).
- Sections are marked by stable anchors in two families:
  modern (~11.5k rows, e.g. `RcpContreindications`) and legacy (~530 rows, e.g. `RcpContreIndic`).
  Anchors such as `Rcp_4_2_PosoAdmin_1` are sub-headings.
- Apostrophes are stored as C1 control characters (`\x92`): cp1252 text decoded as latin-1 upstream.
- A handful of anchors are misplaced (their heading does not match the section number).

## Decision
- Use the 2022-04-15 snapshot of `CIS_RCP.csv`, under Licence Ouverte 2.0 (Etalab).
  The snapshot date is shown to users, since the licence requires up-to-date data.
- Read it row by row with the stdlib `csv` module. polars ran out of memory on a full read;
  streaming peaks at 26 MB.
- Split each document on main anchors with a regex; every main anchor bounds the previous
  section. Use selectolax only to turn HTML fragments into text.
- Map both anchor families to `SectionCode`; ignore sub-anchors and misplaced anchors.
- Translate C1 control characters to their cp1252 equivalent. Two rows with Mac Roman
  artefacts (`\xd5`) are left as-is.
- Skip empty or anomalous rows and count them by reason instead of failing the run.
- Commit only a small extracted sample as test fixtures; the raw export stays out of git.

## Consequences
- Memory is bounded regardless of export size.
- Section boundaries depend on BDPM anchor names; a format change would surface as a drop
  in parsed sections, visible through the skip counters.
- Data is not current: answers must state the snapshot date.
