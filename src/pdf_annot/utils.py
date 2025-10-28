# src/pdf_annot/utils.py
from __future__ import annotations

import os
import re
import zlib
from dataclasses import dataclass
from typing import List, Optional, Tuple

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
    crc = zlib.crc32(data) & 0xFFFFFFFF

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
