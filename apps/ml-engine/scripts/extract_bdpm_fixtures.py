"""Extract a small sample of the BDPM SmPC export covering parsing edge cases.

Usage (from apps/ml-engine):
    uv run python scripts/extract_bdpm_fixtures.py ../../data/raw/CIS_RCP.csv
"""

import csv
import re
import sys
from pathlib import Path

OUT = Path(__file__).parents[1] / "tests" / "fixtures" / "bdpm" / "CIS_RCP_sample.csv"
MAX_BYTES = 500_000
MODERN_ANCHORS = (
    "RcpIndicTherap",
    "RcpPosoAdmin",
    "RcpContreindications",
    "RcpMisesEnGarde",
    "RcpInteractionsMed",
    "RcpFertGrossAllait",
    "RcpEffetsIndesirables",
)
_TAG = re.compile(r"<[^>]+>")


def _has(doc: str, anchor: str) -> bool:
    return f'name="{anchor}"' in doc


def _title(doc: str, anchor: str) -> str | None:
    match = re.search(rf'name="{anchor}"[^>]*>(.*?)</p>', doc, re.DOTALL)
    return " ".join(_TAG.sub(" ", match[1]).split()) if match else None


def _categories(doc: str) -> list[str]:
    if not doc:
        return ["empty"]
    categories: list[str] = []
    dated = "DateNotif" in doc
    posology = _title(doc, "RcpPosoAdmin")
    well_placed = posology is not None and posology.startswith("4.2")
    if dated and well_placed and all(_has(doc, a) for a in MODERN_ANCHORS):
        categories.append("modern")
        if "Rcp_4_2_PosoAdmin_1" in doc:
            categories.append("sub_anchors")
    if dated and _has(doc, "RcpContreIndic"):
        categories.append("legacy")
    if posology is not None and not well_placed:
        categories.append("misplaced_anchor")
    if not _has(doc, "RcpPosoAdmin"):
        categories.append("no_posology")
    return categories


def main(source: Path) -> None:
    csv.field_size_limit(sys.maxsize)
    best: dict[str, tuple[str, str]] = {}  # category -> smallest (cis, html)
    with source.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter="\t")
        header = next(reader)
        for cis, doc in reader:
            for category in _categories(doc):
                if category not in best or len(doc) < len(best[category][1]):
                    best[category] = (cis, doc)

    rows = dict(best.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows.items())

    with OUT.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter="\t")
        next(reader)
        if {row[0]: row[1] for row in reader} != rows:
            raise SystemExit("Round-trip mismatch")

    for category, (cis, doc) in sorted(best.items()):
        print(f"{category:18} {cis}  {len(doc) // 1024:5} KB")
    size = OUT.stat().st_size
    print(f"{OUT.name}: {len(rows)} rows, {size // 1024} KB")
    if size > MAX_BYTES:
        raise SystemExit(f"Fixture larger than {MAX_BYTES} bytes")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
