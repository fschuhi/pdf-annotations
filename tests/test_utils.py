# tests/test_utils.py
from __future__ import annotations

from pdf_annot.utils import (
    crc32_az7,
    hash_text,
    is_valid_pdf_id,
    parse_filename,
    pdf_id_from_filename,
)


def test_crc32_az7_basic_stability():
    # Expected values computed from the implementation in utils.py (VBA-parity)
    cases = {
        "": "AAAAAAA",  # crc32(b"") -> 0 -> all 'A'
        "a": "XKIXPQM",
        "A": "XKIXPQM",  # lowercased
        "hello": "OAYXIYC",
        "authors": "NMVBPSH",
        "doe+roe": "SZUNTVJ",
        "müller": "FKIGOXI",  # unicode lowercase, utf-8 bytes
        "(smith 2015)": "OVMKNOJ",
    }
    for text, expected in cases.items():
        assert crc32_az7(text) == expected


def test_hash_text_alias():
    assert hash_text("Smith+Doe") == crc32_az7("Smith+Doe")


def test_parse_filename_bracket_format():
    pf = parse_filename("(Smith+Doe 2015a) Some Paper.pdf")
    assert pf.authors == "Smith+Doe"
    assert pf.year == "2015a"
    assert pf.pdf_title == "Some Paper"
    assert pf.filename.endswith(".pdf")
    assert pf.pdf_id == "(Smith+Doe 2015a)"
    assert pf.authors_array == ["Smith", "Doe"]


def test_parse_filename_dash_format_basic():
    pf = parse_filename("Smith+Doe - 2015 - Some Paper.pdf")
    assert pf.authors == "Smith+Doe"
    assert pf.year == "2015"
    assert pf.pdf_title == "Some Paper"
    assert pf.pdf_id == "(Smith+Doe 2015)"


def test_parse_filename_dash_format_extra_dashes_in_title():
    pf = parse_filename("Smith+Doe - 2015a - Some Paper - Extended - Title.pdf")
    assert pf.authors == "Smith+Doe"
    assert pf.year == "2015a"
    assert pf.pdf_title == "Some Paper - Extended - Title"


def test_pdf_id_from_filename_helpers():
    assert pdf_id_from_filename("(Roe 1999) Title.pdf") == "(Roe 1999)"


def test_parse_filename_missing_pieces():
    pf = parse_filename("(OnlyAuthors) Title.pdf")
    assert pf.authors == "OnlyAuthors"
    assert pf.year == ""
    assert pf.pdf_title == "Title"


def test_parse_filename_paths_and_os_splits(tmp_path):
    f = tmp_path / "(Alpha+Beta 2020) Name.pdf"
    # --- FIX: Ignore PyCharm's incorrect type warning ---
    f.write_bytes(b"%PDF-1.4\n%...")  # type: ignore
    pf = parse_filename(str(f))
    assert pf.path == str(tmp_path)
    assert pf.filename_with_ext == "(Alpha+Beta 2020) Name.pdf"
    assert pf.pdf_title == "Name"
    assert pf.pdf_id == "(Alpha+Beta 2020)"


def test_is_valid_pdf_id_accepts_current_collection_shapes():
    valid = [
        "(Fink 2012)",
        "(Das 2000b)",
        "(Gollwitzer-Schwarz+Sheeran 2006b)",
        "(Sciortino+Kayser 2021)",
        # Multi-word surnames: the space belongs to the name, not to a second author
        "(Anyen Rinpoche+Graboski 2012)",
        "(De Preester+Van De Vijver 2005)",
        "(Van Schaik 2004)",
        # Non-ASCII author names are valid; the pattern constrains structure, not script
        "(Müller 2011)",
        "(Schürmann+Böhme 1994a)",
    ]
    for pdf_id in valid:
        assert is_valid_pdf_id(pdf_id), pdf_id


def test_is_valid_pdf_id_rejects_old_system_ids():
    # The year is the discriminator: an old id parses as an author with no year
    # and therefore hashes to a different identity (AUDIT.md A5, F9).
    for pdf_id in ["(Smilek2011)", "(Gollwitzer-Schwarz+Sheeran2006b)"]:
        assert not is_valid_pdf_id(pdf_id), pdf_id


def test_is_valid_pdf_id_rejects_malformed():
    invalid = [
        "(OnlyAuthors)",  # no year at all
        "(2012)",  # no authors
        "()",  # empty
        "(Guenther 1984A)",  # uppercase disambiguation letter
        "(Guenther 198)",  # three digits
        "(Guenther 19845)",  # five digits
        "(Fink  2012)",  # two spaces before the year
        "( Fink 2012)",  # leading space
        "(Fink 2012 )",  # trailing space
        "(Deroche + Sheehy 2022)",  # padding around "+"
        "(Deroche +Sheehy 2022)",
        "(Deroche+ Sheehy 2022)",
        "(Deroche++Sheehy 2022)",  # empty author segment
        "(Fink\u00a02012)",  # non-breaking space instead of a real one
        "Fink 2012",  # no parentheses
        "(Fink 2012",  # unbalanced
        "(Fink (2012))",  # nested parentheses
    ]
    for pdf_id in invalid:
        assert not is_valid_pdf_id(pdf_id), pdf_id


def test_is_valid_pdf_id_accepts_what_parse_filename_generates():
    # Whatever parse_filename builds from a well-formed filename must pass the
    # gate; the two must not disagree about the same file.
    for name in [
        "(Fink 2012) The Scent of a Self.pdf",
        "(De Preester+Van De Vijver 2005) Body image and body schema.pdf",
        "(Das 2000b) Other title.pdf",
    ]:
        assert is_valid_pdf_id(parse_filename(name).pdf_id), name
