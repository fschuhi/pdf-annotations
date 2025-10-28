import argparse
import json
from pathlib import Path
from typing import List
import fitz
import numpy as np

from .annotation import Annotation, TEXTUAL_ANNOTS


# ===============================================================
#  Default heuristic parameters
# ===============================================================
DEFAULT_HEADER_HEIGHT = 60.0  # points: ignore annotations above this y value
DEFAULT_FOOTER_HEIGHT = 50.0  # points: ignore annotations below this y value
FULLWIDTH_RATIO = 0.80  # rect.width / page.width threshold for "single block"
COLUMN_GAP_THRESHOLD = 100  # x gap (points) to detect separate columns


# ===============================================================
#  Column detector
# ===============================================================
def detect_columns(rects: List[fitz.Rect], x_gap_threshold: float = COLUMN_GAP_THRESHOLD):
    """
    Detect columns by looking for large X gaps between rect groups.
    Returns a list of clusters (each cluster = one column's rects).
    """
    if not rects:
        return []

    rects_sorted = sorted(rects, key=lambda r: r.x0)
    x_positions = sorted({int(r.x0) for r in rects_sorted})
    if len(x_positions) < 2:
        return [rects_sorted]

    gaps = np.diff(x_positions)
    if any(gap > x_gap_threshold for gap in gaps):
        max_gap_idx = int(np.argmax(gaps))
        split_x = (x_positions[max_gap_idx] + x_positions[max_gap_idx + 1]) / 2
        left = [r for r in rects_sorted if r.x0 < split_x]
        right = [r for r in rects_sorted if r.x0 >= split_x]
        # Try detecting 3 columns by splitting again if needed
        if len(right) > 1:
            right_xs = sorted({int(r.x0) for r in right})
            right_gaps = np.diff(right_xs)
            if any(gap > x_gap_threshold for gap in right_gaps):
                mid_gap_idx = int(np.argmax(right_gaps))
                split_mid = (right_xs[mid_gap_idx] + right_xs[mid_gap_idx + 1]) / 2
                mid = [r for r in right if r.x0 < split_mid]
                far_right = [r for r in right if r.x0 >= split_mid]
                return [left, mid, far_right]
        return [left, right]
    else:
        return [rects_sorted]


# ===============================================================
#  Highlight text extraction with region awareness
# ===============================================================
def extract_highlight_text(page: fitz.Page, annot: fitz.Annot, header_height: float, footer_height: float) -> str:
    """
    Extract highlighted text, handling:
      - header/footer exclusion
      - full-width (abstract) zones
      - 2/3 column page layouts
    """
    verts = annot.vertices
    if not verts:
        return ""

    n = len(verts) // 4
    rects = [fitz.Quad(*verts[i * 4 : (i + 1) * 4]).rect for i in range(n)]

    # Filter out header/footer areas
    usable_rects = [r for r in rects if (r.y0 > header_height) and (r.y1 < page.rect.height - footer_height)]
    if not usable_rects:
        return ""

    # Region analysis
    page_width = page.rect.width
    is_fullwidth = any(r.width > FULLWIDTH_RATIO * page_width for r in usable_rects)

    if is_fullwidth:
        clusters = [usable_rects]
    else:
        clusters = detect_columns(usable_rects)

    text_parts = []
    for col in clusters:
        col.sort(key=lambda r: (round(r.y0, 1), r.x0))
        for rect in col:
            t = page.get_text("text", clip=rect).strip()
            if t:
                text_parts.append(t)

    return " ".join(text_parts)


# ===============================================================
#  Annotation extractor
# ===============================================================
def extract_annotations(doc: fitz.Document, header_height: float, footer_height: float):
    """
    Yield Annotation objects for all textual annotations in the document.
    For highlights, also include extracted text in info['extractedText'].
    """
    for i, page in enumerate(doc):
        for annot in page.annots(types=TEXTUAL_ANNOTS):
            if not annot:
                continue

            info = dict(annot.info)
            if annot.type[1].lower() == "highlight":
                info["extractedText"] = extract_highlight_text(page, annot, header_height, footer_height)

            rect = annot.rect
            yield Annotation(
                colors=annot.colors,
                info=info,
                pageNum=i,
                annotType=annot.type,
                vertices=annot.vertices,
                border=annot.border,
                lineEnds=getattr(annot, "line_ends", None),
                opacity=annot.opacity,
                topLeft=(rect.x0, rect.y0),
                botRight=(rect.x1, rect.y1),
            )


# ===============================================================
#  Main CLI
# ===============================================================
def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract annotations from a PDF (handling headers, abstracts, "
            "and multi-column layouts) and save as JSON in the same folder."
        )
    )
    parser.add_argument("-p", "--pdf", required=True, help="Path to the PDF to process.")
    parser.add_argument(
        "--header-height",
        type=float,
        default=DEFAULT_HEADER_HEIGHT,
        help=f"Header height cutoff in points (default: {DEFAULT_HEADER_HEIGHT}).",
    )
    parser.add_argument(
        "--footer-height",
        type=float,
        default=DEFAULT_FOOTER_HEIGHT,
        help=f"Footer height cutoff in points (default: {DEFAULT_FOOTER_HEIGHT}).",
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    output_path = pdf_path.with_suffix(".ndjson")

    doc = fitz.open(pdf_path)

    # Collect all annotations first
    annotations = list(extract_annotations(doc, args.header_height, args.footer_height))

    # Sort by visual reading order: page, y (top to bottom), x (left to right)
    annotations.sort(key=lambda a: (a.pageNum, a.topLeft[1], a.topLeft[0]))

    # Write sorted annotations to JSON (NDJSON style)
    with output_path.open("w", encoding="utf-8") as f:
        for ann in annotations:
            json.dump(ann.to_dict(), f, ensure_ascii=False)
            f.write("\n")

    print(f"✅ Extracted annotations saved to: {output_path}")
    print(f"(header cutoff = {args.header_height}, footer cutoff = {args.footer_height})")


# ===============================================================
#  Entry point
# ===============================================================
if __name__ == "__main__":
    main()
