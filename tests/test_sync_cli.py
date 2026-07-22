"""
End-to-end test for the CLI entry point: pdf-annot-sync.

This test runs the main() function by patching sys.argv, simulating a
full command-line execution. It uses the same fixture setup as
test_core_workflow.py to create a runtime environment, then checks
both the stdout and the resulting golden files.
"""

import io
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import contextlib

import pytest

# --- FIX: Added # noqa to silence false positive warnings ---
from pdf_annot.env import load_env, Env, Paths, IO  # noqa
from pdf_annot.pdf_registry import build_pdf_index
from pdf_annot.frontmatter import parse_note

# Import the main function we are testing
from pdf_annot.sync import main as sync_main
from pdf_annot.sync import _decline_reason
from pdf_annot import sync as sync_module
from pdf_annot.utils import atomic_write_file as real_atomic_write_file

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

    # 6.5. FIX: Align PDF mtimes with Note frontmatter to fix git-clone timestamp issues
    # Iterates over notes, parses the expected mtime, and forces the PDF file to match.
    # This ensures tests are stable even if 'git clone' reset file timestamps.
    for note_file in env.paths.temp_dir.glob("*.md"):
        try:
            text = note_file.read_text(encoding="utf-8")
            pn = parse_note(text)
            fm = pn.front_matter

            target_mtime_str = fm.get("pdf_mtime")
            target_id = fm.get("pdf_id")

            if target_mtime_str and target_id and isinstance(target_id, str):
                # Convert ISO string back to timestamp
                dt = datetime.fromisoformat(str(target_mtime_str))
                timestamp = dt.timestamp()

                # Find the matching PDF by checking if the PDF filename contains the ID
                for pdf_file in env.paths.temp_dir.glob("*.pdf"):
                    if target_id.lower() in pdf_file.name.lower():
                        os.utime(pdf_file, (timestamp, timestamp))
                        break
        except Exception:
            # Ignore parsing errors or missing fields; strictly a best-effort fix
            pass

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
    cli_args = ["pdf-annot-sync", "-c", str(config_path)]

    # 2. Patch sys.argv and capture stdout
    stdout_capture = io.StringIO()
    with contextlib.redirect_stdout(stdout_capture), patch.object(sys, "argv", cli_args):
        # 3. Run the main function
        return_code = sync_main()

    # 4. Check results
    assert return_code == 0, "CLI should exit with status 0"

    output = stdout_capture.getvalue()

    # 5. Check stdout for correct summary
    assert "SKIPPED: (Albini 2013).md" in output
    assert "UPDATED: (Calbini 2015).md" in output
    assert "Sync complete." in output
    assert "Errors:   0" in output

    # 6. Verify files on disk against goldens
    # This proves the sync logic ran correctly

    # Verify (Albini 2013).md (was skipped, should match its seed/golden)
    note_path_albini = env.paths.notes_root / "(Albini 2013).md"
    golden_path_albini = goldens_dir / "(Albini 2013).md"
    self_verify_golden(note_path_albini, golden_path_albini)

    # Verify (Calbini 2015).md (was updated)
    note_path_calbini = env.paths.notes_root / "(Calbini 2015).md"
    golden_path_calbini = goldens_dir / "(Calbini 2015).md"
    self_verify_golden(note_path_calbini, golden_path_calbini)


