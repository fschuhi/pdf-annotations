#!/usr/bin/env python3
import sys
import json
import argparse
import re
from typing import Optional, TextIO, Dict, Any, List

WS_RE = re.compile(r"\s+")
HEADING_RE = re.compile(r"^[Hh]([1-6])$")


def normalize_text(s: Optional[str]) -> str:
    if s is None:
        return ""
    return WS_RE.sub(" ", str(s)).strip()


def is_link(content_norm: str) -> bool:
    return content_norm.lower() == "link"


def extract_heading_label(content_norm: str) -> Optional[str]:
    m = HEADING_RE.match(content_norm)
    if not m:
        return None
    return f"H{m.group(1)}"


def make_output_obj(
    highlight_text: str,
    comment_text: str,
    header: str,
    page_num: int,
    author: str,
    creation_date: str,
    mod_date: str,
) -> Dict[str, Any]:
    return {
        "highlightText": highlight_text,
        "commentText": comment_text,
        "header": header,
        "pageNum": page_num,
        "author": author or "",
        "creationDate": creation_date or "",
        "modDate": mod_date or "",
    }


def merge_highlight_with_link(left_text: str, right_text: str) -> str:
    """
    Merge pending highlight (left_text) with link text (right_text).

    Hyphenation rule:
    - If left ends with a hyphen (ignoring trailing spaces), treat as hyphenated line break:
      * remove the hyphen and trailing spaces from left;
      * right: trim leading spaces, take the first token and join directly to left (no space);
      * if the remainder is only whitespace plus a single token (e.g., " C"), also join that token
        directly (no space) so "B" + " C" -> "BC";
      * otherwise, append the remainder with a single space.
    Otherwise:
    - Join left and right with a single space.

    Finally collapse whitespace.
    """
    left_rstrip = left_text.rstrip()
    if left_rstrip.endswith("-"):
        left_clean = left_rstrip[:-1]

        r = right_text.lstrip()
        m = re.match(r"(\S+)(.*)", r)
        if m:
            first = m.group(1)
            remainder = m.group(2)  # may contain leading spaces and more content

            # Base merged after hyphen join: no space
            merged_core = f"{left_clean}{first}"

            # If remainder is only whitespace or whitespace + one token, join without space
            # Example remainder: " C" -> join to get "ABC"
            # If remainder has further non-space after that token, keep a space before remainder
            rem = remainder
            if rem.strip() == "":
                merged = merged_core
            else:
                m2 = re.match(r"\s*(\S+)\s*$", rem)
                if m2:
                    # Only one trailing token after whitespace -> treat as continuation, no space
                    merged = f"{merged_core}{m2.group(1)}"
                else:
                    # Complex remainder: keep a single space before the remainder
                    merged = f"{merged_core} {rem}"
        else:
            merged = left_clean
    else:
        merged = f"{left_text} {right_text}"

    return normalize_text(merged)


