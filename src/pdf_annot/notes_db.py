# src/pdf_annot/notes_db.py
from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Tuple, Mapping as TypingMapping, Protocol

from .frontmatter import parse_note, upsert_fields
from .env import Env

CONTROLLED_MD_RE = re.compile(r"^\((?P<id>.+?)\)\.md$", re.IGNORECASE)

# Annotation block markers
ANNOT_SEP = '<hr class="pdf-annot-sep">'
ANNOT_INFO_PREFIX = '<span class="pdf-annot-info">'
NEWLINE = "\n"


class ProvidesLogging(Protocol):
    """A duck type for an object that has info() and error() methods."""

    def info(self, msg: str) -> None: ...

    def error(self, msg: str) -> None: ...


class DuplicateNoteIdError(Exception):
    def __init__(self, pdf_id: str, paths: List[str]) -> None:
        super().__init__(f"Duplicate note id '{pdf_id}' for paths: {paths}")
        self.pdf_id = pdf_id
        self.paths = paths


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


class NotesDB(Mapping[str, NoteInfo]):
    """
    Lightweight index of Markdown notes named exactly "(ID).md".

    * ID matching is case-insensitive; keys are normalized (e.g., "(keating 1995)").
    * Only files whose basename matches r'^.+.+.md$' are included; variants like "(ID) v2.md" are ignored.
    * Stores per-note metadata (path, mtime, size) and parsed front matter.
    * front matter updates only, body updates are not handled yet
    Raises:
    DuplicateNoteIdError: when two or more notes share the same ID (case-insensitive).
    """

    def __init__(self, root: str, index: Dict[str, NoteInfo]) -> None:
        self.root = os.path.abspath(root)
        self._index = index

    @classmethod
    def from_env(cls, env: "Env") -> "NotesDB":
        """
        Build a NotesDB using env.paths.notes_root.
        This is just a convenience wrapper around build().
        """
        return cls.build(str(env.paths.notes_root))

    @classmethod
    def build(cls, vault_root: str) -> "NotesDB":
        vault_root = os.path.abspath(vault_root)
        by_id: Dict[str, List[NoteInfo]] = {}

        for dirpath, _, filenames in os.walk(vault_root):
            for name in filenames:
                if not name.lower().endswith(".md"):
                    continue
                m = CONTROLLED_MD_RE.match(name)
                if not m:
                    continue
                pdf_id_raw = f"({m.group('id')})"
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

        # Detect duplicates
        index: Dict[str, NoteInfo] = {}
        for k, notes in by_id.items():
            if len(notes) > 1:
                raise DuplicateNoteIdError(k, [n.abs_path for n in notes])
            index[k] = notes[0]

        return cls(vault_root, index)

    # Mapping interface
    def __len__(self) -> int:
        return len(self._index)

    def __iter__(self) -> Iterator[str]:
        return iter(self._index)

    def __getitem__(self, key: str) -> NoteInfo:
        return self._index[key.lower()]

    # Convenience
    def ids(self) -> Iterable[str]:
        return (info.pdf_id for info in self._index.values())

    def values(self) -> Iterable[NoteInfo]:  # type: ignore[override]
        return self._index.values()

    def items(self) -> Iterable[Tuple[str, NoteInfo]]:  # type: ignore[override]
        return self._index.items()

    # Planning and applying frontmatter updates

    @dataclass(frozen=True)
    class FrontmatterUpdatePlan:
        """
        Proposed front-matter changes for a single note.

        Attributes:
        note_path: Path to the Markdown file.
        fields: Dict[str, Any] of keys to set/update in YAML front matter.
        """

        pdf_id: str
        note_path: str
        desired_frontmatter: Dict[str, object]
        current_frontmatter: Dict[str, object]

    @dataclass(frozen=True)
    class FrontmatterPlanSummary:
        """
        Output of planning step.

        Attributes:
        plans: List[UpdatePlan]
        missing_notes: Set[str] pdf_ids present in registry but missing as "(ID).md"
        orphan_notes: Set[str] notes that have no matching pdf_id in registry
        """

        plans: List["NotesDB.FrontmatterUpdatePlan"]
        missing_notes: List[str]
        orphan_notes: List[str]

    @dataclass(frozen=True)
    class FrontmatterApplySummary:
        """
        Result of apply step.

        Attributes:
        updated: List[Path]
        skipped: List[Path]
        errors: List[tuple[Path, Exception]]
        """

        updated: List[str]  # note paths
        unchanged: List[str]
        errors: List[Tuple[str, str]]  # (note_path, error_message)

    def plan_frontmatter_updates(
        self,
        pdf_db: Mapping[str, object],
        *,
        pdf_id_attr: str = "pdf_id",
        title_attr_path: Tuple[str, ...] = ("title_from_filename",),
        size_attr: str = "size",
    ) -> "NotesDB.FrontmatterPlanSummary":
        """
        Compare notes with a PDF registry and propose front-matter changes.
        """

        # --- FIX: Removed unused 'norm_key' function ---

        def get_attr_chain(obj: object, path: Tuple[str, ...]) -> object:
            cur = obj
            for p in path:
                if isinstance(cur, dict):
                    cur = cur.get(p)
                else:
                    cur = getattr(cur, p)
            return cur

        pdf_index: Dict[str, object] = {}
        for v in pdf_db.values():  # type: ignore[attr-defined]
            # Support dict-like or attr-like
            if isinstance(v, dict):
                pid = str(v.get(pdf_id_attr, "")).lower()
            else:
                pid = str(getattr(v, pdf_id_attr)).lower()
            if not pid:
                continue
            pdf_index[pid] = v

        plans: List[NotesDB.FrontmatterUpdatePlan] = []
        missing_notes: List[str] = []
        orphan_notes: List[str] = []

        # Matched and missing
        for pid, pobj in pdf_index.items():
            note = self._index.get(pid)
            if not note:
                missing_notes.append(pid)
                continue
            # Fetch desired fields
            if isinstance(pobj, dict):
                title_val = get_attr_chain(pobj, title_attr_path)  # supports nested dicts
                size_val = pobj.get(size_attr)
            else:
                title_val = get_attr_chain(pobj, title_attr_path)
                size_val = getattr(pobj, size_attr)
            desired: Dict[str, object] = {}
            if isinstance(title_val, str):
                desired["pdf_title"] = title_val
            if isinstance(size_val, int):
                desired["pdf_size"] = size_val

            current = dict(note.front_matter)
            # Only plan if something would change
            would_change = False
            for k, v in desired.items():
                if current.get(k) != v:
                    would_change = True
                    break
            if would_change:
                plans.append(
                    NotesDB.FrontmatterUpdatePlan(
                        pdf_id=note.pdf_id,
                        note_path=note.abs_path,
                        desired_frontmatter=desired,
                        current_frontmatter=current,
                    )
                )

        # Orphans: notes with no pdf counterpart
        for pid in self._index.keys():
            if pid not in pdf_index:
                orphan_notes.append(self._index[pid].pdf_id)

        return NotesDB.FrontmatterPlanSummary(plans=plans, missing_notes=missing_notes, orphan_notes=orphan_notes)

    # --- FIX: Added @staticmethod ---
    @staticmethod
    def apply_frontmatter_updates(
        plans: Iterable["NotesDB.FrontmatterUpdatePlan"],
        *,
        dry_run: bool = False,
        logger: Optional[ProvidesLogging] = None,
    ) -> "NotesDB.FrontmatterApplySummary":
        """
        Apply a list of UpdatePlan changes to note files.
        * Writes are atomic: content is written to a temp file and moved into place.
        * If dry_run is True, no files are changed; a preview result is returned.
        """
        updated: List[str] = []
        unchanged: List[str] = []
        errors: List[Tuple[str, str]] = []

        for plan in plans:
            path = plan.note_path
            try:
                with open(path, "r", encoding="utf-8") as f:
                    original = f.read()
            # --- FIX: Catch specific OSError ---
            except OSError as e:
                msg = f"Failed to read note '{path}': {e}"
                if logger:
                    logger.error(msg)
                errors.append((path, str(e)))
                continue

            changed, new_text = upsert_fields(original, plan.desired_frontmatter)
            if not changed:
                unchanged.append(path)
                if logger:
                    logger.info(f"No change for {path}")
                continue

            if dry_run:
                updated.append(path)
                if logger:
                    logger.info(f"[dry-run] Would update {path}")
                continue

            # --- REFACTORED: Use atomic write helper ---
            try:
                _atomic_write_file(path, new_text)
                updated.append(path)
                if logger:
                    logger.info(f"Updated {path}")
            except Exception as e:
                msg = f"Failed to atomically write '{path}': {e}"
                if logger:
                    logger.error(msg)
                errors.append((path, str(e)))

        return NotesDB.FrontmatterApplySummary(updated=updated, unchanged=unchanged, errors=errors)

    # ------------------------------------------------------------
    # Annotation block planning and applying
    # ------------------------------------------------------------

    @dataclass(frozen=True)
    class AnnotationUpdatePlan:
        pdf_id: str
        note_path: str
        new_block: str  # full block: starts with ANNOT_SEP and includes info span + required spacing
        action: str  # "create_block" | "update_block" | "unchanged"

    @dataclass(frozen=True)
    class AnnotationPlanSummary:
        plans: List["NotesDB.AnnotationUpdatePlan"]
        missing_notes: List[str]

    @dataclass(frozen=True)
    class AnnotationApplySummary:
        updated: List[str]
        unchanged: List[str]
        errors: List[Tuple[str, str]]  # (note_path, error_message)

    def plan_annotation_updates(
        self,
        blocks_by_pdf_id: TypingMapping[str, str],
    ) -> "NotesDB.AnnotationPlanSummary":
        """
        Decide per-note whether to insert/update/skip the annotation block.

        blocks_by_pdf_id: mapping of pdf_id (any case) -> rendered block string
        The block must:
          - start with ANNOT_SEP line
          - include exactly one blank line after the separator
          - include '<span class="pdf-annot-info">…</span>' line
          - include one blank line after the span (as produced by ndjson_to_md_block.render_block())
        """
        plans: List[NotesDB.AnnotationUpdatePlan] = []
        missing: List[str] = []

        for pid_raw, block in blocks_by_pdf_id.items():
            pid = pid_raw.lower()
            note = self._index.get(pid)
            if not note:
                missing.append(pid_raw)
                continue

            try:
                with open(note.abs_path, "r", encoding="utf-8") as f:
                    original = f.read()
            # --- FIX: Catch specific OSError ---
            except OSError:
                # If unreadable, still produce a plan; apply step will report error
                original = ""

            changed, _ = _body_after_update(original, block)
            action = "unchanged"
            if original == "":
                action = "update_block"
            else:
                body = parse_note(original).body
                if _find_annot_block_start(body) == -1 and changed:
                    action = "create_block"
                elif changed:
                    action = "update_block"

            plans.append(
                NotesDB.AnnotationUpdatePlan(
                    pdf_id=note.pdf_id,
                    note_path=note.abs_path,
                    new_block=block,
                    action=action,
                )
            )

        return NotesDB.AnnotationPlanSummary(plans=plans, missing_notes=missing)

    # --- FIX: Added @staticmethod ---
    @staticmethod
    def apply_annotation_updates(
        plans: Iterable["NotesDB.AnnotationUpdatePlan"],
        *,
        dry_run: bool = False,
        logger: Optional[ProvidesLogging] = None,
    ) -> "NotesDB.AnnotationApplySummary":
        updated: List[str] = []
        unchanged: List[str] = []
        errors: List[Tuple[str, str]] = []

        for plan in plans:
            path = plan.note_path
            try:
                with open(path, "r", encoding="utf-8") as f:
                    original = f.read()
            # --- FIX: Catch specific OSError ---
            except OSError as e:
                errors.append((path, f"read error: {e}"))
                if logger:
                    logger.error(f"Failed to read '{path}': {e}")
                continue

            changed, new_text = _body_after_update(original, plan.new_block)
            if not changed:
                unchanged.append(path)
                if logger:
                    logger.info(f"No annotation change for {path}")
                continue

            if dry_run:
                updated.append(path)
                if logger:
                    logger.info(f"[dry-run] Would update annotations in {path}")
                continue

            # --- REFACTORED: Use atomic write helper ---
            try:
                _atomic_write_file(path, new_text)
                updated.append(path)
                if logger:
                    logger.info(f"Updated annotations in {path}")
            except Exception as e:
                errors.append((path, f"write error: {e}"))
                if logger:
                    logger.error(f"Failed to write '{path}': {e}")

        return NotesDB.AnnotationApplySummary(updated=updated, unchanged=unchanged, errors=errors)


