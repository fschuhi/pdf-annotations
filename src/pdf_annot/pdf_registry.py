# src/pdf_annot/pdf_registry.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional

from .utils import crc32_az7, is_valid_pdf_id, parse_filename


class DuplicatePdfIdError(Exception):
    """
    Raised when two or more PDFs map to the same normalized id.

    Carries every colliding id, not just the first one the walk happened to hit,
    so a single run reports the whole problem instead of one id per run
    (AUDIT.md F8).

    pdf_id and paths name the first collision in sorted order. They exist because
    resolve.py formats them into DUPLICATE_MSG, and a pdf:// alert is about the
    one click that failed, so it stays singular by design
    (TARGET_ARCHITECTURE.md section 3.4). They are derived from duplicates rather
    than passed alongside it, so the two cannot disagree, and the sort keeps the
    choice stable: walk order is filesystem order and would otherwise name a
    different id from run to run.
    """

    def __init__(self, duplicates: Mapping[str, List[str]]) -> None:
        self.duplicates: Dict[str, List[str]] = {key: sorted(paths) for key, paths in sorted(duplicates.items())}
        self.pdf_id = next(iter(self.duplicates))
        self.paths = self.duplicates[self.pdf_id]
        report = "\n".join(
            "  {}\n{}".format(pdf_id, "\n".join(f"    {path}" for path in paths))
            for pdf_id, paths in self.duplicates.items()
        )
        super().__init__(f"Duplicate PDF ids detected ({len(self.duplicates)}):\n{report}")


@dataclass(frozen=True)
class PdfInfo:
    # Identity and naming
    pdf_id: str  # e.g., "(Das 2000b)"
    pdf_hash: str  # 7-letter hash from lowercase pdf_id
    pdf_title: str  # filename sans pdf_id and extension
    authors: str  # "Smith+Doe" (as parsed)
    year: str  # "2015a" or "2015" or ""

    # Paths and filesystem
    abs_path: str  # absolute path to the PDF (native separators)
    dropbox_rel_path: Optional[str]  # POSIX-style path relative to dropbox_root, if provided
    size: int  # file size in bytes
    mtime: float  # mtime (epoch seconds)

    # Original filename with extension (for reference)
    filename_with_ext: str


def _is_pdf_ext(name: str) -> bool:
    return name.lower().endswith(".pdf")


def is_controlled_pdf_name(filename_with_ext: str) -> bool:
    """
    Controlled PDFs:
      - Must start with a well-formed id "(Authors Year)", then a space, then the rest
      - Must end with .pdf (case-insensitive)

    The id itself is validated by utils.is_valid_pdf_id, which the notes-side gate
    (notes_db.is_controlled_md_name) also uses, so the two cannot drift apart
    (AUDIT.md A5, findings F9 and F17).

    Examples:
      - (Das 2000b) Title.pdf        -> controlled
      - (Smilek2011) Title.pdf       -> not controlled: an old-system id. Without the
                                        year gate it parses as an author named
                                        "Smilek2011" with no year, hashes differently,
                                        and so silently becomes a different work.
      - (OnlyAuthors) Title.pdf      -> not controlled (no year)
      - (Alpha 2020)Name.pdf         -> not controlled (missing space after ')')
      - Smith+Doe - 2015 - Title.pdf -> not controlled (legacy format)
    """
    if not _is_pdf_ext(filename_with_ext):
        return False
    name = filename_with_ext[:-4]  # strip .pdf
    if not name.startswith("("):
        return False
    # Require a closing ')' followed by a space
    try:
        close_idx = name.index(")")
    except ValueError:
        return False
    # Must be followed by a space and at least something after it (paper name can technically be empty, but we expect a space)
    if not (len(name) > close_idx + 1 and name[close_idx + 1] == " "):
        return False
    return is_valid_pdf_id(name[: close_idx + 1])


def _posix_relpath_if_under(path: str, root: Optional[str]) -> Optional[str]:
    if not root:
        return None
    # Normalize and test ancestry
    abs_path = os.path.abspath(path)
    abs_root = os.path.abspath(root)
    try:
        rel = os.path.relpath(abs_path, abs_root)
    except ValueError:
        # Different drives on Windows or other relpath issues
        return None
    # If path is outside root, relpath will start with '..'
    if rel.startswith(".."):
        return None
    # Convert to POSIX-style separators
    return rel.replace(os.sep, "/")


def pdf_info_from_path(path: str, *, dropbox_root: Optional[str] = None) -> Optional[PdfInfo]:
    """
    Build PdfInfo from a single file path.
    Returns None if the file is not a controlled PDF by name.
    """
    filename_with_ext = os.path.basename(path)
    if not is_controlled_pdf_name(filename_with_ext):
        return None

    pf = parse_filename(path)
    pdf_id = pf.pdf_id  # derived from authors/year as parsed
    # Hash is calculated from lowercase pdf_id
    pdf_hash = crc32_az7(pdf_id.lower())

    # pdf_title is the remainder after "(Authors Year) "
    # parse_filename already exposes pdf_title for bracket-format
    pdf_title = pf.pdf_title

    st = os.stat(path)
    abs_path = os.path.abspath(path)
    dropbox_rel = _posix_relpath_if_under(abs_path, dropbox_root)

    return PdfInfo(
        pdf_id=pdf_id,
        pdf_hash=pdf_hash,
        pdf_title=pdf_title,
        authors=pf.authors,
        year=pf.year,
        abs_path=abs_path,
        dropbox_rel_path=dropbox_rel,
        size=st.st_size,
        mtime=st.st_mtime,
        filename_with_ext=filename_with_ext,
    )


def _iter_pdf_files(roots: Iterable[str]) -> Iterable[str]:
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if _is_pdf_ext(fn):
                    yield os.path.join(dirpath, fn)


def build_pdf_index(roots: List[str], *, dropbox_root: Optional[str] = None) -> Dict[str, PdfInfo]:
    """
    Walk given roots and build an index of controlled PDFs.
    - Only bracket-format controlled names are included.
    - Keys are normalized pdf_id for case-insensitive lookups (lowercase).
    - Raises DuplicatePdfIdError if multiple files map to the same normalized id;
      every colliding id is collected first, so one run reports them all.
    """
    index: Dict[str, PdfInfo] = {}
    collisions: Dict[str, List[str]] = {}

    for path in _iter_pdf_files(roots):
        info = pdf_info_from_path(path, dropbox_root=dropbox_root)
        if info is None:
            continue
        key = info.pdf_id.lower()
        if key in index:
            # Track collisions for a helpful error
            existing = collisions.setdefault(key, [index[key].abs_path])
            existing.append(info.abs_path)
        else:
            index[key] = info

    if collisions:
        raise DuplicatePdfIdError(collisions)

    return index
