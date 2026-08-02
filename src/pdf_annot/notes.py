# src/pdf_annot/notes.py
"""
Note-level operations for working with Obsidian markdown notes.

Handles annotation blocks, info text extraction, and other note-specific logic
that goes beyond frontmatter manipulation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pdf_annot.thumbnails import DISPLAY_WIDTH_PX
from pdf_annot.synopsis import SYNOPSIS_HEADER

DEFAULT_INFO_TEXT = "(annotations from the PDF below)"

# The resume-pdf button: always added for a brand-new bibnote, regardless of
# has_annotations, because a PDF with zero annotations renders no pdf://
# link anywhere in its block -- without this, there is no way to open it
# from the note at all. Only ever added at creation time; existing bibnotes
# are never touched by a button, so there is nothing to detect for them.
RESUME_BUTTON_LINE = "`BUTTON[resume-pdf]`"

# The thumbnail span, immediately after the frontmatter for an existing
# bibnote, or after the resume-pdf button for a brand-new one. {{}} escapes
# a literal brace for .format(); DISPLAY_WIDTH_PX is filled in now, at
# import time, so the img width stays a single source of truth shared with
# thumbnails.py rather than a second hardcoded number here.
THUMBNAIL_SPAN_TEMPLATE = f'<span class="pdf-thumbnail"><img src="{{pdf_id}}.jpg" width="{DISPLAY_WIDTH_PX}"></span>'

# What marks a bibnote as already having a thumbnail span, for idempotency.
THUMBNAIL_MARKER = 'class="pdf-thumbnail"'


def has_thumbnail_header(body: str) -> bool:
    """
    Does this bibnote's body already carry a thumbnail span?

    body is the post-frontmatter text, e.g. from ParsedNote.body.
    """
    return THUMBNAIL_MARKER in body


def new_bibnote_header(pdf_id: str, *, with_thumbnail: bool) -> str:
    """
    The fixed header for a brand-new bibnote: the resume-pdf button, always,
    plus the thumbnail span beneath it when with_thumbnail is True (i.e. a
    thumbnail was configured and rendered successfully for it).

    Only for sync.py's new-note path (note_exists is False) -- a new note's
    shape is fully known in advance, so there is nothing to detect. Existing
    bibnotes are never retrofitted with a button; see ensure_thumbnail_header
    for what they get instead.
    """
    if with_thumbnail:
        span_line = THUMBNAIL_SPAN_TEMPLATE.format(pdf_id=pdf_id)
        return f"{RESUME_BUTTON_LINE}\n\n{span_line}\n\n"
    return f"{RESUME_BUTTON_LINE}\n"


def ensure_thumbnail_header(body: str, pdf_id: str) -> str:
    """
    Insert the thumbnail span into an existing bibnote's body, unless it's
    already there.

    Existing bibnotes never get a button -- only a brand-new bibnote does,
    via new_bibnote_header, called separately by sync.py's new-note path.
    So this always does the same thing: prepend the span, with a blank
    line before and after.

    Idempotent: calling this twice on the same body is a no-op the second
    time, matching the "nothing to do if already present" requirement in
    TODO.md. Does not touch the PDF or the filesystem -- naming/rendering
    the actual JPEG is thumbnails.py's job; this only manages the note text.
    """
    if has_thumbnail_header(body):
        return body
    span_line = THUMBNAIL_SPAN_TEMPLATE.format(pdf_id=pdf_id)
    return f"\n{span_line}\n\n{body}"


def has_synopsis_block(body: str) -> bool:
    """
    Does this bibnote's body already carry a synopsis callout?

    Case-insensitive: also matches (Thrangu 2003)'s pre-existing,
    hand-written ">[!Abstract] Synopsis (ISBNdb.com)" callout -- the one
    manually-inserted synopsis already in the corpus -- so the fill-synopses
    tool never double-inserts on top of it. Requires the full sentinel, not
    just "[!abstract]", so an unrelated callout the user wrote for some
    other purpose is never mistaken for ours.
    """
    return SYNOPSIS_HEADER.lower() in body.lower()


def ensure_synopsis_block(body: str, callout: str) -> str:
    """
    Insert a rendered synopsis callout into an existing bibnote's body,
    unless one is already there.

    Placement: directly below the thumbnail span if present, else directly
    below the resume-pdf button, else at the very top of the body -- covers
    the case where a thumbnail was never configured/rendered, or was
    manually deleted from a note (bibnotes are plain text; nothing stops
    that). Always normalizes to exactly one blank line before and after
    the callout, regardless of how much whitespace was already there --
    same fixed-spacing convention as ensure_thumbnail_header, so re-running
    against a hand-edited note doesn't accumulate stray blank lines.

    Idempotent: calling this twice on the same body is a no-op the second
    time. Does not touch the filesystem or read the synopsis .txt --
    formatting the callout text is synopsis.format_synopsis_callout's job
    (see `resolve_row` in `isbndb_synopsis.py` for where the raw text
    itself comes from); this only manages the note text.
    """
    if has_synopsis_block(body):
        return body

    anchor_end = 0
    for marker in (THUMBNAIL_MARKER, RESUME_BUTTON_LINE):
        idx = body.find(marker)
        if idx != -1:
            newline_idx = body.find("\n", idx)
            anchor_end = newline_idx + 1 if newline_idx != -1 else len(body)
            break

    before = body[:anchor_end]
    after = body[anchor_end:].lstrip("\n")
    return f"{before}\n{callout}\n\n{after}"


@dataclass
class UpdateResult:
    """
    Result of processing a single PDF-note pair.

    Captures what changed during the update workflow so tests and workflows
    can make assertions or decisions based on the outcome.
    """

    note_path: Path
    frontmatter_changed: bool
    annotation_block_changed: bool
    note_updated: bool
    error: Optional[str] = None
    # Reason sync refused to touch the note (missing separator or frontmatter).
    # None means the note was not declined. A decline is not an error: sync did
    # the right thing by not guessing, so `success` stays True.
    declined: Optional[str] = None
    # True when this result came from a preview run: everything was computed,
    # nothing was written. `note_updated` then reads as "would have been
    # updated" rather than "was updated" (AUDIT.md A8, finding F20).
    dry_run: bool = False
    # Set when thumbnail rendering was attempted and failed. A failed
    # thumbnail does not fail the whole sync -- the note's frontmatter and
    # annotations are the primary job -- but the failure still needs to be
    # visible somewhere, so it's carried here rather than swallowed.
    thumbnail_error: Optional[str] = None

    @property
    def success(self) -> bool:
        """True if processing completed without errors."""
        return self.error is None


def extract_info_text(note_text: str) -> str:
    """
    Extract the text from <span class="pdf-annot-info">...</span>.

    This allows preserving custom info text that users may have edited,
    rather than overwriting with the default text.

    Args:
        note_text: Full note content

    Returns:
        The info text if found, otherwise the default text.
    """
    pattern = r'<span class="pdf-annot-info">([^<]+)</span>'
    match = re.search(pattern, note_text)
    if match:
        return match.group(1)
    return DEFAULT_INFO_TEXT


def replace_annotation_block(note_text: str, new_block: str) -> str:
    """
    Replace the annotation block in a note (everything from the separator onward).

    The separator is: <hr class="pdf-annot-sep">

    Args:
        note_text: Original note content
        new_block: New annotation block (should already include separator + info + annotations)

    Returns:
        Updated note text with replaced annotation block
    """
    separator = '<hr class="pdf-annot-sep">'

    if separator not in note_text:
        # No existing annotation block yet, append it. rstrip first: the
        # header template (new_bibnote_header / ensure_thumbnail_header)
        # already leaves note_text ending in a blank line, so appending
        # "\n" + new_block unconditionally on top of that stacked a second
        # one -- only ever visible the first time a bibnote gets its
        # annotation block, which is why it went unnoticed until a
        # zero-annotation new bibnote made it obvious.
        return note_text.rstrip("\n") + "\n\n" + new_block

    # Split before separator and replace everything from separator onward
    before_sep, _ = note_text.split(separator, 1)
    return before_sep + new_block
