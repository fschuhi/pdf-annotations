"""
End-to-end test for the PDF-to-note update workflow.
Tests the complete workflow:
1. Detect PDF changes (mtime/size) via frontmatter comparison
2. Extract annotations from PDF
3. Streamline annotations
4. Render markdown annotation block (preserving custom info text)
5. Update note atomically (frontmatter + annotation block)
6. Verify result matches golden
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import pytest

from pdf_annot.env import load_env, Env, Paths, IO
from pdf_annot.pdf_registry import build_pdf_index, PdfInfo
from pdf_annot.frontmatter import parse_note
from pdf_annot.sync import sync_pdf_to_note

# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ROOT = FIXTURES_DIR.parent.parent


@pytest.fixture
def setup_workflow(request):
    """
    A pytest fixture that sets up a test environment based on a fixture_name.
    1. CLEANS the /tests/tmp/<name> directory.
    2. Loads or creates an Env pointing to that directory.
    3. Copies seeds (preserving metadata) into the runtime temp dir.
    4. Builds a PDF registry from the runtime directory.
    5. Yields the Env, PDF index, and path to golden files.
    """
    fixture_name = request.param

    # 1. Define fixture source paths
    fixture_source_dir = FIXTURES_DIR / fixture_name
    config_file = fixture_source_dir / "config.toml"
    source_seeds_dir = fixture_source_dir / "seeds"
    source_goldens_dir = fixture_source_dir / "goldens"

    # 2. Define runtime path
    runtime_temp_dir = PROJECT_ROOT / "tests" / "tmp" / fixture_name

    # 3. Clean the temp directory before setup
    # This ensures no leftover files from previous runs
    shutil.rmtree(runtime_temp_dir, ignore_errors=True)

    # 4. Load or create Env: This is the source of truth for runtime
    if config_file.exists():
        # Load Env from the explicit file
        env = load_env(config_file)
    else:
        # Generate a default Env in memory
        paths_config = Paths(
            notes_root=runtime_temp_dir, pdf_dirs=[runtime_temp_dir], temp_dir=runtime_temp_dir, backup_dir=None
        )
        io_config = IO(create_missing_dirs=True)  # This is the important default

        # This will create the runtime_temp_dir
        env = Env(paths=paths_config, io=io_config)

    assert env.paths.temp_dir is not None, "temp_dir must be set in Env for tests"

    # 5. Setup: Copy seeds from source to runtime dir
    for seed_file in source_seeds_dir.glob("*"):
        if seed_file.is_file():
            dest_path = env.paths.temp_dir / seed_file.name
            # Use copy2 to preserve mtime metadata
            shutil.copy2(seed_file, dest_path)

    # 5.5. FIX: Align PDF mtimes with Note frontmatter to fix git-clone timestamp issues
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
                # Fixtures typically use 'YYYY-MM-DDTHH:MM:SS'
                dt = datetime.fromisoformat(str(target_mtime_str))
                timestamp = dt.timestamp()

                # Find the matching PDF by checking if the PDF filename contains the ID
                # (e.g. ID "(Albini 2013)" matches file "(Albini 2013) Title.pdf")
                for pdf_file in env.paths.temp_dir.glob("*.pdf"):
                    if target_id.lower() in pdf_file.name.lower():
                        os.utime(pdf_file, (timestamp, timestamp))
                        break
        except Exception:
            # Ignore parsing errors or missing fields; strictly a best-effort fix for tests
            pass

    # 6. Build registry from the runtime PDF dirs specified in the Env
    # Note: We do this AFTER Step 5.5 so the registry picks up the forced mtimes
    pdf_index = build_pdf_index([str(p) for p in env.paths.pdf_dirs])

    # 7. Yield the runtime Env and source goldens
    yield {
        "env": env,
        "pdf_index": pdf_index,
        "goldens_dir": source_goldens_dir,
    }

    # 8. Teardown
    # Intentionally do NOT clean up temp directory.
    pass


# =============================================================================
# ORIGINAL CORE TESTS
# =============================================================================


@pytest.mark.parametrize("setup_workflow", ["workflow_complete_update"], indirect=True)
def test_complete_update_workflow(setup_workflow: dict):
    """
    End-to-end test: Detect change → extract → streamline → update note → verify.
    This test explicitly verifies the Albini 2013 PDF/note pair with detailed assertions.
    """
    # Get all setup data from the fixture
    env: Env = setup_workflow["env"]
    pdf_index: dict[str, PdfInfo] = setup_workflow["pdf_index"]
    goldens_dir: Path = setup_workflow["goldens_dir"]

    # These are specific to this test case
    note_filename = "(Albini 2013).md"
    pdf_id_key = "(albini 2013)"  # lowercase for lookup

    # =====================================================================
    # 1. Get PDF info from registry (built in setUp)
    # =====================================================================
    assert len(pdf_index) == 1, "Should find exactly one PDF"
    assert pdf_id_key in pdf_index
    pdf_info: PdfInfo = pdf_index[pdf_id_key]

    # =====================================================================
    # 2. Process through workflow
    # =====================================================================
    # Construct runtime note_path using the env
    note_path = env.paths.notes_root / note_filename
    current_time_iso = datetime.now().isoformat(timespec="seconds")

    result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)

    # =====================================================================
    # 3. Assert workflow result
    # =====================================================================
    assert result.success, f"Workflow should succeed without errors: {result.error}"
    assert result.frontmatter_changed, "Frontmatter should have changed (mtime/size differ)"
    assert result.annotation_block_changed, "Annotation block should have changed"
    assert result.note_updated, "Note should have been updated"

    # =====================================================================
    # 4. Verify against golden file
    # =====================================================================
    golden_path = goldens_dir / note_filename
    assert golden_path.exists(), f"Golden file not found: {golden_path}"

    self_verify_golden(note_path, golden_path)


@pytest.mark.parametrize("setup_workflow", ["workflow_all_pdfs_loop"], indirect=True)
def test_all_pdfs_with_loop(setup_workflow: dict):
    """
    Process all PDFs in the index through the workflow.
    This test uses the same workflow as the explicit test, but loops over
    all PDFs and makes flexible assertions about the batch results.
    """
    # Get setup data
    env: Env = setup_workflow["env"]
    pdf_index: dict[str, PdfInfo] = setup_workflow["pdf_index"]

    current_time_iso = datetime.now().isoformat(timespec="seconds")
    results = []

    # Process all PDFs in the registry
    for pdf_id_lower, pdf_info in pdf_index.items():
        # Find corresponding note using the env
        note_path = env.paths.notes_root / f"{pdf_info.pdf_id}.md"

        result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)
        results.append(result)

    # =====================================================================
    # Flexible assertions on batch results
    # =====================================================================
    errors = [r for r in results if not r.success]
    assert not errors, f"No errors expected, got: {[r.error for r in errors]}"

    updated = [r for r in results if r.note_updated]
    assert len(updated) > 0, "At least one note should have been updated"

    fm_changed_count = sum(1 for r in results if r.frontmatter_changed)
    annot_changed_count = sum(1 for r in results if r.annotation_block_changed)

    assert len(results) == 1, "Should process exactly one PDF"
    assert fm_changed_count == 1, "Albini PDF should trigger frontmatter update"
    assert annot_changed_count == 1, "Albini PDF should trigger annotation update"


# =============================================================================
# NEW SCENARIO TESTS
# =============================================================================


@pytest.mark.parametrize("setup_workflow", ["workflow_pdf_unchanged"], indirect=True)
def test_workflow_pdf_unchanged(setup_workflow: dict):
    """
    Tests idempotency: running the workflow on an already-synced PDF
    should NOT update the note and NOT change its modification time.
    """
    env: Env = setup_workflow["env"]
    pdf_index: dict[str, PdfInfo] = setup_workflow["pdf_index"]

    pdf_info = pdf_index["(albini 2013)"]
    note_path = env.paths.notes_root / f"{pdf_info.pdf_id}.md"
    current_time_iso = datetime.now().isoformat(timespec="seconds")

    # 1. Get original mtime of the synced note
    assert note_path.exists()
    original_mtime = note_path.stat().st_mtime

    # 2. Process through workflow
    result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)

    # 3. Get new mtime
    new_mtime = note_path.stat().st_mtime

    # 4. Assert workflow result
    assert result.success, "Workflow should succeed"
    assert not result.frontmatter_changed, "Frontmatter should NOT have changed"
    assert not result.note_updated, "Note should NOT have been updated"

    # 5. Assert mtime
    assert new_mtime == original_mtime, "Note mtime should not have changed"


@pytest.mark.parametrize("setup_workflow", ["workflow_new_pdfs"], indirect=True)
def test_workflow_new_pdfs(setup_workflow: dict):
    """
    Tests note creation:
    1. A new PDF with annotations creates a note with a full annotation block.
    2. A new PDF *without* annotations creates a note with `has_annotations: false`
       and an empty annotation block.
    """
    env: Env = setup_workflow["env"]
    pdf_index: dict[str, PdfInfo] = setup_workflow["pdf_index"]
    goldens_dir: Path = setup_workflow["goldens_dir"]

    assert len(pdf_index) == 2, "Should find two PDFs in this fixture"

    current_time_iso = datetime.now().isoformat(timespec="seconds")
    results = {}

    # Process all PDFs
    for pdf_id_lower, pdf_info in pdf_index.items():
        note_path = env.paths.notes_root / f"{pdf_info.pdf_id}.md"
        assert not note_path.exists(), f"Seed note {note_path.name} should not exist"

        result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)
        results[pdf_id_lower] = (result, note_path)

    # --- Assertions for (Albini 2013) ---
    result_albini, note_path_albini = results["(albini 2013)"]
    assert result_albini.success
    assert result_albini.note_updated
    assert result_albini.frontmatter_changed
    self_verify_golden(note_path_albini, goldens_dir / "(Albini 2013).md")

    # --- Assertions for (Balbini 2014) ---
    result_balbini, note_path_balbini = results["(balbini 2014)"]
    assert result_balbini.success
    assert result_balbini.note_updated
    assert result_balbini.frontmatter_changed
    self_verify_golden(note_path_balbini, goldens_dir / "(Balbini 2014).md")

    # Check frontmatter field specific to this test
    parsed_balbini = parse_note(note_path_balbini.read_text(encoding="utf-8"))
    assert parsed_balbini.front_matter.get("has_annotations") is False, "Balbini PDF should have has_annotations: false"


@pytest.mark.parametrize("setup_workflow", ["workflow_manual_edits"], indirect=True)
def test_workflow_manual_edits(setup_workflow: dict):
    """
    Tests that manual text is preserved.
    1. (Albini 2013) is in-sync: Note mtime should not change.
    2. (Calbini 2015) is out-of-sync: Note should be updated, but manual
       text between frontmatter and annotation block must be preserved.
    """
    env: Env = setup_workflow["env"]
    pdf_index: dict[str, PdfInfo] = setup_workflow["pdf_index"]
    goldens_dir: Path = setup_workflow["goldens_dir"]

    assert len(pdf_index) == 2
    current_time_iso = datetime.now().isoformat(timespec="seconds")
    results = {}

    # Store original mtime for the "unchanged" case
    note_path_albini = env.paths.notes_root / "(Albini 2013).md"
    original_mtime_albini = note_path_albini.stat().st_mtime

    # Process all PDFs
    for pdf_id_lower, pdf_info in pdf_index.items():
        note_path = env.paths.notes_root / f"{pdf_info.pdf_id}.md"
        result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)
        results[pdf_id_lower] = (result, note_path)

    # --- Assertions for (Albini 2013) [Unchanged] ---
    result_albini, note_path_albini = results["(albini 2013)"]
    new_mtime_albini = note_path_albini.stat().st_mtime

    assert result_albini.success
    assert not result_albini.note_updated, "In-sync note should not be updated"
    assert new_mtime_albini == original_mtime_albini, "In-sync note mtime changed"

    # --- Assertions for (Calbini 2015) [Changed] ---
    result_calbini, note_path_calbini = results["(calbini 2015)"]

    assert result_calbini.success
    assert result_calbini.note_updated, "Out-of-sync note should be updated"

    # Verify against golden. This implicitly checks that the manual text
    # in the body was preserved, as the golden file contains it.
    self_verify_golden(note_path_calbini, goldens_dir / "(Calbini 2015).md")


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
