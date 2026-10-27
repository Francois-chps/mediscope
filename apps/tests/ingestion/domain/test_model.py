from datetime import date

import pytest

from mediscope_ml.ingestion.domain.model import (
    CisCode,
    DataSnapshot,
    InvalidCisCodeError,
    InvalidSmpcError,
    SectionCode,
    Smpc,
    SmpcSection,
)

SNAPSHOT = DataSnapshot(source="iDoc Sante BDPM export", exported_on=date(2022, 4, 15))


def an_smpc(*sections: SmpcSection, cis: str = "61266250") -> Smpc:
    return Smpc(cis_code=CisCode(cis), revised_on=date(2009, 8, 17), sections=sections)


def a_section(code: SectionCode, text: str = "Some clinical text.") -> SmpcSection:
    return SmpcSection(code=code, text=text)


class TestCisCode:
    def test_accepts_eight_digits(self) -> None:
        assert str(CisCode("61266250")) == "61266250"

    @pytest.mark.parametrize(
        "value", ["", "1234567", "123456789", "6126625a", " 61266250"]
    )
    def test_rejects_invalid_values(self, value: str) -> None:
        with pytest.raises(InvalidCisCodeError):
            CisCode(value)

    def test_equal_when_same_value(self) -> None:
        assert CisCode("61266250") == CisCode("61266250")


class TestSectionCode:
    def test_rejects_unknown_code(self) -> None:
        with pytest.raises(ValueError):
            SectionCode("4.10")

    @pytest.mark.parametrize("code", ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.8"])
    def test_v1_sections_are_ingested(self, code: str) -> None:
        assert SectionCode(code).is_ingested

    @pytest.mark.parametrize("code", ["4.7", "4.9"])
    def test_other_sections_are_not_ingested(self, code: str) -> None:
        assert not SectionCode(code).is_ingested


class TestSmpc:
    def test_rejects_duplicate_sections(self) -> None:
        with pytest.raises(InvalidSmpcError):
            an_smpc(a_section(SectionCode.POSOLOGY), a_section(SectionCode.POSOLOGY))

    def test_is_identified_by_cis_code(self) -> None:
        first = an_smpc(a_section(SectionCode.POSOLOGY))
        second = an_smpc(a_section(SectionCode.INDICATIONS))

        assert first == second
        assert first != an_smpc(cis="12345678")

    def test_creates_one_chunk_per_ingested_section(self) -> None:
        smpc = an_smpc(
            a_section(SectionCode.POSOLOGY), a_section(SectionCode.INTERACTIONS)
        )

        chunks = smpc.to_chunks(SNAPSHOT)

        assert [chunk.section_code for chunk in chunks] == [
            SectionCode.POSOLOGY,
            SectionCode.INTERACTIONS,
        ]

    def test_skips_sections_outside_v1_scope(self) -> None:
        smpc = an_smpc(a_section(SectionCode.DRIVING), a_section(SectionCode.OVERDOSE))

        assert smpc.to_chunks(SNAPSHOT) == []

    def test_skips_empty_sections(self) -> None:
        smpc = an_smpc(a_section(SectionCode.POSOLOGY, text="  \n "))

        assert smpc.to_chunks(SNAPSHOT) == []

    def test_chunk_is_traceable_to_its_sources(self) -> None:
        smpc = an_smpc(
            a_section(SectionCode.POSOLOGY, text="  Adults: 1 g every 6 hours.  ")
        )

        (chunk,) = smpc.to_chunks(SNAPSHOT)

        assert chunk.cis_code == CisCode("61266250")
        assert chunk.text == "Adults: 1 g every 6 hours."
        assert chunk.smpc_revised_on == date(2009, 8, 17)
        assert chunk.snapshot == SNAPSHOT

    def test_chunk_key_is_stable(self) -> None:
        (chunk,) = an_smpc(a_section(SectionCode.POSOLOGY)).to_chunks(SNAPSHOT)

        assert chunk.key == "61266250:4.2"
