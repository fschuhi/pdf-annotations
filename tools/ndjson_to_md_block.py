#!/usr/bin/env python3
# tools/ndjson_to_md_block.py
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Iterable, List, Optional

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


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert streamlined NDJSON to Obsidian annotation markdown block.")
    p.add_argument("--pdf-id", required=True, help="7-letter document hash to embed in pdf:// links, e.g., DZWIIEZ")
    p.add_argument("--in", dest="infile", default="-", help="Input NDJSON file path or '-' for stdin")
    p.add_argument(
        "--info-text",
        dest="info_text",
        default=DEFAULT_INFO_TEXT,
        help='Text to put inside <span class="pdf-annot-info">…</span> (default keeps current behavior).',
    )
    return p.parse_args(argv)


def read_ndjson(stream: io.TextIOBase) -> Iterable[Annot]:
    for line_no, line in enumerate(stream, 1):
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON at line {line_no}: {e}") from e
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


def render_block(annots: Iterable[Annot], pdf_id: str, info_text: str = DEFAULT_INFO_TEXT) -> str:
    out: List[str] = []
    out.append('<hr class="pdf-annot-sep">')
    out.append("")
    # Only change: use configurable info_text here. No escaping added to preserve exact behavior.
    out.append(f'<span class="pdf-annot-info">{info_text}</span>')
    out.append("")

    for a in annots:
        if a.header and a.header.upper().startswith("H"):
            try:
                level = int(a.header[1:])
            except (ValueError, IndexError):
                level = 2
            hashes = "#" * max(1, min(level, 6))
            out.append(f"{hashes} {flatten_newlines(a.highlightText)}")
            out.append("")
            continue

        date_span = fmt_date_span(a.modDate, a.creationDate)
        page = a.pageNum + 1
        link = f"[1](pdf://{pdf_id}?page={page})"

        hl_text = flatten_newlines(a.highlightText)
        if date_span:
            line = f"> {hl_text} {date_span} {link}"
        else:
            line = f"> {hl_text} {link}"
        out.append(line)

        comment_lines = split_comment_lines(a.commentText)
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


def main(argv: Optional[List[str]] = None) -> int:
    ns = parse_args(argv)
    if ns.infile == "-" or ns.infile is None:
        stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
        close_stream = False
    else:
        stream = open(ns.infile, "r", encoding="utf-8")
        close_stream = True
    try:
        annots = list(read_ndjson(stream))
    finally:
        if close_stream:
            stream.close()

    md = render_block(annots, ns.pdf_id, info_text=ns.info_text)
    sys.stdout.write(md + ("\n" if not md.endswith("\n") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
