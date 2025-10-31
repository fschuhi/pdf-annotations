import shutil
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from typing import List

# Import the main functions and library functions
from pdf_annot.extract import main as extract_main
from pdf_annot.streamline_annotations import main as streamline_main
from pdf_annot.ndjson_to_md_block import render_block
from pdf_annot.env import load_env

# Define fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# Helper function to load NDJSON
def ndjson_to_list(s: str) -> List[dict]:
    """Loads a newline-delimited JSON string into a list of dicts."""
    return [json.loads(line) for line in s.splitlines() if line.strip()]


@pytest.fixture
def setup_e2e_pipeline(request):
    """
    A pytest fixture that sets up the E2E test environment.
    It copies the input PDF to a temp dir and provides paths
    to the golden (expected) files.
    """
    fixture_name = request.param

    # 1. Define paths
    test_dir = FIXTURES_DIR / fixture_name
    config_file = test_dir / "config.toml"
    input_pdf = test_dir / "input.pdf"

    # 2. Load environment configuration
    env = load_env(config_file)
    temp_path = env.paths.temp_dir

    # Ensure temp dir exists and copy seed PDF
    temp_path.mkdir(parents=True, exist_ok=True)
    temp_pdf_path = temp_path / input_pdf.name
    shutil.copy(input_pdf, temp_pdf_path)

    # 3. Yield paths to the test
    yield {
        "temp_path": temp_path,
        "temp_pdf_path": temp_pdf_path,
        "expected_raw": test_dir / "expected_raw.ndjson",
        "expected_streamlined": test_dir / "expected_streamlined.ndjson",
        "expected_markdown": test_dir / "expected_markdown.md",
    }

    # 4. Teardown (optional)
    # Intentionally do NOT clean up temp directory.
    # Temp files are useful for debugging and serve as documentation.
    pass


@pytest.mark.parametrize("setup_e2e_pipeline", ["pdf_to_markdown_e2e"], indirect=True)
def test_complete_extraction_pipeline(setup_e2e_pipeline):
    """
    End-to-end test: PDF → raw NDJSON → streamlined NDJSON → markdown.
    Tests the complete annotation extraction and rendering pipeline
    by running the CLI entrypoints.
    """
    # 1. --- Get paths from fixture ---
    temp_path = setup_e2e_pipeline["temp_path"]
    temp_pdf_path = setup_e2e_pipeline["temp_pdf_path"]
    expected_raw_ndjson_path = setup_e2e_pipeline["expected_raw"]
    expected_streamlined_ndjson_path = setup_e2e_pipeline["expected_streamlined"]
    expected_markdown_path = setup_e2e_pipeline["expected_markdown"]

    # 2. --- Define paths for generated output files ---
    actual_raw_ndjson_path = temp_path / temp_pdf_path.with_suffix(".ndjson").name
    actual_streamlined_ndjson_path = temp_path / "final_streamlined.ndjson"

    # 3. --- Run Extraction Script ---
    # The extract.py script saves output next to the input PDF.
    # We patch sys.argv to simulate: `python extract.py -p /path/to/temp/input.pdf`
    # We also patch print() to suppress console output during the test
    extract_argv = ["extract.py", "-p", str(temp_pdf_path)]
    with patch("sys.argv", extract_argv), patch("builtins.print"):
        extract_main()

    # Check that the raw file was actually created
    assert actual_raw_ndjson_path.exists(), "Raw NDJSON file was not created"

    # 4. --- Run Streamline Script ---
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
    assert return_code == 0, "Streamline script exited with non-zero status"
    assert actual_streamlined_ndjson_path.exists(), "Streamlined NDJSON file was not created"

    # 5. --- Render Markdown ---
    # Read the streamlined NDJSON and render it to markdown
    with open(actual_streamlined_ndjson_path, "r", encoding="utf-8") as f:
        streamlined_objs = [json.loads(line) for line in f if line.strip()]

    actual_markdown = render_block(streamlined_objs, pdf_id_hash="VQGPEHE")

    # 6. --- Load Expected Results ---
    expected_raw_data = ndjson_to_list(expected_raw_ndjson_path.read_text("utf-8"))
    expected_streamlined_data = ndjson_to_list(expected_streamlined_ndjson_path.read_text("utf-8"))
    expected_markdown = expected_markdown_path.read_text("utf-8")

    actual_raw_data = ndjson_to_list(actual_raw_ndjson_path.read_text("utf-8"))
    actual_streamlined_data = ndjson_to_list(actual_streamlined_ndjson_path.read_text("utf-8"))

    # 7. --- Assert All Stages ---
    # Compare the raw extraction
    assert actual_raw_data == expected_raw_data, "Raw extracted data does not match expected"

    # Compare the streamlined output
    assert actual_streamlined_data == expected_streamlined_data, "Streamlined data does not match expected"

    # Compare the final markdown output
    assert actual_markdown.strip() == expected_markdown.strip(), "Rendered markdown does not match expected"
