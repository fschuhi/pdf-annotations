# src/pdf_annot/extract.py
import argparse
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict

import fitz

from .annotation import Annotation, TEXTUAL_ANNOTS

# ===============================================================
#  Default heuristic parameters
# ===============================================================
DEFAULT_HEADER_HEIGHT = 30.0  # points: ignore annotations above this y value
DEFAULT_FOOTER_HEIGHT = 30.0  # points: ignore annotations below this y value

# Words-based extraction parameters
LINE_MERGE_TOLERANCE = 3.0  # points: quads within this y-distance are on the same line
WORD_OVERLAP_THRESHOLD = 0.5  # fraction: minimum overlap for a word to be "inside" highlight
SUPERSCRIPT_SIZE_RATIO = 0.85  # font size < dominant * this ratio => superscript
SUPERSCRIPT_SKIP_THRESHOLD = 0.8  # if >80% of word overlaps superscript => skip entirely

# Annotation sort parameters
SORT_ROUND = 3.0  # points: y/x rounding for sort key (prevents sub-point misordering)


# ===============================================================
#  Superscript detection
# ===============================================================
def _get_superscript_regions(page: fitz.Page) -> List[fitz.Rect]:
    """
    Identify superscript text regions by comparing span font sizes.

    Superscript footnote numbers (e.g. ², ³⁴) use a smaller font than the
    body text on the same line. We detect spans whose font size is
    significantly smaller than the dominant size on their line.

    Returns a list of Rects covering superscript spans.
    """
    regions: List[fitz.Rect] = []
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            sizes = [span["size"] for span in line["spans"] if span["text"].strip()]
            if not sizes:
                continue
            dominant = max(set(sizes), key=sizes.count)
            for span in line["spans"]:
                if span["size"] < dominant * SUPERSCRIPT_SIZE_RATIO and span["text"].strip():
                    regions.append(fitz.Rect(span["bbox"]))
    return regions


# ===============================================================
#  Quad merging
# ===============================================================
def _merge_quads_by_line(rects: List[fitz.Rect], tolerance: float = LINE_MERGE_TOLERANCE) -> List[fitz.Rect]:
    """
    Group highlight quads that sit on the same text line and merge them.

    Typographic characters like curly quotes (" ") and apostrophes (')
    produce quads with slightly different y-coordinates than the main text.
    This merges them into a single rect per visual line, preventing the
    "rect bleeding" problem where narrow, tall quads clip text from
    adjacent lines.

    Args:
        rects: List of highlight quad rects, pre-filtered for header/footer.
        tolerance: Maximum y0 difference (in points) to consider quads
                   as being on the same line.

    Returns:
        List of merged Rects, one per visual line, sorted top-to-bottom.
    """
    if not rects:
        return []

    sorted_rects = sorted(rects, key=lambda r: (r.y0, r.x0))
    lines: List[List[fitz.Rect]] = [[sorted_rects[0]]]

    for r in sorted_rects[1:]:
        if abs(r.y0 - lines[-1][0].y0) <= tolerance:
            lines[-1].append(r)
        else:
            lines.append([r])

    merged = []
    for line in lines:
        merged.append(
            fitz.Rect(
                min(r.x0 for r in line),
                min(r.y0 for r in line),
                max(r.x1 for r in line),
                max(r.y1 for r in line),
            )
        )

    return merged


# ===============================================================
#  Word-level overlap matching
# ===============================================================
def _best_overlap_ratio(wx0: float, wy0: float, wx1: float, wy1: float, line_rects: List[fitz.Rect]) -> float:
    """
    Compute the best (maximum) overlap ratio between a word bbox and
    any of the merged line rects.

    We check ALL line rects and return the highest ratio, not the first
    match. This is necessary because a word (e.g. "one's") may partially
    overlap a narrow apostrophe-quad line while having high overlap with
    the actual text line.
    """
    word_area = (wx1 - wx0) * (wy1 - wy0)
    if word_area <= 0:
        return 0.0

    best = 0.0
    for lr in line_rects:
        ox0 = max(wx0, lr.x0)
        oy0 = max(wy0, lr.y0)
        ox1 = min(wx1, lr.x1)
        oy1 = min(wy1, lr.y1)
        if ox0 < ox1 and oy0 < oy1:
            ratio = (ox1 - ox0) * (oy1 - oy0) / word_area
            if ratio > best:
                best = ratio
    return best


