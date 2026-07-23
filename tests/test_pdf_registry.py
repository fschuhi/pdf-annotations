# tests/test_pdf_registry.py
import time
from pathlib import Path
import pytest

from pdf_annot.pdf_registry import build_pdf_index, is_controlled_pdf_name, PdfInfo
from pdf_annot.utils import crc32_az7


def _write_dummy_pdf(path: Path, content: bytes = b"%PDF-1.4\n%..."):
    path.parent.mkdir(parents=True, exist_ok=True)
    # --- FIX: Ignore PyCharm's incorrect type warning ---
    path.write_bytes(content)  # type: ignore


@pytest.fixture
def pdf_dir(tmp_path: Path) -> Path:
    d = tmp_path / "pdfs"
    d.mkdir()
    return d


def test_build_pdf_index_basic(pdf_dir: Path):
    p1 = pdf_dir / "(Albini 2013) On dealing with destructive emotions.pdf"
    _write_dummy_pdf(p1)

    p2 = pdf_dir / "subdir" / "(Das 2000b) Other title.pdf"
    _write_dummy_pdf(p2)

    # This one should be ignored
    p3 = pdf_dir / "ignoreme.pdf"
    _write_dummy_pdf(p3)

    idx = build_pdf_index([str(pdf_dir)])
    assert len(idx) == 2

    k1 = "(albini 2013)"
    assert k1 in idx
    info1 = idx[k1]
    assert isinstance(info1, PdfInfo)
    assert info1.pdf_id == "(Albini 2013)"
    assert info1.pdf_title == "On dealing with destructive emotions"
    assert info1.abs_path == str(p1)
    assert info1.pdf_hash == crc32_az7(k1)

    k2 = "(das 2000b)"
    assert k2 in idx
    info2 = idx[k2]
    assert info2.pdf_id == "(Das 2000b)"
    assert info2.pdf_title == "Other title"
    assert info2.abs_path == str(p2)
    assert info2.pdf_hash == crc32_az7(k2)


def test_build_pdf_index_mtime_size(pdf_dir: Path):
    p1 = pdf_dir / "(Test 2025) File A.pdf"
    _write_dummy_pdf(p1, content=b"12345")
    st1 = p1.stat()

    time.sleep(0.01)  # Ensure mtime is different

    p2 = pdf_dir / "(Test 2026) File B.pdf"
    _write_dummy_pdf(p2, content=b"1234567890")
    st2 = p2.stat()

    idx = build_pdf_index([str(pdf_dir)])
    assert len(idx) == 2

    info1 = idx["(test 2025)"]
    assert info1.size == 5
    assert info1.mtime == st1.st_mtime

    info2 = idx["(test 2026)"]
    assert info2.size == 10
    assert info2.mtime == st2.st_mtime
    assert info2.mtime != info1.mtime


def test_empty_dir(pdf_dir: Path):
    idx = build_pdf_index([str(pdf_dir)])
    assert len(idx) == 0


def test_nonexistent_dir(tmp_path: Path):
    idx = build_pdf_index([str(tmp_path / "nonexistent")])
    assert len(idx) == 0


def test_is_controlled_pdf_name_accepts_well_formed():
    for name in [
        "(Das 2000b) Title.pdf",
        "(Albini 2013) On dealing with destructive emotions.pdf",
        "(De Preester+Van De Vijver 2005) Body image and body schema.pdf",
        "(Müller 2011) Ein Titel.pdf",
        "(Fink 2012) Title.PDF",  # extension is case-insensitive
    ]:
        assert is_controlled_pdf_name(name), name


def test_is_controlled_pdf_name_rejects_old_system_ids():
    # The year gate is the discriminator between old-system and new-system
    # references (AUDIT.md A5, F9). Without it these pass as a different identity.
    for name in [
        "(Smilek2011) Title.pdf",
        "(Gollwitzer-Schwarz+Sheeran2006b) Title.pdf",
        "(OnlyAuthors) Title.pdf",
    ]:
        assert not is_controlled_pdf_name(name), name


def test_is_controlled_pdf_name_rejects_other_shapes():
    for name in [
        "(Alpha 2020)Name.pdf",  # no space after the id
        "(Alpha 2020).pdf",  # no title at all
        "Smith+Doe - 2015 - Title.pdf",  # legacy dash format
        "ignoreme.pdf",  # no id
        "(Alpha 2020 Title.pdf",  # unclosed id
        "(Alpha 2020) Title.txt",  # not a PDF
    ]:
        assert not is_controlled_pdf_name(name), name


def test_build_pdf_index_skips_old_system_names(pdf_dir: Path):
    old = pdf_dir / "(Smilek2011) Attention and awareness.pdf"
    _write_dummy_pdf(old)

    new = pdf_dir / "(Smilek 2011) Attention and awareness.pdf"
    _write_dummy_pdf(new)

    idx = build_pdf_index([str(pdf_dir)])
    assert list(idx) == ["(smilek 2011)"]
    assert idx["(smilek 2011)"].abs_path == str(new)
