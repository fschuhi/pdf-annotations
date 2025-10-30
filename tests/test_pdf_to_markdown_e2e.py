import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch
from typing import List

# Import the main functions and library functions
from pdf_annot.extract import main as extract_main
from pdf_annot.streamline_annotations import main as streamline_main
from pdf_annot.ndjson_to_md_block import render_block

# Define fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_DIR = FIXTURES_DIR / "pdf_to_markdown_e2e"
INPUT_PDF = TEST_DIR / "input.pdf"
EXPECTED_RAW_NDJSON = TEST_DIR / "expected_raw.ndjson"
EXPECTED_STREAMLINED_NDJSON = TEST_DIR / "expected_streamlined.ndjson"
EXPECTED_MARKDOWN = TEST_DIR / "expected_markdown.md"


# Helper function to load NDJSON
def ndjson_to_list(s: str) -> List[dict]:
    """Loads a newline-delimited JSON string into a list of dicts."""
    return [json.loads(line) for line in s.splitlines() if line.strip()]


class TestPdfToMarkdownE2E(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Remove the temporary directory after each test."""
        shutil.rmtree(self.temp_dir)

    def test_complete_extraction_pipeline(self):
        """
        End-to-end test: PDF → raw NDJSON → streamlined NDJSON → markdown.
        Tests the complete annotation extraction and rendering pipeline.
        """
        # 1. --- Setup ---
        # Copy the input PDF into the temp directory
        temp_pdf_path = self.temp_path / INPUT_PDF.name
        shutil.copy(INPUT_PDF, temp_pdf_path)

        # Define the paths for our *generated* output files
        actual_raw_ndjson_path = self.temp_path / temp_pdf_path.with_suffix(".ndjson").name
        actual_streamlined_ndjson_path = self.temp_path / "final_streamlined.ndjson"

        # 2. --- Run Extraction Script ---
        # The extract.py script saves output next to the input PDF.
        # We patch sys.argv to simulate: `python extract.py -p /path/to/temp/input.pdf`
        # We also patch print() to suppress console output during the test
        extract_argv = ["extract.py", "-p", str(temp_pdf_path)]
        with patch("sys.argv", extract_argv), patch("builtins.print"):
            extract_main()

        # Check that the raw file was actually created
        self.assertTrue(actual_raw_ndjson_path.exists(), "Raw NDJSON file was not created")

        # 3. --- Run Streamline Script ---
        # We patch sys.argv to simulate:
        # `python streamline_annotations.py -i <raw_file> -o <final_file>`
        streamline_argv = [
            "streamline_annotations.py",
            "-i",
            str(actual_raw_ndjson_path),
            "-o",
            str(actual_streamlined_ndjson_path),
        ]
        with patch("sys.argv", streamline_argv):
            return_code = streamline_main()

        # Check that the script ran successfully
        self.assertEqual(return_code, 0, "Streamline script exited with non-zero status")
        self.assertTrue(actual_streamlined_ndjson_path.exists(), "Streamlined NDJSON file was not created")

        # 4. --- Render Markdown ---
        # Read the streamlined NDJSON and render it to markdown
        with open(actual_streamlined_ndjson_path, "r", encoding="utf-8") as f:
            streamlined_objs = [json.loads(line) for line in f if line.strip()]

        actual_markdown = render_block(streamlined_objs, pdf_id_hash="VQGPEHE")

        # 5. --- Load Expected Results ---
        expected_raw_data = ndjson_to_list(EXPECTED_RAW_NDJSON.read_text("utf-8"))
        expected_streamlined_data = ndjson_to_list(EXPECTED_STREAMLINED_NDJSON.read_text("utf-8"))
        expected_markdown = EXPECTED_MARKDOWN.read_text("utf-8")

        actual_raw_data = ndjson_to_list(actual_raw_ndjson_path.read_text("utf-8"))
        actual_streamlined_data = ndjson_to_list(actual_streamlined_ndjson_path.read_text("utf-8"))

        # 6. --- Assert All Stages ---
        # Compare the raw extraction
        self.assertEqual(actual_raw_data, expected_raw_data, "Raw extracted data does not match expected")

        # Compare the streamlined output
        self.assertEqual(actual_streamlined_data, expected_streamlined_data, "Streamlined data does not match expected")

        # Compare the final markdown output
        self.assertEqual(
            actual_markdown.strip(), expected_markdown.strip(), "Rendered markdown does not match expected"
        )
