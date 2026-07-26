# tests/test_thumbnails.py
from __future__ import annotations

from pathlib import Path

import fitz

from pdf_annot.thumbnails import (
    DISPLAY_WIDTH_PX,
    RENDER_SCALE,
    render_thumbnail,
    thumbnail_path_for,
)


def _build_sample_pdf(path: Path) -> None:
    """
    Build a minimal single-page PDF representative of a journal page: a
    title, two-column-ish body text. No checked-in binary fixture needed --
    rendering page 1 has no content-specific logic the way column-detection
    in extract.py does, so a synthetic page exercises the real code path.
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # US Letter
    page.insert_text((72, 72), "On Dealing with Constructive Emotions", fontsize=16, fontname="helv")
    page.insert_textbox(fitz.Rect(72, 130, 540, 700), "Lorem ipsum dolor sit amet. " * 40, fontsize=9, fontname="helv")
    doc.save(path)
    doc.close()


def test_thumbnail_path_for_uses_pdf_id(tmp_path: Path):
    thumbnails_dir = tmp_path / "Thumbnails"
    result = thumbnail_path_for("(Albini 2013)", thumbnails_dir)
    assert result == thumbnails_dir / "(Albini 2013).jpg"


def test_render_thumbnail_happy_path(tmp_path: Path):
    pdf_path = tmp_path / "input.pdf"
    _build_sample_pdf(pdf_path)
    dest_path = thumbnail_path_for("(Albini 2013)", tmp_path / "Thumbnails")

    result = render_thumbnail(pdf_path, dest_path)

    assert result.success
    assert result.created
    assert result.error is None
    assert result.path == dest_path
    assert dest_path.exists()

    # Reopen as a raw pixmap (not fitz.open(), which wraps a JPEG as a
    # one-page pseudo-PDF and re-renders it at its own DPI assumption,
    # silently distorting the pixel count we're trying to verify here) to
    # confirm it's a valid, correctly-sized JPEG. We don't assert exact
    # bytes/filesize: exact-byte goldens are fragile across PyMuPDF/encoder
    # version bumps.
    rendered = fitz.Pixmap(str(dest_path))
    assert rendered.width == DISPLAY_WIDTH_PX * RENDER_SCALE


def test_render_thumbnail_reports_error_for_invalid_pdf(tmp_path: Path):
    bad_pdf = tmp_path / "not_a_pdf.pdf"
    bad_pdf.write_text("this is not a PDF")
    dest_path = thumbnail_path_for("(Bad 2020)", tmp_path / "Thumbnails")

    result = render_thumbnail(bad_pdf, dest_path)

    assert not result.success
    assert not result.created
    assert result.error is not None
    assert not dest_path.exists()
