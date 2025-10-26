# tests/test_pdf_registry.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import pytest

from pdf_annot.pdf_registry import (
    DuplicatePdfIdError,
    build_pdf_index,
    is_controlled_pdf_name,
    pdf_info_from_path,
)
from pdf_annot.utils import crc32_az7


def _write_dummy_pdf(path: Path, content: bytes = b"%PDF-1.4\n%..."):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_is_controlled_pdf_name_rules():
    assert is_controlled_pdf_name("(Das 2000b) Title.pdf")
    assert is_controlled_pdf_name("(OnlyAuthors) Title.pdf")
    assert not is_controlled_pdf_name("(Alpha 2020)Title.pdf")  # missing space
    assert not is_controlled_pdf_name("Smith+Doe - 2015 - Title.pdf")  # legacy
    assert not is_controlled_pdf_name("Random.pdf")
    assert not is_controlled_pdf_name("(NoClose 2015 Title.pdf")
    assert not is_controlled_pdf_name("(Alpha 2020) Title.txt")  # not pdf


def test_pdf_info_from_path_basic_fields(tmp_path: Path):
    p = tmp_path / "(Sciortino+Kayser 2021) The rubber hand illusion.pdf"
    _write_dummy_pdf(p)

    info = pdf_info_from_path(str(p))
    assert info is not None
    assert info.pdf_id == "(Sciortino+Kayser 2021)"
    assert info.publication_name == "The rubber hand illusion"
    assert info.authors == "Sciortino+Kayser"
    assert info.year == "2021"
    # hash of lowercase id
    expected_hash = crc32_az7("(sciortino+kayser 2021)")
    assert info.pdf_hash == expected_hash
    assert info.size == p.stat().st_size
    assert info.mtime == p.stat().st_mtime
    assert info.filename_with_ext == p.name
    assert os.path.isabs(info.abs_path)


def test_pdf_info_with_diacritics_retained(tmp_path: Path):
    p = tmp_path / "(müller 2018) Überlegung.pdf"
    _write_dummy_pdf(p)

    info = pdf_info_from_path(str(p))
    assert info is not None
    # Preserve diacritics in id; hash computed from lowercase id
    assert info.pdf_id == "(müller 2018)"
    assert info.publication_name == "Überlegung"
    assert info.pdf_hash == crc32_az7("(müller 2018)")  # function lowercases internally


def test_build_pdf_index_filters_and_keys(tmp_path: Path):
    # Controlled
    p1 = tmp_path / "a" / "(Das 2000b) Dream Yoga Study Guide.pdf"
    _write_dummy_pdf(p1)
    p2 = tmp_path / "b" / "(Keating 1995) Open Mind, Open Heart.pdf"
    _write_dummy_pdf(p2)
    # Non-controlled
    p3 = tmp_path / "b" / "Smith+Doe - 2015 - Some Paper.pdf"
    _write_dummy_pdf(p3)

    idx = build_pdf_index([str(tmp_path)])
    # keys are lowercase pdf_id
    assert "(das 2000b)" in idx
    assert "(keating 1995)" in idx
    assert "smith+doe - 2015 - some paper" not in idx
    assert len(idx) == 2


def test_dropbox_relative_paths_posix(tmp_path: Path):
    dropbox_root = tmp_path / "Dropbox"
    pdf_dir = dropbox_root / "Papers" / "Neuro"
    p = pdf_dir / "(Dainton 2014) Self - Philosophy In Transit.pdf"
    _write_dummy_pdf(p)

    info = pdf_info_from_path(str(p), dropbox_root=str(dropbox_root))
    assert info is not None
    assert info.dropbox_rel_path == "Papers/Neuro/(Dainton 2014) Self - Philosophy In Transit.pdf"


def test_duplicate_pdf_id_detection(tmp_path: Path):
    # Two files that differ only by case or placement but same id token
    p1 = tmp_path / "A" / "(Das 2000b) Title.pdf"
    p2 = tmp_path / "B" / "(das 2000b) Another Title.pdf"
    _write_dummy_pdf(p1)
    _write_dummy_pdf(p2)

    with pytest.raises(DuplicatePdfIdError) as ei:
        build_pdf_index([str(tmp_path)])
    assert "(das 2000b)" in str(ei.value)
