"""SmpcSource adapter streaming the BDPM SmPC export (CIS_RCP.csv)."""

import csv
import logging
import sys
from collections import Counter
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from mediscope_ml.ingestion.adapters.bdpm.html import (
    fix_mojibake,
    parse_revision_date,
    split_sections,
)
from mediscope_ml.ingestion.domain.model import (
    CisCode,
    DataSnapshot,
    DomainError,
    SectionCode,
    Smpc,
    SmpcSection,
)

logger = logging.getLogger(__name__)


class BdpmSmpcSource:
    """Reads one row at a time: memory stays bounded whatever the export size."""

    def __init__(self, csv_path: Path, snapshot: DataSnapshot) -> None:
        self._path = csv_path
        self._snapshot = snapshot
        self.skipped: Counter[str] = Counter()

    @property
    def snapshot(self) -> DataSnapshot:
        return self._snapshot

    def fetch(self) -> Iterator[Smpc]:
        self.skipped.clear()
        csv.field_size_limit(sys.maxsize)
        with self._path.open(newline="", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter="\t")
            next(reader, None)  # header
            for row in reader:
                smpc = self._parse_row(row)
                if smpc is not None:
                    yield smpc
        if self.skipped:
            logger.warning("Skipped BDPM rows: %s", dict(self.skipped))

    def _parse_row(self, row: list[str]) -> Smpc | None:
        if len(row) != 2:
            self.skipped["malformed"] += 1
            return None
        cis, raw_html = row
        if not raw_html:
            self.skipped["empty"] += 1
            return None
        html = fix_mojibake(raw_html)
        revised_on = parse_revision_date(html)
        if revised_on is None:
            self.skipped["no_revision_date"] += 1
            return None
        sections = split_sections(html)
        if not sections:
            self.skipped["no_section"] += 1
            return None
        try:
            return _to_smpc(cis, revised_on, sections)
        except DomainError as error:
            self.skipped[type(error).__name__] += 1
            return None


def _to_smpc(cis: str, revised_on: date, sections: dict[SectionCode, str]) -> Smpc:
    return Smpc(
        cis_code=CisCode(cis),
        revised_on=revised_on,
        sections=tuple(
            SmpcSection(code=code, text=text) for code, text in sections.items()
        ),
    )
