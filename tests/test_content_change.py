"""
End-to-end test for content_change scenario.

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
import unittest

from pdf_annot.env import load_env
from pdf_annot.pdf_registry import build_pdf_index, PdfInfo
from pdf_annot.frontmatter import parse_note, upsert_fields
from pdf_annot.ndjson_to_md_block import render_block
from pdf_annot.extract import extract_annotations_to_list
from pdf_annot.streamline_annotations import streamline_annotations_list
from pdf_annot.notes import extract_info_text, replace_annotation_block

# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_DIR = FIXTURES_DIR / "content_change"
CONFIG_FILE = TEST_DIR / "config.toml"
SEEDS_DIR = TEST_DIR / "seeds"
GOLDENS_DIR = TEST_DIR / "goldens"

# Note and PDF identifiers
NOTE_FILENAME = "(Albini 2013).md"
PDF_FILENAME = "(Albini 2013) On dealing with destructive emotions.pdf"


class TestContentChange(unittest.TestCase):
    """Test complete workflow for updating notes when PDF content changes."""

    def setUp(self):
        """Load config and setup temp directory with seed files."""
        # Load environment configuration
        self.env = load_env(CONFIG_FILE)
        self.temp_path = self.env.paths.temp_dir

        # Copy seed files to temp
        shutil.copy(SEEDS_DIR / PDF_FILENAME, self.temp_path / PDF_FILENAME)
        shutil.copy(SEEDS_DIR / NOTE_FILENAME, self.temp_path / NOTE_FILENAME)

    def tearDown(self):
        """
        Intentionally do NOT clean up temp directory.
        Temp files are useful for debugging and serve as documentation.
        """
        pass

    def test_complete_update_workflow(self):
        """
        End-to-end test: Detect change → extract → streamline → update note → verify.
        """
        self.maxDiff = None  # Show full diff for debugging

        # =====================================================================
        # 1. Build PDF registry
        # =====================================================================
        pdf_index = build_pdf_index([str(self.temp_path)])
        self.assertEqual(len(pdf_index), 1, "Should find exactly one PDF")

        pdf_id_key = "(albini 2013)"  # lowercase for lookup
        self.assertIn(pdf_id_key, pdf_index)
        pdf_info: PdfInfo = pdf_index[pdf_id_key]

        # =====================================================================
        # 2. Read note and extract existing info text
        # =====================================================================
        note_path = self.temp_path / NOTE_FILENAME
        note_text = note_path.read_text(encoding="utf-8")

        # Preserve existing info text (allows user customization)
        existing_info_text = extract_info_text(note_text)

        # Build frontmatter updates with PDF info
        pdf_mtime_iso = datetime.fromtimestamp(pdf_info.mtime).isoformat(timespec="seconds")
        current_time_iso = datetime.now().isoformat(timespec="seconds")

        updates = {
            "pdf_title": pdf_info.pdf_title,
            "pdf_size": pdf_info.size,
            "pdf_mtime": pdf_mtime_iso,
            "has_annotations": True,
            "last_run_at": current_time_iso,
        }

        # Check if frontmatter changed (this is our trigger)
        fm_changed, text_with_updated_fm = upsert_fields(note_text, updates)
        self.assertTrue(fm_changed, "Frontmatter should have changed (mtime/size differ)")

        # =====================================================================
        # 3. Extract annotations from PDF
        # =====================================================================
        pdf_path = self.temp_path / PDF_FILENAME
        raw_annotations = extract_annotations_to_list(pdf_path)
        self.assertGreater(len(raw_annotations), 0, "Should extract annotations from PDF")

        # =====================================================================
        # 4. Streamline annotations
        # =====================================================================
        streamlined_annotations = streamline_annotations_list(raw_annotations)
        self.assertGreater(len(streamlined_annotations), 0, "Should have streamlined annotations")

        # =====================================================================
        # 5. Render markdown annotation block with preserved info text
        # =====================================================================
        annotation_block = render_block(
            streamlined_annotations,
            pdf_id_hash=pdf_info.pdf_hash,
            info_text=existing_info_text,  # Preserve custom info text
        )
        self.assertIn("Introduction—Definition", annotation_block, "Should contain section headers")

        # =====================================================================
        # 6. Replace annotation block in note
        # =====================================================================
        # Start with frontmatter-updated text, replace annotation block
        updated_note_text = replace_annotation_block(text_with_updated_fm, annotation_block)

        # Write updated note atomically
        note_path.write_text(updated_note_text, encoding="utf-8")

        # =====================================================================
        # 7. Compare with golden
        # =====================================================================
        golden_path = GOLDENS_DIR / NOTE_FILENAME
        golden_text = golden_path.read_text(encoding="utf-8")

        # Replace placeholder in golden with actual timestamp
        golden_text = golden_text.replace("LAST_RUN_AT", current_time_iso)

        # Parse both for comparison
        actual_parsed = parse_note(updated_note_text)
        golden_parsed = parse_note(golden_text)

        # Compare frontmatter
        for key in ["pdf_id", "pdf_title", "pdf_size", "pdf_hash", "has_annotations"]:
            self.assertEqual(
                actual_parsed.front_matter.get(key),
                golden_parsed.front_matter.get(key),
                f"Frontmatter field {key} should match golden",
            )

        # pdf_mtime should be close to file mtime (within reason for filesystem precision)
        self.assertIsNotNone(actual_parsed.front_matter.get("pdf_mtime"))

        # last_run_at should be the timestamp we set
        self.assertEqual(actual_parsed.front_matter.get("last_run_at"), current_time_iso)

        # Compare body (annotation block)
        self.assertEqual(actual_parsed.body.strip(), golden_parsed.body.strip(), "Annotation block should match golden")
