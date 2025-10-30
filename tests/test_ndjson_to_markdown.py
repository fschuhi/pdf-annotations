# tests/test_ndjson_to_markdown.py
import json
from pathlib import Path

from pdf_annot.ndjson_to_md_block import render_block

ROOT = Path(__file__).resolve().parents[1]
FIXT = ROOT / "tests" / "fixtures"
INPUT = FIXT / "pdf_to_markdown_e2e" / "final_streamlined.ndjson"
EXPECTED = FIXT / "pdf_to_markdown_e2e" / "expected_markdown.md"


def test_ndjson_to_md_block_matches_golden():
    assert INPUT.exists(), f"Missing input NDJSON: {INPUT}"
    assert EXPECTED.exists(), f"Missing expected markdown: {EXPECTED}"

    # Read and parse the NDJSON input
    with open(INPUT, "r", encoding="utf-8") as f:
        objs = [json.loads(line) for line in f if line.strip()]

    # Render the markdown block using the library
    got = render_block(objs, pdf_id_hash="VQGPEHE").strip()
    want = EXPECTED.read_text(encoding="utf-8").strip()

    # If this fails, it will print a readable unified diff via pytest
    assert got == want
