# src/pdf_annot/sync.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime

from pdf_annot.env import Env
from pdf_annot.pdf_registry import PdfInfo
from pdf_annot.frontmatter import upsert_fields
from pdf_annot.ndjson_to_md_block import render_block
from pdf_annot.extract import extract_annotations_to_list
from pdf_annot.streamline_annotations import streamline_annotations_list
from pdf_annot.notes import extract_info_text, replace_annotation_block, UpdateResult


def sync_pdf_to_note(env: Env, pdf_info: PdfInfo, note_path: Path, current_time_iso: str) -> UpdateResult:
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
