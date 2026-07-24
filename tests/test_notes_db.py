# tests/test_notes_db.py
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pdf_annot.notes_db import DuplicateNoteIdError, build_notes_index, is_controlled_md_name


def write(p: Path, s: str) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def test_controlled_name_gate():
    assert is_controlled_md_name("(Keating 1995).md") == "(Keating 1995)"
    assert is_controlled_md_name("(Sciortino+Kayser 2021).md") == "(Sciortino+Kayser 2021)"
    assert is_controlled_md_name("(Keating 1995) v2.md") is None
    assert is_controlled_md_name("Keating 1995.md") is None
    assert is_controlled_md_name("(Keating 1995).md.bak") is None


def test_controlled_name_gate_shares_the_id_predicate():
    # Same rules as the PDF-side gate, because it is the same predicate (AUDIT.md A5).
    assert is_controlled_md_name("(De Preester+Van De Vijver 2005).md") == "(De Preester+Van De Vijver 2005)"
    assert is_controlled_md_name("(M\u00fcller 2011).md") == "(M\u00fcller 2011)"
    assert is_controlled_md_name("(Smilek2011).md") is None
    assert is_controlled_md_name("(OnlyAuthors).md") is None
    assert is_controlled_md_name("(Guenther 1984A).md") is None


def test_build_notes_index_and_detect_duplicates(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    write(vault / "(Das 2000b).md", "Body\n")
    write(
        vault / "(Keating 1995).md",
        textwrap.dedent(
            """\
            ---
            pdf_title: Open Mind, Open Heart
            pdf_size: 123
            ---
            Body
            """
        ),
    )
    db = build_notes_index(str(vault))
    assert len(db) == 2
    assert "(das 2000b)" in db
    assert db["(keating 1995)"].pdf_title == "Open Mind, Open Heart"
    assert db["(keating 1995)"].pdf_size == 123

    # Duplicate (case-insensitive)
    (vault / "Sub").mkdir()
    write(vault / "Sub" / "(das 2000b).md", "Another\n")
    with pytest.raises(DuplicateNoteIdError):
        build_notes_index(str(vault))
