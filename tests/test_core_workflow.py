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

import shutil
from pathlib import Path
from datetime import datetime
import pytest

from pdf_annot.env import load_env, Env, Paths, IO
from pdf_annot.pdf_registry import build_pdf_index, PdfInfo
from pdf_annot.frontmatter import parse_note, upsert_fields
from pdf_annot.ndjson_to_md_block import render_block
from pdf_annot.extract import extract_annotations_to_list
from pdf_annot.streamline_annotations import streamline_annotations_list
from pdf_annot.notes import extract_info_text, replace_annotation_block, UpdateResult

# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ROOT = FIXTURES_DIR.parent.parent


# Helper function
def _process_pdf_for_note(env: Env, pdf_info: PdfInfo, note_path: Path, current_time_iso: str) -> UpdateResult:
    """
    Process a single PDF-note pair through the complete workflow.
    Steps:
    1. Read note (or start empty if non-existent) and extract info text
    2. Build frontmatter updates
    3. Check if frontmatter changed (trigger)
    4. Extract annotations if needed
    5. Streamline annotations
    6. Render markdown block
    7. Update note atomically

    Args:

        env: The loaded configuration environment.
        pdf_info: PDF metadata from registry
        note_path: Path to the note file (in the runtime temp dir)
        current_time_iso: ISO timestamp for last_run_at

    Returns:
        UpdateResult with details about what changed
    """
    try:
        # 1. Read existing note text (or empty string)
        try:
            note_text = note_path.read_text(encoding="utf-8")
            existing_info_text = extract_info_text(note_text)
        except FileNotFoundError:
            note_text = ""  # Start with an empty note
            existing_info_text = env.annotations.default_info_text

        # 2. Build PDF-related updates
        pdf_mtime_iso = datetime.fromtimestamp(pdf_info.mtime).isoformat(timespec="seconds")

        # This is the primary set of fields to check for changes
        pdf_updates = {
            "pdf_title": pdf_info.pdf_title,
            "pdf_size": pdf_info.size,
            "pdf_mtime": pdf_mtime_iso,
        }

        # 3. Check ONLY if PDF-related fields have changed
        # We pass only these fields to upsert_fields to check for a trigger
        fm_changed, text_with_pdf_fm = upsert_fields(note_text, pdf_updates)

        if not fm_changed:
            # No changes needed
            return UpdateResult(
                note_path=note_path, frontmatter_changed=False, annotation_block_changed=False, note_updated=False
            )

        # 4. OK, changes detected! Now extract annotations and build full updates.
        raw_annotations = extract_annotations_to_list(Path(pdf_info.abs_path))
        has_annotations = bool(raw_annotations)

        # Build the *full* set of updates, including last_run_at
        full_updates = {
            **pdf_updates,  # pdf_title, pdf_size, pdf_mtime
            "pdf_id": pdf_info.pdf_id,
            "pdf_hash": pdf_info.pdf_hash,
            "has_annotations": has_annotations,
            "last_run_at": current_time_iso,
        }

        # 5. Apply full updates to the note text
        # (We use note_text here, not text_with_pdf_fm, to start fresh)
        _, text_with_updated_fm = upsert_fields(note_text, full_updates)

        # 6. Streamline annotations
        streamlined_annotations = streamline_annotations_list(raw_annotations)

        # 7. Render markdown annotation block with preserved info text
        annotation_block = render_block(
            streamlined_annotations, pdf_id_hash=pdf_info.pdf_hash, info_text=existing_info_text
        )

        # 8. Replace annotation block in note
        updated_note_text = replace_annotation_block(text_with_updated_fm, annotation_block)

        # 9. Write updated note atomically
        note_path.write_text(updated_note_text, encoding="utf-8")

        return UpdateResult(
            note_path=note_path,
            frontmatter_changed=True,
            annotation_block_changed=True,  # If we extracted, we updated
            note_updated=True,
        )

    except Exception as e:
        return UpdateResult(
            note_path=note_path,
            frontmatter_changed=False,
            annotation_block_changed=False,
            note_updated=False,
            error=str(e),
        )


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
        # --- FIX: Explicitly set backup_dir=None to satisfy linter ---
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

    # 6. Build registry from the runtime PDF dirs specified in the Env
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


@pytest.mark.parametrize("setup_workflow", ["complete_update_workflow"], indirect=True)
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

    # Pass only what's needed
    result = _process_pdf_for_note(env, pdf_info, note_path, current_time_iso)

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

    self_verify_golden(note_path, golden_path, current_time_iso)


@pytest.mark.parametrize("setup_workflow", ["all_pdfs_with_loop"], indirect=True)
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

        # Note: _process_pdf_for_note will handle if note_path doesn't exist
        result = _process_pdf_for_note(env, pdf_info, note_path, current_time_iso)
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
    result = _process_pdf_for_note(env, pdf_info, note_path, current_time_iso)

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

        result = _process_pdf_for_note(env, pdf_info, note_path, current_time_iso)
        results[pdf_id_lower] = (result, note_path)

    # --- Assertions for (Albini 2013) ---
    result_albini, note_path_albini = results["(albini 2013)"]
    assert result_albini.success
    assert result_albini.note_updated
    assert result_albini.frontmatter_changed
    self_verify_golden(note_path_albini, goldens_dir / "(Albini 2013).md", current_time_iso)

    # --- Assertions for (Balbini 2014) ---
    result_balbini, note_path_balbini = results["(balbini 2014)"]
    assert result_balbini.success
    assert result_balbini.note_updated
    assert result_balbini.frontmatter_changed
    self_verify_golden(note_path_balbini, goldens_dir / "(Balbini 2014).md", current_time_iso)

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
        result = _process_pdf_for_note(env, pdf_info, note_path, current_time_iso)
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
    self_verify_golden(note_path_calbini, goldens_dir / "(Calbini 2015).md", current_time_iso)


def self_verify_golden(updated_note_path: Path, golden_path: Path, current_time_iso: str):
    """
    Helper to compare an updated note against its golden file.
    Replaces LAST_RUN_AT in the golden file for comparison.
    """
    assert golden_path.exists(), f"Golden file not found: {golden_path}"
    golden_text = golden_path.read_text(encoding="utf-8")

    # Replace placeholder in golden with actual timestamp
    golden_text = golden_text.replace("LAST_RUN_AT", current_time_iso)

    # Parse both for comparison
    updated_note_text = updated_note_path.read_text(encoding="utf-8")
    actual_parsed = parse_note(updated_note_text)
    golden_parsed = parse_note(golden_text)

    # Compare frontmatter fields
    for key in ["pdf_id", "pdf_title", "pdf_size", "pdf_hash", "has_annotations"]:
        assert actual_parsed.front_matter.get(key) == golden_parsed.front_matter.get(
            key
        ), f"Frontmatter field {key} should match golden"

    # pdf_mtime should exist
    assert actual_parsed.front_matter.get("pdf_mtime") is not None

    # last_run_at should be the timestamp we set
    assert actual_parsed.front_matter.get("last_run_at") == current_time_iso

    # Compare body (annotation block)
    assert actual_parsed.body.strip() == golden_parsed.body.strip(), "Annotation block should match golden"
