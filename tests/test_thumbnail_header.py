# tests/test_thumbnail_header.py
from __future__ import annotations

from pdf_annot.notes import BUTTONS_LINE, DISPLAY_WIDTH_PX, ensure_thumbnail_header, has_thumbnail_header

PDF_ID = "(Albini 2013)"
SPAN = f'<span class="pdf-thumbnail"><img src="{PDF_ID}.jpg" width="{DISPLAY_WIDTH_PX}"></span>'


def test_has_thumbnail_header_false_for_plain_body():
    assert not has_thumbnail_header("Some free text.\n")


def test_has_thumbnail_header_true_once_present():
    body = ensure_thumbnail_header("Some free text.\n", PDF_ID)
    assert has_thumbnail_header(body)


def test_ensure_thumbnail_header_without_buttons_prepends_span_only():
    """
    No buttons line -- covers both an existing bibnote without buttons and
    every brand-new bibnote (sync.py's new-note path starts with body="").
    Buttons are never added here; only the span goes in.
    """
    body = ensure_thumbnail_header("Some free text.\n", PDF_ID)
    assert body == f"\n{SPAN}\n\nSome free text.\n"
    assert BUTTONS_LINE not in body


def test_ensure_thumbnail_header_on_empty_body():
    body = ensure_thumbnail_header("", PDF_ID)
    assert body == f"\n{SPAN}\n\n"


def test_ensure_thumbnail_header_with_existing_buttons_inserts_between():
    """
    Buttons were added manually (Dataview template call) -- the span goes
    in below them, with a blank line on each side, and the buttons line
    itself is preserved exactly.
    """
    body = f"{BUTTONS_LINE}\n\nSome free text.\n"
    result = ensure_thumbnail_header(body, PDF_ID)
    assert result == f"{BUTTONS_LINE}\n\n{SPAN}\n\nSome free text.\n"


def test_ensure_thumbnail_header_with_buttons_and_no_blank_line_yet():
    """
    Same as above, but the Dataview call left no blank line beneath it --
    the function supplies one rather than assuming it's already there.
    """
    body = f"{BUTTONS_LINE}\nSome free text.\n"
    result = ensure_thumbnail_header(body, PDF_ID)
    assert result == f"{BUTTONS_LINE}\n\n{SPAN}\n\nSome free text.\n"


def test_ensure_thumbnail_header_is_idempotent():
    once = ensure_thumbnail_header(f"{BUTTONS_LINE}\n\nSome free text.\n", PDF_ID)
    twice = ensure_thumbnail_header(once, PDF_ID)
    assert once == twice


def test_buttons_line_elsewhere_in_body_is_not_treated_as_the_header_buttons():
    """
    Only the first line counts as "the" buttons line (see
    _split_leading_buttons_line's docstring). A pasted-in mention further
    down the free text must not be mistaken for it.
    """
    body = f"Some free text mentioning {BUTTONS_LINE} in passing.\n"
    result = ensure_thumbnail_header(body, PDF_ID)
    assert result == f"\n{SPAN}\n\n{body}"
