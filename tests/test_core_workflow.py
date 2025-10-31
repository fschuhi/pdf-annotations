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
def _process_pdf_for_note(pdf_info: PdfInfo, note_path: Path, current_time_iso: str) -> UpdateResult:
    """
    Process a single PDF-note pair through the complete workflow.
    Steps:
    1. Read note and extract existing info text
    2. Build frontmatter updates
    3. Check if frontmatter changed (trigger)
    4. Extract annotations if needed
    5. Streamline annotations
    6. Render markdown block
    7. Update note atomically

    Args:

        pdf_info: PDF metadata from registry
        note_path: Path to the note file (in the runtime temp dir)
        current_time_iso: ISO timestamp for last_run_at

    Returns:
        UpdateResult with details about what changed
    """
    try:
        # Read note and extract existing info text
        note_text = note_path.read_text(encoding="utf-8")
        existing_info_text = extract_info_text(note_text)

        # Build frontmatter updates with PDF info
        pdf_mtime_iso = datetime.fromtimestamp(pdf_info.mtime).isoformat(timespec="seconds")

        updates = {
            "pdf_title": pdf_info.pdf_title,
            "pdf_size": pdf_info.size,
            "pdf_mtime": pdf_mtime_iso,
            "has_annotations": True,
            "last_run_at": current_time_iso,
        }

        # Check if frontmatter changed (this is our trigger)
        fm_changed, text_with_updated_fm = upsert_fields(note_text, updates)

        if not fm_changed:
            # No changes needed
            return UpdateResult(
                note_path=note_path, frontmatter_changed=False, annotation_block_changed=False, note_updated=False
            )

        # Extract annotations from PDF
        # pdf_info.abs_path is the correct path from the registry
        raw_annotations = extract_annotations_to_list(Path(pdf_info.abs_path))

        # Streamline annotations
        streamlined_annotations = streamline_annotations_list(raw_annotations)

        # Render markdown annotation block with preserved info text
        annotation_block = render_block(
            streamlined_annotations, pdf_id_hash=pdf_info.pdf_hash, info_text=existing_info_text
        )

        # Replace annotation block in note
        updated_note_text = replace_annotation_block(text_with_updated_fm, annotation_block)

        # Write updated note atomically
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

    1. Checks for /tests/fixtures/<name>/config.toml.
    2. If it exists, loads it to create a validated Env.
    3. If it DOES NOT exist, creates a default Env in memory, with all paths
       pointing to /tests/tmp/<name>.
    4. Copies seeds from /tests/fixtures/<name>/seeds into the runtime temp dir.
    5. Builds a PDF registry from the runtime directory.
    6. Yields the Env, PDF index, and path to golden files.

    The 'request.param' must be the name of the fixture directory,
    e.g., "complete_update_workflow".
    """
    fixture_name = request.param

    # 1. Define fixture source paths
    fixture_source_dir = FIXTURES_DIR / fixture_name
    config_file = fixture_source_dir / "config.toml"
    source_seeds_dir = fixture_source_dir / "seeds"
    source_goldens_dir = fixture_source_dir / "goldens"

    # 2. Load Env: This is the source of truth for runtime
    if config_file.exists():
        # Load Env from the explicit file
        env = load_env(config_file)
    else:
        # Generate a default Env in memory
        runtime_temp_dir = PROJECT_ROOT / "tests" / "tmp" / fixture_name

        paths_config = Paths(notes_root=runtime_temp_dir, pdf_dirs=[runtime_temp_dir], temp_dir=runtime_temp_dir)
        io_config = IO(create_missing_dirs=True)  # This is the important default

        # This will create the runtime_temp_dir
        env = Env(paths=paths_config, io=io_config)

    assert env.paths.temp_dir is not None, "temp_dir must be set in Env for tests"

    # 3. Setup: Copy seeds from source to runtime dir
    for seed_file in source_seeds_dir.glob("*"):
        if seed_file.is_file():
            # Use the temp_dir *from the env* as the destination
            shutil.copy(seed_file, env.paths.temp_dir / seed_file.name)

    # 4. Build registry from the runtime PDF dirs specified in the Env
    pdf_index = build_pdf_index([str(p) for p in env.paths.pdf_dirs])

    # 5. Yield the runtime Env and source goldens
    yield {
        "env": env,
        "pdf_index": pdf_index,
        "goldens_dir": source_goldens_dir,
    }

    # 6. Teardown (optional)
    # Intentionally do NOT clean up temp directory.
    pass


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
    result = _process_pdf_for_note(pdf_info, note_path, current_time_iso)

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
    golden_text = golden_path.read_text(encoding="utf-8")

    # Replace placeholder in golden with actual timestamp
    golden_text = golden_text.replace("LAST_RUN_AT", current_time_iso)

    # Parse both for comparison
    updated_note_text = note_path.read_text(encoding="utf-8")
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


@pytest.mark.parametrize("setup_workflow", ["all_pdfs_with_loop"], indirect=True)
def test_all_pdfs_with_loop(setup_workflow: dict):
    """
    Process all PDFs in the index through the workflow.
    This test uses the same workflow as the explicit test, but loops over
    all PDFs and makes flexible assertions about the batch results.
    Currently we only have one PDF (Albini 2013), but this structure is
    ready for multiple PDFs.
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

        if not note_path.exists():
            # PDF has no corresponding note - skip for now
            continue

        result = _process_pdf_for_note(pdf_info, note_path, current_time_iso)
        results.append(result)

    # =====================================================================
    # Flexible assertions on batch results
    # =====================================================================

    # All should succeed (no errors)
    errors = [r for r in results if not r.success]
    assert not errors, f"No errors expected, got: {[r.error for r in errors]}"

    # At least one note should have been updated
    updated = [r for r in results if r.note_updated]
    assert len(updated) > 0, "At least one note should have been updated"

    # Count statistics
    fm_changed_count = sum(1 for r in results if r.frontmatter_changed)
    annot_changed_count = sum(1 for r in results if r.annotation_block_changed)

    # For this specific test fixture, we expect:
    # - Exactly 1 PDF processed (Albini 2013)
    # - Frontmatter changed (mtime/size differ from seed)
    # - Annotation block changed
    assert len(results) == 1, "Should process exactly one PDF"
    assert fm_changed_count == 1, "Albini PDF should trigger frontmatter update"
    assert annot_changed_count == 1, "Albini PDF should trigger annotation update"
