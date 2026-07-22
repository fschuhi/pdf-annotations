# src/pdf_annot/sync.py
from __future__ import annotations

import sys
import argparse
from pathlib import Path
from datetime import datetime

from pdf_annot.env import load_env, Env
from pdf_annot.pdf_registry import build_pdf_index, PdfInfo
from pdf_annot.notes_db import NotesDB
from pdf_annot.frontmatter import upsert_fields, parse_note
from pdf_annot.ndjson_to_md_block import render_block
from pdf_annot.extract import extract_annotations_to_list
from pdf_annot.streamline_annotations import streamline_annotations_list
from pdf_annot.notes import extract_info_text, replace_annotation_block, UpdateResult
from pdf_annot.utils import atomic_write_file


def _pdf_has_changed(note_text: str, pdf_info: PdfInfo) -> bool:
    """
    Quick check: has the PDF changed since the last sync?

    Compares pdf_mtime and pdf_size from the note's frontmatter against
    the current PDF on disk. This is the cheap gate that avoids opening
    the PDF at all when nothing has changed.
    """
    if not note_text:
        return True  # New note — always process

    parsed = parse_note(note_text)
    if not parsed.has_fm:
        return True  # No frontmatter — treat as new

    fm = parsed.front_matter
    pdf_mtime_iso = datetime.fromtimestamp(pdf_info.mtime).isoformat(timespec="seconds")

    # Compare the two cheap fields
    if fm.get("pdf_mtime") != pdf_mtime_iso:
        return True
    if fm.get("pdf_size") != pdf_info.size:
        return True

    return False


def sync_pdf_to_note(env: Env, pdf_info: PdfInfo, note_path: Path, current_time_iso: str) -> UpdateResult:
    """
    Process a single PDF-note pair through the complete workflow.
    Steps:
    1. Read note (or start empty if non-existent) and extract info text
    2. Quick-check: has pdf_mtime or pdf_size changed?
    3. If unchanged, skip immediately (no PDF parsing)
    4. Extract annotations and stats
    5. Build frontmatter updates
    6. Streamline annotations
    7. Render markdown block
    8. Update note atomically

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

        # 2. Quick gate: skip if PDF hasn't changed (no PDF parsing needed)
        if not _pdf_has_changed(note_text, pdf_info):
            return UpdateResult(
                note_path=note_path, frontmatter_changed=False, annotation_block_changed=False, note_updated=False
            )

        # 3. PDF has changed — do the expensive extraction
        raw_annotations_list, pdf_stats = extract_annotations_to_list(Path(pdf_info.abs_path))
        has_annotations = bool(raw_annotations_list)

        # 4. Build the full set of frontmatter updates
        pdf_mtime_iso = datetime.fromtimestamp(pdf_info.mtime).isoformat(timespec="seconds")

        full_updates = {
            "pdf_id": pdf_info.pdf_id,
            "pdf_title": pdf_info.pdf_title,
            "pdf_size": pdf_info.size,
            "pdf_mtime": pdf_mtime_iso,
            "pdf_hash": pdf_info.pdf_hash,
            "has_annotations": has_annotations,
            "last_run_at": current_time_iso,
            "pdf_pages": pdf_stats.get("pdf_pages"),
            "pdf_highlights": pdf_stats.get("pdf_highlights"),
            "pdf_textboxes": pdf_stats.get("pdf_textboxes"),
        }

        # 5. Apply updates to frontmatter
        _, text_with_updated_fm = upsert_fields(note_text, full_updates)

        # 6. Streamline annotations
        streamlined_annotations = streamline_annotations_list(raw_annotations_list)

        # 7. Render markdown annotation block with preserved info text
        annotation_block = render_block(
            streamlined_annotations, pdf_id_hash=pdf_info.pdf_hash, info_text=existing_info_text
        )

        # 8. Replace annotation block in note
        updated_note_text = replace_annotation_block(text_with_updated_fm, annotation_block)

        # 9. Write updated note atomically
        # TODO: This logic should respect dry_run
        atomic_write_file(note_path, updated_note_text)

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


def main() -> int:
    """
    Main CLI entry point for the PDF-to-Note sync workflow.
    """
    parser = argparse.ArgumentParser(description="Sync PDF annotations and metadata to Markdown notes.")
    parser.add_argument("-c", "--config", help="Path to the TOML config file (e.g., pdf_annot.toml).")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run without writing any files, just print what would change."
    )
    args = parser.parse_args()

    try:
        # 1. Setup: Load Env, Build PDF Registry and NotesDB
        print(f"Loading configuration from: {args.config or 'default'}")
        env = load_env(source=args.config)

        print(f"Scanning for PDFs in: {env.paths.pdf_dirs}")
        pdf_index = build_pdf_index([str(p) for p in env.paths.pdf_dirs])

        print(f"Scanning for notes in: {env.paths.notes_root}")
        notes_db = NotesDB.from_env(env)

        print(f"Found {len(pdf_index)} PDFs and {len(notes_db)} notes. Starting sync...")
        print("-" * 30)

        # 2. Loop: Iterate over all PDFs and sync
        current_time_iso = datetime.now().isoformat(timespec="seconds")
        stats = {"updated": 0, "skipped": 0, "errors": 0}

        for pdf_id_lower, pdf_info in pdf_index.items():
            note_info = notes_db.get(pdf_id_lower)

            if note_info:
                note_path = Path(note_info.abs_path)
            else:
                # Note doesn't exist; create a new path for it
                note_path = env.paths.notes_root / f"{pdf_info.pdf_id}.md"

            # This is where the core logic happens
            result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)

            # 3. Report: Log the result for this file
            if not result.success:
                print(f"❌ ERROR: Failed to sync {pdf_info.filename_with_ext}:\n  {result.error}")
                stats["errors"] += 1
            elif result.note_updated:
                print(f"✅ UPDATED: {note_path.name}")
                stats["updated"] += 1
            else:
                # No error and not updated means skipped
                print(f"➖ SKIPPED: {note_path.name} (already up-to-date)")
                stats["skipped"] += 1

        # 4. Summary
        print("-" * 30)
        print("Sync complete.")
        print(f"  Updated: {stats['updated']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Errors:  {stats['errors']}")
        print("-" * 30)

        return 1 if stats["errors"] > 0 else 0

    except FileNotFoundError as e:
        print(f"❌ CONFIG ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ FATAL ERROR: An unexpected error occurred: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
