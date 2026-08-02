#!/usr/bin/env python3
"""
fill_synopses.py

Insert ISBNdb-sourced synopses into existing bibnotes that don't have one
yet. The <pdf_id>.txt files themselves come from a separate, earlier step
(isbndb_synopsis.py in haddolib) -- this tool only ever reads them and
writes the corresponding bibnote's body; it never touches the PDF, the
frontmatter's PDF-related fields, or the annotation block.

Unlike backfill_thumbnails.py, this is not catching up on something
sync.py otherwise keeps current on its own -- there is no automatic path
for synopses at all. Running this tool is the only way a synopsis ever
gets into a bibnote.

Idempotency: whether to insert is decided purely by whether the bibnote's
body already carries a synopsis callout (notes.has_synopsis_block), never
by re-checking the .txt file's content -- synopses are assumed not to
change once fetched. There is deliberately no --force: to get a fresh
synopsis inserted, delete the existing callout from the note by hand
first. That's a conscious choice, not an oversight -- a --force flag would
silently overwrite a synopsis you may have hand-edited, and this tool has
no way to tell the two cases apart.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pdf_annot.env import load_env, Env
from pdf_annot.notes_db import build_notes_index, NoteInfo
from pdf_annot.frontmatter import parse_note, format_note
from pdf_annot.notes import has_synopsis_block, ensure_synopsis_block
from pdf_annot.synopsis import synopsis_path_for, format_synopsis_callout
from pdf_annot.sync import _decline_reason
from pdf_annot.utils import atomic_write_file


@dataclass
class FillResult:
    """
    Result of processing a single bibnote.

    Mirrors BackfillResult's shape (pdf_id, note_path, a boolean for "did
    something change", skipped_reason, error) so the CLI reporting loop
    reads the same way backfill_thumbnails.py's does.
    """

    pdf_id: str
    note_path: Path
    updated: bool = False
    skipped_reason: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """True if processing completed without errors (a skip is not an error)."""
        return self.error is None


def fill_one(env: Env, note_info: NoteInfo) -> FillResult:
    """
    Fill in the synopsis for a single bibnote, if there is one to fill and
    the bibnote doesn't already carry one.

    Cases, checked in this order (cheapest / most common first):
      1. Bibnote already has a synopsis block -> skipped. Permanent: the
         only way to get a fresh one inserted is to delete the existing
         block from the note by hand first (see module docstring).
      2. No <pdf_id>.txt in synopses_dir -> skipped, not yet resolved by
         the ISBNdb tool.
      3. <pdf_id>.txt exists but is zero-length -> skipped, ISBNdb had
         nothing for this pdf_id (isbndb_synopsis.py's deliberate marker
         for "resolved, nothing found", not an error).
      4. Bibnote fails the decline-guard (missing separator or frontmatter)
         -> skipped, left untouched, same guard sync.py and
         backfill_thumbnails.py use.
      5. Otherwise: read, format, insert, write.
    """
    note_path = Path(note_info.abs_path)
    note_text = note_path.read_text(encoding="utf-8")
    parsed = parse_note(note_text)

    if has_synopsis_block(parsed.body):
        return FillResult(pdf_id=note_info.pdf_id, note_path=note_path, skipped_reason="already has a synopsis")

    txt_path = synopsis_path_for(note_info.pdf_id, env.paths.synopses_dir)
    if not txt_path.exists():
        return FillResult(pdf_id=note_info.pdf_id, note_path=note_path, skipped_reason="no synopsis file")
    if txt_path.stat().st_size == 0:
        return FillResult(
            pdf_id=note_info.pdf_id, note_path=note_path, skipped_reason="no synopsis available from ISBNdb"
        )

    decline_reason = _decline_reason(note_text)
    if decline_reason:
        return FillResult(pdf_id=note_info.pdf_id, note_path=note_path, skipped_reason=f"declined: {decline_reason}")

    try:
        raw_text = txt_path.read_text(encoding="utf-8-sig")
        callout = format_synopsis_callout(raw_text)
        updated_body = ensure_synopsis_block(parsed.body, callout)
        updated_text = format_note(parsed.front_matter, updated_body)
        atomic_write_file(note_path, updated_text)
    except OSError as e:
        return FillResult(pdf_id=note_info.pdf_id, note_path=note_path, error=str(e))

    return FillResult(pdf_id=note_info.pdf_id, note_path=note_path, updated=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Insert ISBNdb synopses into existing bibnotes that don't have one yet."
    )
    parser.add_argument("--env", "-e", default="pdf_annot.toml", help="Path to the TOML config file.")
    parser.add_argument("--pdf-id", help='Scope to a single bibnote, e.g. "(Johnson 2017a)". Default: every bibnote.')
    args = parser.parse_args()

    try:
        env = load_env(source=args.env)
    except FileNotFoundError as e:
        print(f"❌ CONFIG ERROR: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        # Covers synopses_dir configured but missing on disk -- deliberately
        # not auto-created, see env.py's _validate_directories.
        print(f"❌ CONFIG ERROR: {e}", file=sys.stderr)
        return 1

    if env.paths.synopses_dir is None:
        print("❌ CONFIG ERROR: synopses_dir is not set in your config; nothing for this tool to do.", file=sys.stderr)
        return 1

    notes_db = build_notes_index(str(env.paths.notes_root))

    if args.pdf_id:
        key = args.pdf_id.lower()
        if key not in notes_db:
            print(f"❌ ERROR: no bibnote found for pdf_id {args.pdf_id}", file=sys.stderr)
            return 1
        notes_db = {key: notes_db[key]}

    print(f"Filling synopses from: {env.paths.synopses_dir}")
    print("-" * 30)

    stats = {"updated": 0, "skipped": 0, "declined": 0, "errors": 0}

    for pdf_id_lower, note_info in notes_db.items():
        result = fill_one(env, note_info)

        if not result.success:
            print(f"❌ ERROR: {result.pdf_id} -- {result.error}")
            stats["errors"] += 1
        elif result.skipped_reason and result.skipped_reason.startswith("declined"):
            print(f"⚠️ DECLINED: {result.note_path.name} -- {result.skipped_reason[len('declined: '):]}")
            stats["declined"] += 1
        elif result.skipped_reason:
            print(f"➖ SKIPPED: {result.note_path.name} -- {result.skipped_reason}")
            stats["skipped"] += 1
        else:
            print(f"✅ UPDATED: {result.note_path.name}")
            stats["updated"] += 1

    print("-" * 30)
    print("Fill complete.")
    print(f"  Updated:  {stats['updated']}")
    print(f"  Skipped:  {stats['skipped']}")
    print(f"  Declined: {stats['declined']}")
    print(f"  Errors:   {stats['errors']}")
    print("-" * 30)

    return 1 if stats["errors"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
