from dataclasses import dataclass
from typing import List, Tuple, Union

import fitz


TEXTUAL_ANNOTS = [
    fitz.PDF_ANNOT_TEXT,
    fitz.PDF_ANNOT_FREE_TEXT,
    fitz.PDF_ANNOT_HIGHLIGHT,
    fitz.PDF_ANNOT_SQUIGGLY,
    fitz.PDF_ANNOT_STRIKE_OUT,
    fitz.PDF_ANNOT_UNDERLINE,
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

    def __post_init__(self):
        self.rect = fitz.Rect(self.topLeft, self.botRight)
        if self.vertices:
            n = len(self.vertices) // 4
            self.quads: List[fitz.Quad] = [
                fitz.Quad(*self.vertices[i*4:i*4+4]) for i in range(n)]
        else:
            self.quads = None
        self.point = self.rect.top_left

    def to_dict(self):
        return dict(
            colors=self.colors, info=self.info, pageNum=self.pageNum, annotType=self.annotType,
            vertices=self.vertices, topLeft=self.topLeft, botRight=self.botRight,
            border=self.border, lineEnds=self.lineEnds, opacity=self.opacity
        )
