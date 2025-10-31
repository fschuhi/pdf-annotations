from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional

import fitz

TEXTUAL_ANNOTS = [
    fitz.PDF_ANNOT_TEXT,  # type: ignore
    fitz.PDF_ANNOT_FREE_TEXT,  # type: ignore
    fitz.PDF_ANNOT_HIGHLIGHT,  # type: ignore
    fitz.PDF_ANNOT_SQUIGGLY,  # type: ignore
    fitz.PDF_ANNOT_STRIKE_OUT,  # type: ignore
    fitz.PDF_ANNOT_UNDERLINE,  # type: ignore
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