def _superscript_overlap(wx0: float, wy0: float, wx1: float, wy1: float, sup_regions: List[fitz.Rect]) -> float:
    """Fraction of word area that overlaps with superscript regions."""
    word_area = (wx1 - wx0) * (wy1 - wy0)
    if word_area <= 0:
        return 0.0
    total = 0.0
    for sr in sup_regions:
        ox0 = max(wx0, sr.x0)
        oy0 = max(wy0, sr.y0)
        ox1 = min(wx1, sr.x1)
        oy1 = min(wy1, sr.y1)
        if ox0 < ox1 and oy0 < oy1:
            total += (ox1 - ox0) * (oy1 - oy0)
    return total / word_area


# ===============================================================
#  Highlight text extraction (words-based)
# ===============================================================
def extract_highlight_text(page: fitz.Page, annot: fitz.Annot, header_height: float, footer_height: float) -> str:
    """
    Extract highlighted text using word-level overlap matching.

    This approach solves three problems with the previous rect-clipping method:

    1. **Stray characters**: Curly quotes and apostrophes produce quads with
       different vertical extents. Clipping these quads individually would
       pick up characters from adjacent lines. By merging quads per visual
       line and matching at the word level, stray characters are excluded.

    2. **Footnote number leakage**: Superscript footnote numbers (e.g. ²⁴)
       sometimes get merged into adjacent words by PyMuPDF's word segmentation
       (e.g. "of).4"). We detect superscript regions via font-size analysis
       and strip trailing digits from contaminated words.

    3. **Intra-highlight ordering**: Words come pre-sorted in reading order
       from PyMuPDF's get_text("words"), so we get correct ordering even
       when individual quads have inconsistent y-coordinates.

    Args:
        page: The fitz.Page containing the annotation.
        annot: The highlight annotation.
        header_height: Y cutoff for header exclusion (points from top).
        footer_height: Y cutoff for footer exclusion (points from bottom).

    Returns:
        Extracted text as a single string, words joined by spaces.
    """
    verts = annot.vertices
    if not verts:
        return ""

    n = len(verts) // 4
    rects = [fitz.Quad(*verts[i * 4 : (i + 1) * 4]).rect for i in range(n)]

    # Filter out header/footer areas
    page_height = page.rect.height
    usable_rects = [r for r in rects if r.y0 > header_height and r.y1 < page_height - footer_height]
    if not usable_rects:
        return ""

    # Merge quads on the same visual line
    line_rects = _merge_quads_by_line(usable_rects)

    # Get all words and superscript regions for this page
    words = page.get_text("words")
    sup_regions = _get_superscript_regions(page)

    # Match words against highlight line rects
    matched: List[str] = []
    for w in words:
        wx0, wy0, wx1, wy1 = w[:4]
        word: str = w[4]

        # Check overlap with highlight
        overlap = _best_overlap_ratio(wx0, wy0, wx1, wy1, line_rects)
        if overlap < WORD_OVERLAP_THRESHOLD:
            continue

        # Check for superscript contamination
        sup_ratio = _superscript_overlap(wx0, wy0, wx1, wy1, sup_regions)
        if sup_ratio > SUPERSCRIPT_SKIP_THRESHOLD:
            continue  # word is entirely a superscript number
        if sup_ratio > 0.01:
            # Word partially overlaps superscript — strip trailing digits
            word = re.sub(r"\d+$", "", word)
            if not word:
                continue

        matched.append(word)

    return " ".join(matched)


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
    """Extracts and sorts annotations by visual reading order.

    Sort key: (page, rounded_y, rounded_x, width).
    Rounding y and x to the nearest SORT_ROUND points prevents sub-point
    coordinate differences from misordering annotations on the same visual
    line. The width tiebreaker ensures that narrow annotations (e.g. a
    heading like "Abstract") sort before wider ones (the body paragraph)
    when they share the same line position.
    """
    annotations = list(extract_annotations(doc, header_height, footer_height))

    def _sort_key(a: Annotation):
        y = round(a.topLeft[1] / SORT_ROUND) * SORT_ROUND
        x = round(a.topLeft[0] / SORT_ROUND) * SORT_ROUND
        width = a.botRight[0] - a.topLeft[0]
        return (a.pageNum, y, x, width)

    annotations.sort(key=_sort_key)
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
