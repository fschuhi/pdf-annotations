# tests/test_synopsis.py
from __future__ import annotations

from pathlib import Path

import pytest

from pdf_annot.synopsis import format_synopsis_callout, synopsis_path_for
from pdf_annot.notes import DISPLAY_WIDTH_PX, RESUME_BUTTON_LINE, ensure_synopsis_block, has_synopsis_block

PDF_ID = "(Johnson 2017a)"
SPAN = f'<span class="pdf-thumbnail"><img src="{PDF_ID}.jpg" width="{DISPLAY_WIDTH_PX}"></span>'

# The generated header line, hardcoded here rather than imported from
# pdf_annot.notes/synopsis -- if the production constant is ever typo'd,
# a test that imports the same constant it's checking against would still
# pass. See test_thumbnail_header.py's ANNOT_SEP for the same convention.
SYNOPSIS_HEADER = ">[!abstract] Synopsis (ISBNdb.com)"

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "synopsis"


# --- synopsis_path_for: naming rule, mirrors thumbnail_path_for -------------


def test_synopsis_path_for_uses_pdf_id_as_filename():
    assert synopsis_path_for(PDF_ID, Path("/tmp/synopses")) == Path("/tmp/synopses") / f"{PDF_ID}.txt"


# --- format_synopsis_callout: the canonicalization + render pipeline -------


def test_single_paragraph_no_breaks():
    raw = "Just one paragraph, no breaks anywhere."
    expected = f"{SYNOPSIS_HEADER}\n> Just one paragraph, no breaks anywhere."
    assert format_synopsis_callout(raw) == expected


def test_br_separated_paragraphs():
    raw = "First paragraph.<br/>Second paragraph."
    expected = f"{SYNOPSIS_HEADER}\n> First paragraph.\n>\n> Second paragraph."
    assert format_synopsis_callout(raw) == expected


def test_consecutive_br_collapses_to_one_break():
    raw = "First paragraph.<br/><br/>Second paragraph."
    expected = f"{SYNOPSIS_HEADER}\n> First paragraph.\n>\n> Second paragraph."
    assert format_synopsis_callout(raw) == expected


def test_mixed_case_and_variant_tags_collapse_too():
    """A run of <BR>, <hr/> (or any mix, with or without the trailing slash,
    any case) counts as a single break, same as a repeated <br/>."""
    raw = "First.<BR><hr/>Second."
    expected = f"{SYNOPSIS_HEADER}\n> First.\n>\n> Second."
    assert format_synopsis_callout(raw) == expected


def test_whitespace_between_break_tags_still_collapses_to_one_break():
    """A space (or other whitespace) directly between two break-like tags
    must not break the run -- otherwise the tags are still collapsed
    pairwise but the gap between them survives as a stray near-empty
    paragraph of its own."""
    raw = "First paragraph.<br> <br>Second paragraph."
    expected = f"{SYNOPSIS_HEADER}\n> First paragraph.\n>\n> Second paragraph."
    assert format_synopsis_callout(raw) == expected


def test_leading_and_trailing_blank_lines_and_whitespace_are_stripped():
    raw = "\n\n  First paragraph.  \n\nSecond paragraph.\n\n"
    expected = f"{SYNOPSIS_HEADER}\n> First paragraph.\n>\n> Second paragraph."
    assert format_synopsis_callout(raw) == expected


def test_blank_line_without_br_still_separates_paragraphs():
    """A blank line is deleted during canonicalization same as any other --
    what's left is two adjacent lines with no <br/> between them, which
    end up as two separate paragraphs, not one joined by a space."""
    raw = (
        "Paragraph one, line one\n" "continues on line two with no break tag.\n" "\n" "Paragraph two, all on one line."
    )
    expected = (
        f"{SYNOPSIS_HEADER}\n"
        "> Paragraph one, line one\n"
        ">\n"
        "> continues on line two with no break tag.\n"
        ">\n"
        "> Paragraph two, all on one line."
    )
    assert format_synopsis_callout(raw) == expected


