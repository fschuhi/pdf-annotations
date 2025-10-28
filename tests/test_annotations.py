# tests/test_annotations.py
from __future__ import annotations

import textwrap
from pathlib import Path

from pdf_annot.notes_db import NotesDB


def write(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def test_plan_create_and_apply_block(tmp_path: Path):
    vault = tmp_path / "vault"
    note_path = vault / "(Alpha 2020).md"

    # Note with correct frontmatter and no annotation block yet
    text = textwrap.dedent(
        """\
        ---
        pdf_title: Foo
        pdf_size: 1
        ---
        Body before
        """
    )
    write(note_path, text)
    db = NotesDB.build(str(vault))

    # Rendered block (as produced by tools/ndjson_to_md_block.py)
    block = textwrap.dedent(
        """\
        <hr class="pdf-annot-sep">

        <span class="pdf-annot-info">below the automatically generated annotations from the PDF</span>

        > Quote A [1](pdf://VQGPEHE?page=1)
        """
    )

    # Plan
    ps = db.plan_annotation_updates({"Alpha 2020": block})
    assert len(ps.missing_notes) == 0
    assert len(ps.plans) == 1
    assert ps.plans[0].action in ("create_block", "update_block")

    # Dry-run apply
    ar = db.apply_annotation_updates(ps.plans, dry_run=True)
    assert ar.errors == []
    assert ar.updated == [str(note_path)]
    assert ar.unchanged == []

    # Real apply
    ar2 = db.apply_annotation_updates(ps.plans, dry_run=False)
    assert ar2.errors == []
    assert ar2.updated == [str(note_path)]

    # Running again should be idempotent -> unchanged
    db2 = NotesDB.build(str(vault))
    ps2 = db2.plan_annotation_updates({"Alpha 2020": block})
    ar3 = db2.apply_annotation_updates(ps2.plans, dry_run=False)
    assert ar3.updated == []
    assert ar3.errors == []
    assert ar3.unchanged == [str(note_path)]


def test_update_existing_block_preserves_frontmatter_and_prefix(tmp_path: Path):
    vault = tmp_path / "vault"
    note_path = vault / "(Beta 2019).md"

    original = textwrap.dedent(
        """\
        ---
        a: 1
        pdf_title: Old
        pdf_size: 2
        ---
        Intro text

        <hr class="pdf-annot-sep">

        <span class="pdf-annot-info">below the automatically generated annotations from the PDF</span>

        > Old quote [1](pdf://HASH?page=1)
        """
    )
    write(note_path, original)
    db = NotesDB.build(str(vault))

    new_block = textwrap.dedent(
        """\
        <hr class="pdf-annot-sep">

        <span class="pdf-annot-info">below the automatically generated annotations from the PDF</span>

        > New quote [1](pdf://HASH?page=1)
        """
    )

    ps = db.plan_annotation_updates({"Beta 2019": new_block})
    assert len(ps.plans) == 1
    assert ps.plans[0].action == "update_block"

    ar = db.apply_annotation_updates(ps.plans, dry_run=False)
    assert ar.errors == []
    assert ar.updated == [str(note_path)]

    # Verify FM intact and prefix preserved
    text_after = note_path.read_text(encoding="utf-8")
    assert text_after.startswith("---\n")
    assert "a: 1" in text_after
    assert "pdf_title: Old" in text_after
    assert "pdf_size: 2" in text_after
    assert "Intro text" in text_after
    assert "> New quote" in text_after
    assert "> Old quote" not in text_after


def test_missing_note_is_reported(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    db = NotesDB.build(str(vault))
    block = '<hr class="pdf-annot-sep">\n\n<span class="pdf-annot-info">below the automatically generated annotations from the PDF</span>\n\n> Q\n'
    ps = db.plan_annotation_updates({"Missing 2010": block})
    assert ps.missing_notes == ["Missing 2010"]
    assert ps.plans == []
