# tests/test_backfill_thumbnails.py
"""
Tests for tools/backfill_thumbnails.py.

Self-contained with tmp_path and an in-test synthetic PDF, same reasoning
as test_thumbnails.py and test_sync_thumbnails.py: rendering page 1 has no
content-specific logic, so no checked-in binary fixture is needed.
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import fitz

# tools/ is not part of the installed pdf_annot package (it's invoked
# directly, e.g. `python tools/backfill_thumbnails.py`, same as
# show_pdf_info.py) and so isn't reachable via pyproject.toml's
# pythonpath = ["src"]. Add the project root to sys.path here, scoped to
# this test file only, rather than changing pytest/Makefile configuration
# that every other test would also be affected by.
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_annot.env import Env, IO, Paths
from pdf_annot.frontmatter import format_note, parse_note
from pdf_annot.notes import ensure_thumbnail_header
from pdf_annot.pdf_registry import build_pdf_index
from pdf_annot.thumbnails import ThumbnailResult, thumbnail_path_for
from tools.backfill_thumbnails import BackfillResult, backfill_one, main

PDF_ID = "(Albini 2013)"
ANNOT_SEP = '<hr class="pdf-annot-sep">'


def _build_sample_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "On Dealing with Constructive Emotions", fontsize=16, fontname="helv")
    doc.save(path)
    doc.close()


def _write_bibnote(path: Path, *, with_span: bool = False, free_text: str = "Some free text.\n") -> None:
    body = free_text
    if with_span:
        body = ensure_thumbnail_header(body, PDF_ID)
    body += f"\n{ANNOT_SEP}\n"
    front_matter = {"pdf_id": PDF_ID, "pdf_size": 123, "pdf_mtime": "2026-01-01T00:00:00"}
    path.write_text(format_note(front_matter, body), encoding="utf-8")


def _make_env(tmp_path: Path) -> Env:
    notes_root = tmp_path / "Notes"
    pdf_dir = tmp_path / "PDFs"
    thumbnails_dir = tmp_path / "Thumbnails"
    notes_root.mkdir()
    pdf_dir.mkdir()
    return Env(
        paths=Paths(notes_root=notes_root, pdf_dirs=[pdf_dir], thumbnails_dir=thumbnails_dir),
        io=IO(create_missing_dirs=True),
    )


def _build_pdf_and_index(env: Env, pdf_id: str = PDF_ID):
    pdf_path = env.paths.pdf_dirs[0] / f"{pdf_id} Some Title.pdf"
    _build_sample_pdf(pdf_path)
    return build_pdf_index([str(env.paths.pdf_dirs[0])])


# --- Case 1: no bibnote for this PDF yet ------------------------------------


def test_no_bibnote_is_skipped_not_created(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"

    result = backfill_one(env, pdf_index["(albini 2013)"], note_path)

    assert result.success
    assert result.skipped_reason == "no bibnote for this PDF"
    assert not note_path.exists(), "this tool must never create a bibnote"


# --- Case 2: decline-guard ---------------------------------------------------


def test_note_missing_separator_is_declined(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"
    note_path.write_text(format_note({"pdf_id": PDF_ID}, "Some free text, no separator.\n"), encoding="utf-8")

    result = backfill_one(env, pdf_index["(albini 2013)"], note_path)

    assert result.success
    assert result.skipped_reason == "declined: missing annotation separator"
    assert 'class="pdf-thumbnail"' not in note_path.read_text(encoding="utf-8")


# --- Case 3: fully up to date -------------------------------------------------


def test_already_up_to_date_is_a_true_no_op(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"
    _write_bibnote(note_path, with_span=True)
    thumbnail_dest = thumbnail_path_for(PDF_ID, env.paths.thumbnails_dir)
    thumbnail_dest.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_dest.write_bytes(b"existing jpg bytes")
    before = note_path.read_bytes()

    with patch("tools.backfill_thumbnails.render_thumbnail") as render_spy:
        result = backfill_one(env, pdf_index["(albini 2013)"], note_path)

    assert result.success
    assert result.skipped_reason == "already up to date"
    render_spy.assert_not_called()
    assert note_path.read_bytes() == before, "an up-to-date note must not be rewritten"
    assert thumbnail_dest.read_bytes() == b"existing jpg bytes"


# --- Case 4: span absent, JPEG absent ----------------------------------------


def test_span_absent_jpeg_absent_renders_and_adds_span(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"
    _write_bibnote(note_path, with_span=False)

    result = backfill_one(env, pdf_index["(albini 2013)"], note_path)

    assert result.success
    assert result.rendered
    assert result.span_added
    assert thumbnail_path_for(PDF_ID, env.paths.thumbnails_dir).exists()
    assert 'class="pdf-thumbnail"' in note_path.read_text(encoding="utf-8")


# --- Case 5: span absent, JPEG already exists --------------------------------


def test_span_absent_jpeg_present_adds_span_without_rerendering(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"
    _write_bibnote(note_path, with_span=False)
    thumbnail_dest = thumbnail_path_for(PDF_ID, env.paths.thumbnails_dir)
    thumbnail_dest.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_dest.write_bytes(b"pre-existing jpg bytes")

    with patch("tools.backfill_thumbnails.render_thumbnail") as render_spy:
        result = backfill_one(env, pdf_index["(albini 2013)"], note_path)

    assert result.success
    assert not result.rendered
    assert result.span_added
    render_spy.assert_not_called()
    assert thumbnail_dest.read_bytes() == b"pre-existing jpg bytes"
    assert 'class="pdf-thumbnail"' in note_path.read_text(encoding="utf-8")


# --- Case 6: span present, JPEG missing (the "delete to regenerate" case) ---


def test_span_present_jpeg_missing_rerenders_without_rewriting_note(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"
    _write_bibnote(note_path, with_span=True)
    before = note_path.read_bytes()
    assert not thumbnail_path_for(PDF_ID, env.paths.thumbnails_dir).exists()

    result = backfill_one(env, pdf_index["(albini 2013)"], note_path)

    assert result.success
    assert result.rendered
    assert not result.span_added
    assert thumbnail_path_for(PDF_ID, env.paths.thumbnails_dir).exists()
    assert note_path.read_bytes() == before, "the note already had the span; it must not be rewritten"


def test_force_rerenders_even_when_everything_is_already_present(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"
    _write_bibnote(note_path, with_span=True)
    thumbnail_dest = thumbnail_path_for(PDF_ID, env.paths.thumbnails_dir)
    thumbnail_dest.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_dest.write_bytes(b"stale jpg bytes")

    result = backfill_one(env, pdf_index["(albini 2013)"], note_path, force=True)

    assert result.success
    assert result.rendered
    assert not result.span_added
    assert thumbnail_dest.read_bytes() != b"stale jpg bytes", "force must re-render even though the span is present"


# --- Case 7: rendering fails --------------------------------------------------


def test_render_failure_is_reported_and_note_left_untouched(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"
    _write_bibnote(note_path, with_span=False)
    before = note_path.read_bytes()

    failing_result = ThumbnailResult(path=Path("unused"), created=False, error="simulated render failure")
    with patch("tools.backfill_thumbnails.render_thumbnail", return_value=failing_result):
        result = backfill_one(env, pdf_index["(albini 2013)"], note_path)

    assert not result.success
    assert result.error == "simulated render failure"
    assert note_path.read_bytes() == before


# --- CLI smoke test: --pdf-id and --force ------------------------------------


def test_cli_single_pdf_id_with_force(tmp_path: Path):
    env = _make_env(tmp_path)
    pdf_index = _build_pdf_and_index(env)
    note_path = env.paths.notes_root / f"{PDF_ID}.md"
    _write_bibnote(note_path, with_span=True)
    thumbnail_dest = thumbnail_path_for(PDF_ID, env.paths.thumbnails_dir)
    thumbnail_dest.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_dest.write_bytes(b"stale jpg bytes")

    config_path = tmp_path / "pdf_annot.toml"
    config_path.write_text(
        f'[paths]\nnotes_root = "{env.paths.notes_root}"\n'
        f'pdf_dirs = ["{env.paths.pdf_dirs[0]}"]\n'
        f'thumbnails_dir = "{env.paths.thumbnails_dir}"\n',
        encoding="utf-8",
    )

    cli_args = ["backfill_thumbnails", "--env", str(config_path), "--pdf-id", PDF_ID, "--force"]
    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture), patch.object(sys, "argv", cli_args):
        return_code = main()

    assert return_code == 0
    output = stdout_capture.getvalue()
    assert "UPDATED" in output
    assert "Errors:   0" in output
    assert thumbnail_dest.read_bytes() != b"stale jpg bytes"