def test_br_at_start_and_end_vanishes_after_final_trim():
    raw = "<br/>First paragraph.<br/>"
    expected = f"{SYNOPSIS_HEADER}\n> First paragraph."
    assert format_synopsis_callout(raw) == expected


def test_whitespace_next_to_a_break_tag_does_not_leak_into_the_paragraph():
    """A break tag immediately followed by leading whitespace on the next
    paragraph (e.g. an attribution line like " --Martin Aylward") must have
    that whitespace stripped -- only the whole-string strip existed before,
    which never touched interior paragraphs."""
    raw = "First paragraph.<br> --Second paragraph, with a leading space."
    expected = f"{SYNOPSIS_HEADER}\n> First paragraph.\n>\n> --Second paragraph, with a leading space."
    assert format_synopsis_callout(raw) == expected


def test_johnson_2017a_fixture():
    """Regression test against a real synopsis file: seven <br/>-delimited
    paragraphs, including a double <br/><br/> after the first one."""
    raw = (FIXTURES_DIR / "johnson_2017a_raw.txt").read_text(encoding="utf-8-sig")
    expected = (FIXTURES_DIR / "johnson_2017a_expected.md").read_text(encoding="utf-8")
    assert format_synopsis_callout(raw) == expected


# --- has_synopsis_block: case-insensitive marker detection -----------------


def test_has_synopsis_block_false_for_plain_body():
    assert not has_synopsis_block("Some free text.\n")


def test_has_synopsis_block_true_for_generated_marker():
    body = f"{SYNOPSIS_HEADER}\n> Some synopsis text.\n"
    assert has_synopsis_block(body)


def test_has_synopsis_block_true_case_insensitively():
    """Must recognize (Thrangu 2003)'s pre-existing, hand-written callout --
    the one manually-inserted synopsis already in the corpus -- so the tool
    never double-inserts on top of it."""
    body = ">[!Abstract] Synopsis (ISBNdb.com)\nThe _Ocean of Definitive Meaning_ ...\n"
    assert has_synopsis_block(body)


def test_has_synopsis_block_false_for_unrelated_abstract_callout():
    """The full sentinel is required -- a bare '[!abstract]' callout the
    user wrote for some other purpose must not be mistaken for ours."""
    body = ">[!abstract] Some other note\nUnrelated content.\n"
    assert not has_synopsis_block(body)


# --- ensure_synopsis_block: placement + one-blank-line normalization -------

CALLOUT = f"{SYNOPSIS_HEADER}\n> Some synopsis text."


def test_inserted_below_thumbnail_span_when_present():
    body = f"{SPAN}\n\nSome free text.\n"
    result = ensure_synopsis_block(body, CALLOUT)
    assert result == f"{SPAN}\n\n{CALLOUT}\n\nSome free text.\n"


def test_inserted_below_resume_button_when_no_thumbnail():
    body = f"{RESUME_BUTTON_LINE}\nSome free text.\n"
    result = ensure_synopsis_block(body, CALLOUT)
    assert result == f"{RESUME_BUTTON_LINE}\n\n{CALLOUT}\n\nSome free text.\n"


def test_inserted_at_top_when_neither_span_nor_button_present():
    body = "Some free text with no anchors.\n"
    result = ensure_synopsis_block(body, CALLOUT)
    assert result == f"\n{CALLOUT}\n\nSome free text with no anchors.\n"


def test_existing_extra_blank_lines_after_anchor_collapse_to_exactly_one():
    body = f"{SPAN}\n\n\n\nSome free text.\n"
    result = ensure_synopsis_block(body, CALLOUT)
    assert result == f"{SPAN}\n\n{CALLOUT}\n\nSome free text.\n"


def test_ensure_synopsis_block_is_idempotent():
    body = f"{SPAN}\n\nSome free text.\n"
    once = ensure_synopsis_block(body, CALLOUT)
    twice = ensure_synopsis_block(once, CALLOUT)
    assert once == twice
