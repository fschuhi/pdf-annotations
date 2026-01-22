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
        The info text if found, otherwise the default text
    """
    pattern = r'<span class="pdf-annot-info">([^<]+)</span>'
    match = re.search(pattern, note_text)
    if match:
        return match.group(1)
    return "(annotations from the PDF below)"


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
