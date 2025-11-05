# tests/test_extract.py
from __future__ import annotations

from pathlib import Path

from pdf_annot.extract import extract_annotations_to_list

# Define fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
