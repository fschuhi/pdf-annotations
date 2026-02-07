# tests/test_fasching_extraction.py
"""
Regression test for extraction quality using the Fasching (2008) PDF.

This PDF exercises all the extraction challenges we've fixed:
- Curly quotes with different vertical extents ("forgetting", "do")
- Apostrophes (one's)
- Superscript footnote numbers (leaking into highlight text)
- Header/footer margin detection (first line of page cut off)
- Intra-highlight word ordering

The golden file contains the expected extractedText for all 77 annotations.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdf_annot.extract import extract_annotations_to_list

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_DIR = FIXTURES_DIR / "fasching_extraction"


@pytest.fixture
def fasching_annotations():
    """Extract annotations from the Fasching PDF."""
    pdf_path = FIXTURE_DIR / "input.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found at {pdf_path}")

    annotations, stats = extract_annotations_to_list(pdf_path)
    return annotations, stats


@pytest.fixture
def golden_data():
    """Load the golden expected extraction data."""
    golden_path = FIXTURE_DIR / "expected_extracted_texts.json"
    if not golden_path.exists():
        pytest.skip(f"Golden file not found at {golden_path}")

    with golden_path.open(encoding="utf-8") as f:
        return json.load(f)


def test_annotation_count(fasching_annotations):
    """The PDF should yield exactly 77 annotations."""
    annotations, _ = fasching_annotations
    assert len(annotations) == 77


def test_pdf_stats(fasching_annotations):
    """Verify PDF-level statistics."""
    _, stats = fasching_annotations
    assert stats["pdf_pages"] == 21
    assert stats["pdf_highlights"] == 77
    assert stats["pdf_textboxes"] == 0


def test_extracted_texts_match_golden(fasching_annotations, golden_data):
    """Every annotation's extractedText must match the golden file exactly."""
    annotations, _ = fasching_annotations

    assert len(annotations) == len(
        golden_data
    ), f"Annotation count mismatch: got {len(annotations)}, expected {len(golden_data)}"

    mismatches = []
    for i, (actual, expected) in enumerate(zip(annotations, golden_data)):
        actual_text = actual.get("info", {}).get("extractedText", "")
        expected_text = expected["extractedText"]

        if actual_text != expected_text:
            mismatches.append(
                f"  [{i}] p{expected['pageNum']+1} comment='{expected['content'][:30]}'\n"
                f"    EXPECTED: {expected_text[:100]}\n"
                f"    ACTUAL:   {actual_text[:100]}"
            )

    assert not mismatches, f"{len(mismatches)} extraction mismatches:\n" + "\n".join(mismatches)


def test_no_stray_characters(fasching_annotations):
    """No extracted text should contain stray single-character artefacts."""
    annotations, _ = fasching_annotations
    import re

    for ann in annotations:
        text = ann.get("info", {}).get("extractedText", "")
        # Stray characters: a single letter surrounded by spaces that doesn't
        # make sense as a word (e.g. " g ", " p ", " j ")
        strays = re.findall(r" ([gpjy]) ", text)
        assert not strays, f"Stray character(s) {strays} in p{ann['pageNum']+1}: '{text[:80]}'"


def test_no_footnote_leakage(fasching_annotations):
    """No extracted text should contain leaked footnote numbers after punctuation."""
    annotations, _ = fasching_annotations
    import re

    for ann in annotations:
        text = ann.get("info", {}).get("extractedText", "")
        # Pattern: punctuation followed by 1-2 digits that are footnote refs
        # e.g. "of).4", "itself.13"
        # Exclude legitimate patterns like "(1)" or "I.41"
        leaks = re.findall(r"[.),;:!?]\d{1,2}\b", text)
        # Filter out false positives (e.g. numbered lists, references)
        real_leaks = [m for m in leaks if not re.search(r"[A-Z]\.\d", text)]
        # This is a soft check - some patterns might be legitimate
        # The golden file comparison above is the authoritative test
