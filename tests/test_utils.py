# tests/test_utils.py
from __future__ import annotations

from pdf_annot.utils import (
    crc32_az7,
    hash_text,
    parse_filename,
    pdf_id_from_filename,
)

def test_crc32_az7_basic_stability():
    # Expected values computed from the implementation in utils.py (VBA-parity)
    cases = {
        "": "AAAAAAA",        # crc32(b"") -> 0 -> all 'A'
        "a": "XKIXPQM",
        "A": "XKIXPQM",       # lowercased
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
    assert pf.paper_name == "Some Paper"
    assert pf.filename.endswith(".pdf")
    assert pf.pdf_id == "(Smith+Doe 2015a)"
    assert pf.authors_array == ["Smith", "Doe"]

def test_parse_filename_dash_format_basic():
    pf = parse_filename("Smith+Doe - 2015 - Some Paper.pdf")
    assert pf.authors == "Smith+Doe"
    assert pf.year == "2015"
    assert pf.paper_name == "Some Paper"
    assert pf.pdf_id == "(Smith+Doe 2015)"

def test_parse_filename_dash_format_extra_dashes_in_title():
    pf = parse_filename("Smith+Doe - 2015a - Some Paper - Extended - Title.pdf")
    assert pf.authors == "Smith+Doe"
    assert pf.year == "2015a"
    assert pf.paper_name == "Some Paper - Extended - Title"

def test_pdf_id_from_filename_helpers():
    assert pdf_id_from_filename("(Roe 1999) Title.pdf") == "(Roe 1999)"

def test_parse_filename_missing_pieces():
    pf = parse_filename("(OnlyAuthors) Title.pdf")
    assert pf.authors == "OnlyAuthors"
    assert pf.year == ""
    assert pf.paper_name == "Title"

def test_parse_filename_paths_and_os_splits(tmp_path):
    f = tmp_path / "(Alpha+Beta 2020) Name.pdf"
    f.write_bytes(b"%PDF-1.4\n%...")
    pf = parse_filename(str(f))
    assert pf.path == str(tmp_path)
    assert pf.filename_with_ext == "(Alpha+Beta 2020) Name.pdf"
    assert pf.paper_name == "Name"
    assert pf.pdf_id == "(Alpha+Beta 2020)"
