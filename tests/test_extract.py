# tests/test_extract.py
from __future__ import annotations

from pathlib import Path

import pytest

from pdf_annot.extract import extract_annotations_to_list
from pdf_annot.streamline_annotations import streamline_annotations_list

# Define fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"

# The annotation-type fixture. Page 1 of this PDF carries exactly one of each
# type the project can meet (AUDIT.md A6):
#   Highlight   with content "H2"  -> the streamliner reads a bare "H<n>" as a
#                                     heading label, so this one renders as a
#                                     section header, not as a comment
#   Highlight   without content    -> renders as a plain quote
#   StrikeOut / Underline / Squiggly -> marker types, dropped at the gate
#   FreeText                       -> the PDF-XChange "Text Box", counted by
#                                     pdf_textboxes and never rendered
ANNOT_TYPES_PDF = FIXTURES_DIR / "annot_types" / "input.pdf"

# The FreeText box carries this text. It must not reach the rendered block.
TEXTBOX_CONTENT = "textbox"


@pytest.fixture(scope="module")
def annot_types_extraction():
    """Extract the annotation-type fixture once for the tests below."""
    return extract_annotations_to_list(ANNOT_TYPES_PDF)


def test_marker_types_are_not_counted_as_highlights(annot_types_extraction):
    """
    Squiggly, StrikeOut and Underline are not annotations this project reads.

    They were counted into pdf_highlights while the streamliner filtered them
    out of rendering, so the number in the frontmatter promised more than the
    block delivered. They are now excluded at the gate (TEXTUAL_ANNOTS), which
    is why they are absent from the extracted list as well as from the count.
    """
    annotation_dicts, pdf_stats = annot_types_extraction

    type_names = sorted({ann["annotType"][1] for ann in annotation_dicts})
    assert type_names == ["FreeText", "Highlight"], "a marker type reached extraction"

    assert pdf_stats["pdf_pages"] == 7, "wrong fixture PDF in place"
    assert pdf_stats["pdf_highlights"] == 2, "pdf_highlights must count true Highlights only"


def test_textboxes_are_counted_but_not_rendered(annot_types_extraction):
    """
    Text and FreeText are counted and deliberately never rendered.

    pdf_textboxes is kept permanently: it is the Dataview tracker for PDFs
    whose legacy textboxes are not yet converted, and the signal for
    author-supplied textboxes. The asymmetry is intent, not an oversight --
    see README.md. This test is the guard against a future cleanup that reads
    "extracted but never rendered" as dead weight and removes the type.
    """
    annotation_dicts, pdf_stats = annot_types_extraction

    assert pdf_stats["pdf_textboxes"] == 1

    streamlined = streamline_annotations_list(annotation_dicts)
    assert len(streamlined) == 2, "only the two Highlights may reach the renderer"

    rendered_text = " ".join(str(value) for obj in streamlined for value in obj.values())
    assert TEXTBOX_CONTENT not in rendered_text


def test_highlight_scrambled_bug():
    """
    Tests the fix for the scrambled highlight bug.

    The bug occurred when a multi-line highlight was composed of rectangles
    that did not vertically align, causing an aggressive column-detection
    algorithm to incorrectly split the highlight into two "columns".

    This test uses a PDF with such a highlight ("(Dalbini 2016)...").
    The simplified extraction logic should now sort all rectangles
    purely top-to-bottom, resulting in the correct, unscrambled text.
    """
    # Define the path to the test PDF
    # This PDF must be manually placed at:
    # tests/fixtures/highlight_scrambled_bug/input.pdf
    pdf_path = FIXTURES_DIR / "highlight_scrambled_bug" / "input.pdf"

    # Ensure the test file exists before running
    if not pdf_path.exists():
        # This skips the test if the file is missing, preventing a CI failure.
        # We can make this a hard failure later if preferred.
        import pytest

        pytest.skip(f"Test PDF not found at {pdf_path}")

    # --- Act ---
    # Run the extraction function from the library
    annotation_dicts, _ = extract_annotations_to_list(pdf_path)

    # --- Assert ---
    # We expect two annotations from this PDF
    assert len(annotation_dicts) == 2, "Expected exactly two annotations to be extracted"

    # Find the problematic highlight. Based on the NDJSON you provided,
    # it's the second one (index 1).
    scrambled_highlight = annotation_dicts[1]

    # This is the correctly ordered text
    expected_text = (
        "considered the basis upon which all individuals nurture "
        "Samsara, the unending wheel of transmigration and suffering."
    )

    # The main assertion: check that the extracted text is in the correct order
    # --- FIX: Access the "extractedText" key *inside* the "info" dict ---
    assert scrambled_highlight["info"]["extractedText"] == expected_text

    # We can also check the first highlight just to be safe
    first_highlight = annotation_dicts[0]
    assert first_highlight["info"]["extractedText"] == "Introduction—Definition"
