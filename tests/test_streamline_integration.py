import io
import os
import json
import unittest
from pathlib import Path
from typing import List
from pdf_annot.streamline_annotations import process_stream

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def read_fixture(relative_path: str) -> str:
    """Read a fixture file by its path relative to fixtures/"""
    with open(FIXTURES_DIR / relative_path, "r", encoding="utf-8") as f:
        return f.read()


class TestStreamIntegration:
    def ndjson_to_list(self, s: str) -> List[dict]:
        return [json.loads(line) for line in s.splitlines() if line.strip()]

    def test_end_to_end_link_merge(self):
        inp = read_fixture("link_merge/input.ndjson")
        expected = read_fixture("link_merge/expected.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        rc = process_stream(src, dst)
        assert rc == 0
        assert dst.getvalue() == expected

    def test_filters_annot_type_and_headers(self):
        inp = read_fixture("filter_and_pages/input.ndjson")
        expected = read_fixture("filter_and_pages/expected.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        rc = process_stream(src, dst)
        assert rc == 0
        assert dst.getvalue() == expected

    def test_malformed_json(self):
        inp = read_fixture("malformed/input.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        # capture stderr by redirecting temporarily
        buf = io.StringIO()
        import sys

        old_stderr = sys.stderr
        try:
            sys.stderr = buf
            rc = process_stream(src, dst)
        finally:
            sys.stderr = old_stderr
        assert rc != 0
        assert "malformed JSON" in buf.getvalue()

    def test_simple(self):
        inp = read_fixture("simple/input.ndjson")
        expected = read_fixture("simple/expected.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        rc = process_stream(src, dst)
        assert rc == 0
        assert dst.getvalue() == expected

    def test_consecutive_links(self):
        inp = read_fixture("consecutive_links/input.ndjson")
        expected = read_fixture("consecutive_links/expected.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        rc = process_stream(src, dst)
        assert rc == 0
        assert dst.getvalue() == expected
