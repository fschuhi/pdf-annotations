# tests/test_notes_db.py
from __future__ import annotations

import os
import stat
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

from pdf_annot.notes_db import CONTROLLED_MD_RE, DuplicateNoteIdError, NotesDB


def write(p: Path, s: str) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def test_controlled_name_regex():
    assert CONTROLLED_MD_RE.match("(Keating 1995).md")
    assert CONTROLLED_MD_RE.match("(Sciortino+Kayser 2021).md")
    assert not CONTROLLED_MD_RE.match("(Keating 1995) v2.md")
    assert not CONTROLLED_MD_RE.match("Keating 1995.md")
    assert not CONTROLLED_MD_RE.match("(Keating 1995).md.bak")


def test_build_notes_db_and_detect_duplicates(tmp_path: Path):
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
    db = NotesDB.build(str(vault))
    assert len(db) == 2
    assert "das 2000b" in db
    assert db["keating 1995"].pdf_title == "Open Mind, Open Heart"
    assert db["keating 1995"].pdf_size == 123

    # Duplicate (case-insensitive)
    (vault / "Sub").mkdir()
    write(vault / "Sub" / "(das 2000b).md", "Another\n")
    with pytest.raises(DuplicateNoteIdError):
        NotesDB.build(str(vault))


@dataclass
class PdfMock:
    pdf_id: str
    title_from_filename: str
    size: int


def test_plan_updates_and_apply_dry_run_then_real(tmp_path: Path, capsys):
    vault = tmp_path / "vault"
    vault.mkdir()
    # Notes
    write(
        vault / "(Keating 1995).md",
        textwrap.dedent(
            """\
            ---
            other: keep
            pdf_title: Wrong Title
            ---
            Body
            """
        ),
    )
    write(vault / "(Das 2000b).md", "Just body\n")
    # Ignored variant
    write(vault / "(Das 2000b) v2.md", "Ignore me\n")

    db = NotesDB.build(str(vault))

    # PDFs
    pdfs = {
        "keating 1995": PdfMock(pdf_id="Keating 1995", title_from_filename="Open Mind, Open Heart", size=1000),
        "das 2000b": PdfMock(pdf_id="Das 2000b", title_from_filename="Some Book", size=2000),
        "missing 2010": PdfMock(pdf_id="Missing 2010", title_from_filename="Ghost", size=1),
    }

    plan_summary = db.plan_frontmatter_updates(pdfs)
    plans = plan_summary.plans
    # We expect 2 planned updates (keating title fix, das insert both fields)
    planned_ids = sorted(p.pdf_id for p in plans)
    assert planned_ids == ["Das 2000b", "Keating 1995"]
    assert sorted(plan_summary.missing_notes) == ["missing 2010"]
    # No orphans because both notes have matching PDFs in pdfs dict except variants
    assert sorted(plan_summary.orphan_notes) == []

    # Dry run apply
    summary = db.apply_frontmatter_updates(plans, dry_run=True)
    assert sorted(summary.updated) == sorted([str(vault / "(Keating 1995).md"), str(vault / "(Das 2000b).md")])
    assert summary.unchanged == []
    assert summary.errors == []

    # Real apply
    summary2 = db.apply_frontmatter_updates(plans, dry_run=False)
    assert len(summary2.updated) == 2
    assert summary2.errors == []

    # Rebuild and ensure front matter updated
    db2 = NotesDB.build(str(vault))
    k = db2["keating 1995"]
    d = db2["das 2000b"]
    assert k.front_matter["pdf_title"] == "Open Mind, Open Heart"
    assert k.front_matter["other"] == "keep"
    assert d.front_matter["pdf_title"] == "Some Book"
    assert d.front_matter["pdf_size"] == 2000

    # Plan again should yield no changes
    plan_summary2 = db2.plan_frontmatter_updates(pdfs)
    assert plan_summary2.plans == []


def test_apply_handles_read_errors_and_write_errors(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    path = vault / "(Err 2020).md"
    write(path, "Body\n")

    db = NotesDB.build(str(vault))

    # Craft a plan that will fail reading by pointing to a missing path
    bad_path = vault / "missing.md"
    plans = [
        NotesDB.FrontmatterUpdatePlan(
            pdf_id="Err 2020", note_path=str(bad_path), desired_frontmatter={"pdf_title": "X"}, current_frontmatter={}
        ),
    ]
    summary = db.apply_frontmatter_updates(plans, dry_run=False)
    assert summary.updated == []
    assert len(summary.errors) == 1

    # Now create a plan that cannot write: simulate by making directory read-only
    # On some systems, chmod may not fully prevent replace; we best-effort attempt and accept either path
    plans2 = [
        NotesDB.FrontmatterUpdatePlan(
            pdf_id="Err 2020", note_path=str(path), desired_frontmatter={"pdf_title": "X"}, current_frontmatter={}
        ),
    ]
    old_mode = (vault.stat().st_mode) & 0o777
    try:
        vault.chmod(0o500)
        summary2 = db.apply_frontmatter_updates(plans2, dry_run=False)
        if summary2.errors:
            assert summary2.updated == []
        else:
            assert summary2.updated == [str(path)]
    finally:
        vault.chmod(old_mode)
