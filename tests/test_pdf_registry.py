# tests/test_pdf_registry.py
import time
from pathlib import Path
import pytest

from pdf_annot.pdf_registry import build_pdf_index, PdfInfo
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
