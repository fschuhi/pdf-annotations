# src/pdf_annot/utils.py
from __future__ import annotations

import os
import re
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

# -----------------------------------------------------------------------------
# Core hashing utilities
# -----------------------------------------------------------------------------


def crc32_az7(text: str) -> str:
    """
    Generate a 7-character uppercase A–Z fingerprint from input text,
    matching the Excel VBA approach provided:
      - Lowercase the input
      - Compute CRC32 (unsigned, same polynomial as zlib/crc32)
      - Repeatedly take base-26 remainders to map into 'A'..'Z'
    """
    # Lowercase to mirror the VBA's LCase
    data = text.lower().encode("utf-8")

    # zlib.crc32 returns a signed int in Python <3.0 context, but in modern Python
    # it returns a (potentially) negative int only conceptually; we & 0xFFFFFFFF
    # to force it to an unsigned 32-bit value like VBA's Not crc end result.

    # --- FIX: Ignore PyCharm's incorrect type warning ---
    crc = zlib.crc32(data) & 0xFFFFFFFF  # type: ignore

    # Build 7 letters using base-26 with 'A' as 0
    chars = []
    for _ in range(7):
        remainder = crc % 26
        chars.append(chr(65 + remainder))  # 'A' + remainder
        crc //= 26
    return "".join(chars)


def hash_text(authors: str) -> str:
    """
    Convenience wrapper for author strings to the 7-letter A–Z fingerprint.
    """
    return crc32_az7(authors)


# -----------------------------------------------------------------------------
# Filename parsing
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedFilename:
    path: str
    filename_with_ext: str
    filename: str
    pdf_title: str
    authors: str
    year: str

    @property
    def authors_array(self) -> List[str]:
        # Split by '+' and trim spaces
        return [a.strip() for a in self.authors.split("+")] if self.authors else []

    @property
    def pdf_id(self) -> str:
        # "(Authors Year)" with graceful spacing if year/author missing
        a = self.authors.strip()
        y = self.year.strip()
        if a and y:
            return f"({a} {y})"
        if a:
            return f"({a})"
        if y:
            return f"({y})"
        return "()"


# Patterns:
# - Bracket format: "(Authors Year[letter]) Rest of title.pdf"
#   Authors may be "A" or "A+B+C". Year can be "2015" or "2015a".
# - Dash format: "Authors - 2015[a] - Title.pdf"
_BRACKET_RE = re.compile(
    r"""
    ^\(
      (?P<bracket>[^)]*)
    \)
    \s*
    (?P<rest>.*)$
""",
    re.VERBOSE,
)


def _split_bracket(bracket: str) -> Tuple[str, str]:
    # Split bracket content into authors and year: last space separates
    bracket = bracket.strip()
    if not bracket:
        return "", ""
    last_space = bracket.rfind(" ")
    if last_space == -1:
        # No space; treat entire bracket as authors
        return bracket, ""
    authors = bracket[:last_space].strip()
    year = bracket[last_space + 1 :].strip()
    return authors, year


def parse_filename(full_path: str) -> ParsedFilename:
    """
    Parse either:
      - "(Authors Year) Paper name.pdf"
      - "Authors - Year - Paper name.pdf"
    Returns a ParsedFilename with fields filled as in the VBA example.
    """
    # Normalize path separators
    path, filename_with_ext = os.path.split(full_path)
    filename, ext = os.path.splitext(filename_with_ext)

    pdf_title = ""
    authors = ""
    year = ""

    if filename.startswith("("):
        m = _BRACKET_RE.match(filename)
        if m:
            bracket = m.group("bracket")
            rest = m.group("rest").strip()
            authors, year = _split_bracket(bracket)
            pdf_title = rest
    else:
        parts = filename.split(" - ")
        if len(parts) >= 3:
            authors = parts[0].strip()
            year = parts[1].strip()
            pdf_title = " - ".join(p.strip() for p in parts[2:])

    return ParsedFilename(
        path=path,
        filename_with_ext=filename_with_ext,
        filename=filename_with_ext,  # VBA "full filename w/o path" includes extension
        pdf_title=pdf_title,
        authors=authors,
        year=year,
    )


def pdf_id_from_filename(full_path: str) -> str:
    """
    Convenience: return the '(Authors Year)' id from a file path.
    """
    return parse_filename(full_path).pdf_id


# -----------------------------------------------------------------------------
# Id validation
# -----------------------------------------------------------------------------

# "(Authors Year)": one or more author names joined by "+", then a single space,
# then the year. Author names may contain internal spaces, so the space before
# the year is the LAST space in the id -- anchoring the year at the end is what
# makes that unambiguous. Parentheses are excluded inside the id (AUDIT.md P4).
_PDF_ID_RE = re.compile(r"^\((?P<authors>[^()\s](?:[^()]*[^()\s])?) (?P<year>\d{4}[a-z]?)\)$")


def is_valid_pdf_id(pdf_id: str) -> bool:
    """
    Is this a well-formed new-system PDF id, i.e. "(Authors Year)"?

    Single definition of id validity, shared by the PDF-side gate
    (pdf_registry.is_controlled_pdf_name) and the notes-side gate
    (notes_db.is_controlled_md_name) so that the two cannot drift apart
    (AUDIT.md A5, findings F9 and F17).

    The year is the discriminator between old-system and new-system ids. An old
    id such as "(Smilek2011)" parses as an author named "Smilek2011" with no
    year, which hashes to a different identity and so silently becomes a
    different work.

    Rules:
      - one or more author names joined by "+", then one space, then the year
      - the year is four digits with an optional lowercase disambiguation letter
      - author names may contain internal spaces: "De Preester", "Van De Vijver"
        and "Anyen Rinpoche" are single surnames, not two authors
      - no padding around "+", and no parentheses inside the id

    Examples:
      - (Fink 2012)                         -> valid
      - (Das 2000b)                         -> valid
      - (De Preester+Van De Vijver 2005)    -> valid (spaces inside surnames)
      - (Gollwitzer-Schwarz+Sheeran 2006b)  -> valid
      - (Smilek2011)                        -> not valid (no space before the year)
      - (OnlyAuthors)                       -> not valid (no year)
      - (Guenther 1984A)                    -> not valid (uppercase letter)
      - (Fink  2012)                        -> not valid (two spaces)
      - (Deroche + Sheehy 2022)             -> not valid (padding around "+")

    This validates only; it never repairs. parse_filename stays deliberately
    permissive so that rejected names can still be described in diagnostics.
    """
    m = _PDF_ID_RE.match(pdf_id)
    if not m:
        return False
    # Each "+"-joined segment must be a non-empty name with no padding.
    return all(name and name == name.strip() for name in m.group("authors").split("+"))


# -----------------------------------------------------------------------------
# File I/O
# -----------------------------------------------------------------------------


def atomic_write_file(path: Path | str, new_text: str) -> None:
    """
    Atomically write new_text to path.
    Writes to temp file in same dir, fsyncs, and replaces.

    The replace is what makes the write atomic: a reader sees either the old
    file or the new one, never a half-written one. The directory fsync is what
    makes the replace survive a power loss.
    """
    target = os.fspath(path)
    dirpath = os.path.dirname(target)
    fd, tmppath = tempfile.mkstemp(prefix=".tmp-", suffix=".md", dir=dirpath, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as tmpf:
            tmpf.write(new_text)
            tmpf.flush()
            os.fsync(tmpf.fileno())
        # Also fsync the directory to persist the rename on some filesystems
        os.replace(tmppath, target)
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
