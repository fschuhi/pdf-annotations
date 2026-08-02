# src/pdf_annot/synopsis.py
"""
Synopsis formatting for PDF bibnotes.

Turns the raw text of a <pdf_id>.txt synopsis file (as written by
isbndb_synopsis.py) into an Obsidian `>[!abstract]` callout block, ready to
be inserted into a bibnote's body via notes.ensure_synopsis_block().
Deliberately separate from notes.py: this module only knows how to turn
text into a callout string, with no notion of bibnotes, markers, or where
in a note's body anything goes -- notes.py owns that, same division of
labor as thumbnails.py/notes.py for the thumbnail span.
"""
from __future__ import annotations

import re
from pathlib import Path

# The callout's opening line. "(ISBNdb.com)" identifies the source, since
# every synopsis handled by this pipeline currently comes from ISBNdb via
# isbndb_synopsis.py -- if a second source is ever added, this is the one
# line that would need to vary per source. notes.py imports this same
# constant to detect an existing synopsis block case-insensitively,
# including the one pre-existing hand-written one in the corpus,
# (Thrangu 2003).
SYNOPSIS_HEADER = ">[!abstract] Synopsis (ISBNdb.com)"

# Matches one or more consecutive break-like tags -- <br>, <br/>, <hr>,
# <hr/>, any case, with or without the trailing slash -- collapsing a run
# of any length down to a single logical break.
_BREAK_TAG_RUN = re.compile(r"(?:<\s*/?\s*(?:br|hr)\s*/?\s*>)+", re.IGNORECASE)


def synopsis_path_for(pdf_id: str, synopses_dir: Path) -> Path:
    """
    Return the synopsis .txt path for a given pdf_id, without touching disk.

    Naming rule: same pdf_id as the bibnote, e.g. "(Johnson 2017a)" ->
    "(Johnson 2017a).txt" -- mirrors thumbnails.thumbnail_path_for. Pure
    and side-effect free; callers decide themselves whether/how to read it,
    including treating a zero-length file as "no synopsis available", per
    isbndb_synopsis.py's convention.
    """
    return synopses_dir / f"{pdf_id}.txt"


def format_synopsis_callout(raw_text: str) -> str:
    """
    Turn raw synopsis text into a rendered `>[!abstract]` callout block.

    Pipeline:
      1. Split into lines, strip each line, drop every line that's empty
         after stripping (wherever it occurs, not just at the edges) --
         a blank line is deleted, not treated as a paragraph separator in
         its own right.
      2. Rejoin the surviving lines with "\\n".
      3. Collapse any run of break-like tags (<br/>, <br>, <hr/>, <hr>, any
         case) into a single "<br/>".
      4. Replace every "<br/>" with "\\n" -- this is what actually creates
         paragraph breaks.
      5. Strip the whole result once more, in case a break tag sat right at
         the very start or end.
      6. Render: each surviving line becomes "> {line}"; every line except
         the last is followed by a bare ">" (a blank callout-continuation
         line), so Obsidian's lazy-continuation keeps the whole thing one
         callout block. Joined with "\\n", header line first.

    Assumes raw_text is non-empty synopsis content -- callers are expected
    to have already skipped zero-length synopsis files (see `haddolib`,
    `resolve_row` in `isbndb_synopsis.py`) before ever calling this;
    passing "" through produces a callout with one blank paragraph line,
    which is a caller bug, not something this function guards against.

    Does not touch the filesystem or know about pdf_ids -- callers read the
    raw .txt themselves (see isbndb_synopsis.py's utf-8-sig / utf-8
    encoding convention) and pass the decoded text in.
    """
    lines = [line.strip() for line in raw_text.split("\n")]
    lines = [line for line in lines if line]
    joined = "\n".join(lines)

    joined = _BREAK_TAG_RUN.sub("<br/>", joined)
    joined = joined.replace("<br/>", "\n")
    joined = joined.strip()

    paragraphs = joined.split("\n")
    rendered = []
    for i, paragraph in enumerate(paragraphs):
        rendered.append(f"> {paragraph}")
        if i != len(paragraphs) - 1:
            rendered.append(">")
    return SYNOPSIS_HEADER + "\n" + "\n".join(rendered)
