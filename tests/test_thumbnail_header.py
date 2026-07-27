# tests/test_thumbnail_header.py
from __future__ import annotations

from pdf_annot.notes import (
    DISPLAY_WIDTH_PX,
    RESUME_BUTTON_LINE,
    ensure_thumbnail_header,
    has_thumbnail_header,
    new_bibnote_header,
    replace_annotation_block,
)

PDF_ID = "(Albini 2013)"
SPAN = f'<span class="pdf-thumbnail"><img src="{PDF_ID}.jpg" width="{DISPLAY_WIDTH_PX}"></span>'
ANNOT_SEP = '<hr class="pdf-annot-sep">'


# --- ensure_thumbnail_header: existing bibnotes only, never a button ---------


def test_has_thumbnail_header_false_for_plain_body():
    assert not has_thumbnail_header("Some free text.\n")


def test_has_thumbnail_header_true_once_present():
    body = ensure_thumbnail_header("Some free text.\n", PDF_ID)
    assert has_thumbnail_header(body)


def test_ensure_thumbnail_header_prepends_span_with_blank_lines():
    body = ensure_thumbnail_header("Some free text.\n", PDF_ID)
    assert body == f"\n{SPAN}\n\nSome free text.\n"


def test_ensure_thumbnail_header_is_idempotent():
    once = ensure_thumbnail_header("Some free text.\n", PDF_ID)
    twice = ensure_thumbnail_header(once, PDF_ID)
    assert once == twice


# --- new_bibnote_header: brand-new bibnotes only, always the button ---------


def test_new_bibnote_header_without_thumbnail_is_button_only():
    header = new_bibnote_header(PDF_ID, with_thumbnail=False)
    assert header == f"{RESUME_BUTTON_LINE}\n"


def test_new_bibnote_header_with_thumbnail_puts_span_below_the_button():
    header = new_bibnote_header(PDF_ID, with_thumbnail=True)
    assert header == f"{RESUME_BUTTON_LINE}\n\n{SPAN}\n\n"


# --- replace_annotation_block: the double-blank-line regression -------------


def test_first_annotation_block_gets_exactly_one_blank_line_before_it():
    """
    A brand-new bibnote's header (new_bibnote_header/ensure_thumbnail_header)
    always ends in a blank line already; appending the first-ever annotation
    block must not stack a second one on top of that.
    """
    note_text = f"---\npdf_id: {PDF_ID}\n---\n{RESUME_BUTTON_LINE}\n\n{SPAN}\n\n"
    new_block = f"{ANNOT_SEP}\nsome rendered annotations"

    result = replace_annotation_block(note_text, new_block)

    assert result == f"---\npdf_id: {PDF_ID}\n---\n{RESUME_BUTTON_LINE}\n\n{SPAN}\n\n{new_block}"


def test_replacing_an_existing_annotation_block_is_unaffected_by_the_fix():
    """
    The separator-present branch is untouched by the rstrip fix -- whatever
    spacing already exists before the separator (including anything the
    user hand-edited) is preserved exactly.
    """
    note_text = f"---\npdf_id: {PDF_ID}\n---\nSome free text.\n\n\n{ANNOT_SEP}\nold annotations"
    new_block = f"{ANNOT_SEP}\nnew annotations"

    result = replace_annotation_block(note_text, new_block)

    assert result == f"---\npdf_id: {PDF_ID}\n---\nSome free text.\n\n\n{new_block}"
