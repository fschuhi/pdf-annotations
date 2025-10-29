# src/pdf_annot/ndjson_to_md_block.py
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Iterable, List, Optional

# Converts streamlined NDJSON annotations to Obsidian-compatible markdown blocks.
# It exposes pure functions for converting streamlined annotation objects to
# an Obsidian-friendly markdown block. No CLI code here.

PDF_DATE_RE = re.compile(
    r"""
    ^D:
    (?P<year>\d{4})
    (?P<month>\d{2})
    (?P<day>\d{2})
    (?P<hour>\d{2})
    (?P<minute>\d{2})
    (?P<second>\d{2})
    (?:
        (?P<tzsign>[+\-Z])
        (?:
            (?P<tzhour>\d{2})
            '?
            (?P<tzmin>\d{2})?
            '?
        )?
    )?
    $
    """,
    re.VERBOSE,
)

DEFAULT_INFO_TEXT = "below the automatically generated annotations from the PDF"


@dataclass
class Annot:
    highlightText: str
    commentText: str
    header: str
    pageNum: int
    author: str
    creationDate: Optional[str]
    modDate: Optional[str]


def read_streamlined_objects(objs: Iterable[dict]) -> Iterable[Annot]:
    """
    Convert a sequence of streamlined dict objects into Annot instances.
    Each dict is expected to have keys:
      - highlightText, commentText, header, pageNum, author, creationDate, modDate
    """
    for obj in objs:
        yield Annot(
            highlightText=obj.get("highlightText", ""),
            commentText=obj.get("commentText", ""),
            header=obj.get("header", ""),
            pageNum=int(obj.get("pageNum", 0)),
            author=obj.get("author", "") or "",
            creationDate=obj.get("creationDate"),
            modDate=obj.get("modDate"),
        )


def parse_pdf_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    m = PDF_DATE_RE.match(s)
    if not m:
        return None
    year = int(m.group("year"))
    month = int(m.group("month"))
    day = int(m.group("day"))
    hour = int(m.group("hour"))
    minute = int(m.group("minute"))
    second = int(m.group("second"))

    tzsign = m.group("tzsign")
    tzhour = m.group("tzhour")
    tzmin = m.group("tzmin")
    if tzsign is None or tzsign == "Z":
        return datetime(year, month, day, hour, minute, second)
    else:
        off_hours = int(tzhour or "0")
        off_mins = int(tzmin or "0")
        offset = timedelta(hours=off_hours, minutes=off_mins)
        if tzsign == "-":
            offset = -offset
        tz = timezone(offset)
        dt = datetime(year, month, day, hour, minute, second, tzinfo=tz)
        return dt.astimezone()


def fmt_date_span(mod: Optional[str], cre: Optional[str]) -> str:
    dt = parse_pdf_date(mod) or parse_pdf_date(cre)
    if not dt:
        return ""
    return f'<span class="pdf-annot-date">{dt.strftime("%d.%m.%y %H:%M")}</span>'


def flatten_newlines(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def split_comment_lines(s: str) -> List[str]:
    s = s.strip()
    if not s:
        return []
    return re.split(r"\r\n|\n|\r", s)


def render_block(annots: Iterable[dict] | Iterable[Annot], pdf_id_hash: str, info_text: str = DEFAULT_INFO_TEXT) -> str:
    """
    Render an Obsidian annotation block from streamlined annotations.

    Inputs:
      - annots: either iterable of dicts with the streamlined schema or Annot objects.
      - pdf_id_hash: 7-letter hash used in pdf:// links (e.g., VQGPEHE).
      - info_text: the text placed inside <span class="pdf-annot-info">…</span>
                   Keep default to preserve exact formatting used in tests.

    Output:
      - A markdown string starting with:
          <hr class="pdf-annot-sep">
          <blank line>
          <span class="pdf-annot-info">…</span>
          <blank line>
        Followed by headings or quote blocks with optional [!note] sections.
    """
    # Normalize to Annot objects if dicts were provided
    if annots and isinstance(next(iter(annots)), dict):  # type: ignore[arg-type]
        ann_seq = list(read_streamlined_objects(annots))  # type: ignore[arg-type]
    else:
        ann_seq = list(annots)  # type: ignore[assignment]

    out: List[str] = []
    out.append('<hr class="pdf-annot-sep">')
    out.append("")
    out.append(f'<span class="pdf-annot-info">{info_text}</span>')
    out.append("")

    for a in ann_seq:
        header = getattr(a, "header", "") or ""
        if header and header.upper().startswith("H"):
            try:
                level = int(header[1:])
            except (ValueError, IndexError):
                level = 2
            hashes = "#" * max(1, min(level, 6))
            out.append(f"{hashes} {flatten_newlines(a.highlightText)}")
            out.append("")
            continue

        date_span = fmt_date_span(getattr(a, "modDate", None), getattr(a, "creationDate", None))
        page = int(getattr(a, "pageNum", 0)) + 1
        link = f"[1](pdf://{pdf_id_hash}?page={page})"

        hl_text = flatten_newlines(getattr(a, "highlightText", ""))
        if date_span:
            line = f"> {hl_text} {date_span} {link}"
        else:
            line = f"> {hl_text} {link}"
        out.append(line)

        comment_text = getattr(a, "commentText", "") or ""
        comment_lines = split_comment_lines(comment_text)
        if comment_lines:
            out.append("")
            if date_span:
                out.append(f"> [!note] {date_span}")
            else:
                out.append("> [!note]")
            for cl in comment_lines:
                out.append(f"> {cl}")

        out.append("")

    if out and out[-1] == "":
        out.pop()

    return "\n".join(out)
