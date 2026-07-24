# src/pdf_annot/notes_db.py
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional

from .frontmatter import parse_note
from .utils import is_valid_pdf_id

_CONTROLLED_MD_RE = re.compile(r"^\((?P<id>.+?)\)\.md$", re.IGNORECASE)


def is_controlled_md_name(filename: str) -> Optional[str]:
    """
    Return the PDF id of a bibnote filename, or None if it is not a bibnote.

    Shape belongs to this gate: a bibnote filename is the id and nothing else,
    so "(Keating 1995) v2.md" is not one. Validity of the id itself belongs to
    utils.is_valid_pdf_id, which the PDF-side gate
    (pdf_registry.is_controlled_pdf_name) also uses, so the two cannot drift
    apart (AUDIT.md A5, findings F9 and F17).

    Examples:
      - (Keating 1995).md      -> "(Keating 1995)"
      - (Smilek2011).md        -> None (old-system id: no space before the year)
      - (Keating 1995) v2.md   -> None (the id is not the whole filename)
      - Keating 1995.md        -> None (no parentheses)
    """
    m = _CONTROLLED_MD_RE.match(filename)
    if not m:
        return None
    pdf_id = f"({m.group('id')})"
    return pdf_id if is_valid_pdf_id(pdf_id) else None


class DuplicateNoteIdError(Exception):
    """
    Raised when two or more notes share the same id (case-insensitive).

    Carries every colliding id, not just the first one the walk happened to hit,
    so a single run reports the whole problem instead of one id per run
    (AUDIT.md F8). pdf_id and paths name the first collision in sorted order and
    are derived from duplicates, so the two cannot disagree; the sort keeps the
    choice stable, since walk order is filesystem order.
    """

    def __init__(self, duplicates: Mapping[str, List[str]]) -> None:
        self.duplicates: Dict[str, List[str]] = {key: sorted(paths) for key, paths in sorted(duplicates.items())}
        self.pdf_id = next(iter(self.duplicates))
        self.paths = self.duplicates[self.pdf_id]
        report = "\n".join(
            "  {}\n{}".format(pdf_id, "\n".join(f"    {path}" for path in paths))
            for pdf_id, paths in self.duplicates.items()
        )
        super().__init__(f"Duplicate note ids detected ({len(self.duplicates)}):\n{report}")


@dataclass(frozen=True)
class NoteInfo:
    pdf_id: str
    abs_path: str
    filename: str
    mtime: float
    size: int
    front_matter: Dict[str, object]
    pdf_title: Optional[str]
    pdf_size: Optional[int]
    body: str


def build_notes_index(notes_root: str) -> Dict[str, NoteInfo]:
    """
    Walk notes_root and build an index of bibnotes, mirroring pdf_registry.build_pdf_index.

    - Only files whose basename is exactly "(ID).md" are included; variants like
      "(ID) v2.md" are ignored.
    - Keys are the normalized (lowercased) pdf_id, so callers must lowercase the
      id they look up. sync.py already does.
    - Values carry per-note metadata (path, mtime, size) plus parsed front matter.
    - Raises DuplicateNoteIdError when two or more notes share an id
      (case-insensitive); every colliding id is collected first, so one run
      reports them all (AUDIT.md F8).

    Read-only by construction: this module indexes and reads, it never writes.
    Note mutation belongs to sync.py, which composes it via notes.py (AUDIT.md
    A8; the plan/apply layer that once lived here is retired -- see HISTORY.md).

    There is deliberately no NotesDB class. What survived A8 was a Mapping
    subclass that re-exposed the dict interface it already wrapped, and whose
    only behaviour of its own was lowercasing the key on lookup -- a rule the
    one production caller already honours at the call site. A plain dict is the
    index; this module is the database. Do not re-add a container to hold it.
    """
    notes_root = os.path.abspath(notes_root)
    by_id: Dict[str, List[NoteInfo]] = {}

    for dirpath, _, filenames in os.walk(notes_root):
        for name in filenames:
            if not name.lower().endswith(".md"):
                continue
            pdf_id_raw = is_controlled_md_name(name)
            if pdf_id_raw is None:
                continue
            pdf_id_norm = pdf_id_raw.lower()
            abs_path = os.path.join(dirpath, name)
            try:
                st = os.stat(abs_path)
            except OSError:
                # Skip unreadable files but could be logged by caller
                continue

            with open(abs_path, "r", encoding="utf-8") as f:
                text = f.read()
            pn = parse_note(text)

            fm = pn.front_matter
            note = NoteInfo(
                pdf_id=pdf_id_raw,
                abs_path=abs_path,
                filename=name,
                mtime=st.st_mtime,
                size=st.st_size,
                front_matter=fm,
                pdf_title=(fm.get("pdf_title") if isinstance(fm.get("pdf_title"), str) else None),
                pdf_size=(fm.get("pdf_size") if isinstance(fm.get("pdf_size"), int) else None),
                body=pn.body,
            )
            by_id.setdefault(pdf_id_norm, []).append(note)

    # Detect duplicates -- collect every colliding id before failing (AUDIT.md F8)
    index: Dict[str, NoteInfo] = {}
    duplicates: Dict[str, List[str]] = {}
    for k, notes in by_id.items():
        if len(notes) > 1:
            duplicates[k] = [n.abs_path for n in notes]
            continue
        index[k] = notes[0]

    if duplicates:
        raise DuplicateNoteIdError(duplicates)

    return index
