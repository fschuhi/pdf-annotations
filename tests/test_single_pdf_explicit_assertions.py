"""
End-to-end test for single PDF explicit assertions scenario.

Tests the complete workflow for a single known PDF:
1. Detect PDF changes (mtime/size) via frontmatter comparison
2. Extract annotations from PDF
3. Streamline annotations
4. Render markdown annotation block (preserving custom info text)
5. Update note atomically (frontmatter + annotation block)
6. Verify result matches golden

This test makes explicit assertions about the specific PDF and note,
verifying exact behavior. For looped/batch processing, see other tests.
"""

import shutil
from pathlib import Path
from datetime import datetime
import unittest

from pdf_annot.env import load_env
from pdf_annot.pdf_registry import build_pdf_index, PdfInfo
from pdf_annot.frontmatter import parse_note, upsert_fields
from pdf_annot.ndjson_to_md_block import render_block
from pdf_annot.extract import extract_annotations_to_list
from pdf_annot.streamline_annotations import streamline_annotations_list
from pdf_annot.notes import extract_info_text, replace_annotation_block, UpdateResult

# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_DIR = FIXTURES_DIR / "complete_update_workflow"
CONFIG_FILE = TEST_DIR / "config.toml"
SEEDS_DIR = TEST_DIR / "seeds"
GOLDENS_DIR = TEST_DIR / "goldens"

# Note and PDF identifiers
NOTE_FILENAME = "(Albini 2013).md"
PDF_FILENAME = "(Albini 2013) On dealing with destructive emotions.pdf"


class TestSinglePdfExplicitAssertions(unittest.TestCase):
    """Test complete workflow for a single PDF with explicit assertions."""

    def setUp(self):
        """Load config, setup temp directory with seed files, and build PDF registry."""
        # Load environment configuration
        self.env = load_env(CONFIG_FILE)
        self.temp_path = self.env.paths.temp_dir

        # Copy seed files to temp
        shutil.copy(SEEDS_DIR / PDF_FILENAME, self.temp_path / PDF_FILENAME)
        shutil.copy(SEEDS_DIR / NOTE_FILENAME, self.temp_path / NOTE_FILENAME)

        # Build PDF registry (shared across tests)
        self.pdf_index = build_pdf_index([str(self.temp_path)])

    def tearDown(self):
        """
        Intentionally do NOT clean up temp directory.
        Temp files are useful for debugging and serve as documentation.
        """
        pass

    def _process_pdf_for_note(self, pdf_info: PdfInfo, note_path: Path, current_time_iso: str) -> UpdateResult:
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
            note_path: Path to the note file
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
            pdf_path = self.temp_path / pdf_info.filename_with_ext
            raw_annotations = extract_annotations_to_list(pdf_path)

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

    def test_complete_update_workflow(self):
        """
        End-to-end test: Detect change → extract → streamline → update note → verify.

        This test explicitly verifies the Albini 2013 PDF/note pair with detailed assertions.
        """
        self.maxDiff = None  # Show full diff for debugging

        # =====================================================================
        # 1. Get PDF info from registry (built in setUp)
        # =====================================================================
        self.assertEqual(len(self.pdf_index), 1, "Should find exactly one PDF")

        pdf_id_key = "(albini 2013)"  # lowercase for lookup
        self.assertIn(pdf_id_key, self.pdf_index)
        pdf_info: PdfInfo = self.pdf_index[pdf_id_key]

        # =====================================================================
        # 2. Process through workflow
        # =====================================================================
        note_path = self.temp_path / NOTE_FILENAME
        current_time_iso = datetime.now().isoformat(timespec="seconds")

        result = self._process_pdf_for_note(pdf_info, note_path, current_time_iso)

        # =====================================================================
        # 3. Assert workflow result
        # =====================================================================
        self.assertTrue(result.success, f"Workflow should succeed without errors: {result.error}")
        self.assertTrue(result.frontmatter_changed, "Frontmatter should have changed (mtime/size differ)")
        self.assertTrue(result.annotation_block_changed, "Annotation block should have changed")
        self.assertTrue(result.note_updated, "Note should have been updated")

        # =====================================================================
        # 4. Verify against golden file
        # =====================================================================
        golden_path = GOLDENS_DIR / NOTE_FILENAME
        golden_text = golden_path.read_text(encoding="utf-8")

        # Replace placeholder in golden with actual timestamp
        golden_text = golden_text.replace("LAST_RUN_AT", current_time_iso)

        # Parse both for comparison
        updated_note_text = note_path.read_text(encoding="utf-8")
        actual_parsed = parse_note(updated_note_text)
        golden_parsed = parse_note(golden_text)

        # Compare frontmatter fields
        for key in ["pdf_id", "pdf_title", "pdf_size", "pdf_hash", "has_annotations"]:
            self.assertEqual(
                actual_parsed.front_matter.get(key),
                golden_parsed.front_matter.get(key),
                f"Frontmatter field {key} should match golden",
            )

        # pdf_mtime should exist
        self.assertIsNotNone(actual_parsed.front_matter.get("pdf_mtime"))

        # last_run_at should be the timestamp we set
        self.assertEqual(actual_parsed.front_matter.get("last_run_at"), current_time_iso)

        # Compare body (annotation block)
        self.assertEqual(actual_parsed.body.strip(), golden_parsed.body.strip(), "Annotation block should match golden")

    def test_all_pdfs_with_loop(self):
        """
        Process all PDFs in the index through the workflow.

        This test uses the same workflow as the explicit test, but loops over
        all PDFs and makes flexible assertions about the batch results.

        Currently we only have one PDF (Albini 2013), but this structure is
        ready for multiple PDFs.
        """
        current_time_iso = datetime.now().isoformat(timespec="seconds")
        results = []

        # Process all PDFs in the registry
        for pdf_id_lower, pdf_info in self.pdf_index.items():
            # Find corresponding note (case-sensitive filename)
            note_path = self.temp_path / f"{pdf_info.pdf_id}.md"

            if not note_path.exists():
                # PDF has no corresponding note - skip for now
                # (We could track "missing notes" here in the future)
                continue

            result = self._process_pdf_for_note(pdf_info, note_path, current_time_iso)
            results.append(result)

        # =====================================================================
        # Flexible assertions on batch results
        # =====================================================================

        # All should succeed (no errors)
        errors = [r for r in results if not r.success]
        self.assertEqual(len(errors), 0, f"No errors expected, got: {[r.error for r in errors]}")

        # At least one note should have been updated
        updated = [r for r in results if r.note_updated]
        self.assertGreater(len(updated), 0, "At least one note should have been updated")

        # Count statistics
        fm_changed_count = sum(1 for r in results if r.frontmatter_changed)
        annot_changed_count = sum(1 for r in results if r.annotation_block_changed)

        # For this specific test fixture, we expect:
        # - Exactly 1 PDF processed (Albini 2013)
        # - Frontmatter changed (mtime/size differ from seed)
        # - Annotation block changed
        self.assertEqual(len(results), 1, "Should process exactly one PDF")
        self.assertEqual(fm_changed_count, 1, "Albini PDF should trigger frontmatter update")
        self.assertEqual(annot_changed_count, 1, "Albini PDF should trigger annotation update")
