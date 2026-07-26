# src/pdf_annot/thumbnails.py
"""
Page-1 thumbnail rendering for PDF bibnotes.

Renders the first page of a PDF to a JPEG sized for display at
DISPLAY_WIDTH_PX in the note (the `<span class="pdf-thumbnail">` markup
convention), at a higher pixel resolution so it stays crisp on Retina
displays. Deliberately separate from extract.py: extraction reads
annotations, this rasterizes a page -- a different concern, not a variation
on the same one.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

# Display width of the thumbnail in the note, in CSS pixels. Finetune here,
# not via env/toml -- see TODO.md "Thumbnails": this needs manual adjustment
# by eye, not a per-user config surface.
DISPLAY_WIDTH_PX = 250

# Multiplier for the rendered pixmap over DISPLAY_WIDTH_PX, so the image
# stays sharp when the note displays it at DISPLAY_WIDTH_PX on a Retina/HiDPI
# screen instead of rendering at the final display size and scaling up.
RENDER_SCALE = 3

# JPEG compression quality (0-100). A bibnote thumbnail is mostly a text page,
# not a photo, so it compresses cleanly well below the common photo default
# of 90-95; 80 was visually indistinguishable from 90 at thumbnail size in a
# side-by-side check, at meaningfully lower size across a large library.
JPEG_QUALITY = 80


@dataclass
class ThumbnailResult:
    """
    Result of rendering a single PDF's first page to a thumbnail JPEG.

    Mirrors UpdateResult in notes.py: capture the outcome so tests and
    callers (the sync wiring, the batch tool) can inspect what happened
    without the function raising.
    """

    path: Path
    created: bool
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """True if rendering completed without errors."""
        return self.error is None


def thumbnail_path_for(pdf_id: str, thumbnails_dir: Path) -> Path:
    """
    Return the thumbnail path for a given pdf_id, without touching disk.

    Naming rule: same pdf_id as the bibnote, e.g. "(Albini 2013)" ->
    "(Albini 2013).jpg". Pure and side-effect free, so callers can check
    existence themselves before deciding whether to render (and later, a
    batch tool's --force flag is just "skip that check", not a flag this
    module needs to know about).
    """
    return thumbnails_dir / f"{pdf_id}.jpg"


def render_thumbnail(pdf_path: Path, dest_path: Path) -> ThumbnailResult:
    """
    Render page 1 of pdf_path to a JPEG thumbnail at dest_path.

    Always renders; does not check whether dest_path already exists -- that
    decision belongs to the caller (sync.py for new bibnotes, the batch tool
    for existing ones), since the two have different overwrite policies.

    Never raises: a corrupt, unreadable, or zero-page PDF is reported via
    ThumbnailResult.error rather than propagated, per this project's
    "fail gracefully" convention (LLM_INSTRUCTIONS.md).
    """
    try:
        doc = fitz.open(pdf_path)
        try:
            if doc.page_count < 1:
                return ThumbnailResult(path=dest_path, created=False, error="PDF has no pages")
            page = doc[0]
            render_width_px = DISPLAY_WIDTH_PX * RENDER_SCALE
            zoom = render_width_px / page.rect.width
            matrix = fitz.Matrix(zoom, zoom)
            pixmap = page.get_pixmap(matrix=matrix)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            pixmap.save(dest_path, jpg_quality=JPEG_QUALITY)
        finally:
            doc.close()
        return ThumbnailResult(path=dest_path, created=True)
    except Exception as e:
        return ThumbnailResult(path=dest_path, created=False, error=str(e))
