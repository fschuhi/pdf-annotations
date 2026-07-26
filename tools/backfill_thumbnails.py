#!/usr/bin/env python3
"""
backfill_thumbnails.py

One-time (and on-demand single-file) tool to add page-1 thumbnails to
bibnotes that predate the thumbnail feature, or whose thumbnail JPEG has
gone missing. Going forward, sync.py adds thumbnails to new and changed
bibnotes on its own -- this tool exists for everything sync.py's
change-detection gate will never touch on its own (see TODO.md
"Thumbnails"), mirroring the shape of the earlier add_pdf_ctime one-time
tool.

Deliberately narrower than sync.py: this tool only ever touches the
thumbnail JPEG and the <span> in the note body. It never re-extracts
annotations and never touches any frontmatter field.

Idempotency: whether to re-render is decided purely by whether the JPEG
file exists on disk (or --force), never by whether the span text is
present. Deleting the JPEG is the signal to regenerate it -- if the span
is already there when the file reappears, only the image gets rendered;
the note is not rewritten.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pdf_annot.env import load_env, Env
from pdf_annot.pdf_registry import build_pdf_index, PdfInfo
from pdf_annot.notes_db import build_notes_index
from pdf_annot.frontmatter import parse_note, format_note
from pdf_annot.notes import ensure_thumbnail_header, has_thumbnail_header
from pdf_annot.sync import _decline_reason
from pdf_annot.thumbnails import render_thumbnail, thumbnail_path_for
from pdf_annot.utils import atomic_write_file


@dataclass
class BackfillResult:
    """
    Result of backfilling a single PDF-note pair.

    Mirrors UpdateResult/ThumbnailResult in shape: capture what happened so
    tests and the CLI report can act on it without re-deriving anything.
    """

    pdf_id: str
    note_path: Optional[Path]
    rendered: bool = False
    span_added: bool = False
    skipped_reason: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """True if processing completed without errors (a skip is not an error)."""
        return self.error is None


def backfill_one(env: Env, pdf_info: PdfInfo, note_path: Path, *, force: bool = False) -> BackfillResult:
    """
    Backfill the thumbnail for a single PDF-note pair.

    Cases (see module docstring and TODO.md "Thumbnails" for the full list
    this was designed against):
      1. No bibnote for this PDF yet -> skipped, sync.py's job instead.
      2. Bibnote fails the decline-guard -> skipped, left untouched.
      3. Span present and JPEG exists (and not --force) -> skipped, fully done.
      4. Span absent, JPEG absent -> render, add span, write note.
      5. Span absent, JPEG exists -> add span only, write note.
      6. Span present, JPEG absent (or --force) -> re-render the JPEG only;
         the note already carries the span, so it is not rewritten.
      7. Rendering fails -> note left untouched, reported as an error.
    """
    if not note_path.exists():
        return BackfillResult(pdf_id=pdf_info.pdf_id, note_path=note_path, skipped_reason="no bibnote for this PDF")

    note_text = note_path.read_text(encoding="utf-8")
    decline_reason = _decline_reason(note_text)
    if decline_reason:
        return BackfillResult(pdf_id=pdf_info.pdf_id, note_path=note_path, skipped_reason=f"declined: {decline_reason}")

    thumbnail_dest = thumbnail_path_for(pdf_info.pdf_id, env.paths.thumbnails_dir)
    needs_render = force or not thumbnail_dest.exists()

    rendered = False
    if needs_render:
        render_result = render_thumbnail(Path(pdf_info.abs_path), thumbnail_dest)
        if not render_result.success:
            return BackfillResult(pdf_id=pdf_info.pdf_id, note_path=note_path, error=render_result.error)
        rendered = True

    parsed = parse_note(note_text)
    if has_thumbnail_header(parsed.body):
        if not rendered:
            return BackfillResult(pdf_id=pdf_info.pdf_id, note_path=note_path, skipped_reason="already up to date")
        # File was (re-)rendered but the span was already there -- the image
        # changed, the text didn't, so there is nothing to write into the note.
        return BackfillResult(pdf_id=pdf_info.pdf_id, note_path=note_path, rendered=True)

    updated_body = ensure_thumbnail_header(parsed.body, pdf_info.pdf_id)
    updated_text = format_note(parsed.front_matter, updated_body)
    atomic_write_file(note_path, updated_text)
    return BackfillResult(pdf_id=pdf_info.pdf_id, note_path=note_path, rendered=rendered, span_added=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill page-1 thumbnails into existing bibnotes.")
    parser.add_argument("--env", "-e", default="pdf_annot.toml", help="Path to the TOML config file.")
    parser.add_argument("--pdf-id", help='Scope to a single bibnote, e.g. "(Albini 2013)". Default: every bibnote.')
    parser.add_argument("--force", action="store_true", help="Re-render the thumbnail even if the JPEG already exists.")
    args = parser.parse_args()

    try:
        env = load_env(source=args.env)
    except FileNotFoundError as e:
        print(f"❌ CONFIG ERROR: {e}", file=sys.stderr)
        return 1

    if env.paths.thumbnails_dir is None:
        print(
            "❌ CONFIG ERROR: thumbnails_dir is not set in your config; nothing for this tool to do.", file=sys.stderr
        )
        return 1

    pdf_index = build_pdf_index([str(p) for p in env.paths.pdf_dirs])
    notes_db = build_notes_index(str(env.paths.notes_root))

    if args.pdf_id:
        key = args.pdf_id.lower()
        if key not in pdf_index:
            print(f"❌ ERROR: no PDF found for pdf_id {args.pdf_id}", file=sys.stderr)
            return 1
        pdf_index = {key: pdf_index[key]}

    print(f"Backfilling thumbnails into: {env.paths.thumbnails_dir}")
    print("-" * 30)

    stats = {"updated": 0, "skipped": 0, "declined": 0, "errors": 0}

    for pdf_id_lower, pdf_info in pdf_index.items():
        note_info = notes_db.get(pdf_id_lower)
        note_path = Path(note_info.abs_path) if note_info else env.paths.notes_root / f"{pdf_info.pdf_id}.md"

        result = backfill_one(env, pdf_info, note_path, force=args.force)

        if not result.success:
            print(f"❌ ERROR: {result.pdf_id} -- {result.error}")
            stats["errors"] += 1
        elif result.skipped_reason and result.skipped_reason.startswith("declined"):
            print(f"⚠️ DECLINED: {note_path.name} -- {result.skipped_reason[len('declined: '):]}")
            stats["declined"] += 1
        elif result.skipped_reason:
            label = note_path.name if note_path.exists() else result.pdf_id
            print(f"➖ SKIPPED: {label} -- {result.skipped_reason}")
            stats["skipped"] += 1
        else:
            detail = (
                " (re-rendered image only, span already present)" if result.rendered and not result.span_added else ""
            )
            print(f"✅ UPDATED: {note_path.name}{detail}")
            stats["updated"] += 1

    print("-" * 30)
    print("Backfill complete.")
    print(f"  Updated:  {stats['updated']}")
    print(f"  Skipped:  {stats['skipped']}")
    print(f"  Declined: {stats['declined']}")
    print(f"  Errors:   {stats['errors']}")
    print("-" * 30)

    return 1 if stats["errors"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
