import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import patch
from typing import List

# Import the main functions from your scripts
from pdf_annot.extract import main as extract_main
from pdf_annot.streamline_annotations import main as streamline_main

# Define fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
INPUT_PDF = FIXTURES_DIR / "test1.pdf"
EXPECTED_RAW_NDJSON = FIXTURES_DIR / "expected_test1_raw.ndjson"
EXPECTED_STREAMLINED_NDJSON = FIXTURES_DIR / "expected_test1_streamlined.ndjson"


# Helper function to load NDJSON
def ndjson_to_list(s: str) -> List[dict]:
    """Loads a newline-delimited JSON string into a list of dicts."""
    return [json.loads(line) for line in s.splitlines() if line.strip()]


class TestE2EPipeline(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Remove the temporary directory after each test."""
        shutil.rmtree(self.temp_dir)

    def test_pdf_to_streamlined_pipeline(self):
        # 1. --- Setup ---
        # Copy the input PDF into the temp directory
        temp_pdf_path = self.temp_path / INPUT_PDF.name
        shutil.copy(INPUT_PDF, temp_pdf_path)

        # Define the paths for our *generated* output files
        actual_raw_ndjson_path = self.temp_path / temp_pdf_path.with_suffix(".ndjson").name
        actual_streamlined_ndjson_path = self.temp_path / "final_streamlined.ndjson"

        # 2. --- Run Extraction Script ---
        # The extract.py script saves output next to the input PDF.
        # We patch sys.argv to simulate: `python extract.py -p /path/to/temp/test1.pdf`
        # We also patch print() to suppress console output during the test
        extract_argv = ["extract.py", "-p", str(temp_pdf_path)]
        with patch("sys.argv", extract_argv), patch("builtins.print") as mock_print:
            extract_main()

        # Check that the raw file was actually created
        self.assertTrue(actual_raw_ndjson_path.exists(), "Raw NDJSON file was not created")

        # 3. --- Run Streamline Script ---
        # We patch sys.argv to simulate:
        # `python streamline_annotations.py -i <raw_file> -o <final_file>`
        streamline_argv = [
            "streamline_annotations.py",
            "-i", str(actual_raw_ndjson_path),
            "-o", str(actual_streamlined_ndjson_path)
        ]
        with patch("sys.argv", streamline_argv):
            return_code = streamline_main()

        # Check that the script ran successfully
        self.assertEqual(return_code, 0, "Streamline script exited with non-zero status")
        self.assertTrue(actual_streamlined_ndjson_path.exists(), "Streamlined NDJSON file was not created")

        # 4. --- Compare Results ---
        # Load all 4 files (2 actual, 2 expected)
        actual_raw_data = ndjson_to_list(actual_raw_ndjson_path.read_text("utf-8"))
        expected_raw_data = ndjson_to_list(EXPECTED_RAW_NDJSON.read_text("utf-8"))

        actual_streamlined_data = ndjson_to_list(actual_streamlined_ndjson_path.read_text("utf-8"))
        expected_streamlined_data = ndjson_to_list(EXPECTED_STREAMLINED_NDJSON.read_text("utf-8"))

        # 5. --- Assert ---
        # Compare the raw extraction
        self.assertEqual(actual_raw_data, expected_raw_data, "Raw extracted data does not match expected")

        # Compare the final streamlined output
        self.assertEqual(actual_streamlined_data, expected_streamlined_data, "Streamlined data does not match expected")