@pytest.mark.parametrize("setup_workflow", ["workflow_manual_edits"], indirect=True)
def test_sync_writes_through_atomic_helper(setup_workflow: dict):
    """
    Guards F18: production note writes must go through the atomic writer.

    Runs the same CLI workflow, but spies on the write helper. `wraps=` makes
    the mock record the call *and* delegate to the real function, so the note
    is genuinely written and can still be checked against its golden. A plain
    stub would prove the door was used while leaving nothing on disk.
    """
    env: Env = setup_workflow["env"]
    goldens_dir: Path = setup_workflow["goldens_dir"]
    config_path: Path = setup_workflow["config_path"]

    cli_args = ["pdf-annot-sync", "-c", str(config_path)]
    stdout_capture = io.StringIO()

    # Patch the name in sync's namespace, NOT in utils. sync.py binds the
    # function via `from pdf_annot.utils import atomic_write_file`, so the
    # lookup happens on the sync module. Patching "pdf_annot.utils.atomic_
    # write_file" would leave that binding untouched: the spy would never
    # fire and the test would pass for the wrong reason.
    with patch("pdf_annot.sync.atomic_write_file", wraps=real_atomic_write_file) as write_spy:
        with contextlib.redirect_stdout(stdout_capture), patch.object(sys, "argv", cli_args):
            return_code = sync_main()

    assert return_code == 0, "CLI should exit with status 0"

    # This fixture yields one skip (Albini) and one update (Calbini), so there
    # should be exactly one write, and it must be the updated note.
    assert write_spy.call_count == 1, "Exactly one note should have been written"

    written_path, written_text = write_spy.call_args.args
    expected_path = env.paths.notes_root / "(Calbini 2015).md"
    assert Path(written_path) == expected_path, "The updated note should be the one written"
    assert written_text, "Composed note text should not be empty"

    # Delegation really happened: the file on disk is correct, not just the call.
    self_verify_golden(expected_path, goldens_dir / "(Calbini 2015).md")


def test_sync_has_no_direct_note_write():
    """
    Tripwire against F18 returning.

    The spy test above proves that sync *uses* the atomic writer. It cannot
    prove that a second, direct write has not been added alongside it -- the
    spy would still fire and still pass. This checks the source of sync.py for
    a bare `write_text(` call, which is exactly how the unprotected write
    looked before A1a.

    NOTE: this is a source grep, not a behaviour test. If a future change adds
    a legitimate `write_text(` to sync.py for some unrelated purpose, this test
    will fail. That failure means the assertion needs narrowing, not that the
    new code is wrong. Notes themselves must still go through the helper.
    """
    source = Path(sync_module.__file__).read_text(encoding="utf-8")
    msg = "sync.py must write notes only through atomic_write_file (see AUDIT.md F18/A1)"
    assert "write_text(" not in source, msg


def test_decline_reason_conditions():
    """
    The decline predicate in isolation: two conditions, in order.

    The separator answers "is this a bibnote at all"; the frontmatter answers
    "is it intact". The third case keeps the separator deliberately, so it can
    only be caught by the second condition -- that is what proves the two are
    ordered rather than collapsed into one check.
    """
    intact = '---\npdf_id: (Albini 2013)\n---\n\nfree text\n\n<hr class="pdf-annot-sep">\n\nannotations\n'
    assert _decline_reason(intact) is None

    no_separator = "---\npdf_id: (Albini 2013)\n---\n\nfree text\n"
    assert _decline_reason(no_separator) == "missing annotation separator"

    broken_frontmatter = '---\npdf_title: "unclosed quote\n---\n\n<hr class="pdf-annot-sep">\n'
    assert _decline_reason(broken_frontmatter) == "missing or invalid frontmatter"

    # An empty file is not a bibnote; the separator check is the right diagnosis.
    assert _decline_reason("") == "missing annotation separator"


@pytest.mark.parametrize("setup_workflow", ["workflow_declines"], indirect=True)
def test_sync_declines_note_without_separator(setup_workflow: dict):
    """
    A note whose annotation separator was deleted must be left untouched.

    The seed carries a deliberately wrong pdf_size, so the change gate would
    open and sync would genuinely rewrite this note. The guard has to fire
    ahead of it -- byte-identity is what proves that it did.
    """
    env: Env = setup_workflow["env"]
    goldens_dir: Path = setup_workflow["goldens_dir"]
    config_path: Path = setup_workflow["config_path"]

    cli_args = ["pdf-annot-sync", "-c", str(config_path)]
    stdout_capture = io.StringIO()
    with contextlib.redirect_stdout(stdout_capture), patch.object(sys, "argv", cli_args):
        return_code = sync_main()

    assert return_code == 0, "A decline is not an error: the run still exits 0"

    output = stdout_capture.getvalue()
    assert "DECLINED: (Albini 2013).md -- missing annotation separator" in output
    assert "Declined: 2" in output
    assert "Updated:  0" in output

    verify_bytes_identical(env.paths.notes_root / "(Albini 2013).md", goldens_dir / "(Albini 2013).md")


