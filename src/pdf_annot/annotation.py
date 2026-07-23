from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional

import fitz

# The gate: this list is handed to page.annots(types=...), so a type that is
# not named here never reaches extraction, the stats, or the renderer.
#
# Squiggly, StrikeOut and Underline were dropped (AUDIT.md A6). Anima emits
# only highlights and comments and the collection contains no real use of
# them, yet they were counted into pdf_highlights while the streamliner
# filtered them out of rendering -- an inflated count against a block that
# never showed them.
#
# Text and FreeText stay although nothing renders them either. That asymmetry
# is deliberate and documented in README.md: pdf_textboxes is the Dataview
# tracker for PDFs whose legacy textboxes are not yet converted, and the
# signal for author-supplied textboxes.
TEXTUAL_ANNOTS = [
    fitz.PDF_ANNOT_TEXT,  # type: ignore
    fitz.PDF_ANNOT_FREE_TEXT,  # type: ignore
    fitz.PDF_ANNOT_HIGHLIGHT,  # type: ignore
]


@dataclass
class Annotation:
    colors: dict
    border: dict
    info: dict
    opacity: float
    lineEnds: Tuple[int, int]
    pageNum: int
    annotType: Tuple[int, str]
    topLeft: Tuple[float, float]
    botRight: Tuple[float, float]
    vertices: Union[List[Tuple[float, float]], None] = None

    # --- FIX: Declare quads as a dataclass field ---
    # It is initialized in __post_init__, so we use init=False
    # The type is Optional[List[fitz.Quad]] because it can be None
    quads: Optional[List[fitz.Quad]] = field(default=None, init=False)

    # We can also declare rect and point for full type-safety
    rect: fitz.Rect = field(default=None, init=False)  # type: ignore
    point: fitz.Point = field(default=None, init=False)  # type: ignore

    def __post_init__(self):
        self.rect = fitz.Rect(self.topLeft, self.botRight)
        if self.vertices:
            n = len(self.vertices) // 4
            # --- FIX: Remove the incorrect type hint from here ---
            self.quads = [fitz.Quad(*self.vertices[i * 4 : i * 4 + 4]) for i in range(n)]
        else:
            self.quads = None
        self.point = self.rect.top_left

    def to_dict(self):
        return dict(
            colors=self.colors,
            info=self.info,
            pageNum=self.pageNum,
            annotType=self.annotType,
            vertices=self.vertices,
            topLeft=self.topLeft,
            botRight=self.botRight,
            border=self.border,
            lineEnds=self.lineEnds,
            opacity=self.opacity,
        )
