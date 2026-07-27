# tests/test_sync_thumbnails.py
"""
Integration tests for the thumbnail wiring in sync.py.

Self-contained with tmp_path and an in-test synthetic PDF, deliberately not
the checked-in seeds/goldens convention used by test_core_workflow.py and
test_sync_cli.py -- rendering page 1 has no content-specific logic, so no
new binary fixture is needed (see test_thumbnails.py for the same reasoning).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import fitz

from pdf_annot.env import Env, IO, Paths
from pdf_annot.frontmatter import parse_note
from pdf_annot.notes import RESUME_BUTTON_LINE
from pdf_annot.pdf_registry import build_pdf_index
from pdf_annot.sync import sync_pdf_to_note
from pdf_annot.thumbnails import ThumbnailResult, thumbnail_path_for

ANNOT_SEP = '<hr class="pdf-annot-sep">'


def _build_sample_pdf(path: Path, *, with_highlight: bool = False) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "On Dealing with Constructive Emotions", fontsize=16, fontname="helv")
    if with_highlight:
        page.insert_text((72, 120), "a line worth highlighting", fontsize=11, fontname="helv")
        quad = page.search_for("a line worth highlighting")[0]
        page.add_highlight_annot(quad)
    doc.save(path)
    doc.close()


def _make_env(tmp_path: Path, *, with_thumbnails: bool) -> Env:
    notes_root = tmp_path / "Notes"
    pdf_dir = tmp_path / "PDFs"
    notes_root.mkdir()
    pdf_dir.mkdir()
    thumbnails_dir = None
    if with_thumbnails:
        thumbnails_dir = tmp_path / "Thumbnails"
    return Env(
        paths=Paths(notes_root=notes_root, pdf_dirs=[pdf_dir], thumbnails_dir=thumbnails_dir),
        io=IO(create_missing_dirs=True),
    )


def _build_pdf_and_index(env: Env, pdf_id: str = "(Albini 2013)", *, with_highlight: bool = False):
    pdf_path = env.paths.pdf_dirs[0] / f"{pdf_id} Some Title.pdf"
    _build_sample_pdf(pdf_path, with_highlight=with_highlight)
    return build_pdf_index([str(env.paths.pdf_dirs[0])])


def test_new_bibnote_gets_button_and_thumbnail_when_configured(tmp_path: Path):
    env = _make_env(tmp_path, with_thumbnails=True)
    pdf_index = _build_pdf_and_index(env)
    pdf_info = pdf_index["(albini 2013)"]
    note_path = env.paths.notes_root / "(Albini 2013).md"

    result = sync_pdf_to_note(env, pdf_info, note_path, datetime.now().isoformat(timespec="seconds"))

    assert result.success
    assert result.note_updated
    assert result.thumbnail_error is None

    expected_thumbnail = thumbnail_path_for(pdf_info.pdf_id, env.paths.thumbnails_dir)
    assert expected_thumbnail.exists()

    note_text = note_path.read_text(encoding="utf-8")
    body = parse_note(note_text).body
    assert RESUME_BUTTON_LINE in body
    assert 'class="pdf-thumbnail"' in body
    assert body.index(RESUME_BUTTON_LINE) < body.index('class="pdf-thumbnail"') < body.index(ANNOT_SEP)
    # Exactly one blank line before the annotation separator -- the
    # double-blank-line regression this session's fix addressed.
    assert "\n\n\n" not in note_text


def test_new_bibnote_gets_neither_button_nor_thumbnail_when_unconfigured(tmp_path: Path):
    """
    thumbnails_dir unset must reproduce exactly the pre-thumbnail-feature
    behavior -- this is what every golden fixture predating the feature
    relies on. The button is not independent of this gate, only of
    has_annotations.
    """
    env = _make_env(tmp_path, with_thumbnails=False)
    pdf_index = _build_pdf_and_index(env)
    pdf_info = pdf_index["(albini 2013)"]
    note_path = env.paths.notes_root / "(Albini 2013).md"

    result = sync_pdf_to_note(env, pdf_info, note_path, datetime.now().isoformat(timespec="seconds"))

    assert result.success
    assert result.thumbnail_error is None
    body = parse_note(note_path.read_text(encoding="utf-8")).body
    assert RESUME_BUTTON_LINE not in body
    assert 'class="pdf-thumbnail"' not in body


def test_new_bibnote_gets_the_button_even_with_real_annotations(tmp_path: Path):
    """
    The button is independent of has_annotations -- a PDF that does have
    highlights still gets it, not just the zero-annotation case that
    originally motivated it. (thumbnails_dir must still be configured --
    that gate is unrelated to has_annotations.)
    """
    env = _make_env(tmp_path, with_thumbnails=True)
    pdf_index = _build_pdf_and_index(env, with_highlight=True)
    pdf_info = pdf_index["(albini 2013)"]
    note_path = env.paths.notes_root / "(Albini 2013).md"

    result = sync_pdf_to_note(env, pdf_info, note_path, datetime.now().isoformat(timespec="seconds"))

    assert result.success
    body = parse_note(note_path.read_text(encoding="utf-8")).body
    assert RESUME_BUTTON_LINE in body
    assert "pdf://" in body, "sanity check: this PDF really does have a highlight"


def test_dry_run_never_renders_or_writes_a_thumbnail(tmp_path: Path):
    env = _make_env(tmp_path, with_thumbnails=True)
    pdf_index = _build_pdf_and_index(env)
    pdf_info = pdf_index["(albini 2013)"]
    note_path = env.paths.notes_root / "(Albini 2013).md"

    result = sync_pdf_to_note(env, pdf_info, note_path, datetime.now().isoformat(timespec="seconds"), dry_run=True)

    assert result.success
    assert result.dry_run
    assert not note_path.exists(), "dry run must not write the note"
    expected_thumbnail = thumbnail_path_for(pdf_info.pdf_id, env.paths.thumbnails_dir)
    assert not expected_thumbnail.exists(), "dry run must not render a thumbnail either"


def test_render_failure_does_not_fail_the_sync_but_still_adds_the_button(tmp_path: Path):
    env = _make_env(tmp_path, with_thumbnails=True)
    pdf_index = _build_pdf_and_index(env)
    pdf_info = pdf_index["(albini 2013)"]
    note_path = env.paths.notes_root / "(Albini 2013).md"

    failing_result = ThumbnailResult(path=Path("unused"), created=False, error="simulated render failure")
    with patch("pdf_annot.sync.render_thumbnail", return_value=failing_result):
        result = sync_pdf_to_note(env, pdf_info, note_path, datetime.now().isoformat(timespec="seconds"))

    assert result.success, "a thumbnail failure must not fail the whole sync"
    assert result.note_updated
    assert result.thumbnail_error == "simulated render failure"

    body = parse_note(note_path.read_text(encoding="utf-8")).body
    assert 'class="pdf-thumbnail"' not in body, "must not reference an image that doesn't exist"
    assert RESUME_BUTTON_LINE in body, "the button does not depend on the thumbnail render succeeding"


def test_already_rendered_thumbnail_is_not_rendered_again(tmp_path: Path):
    env = _make_env(tmp_path, with_thumbnails=True)
    pdf_index = _build_pdf_and_index(env)
    pdf_info = pdf_index["(albini 2013)"]
    note_path = env.paths.notes_root / "(Albini 2013).md"

    expected_thumbnail = thumbnail_path_for(pdf_info.pdf_id, env.paths.thumbnails_dir)
    expected_thumbnail.parent.mkdir(parents=True, exist_ok=True)
    expected_thumbnail.write_bytes(b"pre-existing jpg bytes")

    with patch("pdf_annot.sync.render_thumbnail") as render_spy:
        result = sync_pdf_to_note(env, pdf_info, note_path, datetime.now().isoformat(timespec="seconds"))

    assert result.success
    render_spy.assert_not_called()
    # The pre-existing file must survive untouched -- proof render was skipped,
    # not just unobserved.
    assert expected_thumbnail.read_bytes() == b"pre-existing jpg bytes"
    body = parse_note(note_path.read_text(encoding="utf-8")).body
    assert 'class="pdf-thumbnail"' in body
    assert RESUME_BUTTON_LINE in body


def test_existing_bibnote_never_gets_a_button(tmp_path: Path):
    """
    The button is only ever added at creation time. An existing bibnote that
    gets its thumbnail on a later sync (e.g. thumbnails_dir was just
    configured) must get the span only, never the button.
    """
    env = _make_env(tmp_path, with_thumbnails=True)
    pdf_index = _build_pdf_and_index(env)
    pdf_info = pdf_index["(albini 2013)"]
    note_path = env.paths.notes_root / "(Albini 2013).md"

    front_matter = f"---\npdf_id: {pdf_info.pdf_id}\npdf_size: 1\n" f"pdf_mtime: '2000-01-01T00:00:00'\n---\n"
    note_path.write_text(f"{front_matter}Some existing free text.\n\n{ANNOT_SEP}\nold block", encoding="utf-8")

    result = sync_pdf_to_note(env, pdf_info, note_path, datetime.now().isoformat(timespec="seconds"))

    assert result.success
    body = parse_note(note_path.read_text(encoding="utf-8")).body
    assert 'class="pdf-thumbnail"' in body
    assert RESUME_BUTTON_LINE not in body
