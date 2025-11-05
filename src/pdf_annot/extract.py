# src/pdf_annot/extract.py
import argparse
import json
from pathlib import Path
from typing import List, Tuple, Dict
import fitz

# import numpy as np  <- REMOVED

from .annotation import Annotation, TEXTUAL_ANNOTS

# ===============================================================
#  Default heuristic parameters
# ===============================================================
DEFAULT_HEADER_HEIGHT = 60.0  # points: ignore annotations above this y value
DEFAULT_FOOTER_HEIGHT = 50.0  # points: ignore annotations below this y value
# FULLWIDTH_RATIO = 0.80  <- REMOVED
# COLUMN_GAP_THRESHOLD = 100  <- REMOVED


# ===============================================================
#  Column detector (REMOVED)
# ===============================================================

# def _split_rects_by_max_gap(...) <- REMOVED
# def detect_columns(...) <- REMOVED


# ===============================================================
#  Highlight text extraction with region awareness
# ===============================================================
def extract_highlight_text(page: fitz.Page, annot: fitz.Annot, header_height: float, footer_height: float) -> str:
    """
    Extract highlighted text, handling:
      - header/footer exclusion
    Sorts all highlight rectangles by visual reading order (top-to-bottom, left-to-right).
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

    # --- SIMPLIFIED LOGIC ---
    # Sort all usable rects by top-to-bottom, then left-to-right
    usable_rects.sort(key=lambda r: (round(r.y0, 1), r.x0))

    text_parts = []
    for rect in usable_rects:
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
    for i, page in enumerate(doc):  # type: ignore
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


def _extract_and_sort_annots(doc: fitz.Document, header_height: float, footer_height: float) -> List[Annotation]:
    """Extracts and sorts annotations by visual reading order."""
    annotations = list(extract_annotations(doc, header_height, footer_height))
    # Sort by visual reading order: page, y (top to bottom), x (left to right)
    annotations.sort(key=lambda a: (a.pageNum, a.topLeft[1], a.topLeft[0]))
    return annotations


# ===============================================================
#  Library API
# ===============================================================
def extract_annotations_to_list(
    pdf_path: Path,
    header_height: float = DEFAULT_HEADER_HEIGHT,
    footer_height: float = DEFAULT_FOOTER_HEIGHT,
) -> Tuple[List[dict], Dict[str, int]]:
    """
    Extract and sort annotations from PDF, return as list of dicts
    AND a dictionary of PDF stats.
    Args:
        pdf_path: Path to the PDF file
        header_height: Header cutoff in points
        footer_height: Footer cutoff in points

    Returns:
        Tuple of (annotation_dicts, pdf_stats)
        - annotation_dicts: List of annotation dictionaries in visual reading order
        - pdf_stats: Dict with {'pdf_pages', 'pdf_highlights', 'pdf_textboxes'}
    """
    doc = fitz.open(pdf_path)
    page_count = doc.page_count

    annotations = _extract_and_sort_annots(doc, header_height, footer_height)

    # --- NEW: Count annotations from the list we already built ---
    highlights_count = 0
    textboxes_count = 0
    for ann in annotations:
        annot_type_name = ann.annotType[1]  # Get annotation type string name
        if annot_type_name in ("Highlight", "Squiggly", "StrikeOut", "Underline"):
            highlights_count += 1
        elif annot_type_name in ("Text", "FreeText"):
            textboxes_count += 1

    pdf_stats = {
        "pdf_pages": page_count,
        "pdf_highlights": highlights_count,
        "pdf_textboxes": textboxes_count,
    }

    annotation_dicts = [ann.to_dict() for ann in annotations]

    return annotation_dicts, pdf_stats


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

    annotations = _extract_and_sort_annots(doc, args.header_height, args.footer_height)

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
