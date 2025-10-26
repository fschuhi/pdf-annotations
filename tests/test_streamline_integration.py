import io
import os
import json
import unittest
from typing import List
from pdf_annot.streamline_annotations import process_stream

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def read_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, name), "r", encoding="utf-8") as f:
        return f.read()

class TestStreamIntegration(unittest.TestCase):
    def ndjson_to_list(self, s: str) -> List[dict]:
        return [json.loads(line) for line in s.splitlines() if line.strip()]

    def test_end_to_end_link_merge(self):
        inp = read_fixture("input_link_merge.ndjson")
        expected = read_fixture("expected_link_merge.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        rc = process_stream(src, dst)
        self.assertEqual(rc, 0)
        self.assertEqual(dst.getvalue(), expected)

    def test_filters_annot_type_and_headers(self):
        inp = read_fixture("input_filter_and_pages.ndjson")
        expected = read_fixture("expected_filter_and_pages.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        rc = process_stream(src, dst)
        self.assertEqual(rc, 0)
        self.assertEqual(dst.getvalue(), expected)

    def test_malformed_json(self):
        inp = read_fixture("input_malformed.ndjson")
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
        self.assertNotEqual(rc, 0)
        self.assertIn("malformed JSON", buf.getvalue())

    def test_simple(self):
        inp = read_fixture("input_simple.ndjson")
        expected = read_fixture("expected_simple.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        rc = process_stream(src, dst)
        self.assertEqual(rc, 0)
        self.assertEqual(dst.getvalue(), expected)

    def test_consecutive_links(self):
        inp = read_fixture("input_consecutive_links.ndjson")
        expected = read_fixture("expected_consecutive_links.ndjson")
        src = io.StringIO(inp)
        dst = io.StringIO()
        rc = process_stream(src, dst)
        self.assertEqual(rc, 0)
        self.assertEqual(dst.getvalue(), expected)