@pytest.mark.parametrize("setup_workflow", ["workflow_declines"], indirect=True)
def test_sync_declines_note_with_invalid_frontmatter(setup_workflow: dict):
    """
    A note whose frontmatter does not parse must be left untouched.

    The seed keeps its separator, so it passes the first condition. Its
    frontmatter carries an unclosed quote, which also means the fixture cannot
    realign the PDF mtime from it -- so the PDF looks changed and, again, the
    guard must fire ahead of the change gate.
    """
    env: Env = setup_workflow["env"]
    goldens_dir: Path = setup_workflow["goldens_dir"]
    config_path: Path = setup_workflow["config_path"]

    cli_args = ["pdf-annot-sync", "-c", str(config_path)]
    stdout_capture = io.StringIO()
    with contextlib.redirect_stdout(stdout_capture), patch.object(sys, "argv", cli_args):
        return_code = sync_main()

    assert return_code == 0, "A decline is not an error: the run still exits 0"

    output = stdout_capture.getvalue()
    assert "DECLINED: (Balbini 2014).md -- missing or invalid frontmatter" in output
    assert "Errors:   0" in output

    verify_bytes_identical(env.paths.notes_root / "(Balbini 2014).md", goldens_dir / "(Balbini 2014).md")


def self_verify_golden(updated_note_path: Path, golden_path: Path):
    """
    Helper to compare an updated note against its golden file.
    It checks all fields *except* last_run_at.
    """
    assert golden_path.exists(), f"Golden file not found: {golden_path}"
    golden_text = golden_path.read_text(encoding="utf-8")
    updated_note_text = updated_note_path.read_text(encoding="utf-8")

    actual_parsed = parse_note(updated_note_text)
    golden_parsed = parse_note(golden_text)

    # --- FIX: Check only the important fields, skip the timestamp ---
    fields_to_check = ["pdf_id", "pdf_title", "pdf_size", "pdf_hash", "has_annotations"]

    for key in fields_to_check:
        assert actual_parsed.front_matter.get(key) == golden_parsed.front_matter.get(
            key
        ), f"Frontmatter field {key} should match golden"

    # For updated files, we just check that *a* timestamp was written
    if golden_parsed.front_matter.get("last_run_at") == "LAST_RUN_AT":
        assert (
            actual_parsed.front_matter.get("last_run_at") is not None
        ), "last_run_at timestamp should have been written"
    else:
        # For unchanged files, check that the timestamp *didn't* change
        assert actual_parsed.front_matter.get("last_run_at") == golden_parsed.front_matter.get(
            "last_run_at"
        ), "last_run_at timestamp should not have changed"

    # Compare body
    assert actual_parsed.body.strip() == golden_parsed.body.strip(), "Annotation block should match golden"


def verify_bytes_identical(actual_path: Path, golden_path: Path):
    """
    Byte-for-byte comparison, for notes sync declined to touch.

    `self_verify_golden` is the wrong tool here: it compares parsed frontmatter
    fields and body, and for a note whose frontmatter does not parse, both sides
    come back empty and it would pass without proving anything. A decline
    promises the file is untouched, and only the raw bytes can show that.
    """
    assert golden_path.exists(), f"Golden file not found: {golden_path}"
    actual_bytes = actual_path.read_bytes()
    golden_bytes = golden_path.read_bytes()
    assert actual_bytes == golden_bytes, f"Declined note must be byte-identical: {actual_path.name}"
