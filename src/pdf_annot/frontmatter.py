# src/pdf_annot/frontmatter.py
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Dict, List, Tuple

import yaml

YAML_START = "---"
YAML_END = "---"  # We use the same fence for end (common in Obsidian/MD)


@dataclass(frozen=True)
class ParsedNote:
    front_matter: Dict[str, object]
    body: str
    has_fm: bool
    # Raw slices for potential byte-stability when no changes are needed
    _head: str
    _fm_block: str
    _tail: str


def _split_front_matter(text: str) -> Tuple[bool, str, str, str]:
    """
    Return (has_fm, head, fm_block, tail)
    - head: content before front matter (usually '' if FM present)
    - fm_block: the raw text between fences (excluding fences themselves)
    - tail: the rest of the document after the closing fence
    If no front matter, has_fm=False and fm_block='', head='', tail=text.
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return False, "", "", ""
    if not lines[0].lstrip().startswith(YAML_START):
        # No FM; everything is body
        return False, "", "", text

    # Find closing fence
    # Front matter is at the very top per our convention; accept leading BOM/whitespace
    # closing fence must be on its own line (ignoring leading/trailing spaces)
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == YAML_END:
            end_idx = i
            break
    if end_idx is None:
        # Unclosed fence; treat as no FM to avoid destructive behavior
        return False, "", "", text

    head = "".join(lines[:1])
    fm_block = "".join(lines[1:end_idx])
    tail = "".join(lines[end_idx + 1 :])
    return True, head, fm_block, tail


def parse_note(text: str) -> ParsedNote:
    has_fm, head, fm_block, tail = _split_front_matter(text)
    if has_fm:
        try:
            # Safe YAML load; if fm is empty, get None -> convert to {}
            data = yaml.safe_load(fm_block)
            if data is None:
                data = {}
            elif not isinstance(data, dict):
                # If the YAML front matter is not a mapping, treat as empty mapping
                data = {}
        except yaml.YAMLError:
            # On YAML parse error, treat as if no FM to be conservative
            return ParsedNote(front_matter={}, body=text, has_fm=False, _head="", _fm_block="", _tail=text)
        return ParsedNote(front_matter=data, body=tail, has_fm=True, _head=head, _fm_block=fm_block, _tail=tail)
    else:
        return ParsedNote(front_matter={}, body=text, has_fm=False, _head="", _fm_block="", _tail=text)


def _dump_yaml_block(data: Dict[str, object]) -> str:
    """
    Produce a minimal YAML mapping (no document markers) with a trailing newline if non-empty.
    We use a deterministic style: block mapping, keys in the given order.
    """
    # Use a dumper that preserves insertion order (PyYAML 5.1+ preserves dict order)
    stream = io.StringIO()
    # default_flow_style=False -> block style
    # allow_unicode=True -> keep diacritics
    yaml.safe_dump(data, stream, default_flow_style=False, sort_keys=False, allow_unicode=True)
    out = stream.getvalue()
    # Ensure trailing newline for FM block (PyYAML includes it, but double-check)
    if out and not out.endswith("\n"):
        out += "\n"
    return out


def format_note(front_matter: Dict[str, object], body: str) -> str:
    """
    Combine YAML front matter and body into a full note.
    If front_matter is empty, we omit YAML fences and return just the body.
    """
    if not front_matter:
        return body
    fm_block = _dump_yaml_block(front_matter)
    return f"{YAML_START}\n{fm_block}{YAML_END}\n{body}"


def upsert_fields(text: str, updates: Dict[str, object]) -> Tuple[bool, str]:
    """
    Upsert PDF-related fields in the note's YAML front matter.
    - Only modifies the file if any target field changes or is added.
    - Targets: all PDF-related metadata fields
    Returns (changed, new_text).
    """
    # --- FIX: Add the new stats fields to the targets list ---
    targets = (
        "pdf_id",
        "pdf_title",
        "pdf_size",
        "pdf_hash",
        "has_annotations",
        "pdf_mtime",
        "last_run_at",
        "pdf_pages",
        "pdf_highlights",
        "pdf_textboxes",
    )

    parsed = parse_note(text)
    current = dict(parsed.front_matter)

    # Compute whether changes are needed
    need_change = False

    # --- FIX: Check all keys in 'updates', not just 'targets' ---
    # This is the real bug. We need to check every key we're trying to update.
    for key in updates:
        if key not in current or current.get(key) != updates[key]:
            need_change = True
            break

    if not need_change:
        # No modifications necessary; return original text byte-for-byte
        return False, text

    # We will rewrite a normalized FM block, preserving non-target keys in original order
    # Build ordered dict-like sequence:
    new_items: List[Tuple[str, object]] = []

    # First, targets (if provided), in stable order
    # This ensures our special keys are always at the top
    for key in targets:
        if key in updates:
            new_items.append((key, updates[key]))
        elif key in current:
            # If not provided in updates but currently present, keep existing value
            new_items.append((key, current[key]))

    # Then, all other keys in their existing order, skipping duplicates
    # This loop is to add any *new* keys from 'updates' that are not in 'targets'
    for k, v in updates.items():
        if k not in (t for t, _ in new_items):
            new_items.append((k, v))

    # This loop is to add any *old* keys from 'current' that are not in 'targets'
    for k, v in current.items():
        if k not in (t for t, _ in new_items):
            new_items.append((k, v))

    new_fm: Dict[str, object] = {}
    for k, v in new_items:
        new_fm[k] = v

    new_text = format_note(new_fm, parsed.body)
    return True, new_text