# ------------- helpers (module level) -------------


# --- NEW: Helper function for atomic writes ---
def _atomic_write_file(path: str, new_text: str) -> None:
    """
    Atomically write new_text to path.
    Writes to temp file in same dir, fsyncs, and replaces.
    """
    dirpath = os.path.dirname(path)
    fd, tmppath = tempfile.mkstemp(prefix=".tmp-", suffix=".md", dir=dirpath, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as tmpf:
            tmpf.write(new_text)
            tmpf.flush()
            os.fsync(tmpf.fileno())
        # Also fsync the directory to persist the rename on some filesystems
        os.replace(tmppath, path)
        dirfd = os.open(dirpath, os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        # If replace succeeded, tmppath is gone; if failed, try to remove
        if os.path.exists(tmppath):
            try:
                os.remove(tmppath)
            except OSError:
                pass


def _ensure_trailing_nl(s: str) -> str:
    return s if s.endswith("\n") else (s + "\n")


def _find_annot_block_start(body: str) -> int:
    """
    Return index in body where the annotation block starts (at the '<hr ...>' line),
    or -1 if not present.
    """
    return body.find(ANNOT_SEP)


def _normalize_block_spacing(block: str) -> str:
    """
    Trust converter output; only normalize final newline.
    """
    block = block.rstrip("\n")
    return _ensure_trailing_nl(block)


def _compose_new_note_text(original: str, new_block: str) -> str:
    """
    Replace or insert the annotation block region in original with new_block.
    Preserve YAML frontmatter (raw) and any preface before the separator.
    """
    has_fm, head, fm_block_raw, tail = _split_frontmatter_raw(original)
    if has_fm:
        fm_region = f"---\n{fm_block_raw}---\n"
        body = tail
        prefix = fm_region
    else:
        body = original
        prefix = ""

    start = _find_annot_block_start(body)
    nb = _normalize_block_spacing(new_block)

    if start == -1:
        new_body = nb
    else:
        new_body = body[:start] + nb

    out = prefix + new_body
    if not out.endswith("\n"):
        out += "\n"
    return out


def _body_after_update(original: str, new_block: str) -> tuple[bool, str]:
    new_text = _compose_new_note_text(original, new_block)
    return (new_text != original), new_text


def _split_frontmatter_raw(text: str) -> tuple[bool, str, str, str]:
    """
    Reuse frontmatter._split_front_matter for consistent slicing.
    """
    from .frontmatter import _split_front_matter as _split

    return _split(text)
