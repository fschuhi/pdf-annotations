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

DEFAULT_INFO_TEXT = "(annotations from the PDF below)"

# The two workflow buttons are added manually, via an Obsidian Dataview
# template call -- this tool never writes them. This is the literal text of
# that line, used only to detect whether it's already present, so the
# thumbnail span can be positioned relative to it.
BUTTONS_LINE = "`BUTTON[time-spent-increment]` `BUTTON[resume-pdf]`"

# The thumbnail span, immediately after the frontmatter (or after the
# buttons line, if present). {{}} escapes a literal brace for .format();
# DISPLAY_WIDTH_PX is filled in now, at import time, so the img width stays
# a single source of truth shared with thumbnails.py rather than a second
# hardcoded number here.
THUMBNAIL_SPAN_TEMPLATE = f'<span class="pdf-thumbnail"><img src="{{pdf_id}}.jpg" width="{DISPLAY_WIDTH_PX}"></span>'

# What marks a bibnote as already having a thumbnail span, for idempotency.
THUMBNAIL_MARKER = 'class="pdf-thumbnail"'


def has_thumbnail_header(body: str) -> bool:
    """
    Does this bibnote's body already carry a thumbnail span?

    body is the post-frontmatter text, e.g. from ParsedNote.body.
    """
    return THUMBNAIL_MARKER in body


def _split_leading_buttons_line(body: str) -> tuple[bool, str]:
    """
    If body's first line is exactly BUTTONS_LINE, return (True, rest) with
    rest being everything after that line and any blank line(s) directly
    beneath it. Otherwise (False, body) unchanged.

    Only checks the first line: the buttons are expected immediately after
    the frontmatter, from the Dataview template call. A BUTTONS_LINE that
    shows up further down (e.g. pasted into the free text) is not treated
    as "the" buttons line.
    """
    lines = body.split("\n")
    if lines and lines[0].strip() == BUTTONS_LINE:
        remainder = lines[1:]
        while remainder and remainder[0].strip() == "":
            remainder.pop(0)
        return True, "\n".join(remainder)
    return False, body


def ensure_thumbnail_header(body: str, pdf_id: str) -> str:
    """
    Insert the thumbnail span into body, unless it's already there.

    Two cases:
      - Buttons already present (added manually) -> blank line, span, blank
        line, then whatever followed the buttons.
      - No buttons (including every brand-new bibnote) -> span, blank line,
        then body unchanged. Buttons are never added here; see BUTTONS_LINE.

    Idempotent: calling this twice on the same body is a no-op the second
    time, matching the "nothing to do if already present" requirement in
    TODO.md. Does not touch the PDF or the filesystem -- naming/rendering
    the actual JPEG is thumbnails.py's job; this only manages the note text.
    """
    if has_thumbnail_header(body):
        return body
    span_line = THUMBNAIL_SPAN_TEMPLATE.format(pdf_id=pdf_id)
    has_buttons, rest = _split_leading_buttons_line(body)
    if has_buttons:
        return f"{BUTTONS_LINE}\n\n{span_line}\n\n{rest}"
    return f"\n{span_line}\n\n{rest}"


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
        # No existing annotation block, append it
        return note_text + "\n" + new_block

    # Split before separator and replace everything from separator onward
    before_sep, _ = note_text.split(separator, 1)
    return before_sep + new_block
