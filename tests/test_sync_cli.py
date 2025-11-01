"""
End-to-end test for the CLI entry point: pdf-annot-sync.

This test runs the main() function by patching sys.argv, simulating a
full command-line execution. It uses the same fixture setup as
test_core_workflow.py to create a runtime environment, then checks
both the stdout and the resulting golden files.
"""

import io
import shutil
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

import pytest

from pdf_annot.env import load_env, Env, Paths, IO
from pdf_annot.pdf_registry import build_pdf_index, PdfInfo
from pdf_annot.frontmatter import parse_note
from pdf_annot.notes import UpdateResult

# Import the main function we are testing
from pdf_annot.sync import main as sync_main

# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ROOT = FIXTURES_DIR.parent.parent


@pytest.fixture
def setup_workflow(request):
    """
    A pytest fixture that sets up a test environment for the CLI.

    1. CLEANS the /tests/tmp/<name> directory.
    2. CREATES a valid 'config.toml' inside the temp directory.
    3. Copies seeds (preserving metadata) into the runtime temp dir.
    4. Builds a PDF registry from the runtime directory.
    5. Yields the Env, PDF index, path to goldens, and path to the new config.
    """
    fixture_name = request.param

    # 1. Define fixture source paths
    fixture_source_dir = FIXTURES_DIR / fixture_name
    # config_file = fixture_source_dir / "config.toml" # We create our own
    source_seeds_dir = fixture_source_dir / "seeds"
    source_goldens_dir = fixture_source_dir / "goldens"

    # 2. Define runtime path
    runtime_temp_dir = PROJECT_ROOT / "tests" / "tmp" / fixture_name

    # 3. Clean the temp directory before setup
    shutil.rmtree(runtime_temp_dir, ignore_errors=True)
    runtime_temp_dir.mkdir(parents=True, exist_ok=True)

    # 4. --- NEW: Create a valid config.toml inside the temp dir ---
    # The config file will live inside the temp dir and point to it
    runtime_config_path = runtime_temp_dir / "test_config.toml"

    # We use relative paths from the project root for consistency
    relative_temp_dir_str = str(runtime_temp_dir.relative_to(PROJECT_ROOT))

    config_content = f"""
[paths]
notes_root = "{relative_temp_dir_str}"
pdf_dirs = ["{relative_temp_dir_str}"]
temp_dir = "{relative_temp_dir_str}"

[io]
create_missing_dirs = true
"""
    runtime_config_path.write_text(config_content, encoding="utf-8")

    # 5. Load the env *from this new config* to validate
    env = load_env(runtime_config_path)

    # 6. Setup: Copy seeds from source to runtime dir
    for seed_file in source_seeds_dir.glob("*"):
        if seed_file.is_file():
            dest_path = env.paths.temp_dir / seed_file.name
            shutil.copy2(seed_file, dest_path)

    # 7. Build registry (for helper verification, though main() will do its own)
    pdf_index = build_pdf_index([str(p) for p in env.paths.pdf_dirs])

    # 8. Yield the runtime Env and source goldens
    yield {"env": env, "pdf_index": pdf_index, "goldens_dir": source_goldens_dir, "config_path": runtime_config_path}

    # 9. Teardown
    pass


@pytest.mark.parametrize("setup_workflow", ["workflow_manual_edits"], indirect=True)
def test_sync_cli_workflow(setup_workflow: dict):
    """
    Tests the main CLI entry point using the 'workflow_manual_edits' fixture.

    - Checks that the CLI (via patched sys.argv) runs without errors.
    - Captures stdout and checks that it correctly reports
      one skip and one update.
    - Verifies the final files against goldens to prove the logic ran.
    """
    env: Env = setup_workflow["env"]
    goldens_dir: Path = setup_workflow["goldens_dir"]
    config_path: Path = setup_workflow["config_path"]

    # 1. Define the arguments for the CLI
    # We are simulating: $ pdf-annot-sync -c tests/tmp/.../test_config.toml
    cli_args = ["pdf-annot-sync", "-c", str(config_path)]

    # We need a predictable timestamp for golden file checking
    current_time_iso = datetime.now().isoformat(timespec="seconds")

    # 2. Patch sys.argv and builtins.print to capture stdout
    stdout_capture = io.StringIO()
    with patch.object(sys, "argv", cli_args), patch(
        "builtins.print", new=lambda *args, **kwargs: print(*args, file=stdout_capture, **kwargs)
    ), patch("pdf_annot.sync.datetime") as mock_datetime:
        # Mock datetime.now() to control the timestamp
        mock_datetime.now.return_value = datetime.fromisoformat(current_time_iso)

        # 3. Run the main function
        return_code = sync_main()

    # 4. Check results
    assert return_code == 0, "CLI should exit with status 0"

    output = stdout_capture.getvalue()

    # 5. Check stdout for correct summary
    assert "SKIPPED: (Albini 2013).md" in output
    assert "UPDATED: (Calbini 2015).md" in output
    assert "Sync complete." in output
    assert "Errors:  0" in output

    # 6. Verify files on disk against goldens
    # This proves the sync logic ran correctly

    # Verify (Albini 2013).md (was skipped, should match its seed/golden)
    note_path_albini = env.paths.notes_root / "(Albini 2013).md"
    golden_path_albini = goldens_dir / "(Albini 2013).md"
    self_verify_golden(note_path_albini, golden_path_albini, is_new=False)

    # Verify (Calbini 2015).md (was updated)
    note_path_calbini = env.paths.notes_root / "(Calbini 2015).md"
    golden_path_calbini = goldens_dir / "(Calbini 2015).md"
    self_verify_golden(note_path_calbini, golden_path_calbini, is_new=True, timestamp=current_time_iso)


def self_verify_golden(updated_note_path: Path, golden_path: Path, is_new: bool, timestamp: str | None = None):
    """
    Helper to compare an updated note against its golden file.

    Args:
        updated_note_path: Path to the note file in the temp dir.
        golden_path: Path to the golden file in the fixtures dir.
        is_new: If True, replaces "LAST_RUN_AT" with the timestamp.
        timestamp: The timestamp to use for "LAST_RUN_AT".
    """
    assert golden_path.exists(), f"Golden file not found: {golden_path}"
    golden_text = golden_path.read_text(encoding="utf-8")
    updated_note_text = updated_note_path.read_text(encoding="utf-8")

    if is_new:
        assert timestamp, "Timestamp must be provided if is_new is True"
        # Replace placeholder in golden with actual timestamp
        golden_text = golden_text.replace("LAST_RUN_AT", timestamp)

    # Parse both for comparison
    actual_parsed = parse_note(updated_note_text)
    golden_parsed = parse_note(golden_text)

    # Compare frontmatter
    # For 'unchanged' files, we must check all fields
    # For 'new' files, we check the core fields
    fields_to_check = golden_parsed.front_matter.keys()

    for key in fields_to_check:
        assert actual_parsed.front_matter.get(key) == golden_parsed.front_matter.get(
            key
        ), f"Frontmatter field {key} should match golden"

    # Compare body
    assert actual_parsed.body.strip() == golden_parsed.body.strip(), "Annotation block should match golden"