def process_objects(objs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    pending: Optional[Dict[str, Any]] = None
    prev_was_link = False

    def flush():
        nonlocal pending
        if pending is not None:
            out.append(pending)
            pending = None

    for obj in objs:
        annot_type = obj.get("annotType")
        keep = isinstance(annot_type, list) and annot_type and isinstance(annot_type[0], int) and annot_type[0] == 8
        if not keep:
            prev_was_link = False
            continue

        info = obj.get("info") or {}

        extracted_text_norm = normalize_text(info.get("extractedText"))
        content_norm = normalize_text(info.get("content"))
        title = normalize_text(info.get("title"))
        creation_date = normalize_text(info.get("creationDate"))
        mod_date = normalize_text(info.get("modDate"))

        page_num = obj.get("pageNum")
        if not isinstance(page_num, int):
            try:
                page_num = int(page_num)
            except Exception:
                page_num = 0

        if is_link(content_norm):
            if prev_was_link:
                continue

            if pending is not None:
                if not extracted_text_norm:
                    prev_was_link = True
                    continue
                pending["highlightText"] = merge_highlight_with_link(pending["highlightText"], extracted_text_norm)
                prev_was_link = True
                continue

            pending = make_output_obj(
                highlight_text=extracted_text_norm,
                comment_text="",
                header="",
                page_num=page_num,
                author=title,
                creation_date=creation_date,
                mod_date=mod_date,
            )
            prev_was_link = True
            continue

        # Non-link: first flush previous pending, then set new pending
        flush()

        header = extract_heading_label(content_norm)
        if header is not None:
            comment_text = ""
        else:
            header = ""
            comment_text = content_norm

        pending = make_output_obj(
            highlight_text=extracted_text_norm,
            comment_text=comment_text,
            header=header,
            page_num=page_num,
            author=title,
            creation_date=creation_date,
            mod_date=mod_date,
        )
        prev_was_link = False

    flush()
    return out


def compact_json(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def process_stream(instream: TextIO, outstream: TextIO) -> int:
    pending: Optional[Dict[str, Any]] = None
    prev_was_link: bool = False
    line_no = 0

    def flush_pending(p: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if p is not None:
            outstream.write(compact_json(p) + "\n")
        return None

    for raw_line in instream:
        line_no += 1
        raw_line = raw_line.rstrip("\n")
        if not raw_line.strip():
            continue

        try:
            obj = json.loads(raw_line)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"Error: malformed JSON on line {line_no}: {e}\n")
            return 1

        annot_type = obj.get("annotType")
        keep = isinstance(annot_type, list) and annot_type and isinstance(annot_type[0], int) and annot_type[0] == 8
        if not keep:
            prev_was_link = False
            continue

        info = obj.get("info") or {}

        extracted_text_norm = normalize_text(info.get("extractedText"))
        content_norm = normalize_text(info.get("content"))
        title = normalize_text(info.get("title"))
        creation_date = normalize_text(info.get("creationDate"))
        mod_date = normalize_text(info.get("modDate"))

        page_num = obj.get("pageNum")
        if not isinstance(page_num, int):
            try:
                page_num = int(page_num)
            except Exception:
                page_num = 0

        if is_link(content_norm):
            if prev_was_link:
                continue

            if pending is not None:
                if not extracted_text_norm:
                    prev_was_link = True
                    continue
                pending["highlightText"] = merge_highlight_with_link(pending["highlightText"], extracted_text_norm)
                prev_was_link = True
                continue

            pending = make_output_obj(
                highlight_text=extracted_text_norm,
                comment_text="",
                header="",
                page_num=page_num,
                author=title,
                creation_date=creation_date,
                mod_date=mod_date,
            )
            prev_was_link = True
            continue

        # Non-link: flush previous pending first
        pending = flush_pending(pending)

        header = extract_heading_label(content_norm)
        if header is not None:
            comment_text = ""
        else:
            header = ""
            comment_text = content_norm

        pending = make_output_obj(
            highlight_text=extracted_text_norm,
            comment_text=comment_text,
            header=header,
            page_num=page_num,
            author=title,
            creation_date=creation_date,
            mod_date=mod_date,
        )
        prev_was_link = False

    pending = flush_pending(pending)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compact PDF annotation NDJSON (annotType=8) with proper link merging and buffering."
    )
    parser.add_argument("--input", "-i", help="Path to input NDJSON (defaults to stdin).")
    parser.add_argument("--output", "-o", help="Path to output NDJSON (defaults to stdout).")
    args = parser.parse_args(argv)

    if args.input:
        try:
            instream = open(args.input, "r", encoding="utf-8")
        except OSError as e:
            sys.stderr.write(f"Error: cannot open input file '{args.input}': {e}\n")
            return 1
    else:
        instream = sys.stdin

    if args.output:
        try:
            outstream = open(args.output, "w", encoding="utf-8", newline="\n")
        except OSError as e:
            if args.input:
                instream.close()
            sys.stderr.write(f"Error: cannot open output file '{args.output}': {e}\n")
            return 1
    else:
        outstream = sys.stdout

    try:
        rc = process_stream(instream, outstream)
    finally:
        if args.input and instream is not sys.stdin:
            instream.close()
        if args.output and outstream is not sys.stdout:
            outstream.flush()
            outstream.close()

    return rc


if __name__ == "__main__":
    sys.exit(main())
