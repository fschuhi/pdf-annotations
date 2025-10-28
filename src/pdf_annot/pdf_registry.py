# src/pdf_annot/pdf_registry.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .utils import crc32_az7, parse_filename, pdf_id_from_filename


class DuplicatePdfIdError(Exception):
    def __init__(self, pdf_id: str, paths: List[str]):
        super().__init__(f"Duplicate PDF id detected for {pdf_id!r}: {paths}")
        self.pdf_id = pdf_id
        self.paths = paths


@dataclass(frozen=True)
class PdfInfo:
    # Identity and naming
    pdf_id: str                 # e.g., "(Das 2000b)"
    pdf_hash: str               # 7-letter hash from lowercase pdf_id
    pdf_title: str              # filename sans pdf_id and extension
    authors: str                # "Smith+Doe" (as parsed)
    year: str                   # "2015a" or "2015" or ""

    # Paths and filesystem
    abs_path: str               # absolute path to the PDF (native separators)
    dropbox_rel_path: Optional[str]  # POSIX-style path relative to dropbox_root, if provided
    size: int                   # file size in bytes
    mtime: float                # mtime (epoch seconds)

    # Original filename with extension (for reference)
    filename_with_ext: str


def _is_pdf_ext(name: str) -> bool:
    return name.lower().endswith(".pdf")


def is_controlled_pdf_name(filename_with_ext: str) -> bool:
    """
    Controlled PDFs:
      - Must start with '(' then an id, then ')', then a space, then the rest (non-empty preferred)
      - Must end with .pdf (case-insensitive)
    Examples:
      - (Das 2000b) Title.pdf        -> controlled
      - (OnlyAuthors) Title.pdf      -> controlled (year may be empty)
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
    return len(name) > close_idx + 1 and name[close_idx + 1] == " "


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
    - Raises DuplicatePdfIdError if multiple files map to the same normalized id.
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
        # Report the first duplicate with all paths
        for key, paths in collisions.items():
            if len(paths) > 1:
                raise DuplicatePdfIdError(key, paths)

    return index
