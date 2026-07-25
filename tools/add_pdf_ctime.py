"""tools/add_pdf_ctime.py

One-time batch tool: add a `pdf_ctime` line to every existing bibnote's front
matter, copied verbatim from that note's current `pdf_mtime` line.

This is a text-level line insertion, not a front-matter reserialization: the
YAML block is never parsed into a dict and dumped back out, so nothing else
in the block -- key order, quoting, unrelated keys -- can be touched. The
only thing this script ever writes is one new line, directly above the
existing `pdf_mtime:` line.

Usage:
    python tools/add_pdf_ctime.py --env pdf_annot.toml

Behavior:
    - Only touches real bibnotes: filenames matching "(ID).md" via
      notes_db.is_controlled_md_name.
    - Two-pass by design: every note is first *validated* (front matter
      present, a `pdf_mtime:` line present) before any file is written. If
      any note fails validation, the run aborts with a report and writes
      nothing -- there is no partial batch to roll back.
    - Idempotent: a note that already has a `pdf_ctime:` line in its front
      matter is left untouched and counted separately, so a rerun is safe.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from pdf_annot.env import Env, load_env
from pdf_annot.notes_db import is_controlled_md_name
from pdf_annot.utils import atomic_write_file

FRONTMATTER_FENCE = "---"
PDF_MTIME_PREFIX = "pdf_mtime:"
PDF_CTIME_PREFIX = "pdf_ctime:"


@dataclass(frozen=True)
class NotePlan:
    """The outcome of validating one bibnote, before any write happens."""

    path: Path
    action: str  # "insert", "already_present", or "error"
    new_text: Optional[str] = None
    error: Optional[str] = None


def find_frontmatter_end(lines: List[str]) -> Optional[int]:
    """
    Return the line index of the closing '---' fence, or None if this file
    has no recognizable front matter block (first line is not '---', or no
    closing fence is found).
    """
    if not lines or lines[0].rstrip("\n") != FRONTMATTER_FENCE:
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == FRONTMATTER_FENCE:
            return i
    return None


def plan_note(path: Path) -> NotePlan:
    """
    Read one bibnote and decide what (if anything) needs to change.

    Does not write anything -- this is the validation half of the two-pass
    design, so a note with no `pdf_mtime:` line can be reported without any
    other note in the batch having been touched yet.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    fm_end = find_frontmatter_end(lines)
    if fm_end is None:
        return NotePlan(path=path, action="error", error="no front matter block found")

    fm_lines = lines[1:fm_end]

    if any(line.startswith(PDF_CTIME_PREFIX) for line in fm_lines):
        return NotePlan(path=path, action="already_present")

    mtime_idx = next(
        (i for i, line in enumerate(fm_lines) if line.startswith(PDF_MTIME_PREFIX)),
        None,
    )
    if mtime_idx is None:
        return NotePlan(path=path, action="error", error="no 'pdf_mtime:' line in front matter")

    mtime_line = fm_lines[mtime_idx]
    ctime_line = PDF_CTIME_PREFIX + mtime_line[len(PDF_MTIME_PREFIX) :]

    new_fm_lines = fm_lines[:mtime_idx] + [ctime_line] + fm_lines[mtime_idx:]
    new_lines = lines[:1] + new_fm_lines + lines[fm_end:]
    return NotePlan(path=path, action="insert", new_text="".join(new_lines))


def find_bibnotes(notes_root: Path) -> List[Path]:
    """Walk notes_root and return every real bibnote path ("(ID).md")."""
    result: List[Path] = []
    for dirpath, _dirnames, filenames in os.walk(notes_root):
        for name in filenames:
            if not name.lower().endswith(".md"):
                continue
            if is_controlled_md_name(name) is None:
                continue
            result.append(Path(dirpath) / name)
    return sorted(result)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=None, help="Path to the TOML config file (default: pdf_annot.toml).")
    args = parser.parse_args(argv)

    env: Env = load_env(args.env)
    notes = find_bibnotes(env.paths.notes_root)

    plans = [plan_note(path) for path in notes]

    errors = [p for p in plans if p.action == "error"]
    if errors:
        print(f"ABORTED: {len(errors)} note(s) failed validation. No files were written.", file=sys.stderr)
        for p in errors:
            print(f"  {p.path}: {p.error}", file=sys.stderr)
        return 1

    to_insert = [p for p in plans if p.action == "insert"]
    already = [p for p in plans if p.action == "already_present"]

    for p in to_insert:
        assert p.new_text is not None
        atomic_write_file(p.path, p.new_text)

    print(f"Bibnotes scanned:   {len(plans)}")
    print(f"pdf_ctime inserted: {len(to_insert)}")
    print(f"already present:    {len(already)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
