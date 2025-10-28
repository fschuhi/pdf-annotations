# pdf_annot

Small toolkit to extract and streamline PDF highlight annotations using PyMuPDF, plus utilities to keep note front matter in sync with your PDFs.

## Features
- Extract annotations from PDFs into newline-delimited JSON (NDJSON).
- Streamline annotations: keep highlights, merge adjacent “link” notes, extract headings, and emit compact NDJSON.
- Maintain a lightweight NotesDB over Markdown notes named like `(Author Year).md`.
- Plan and apply front matter updates (e.g., pdf_title, pdf_size) to notes based on a PDF registry/database.
- Safe, atomic writes and optional dry-run to preview changes.

## Quick start (macOS/Linux)
Prerequisites: Python 3.13+

```bash
# 1) Clone and enter the project
git clone https://github.com/fschuhi/pdf-annotations
cd pdf-annotations

# 2) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3) Install in editable mode with dependencies
pip install -r requirements.txt

Tip: for developing the package, you can also install in editable mode:
pip install -e .

# 4) Run tests (optional)
pytest -q

# 5) Use the CLIs
# Extraction and streamline (provided by the package when installed)
pdf-annot-extract -p tests/fixtures/test1.pdf
pdf-annot-streamline -i tests/fixtures/test1.ndjson -o /tmp/final_streamlined.ndjson

# Local repo tools (no install needed)
# Note: these run from the repo root; they manage sys.path for src/
python tools/discover_pdfs.py --env tests/fixtures/env/test_pdf_annot.toml --relative-to .
```

## Command-line tools
### pdf-annot-extract

Reads a PDF and writes annotations to an NDJSON file (one JSON object per line), next to the PDF.

Options:
--header-height (default 60.0)
--footer-height (default 50.0)

### pdf-annot-streamline

- Reads NDJSON produced by extraction.
- Keeps only highlight annotations (annotType 8).
- Merges “link” notes into the previous highlight with hyphenation handling.
- Extracts headers (H1–H6).
- Writes a compact NDJSON suitable for downstream processing.

## Library overview
### src/pdf_annot/env.py
- load_env(path=None): loads configuration from a TOML file.
- Paths: notes_root, pdf_dirs (list of directories to scan), optional backup_dir.
- Front matter field names are configurable via [frontmatter]:
  - title_field (default "pdf_title")
  - size_field (default "pdf_size")
  - has_annots_field (default "has_annotations")
  - last_run_field (default "last_run_at")

### src/pdf_annot/pdf_discovery.py
- discover_pdfs(env): returns a list of PDF paths found under env.paths.pdf_dirs.
- iter_pdfs_in_dirs(dirs): generator to stream PDFs from directories.

### tools/discover_pdfs.py
- Small CLI to print discovered PDFs:
  - python tools/discover_pdfs.py --env path/to/pdf_annot.toml --relative-to .

### src/pdf_annot/notes_db.py
- NotesDB: small, mapping-like index of Markdown notes named exactly (ID).md, where ID is typically a normalized PDF identifier such as Author Year. Keys are case-insensitive.
- NoteInfo: metadata for each note (path, mtime, size, front matter, body).
- DuplicateNoteIdError: raised if multiple notes share the same ID (case-insensitive).
- Planning utilities to compare notes with a PDF registry and propose front matter updates.
- Atomic apply step to update front matter safely (with dry-run support).
- Convenience: NotesDB.from_env(env) builds the index using env.paths.notes_root.

### src/pdf_annot/frontmatter.py
- parse_note(text): parses a Markdown note into front matter (dict) and body.
- upsert_fields(text, fields): inserts or updates YAML front matter fields; returns (changed: bool, new_text: str).

### src/pdf_annot/pdf_registry.py (shape assumed by tests; your implementation may differ)
- Exposes per-PDF records with at least:
  - pdf_id (normalized identifier)
  - title_from_filename (or equivalent title)
  - size (bytes)
- NotesDB planning is duck-typed and can be adapted to your structure.

## Keeping note front matter in sync
You can drive front matter updates from:
- a PDF registry/database you maintain (e.g., CSV/DB mapping), or
- on-the-fly discovery (see pdf_discovery) combined with extracted metadata.

The planning utilities are duck-typed and work with any object/mapping that exposes the needed attributes (e.g., id/title/size), and the actual front matter key names are read from Env.frontmatter.

### Workflow:

1. Build a NotesDB from your vault directory containing notes named like (Keating 1995).md:
- Only exact names (Something).md are included.
- Variants like (Keating 1995) v2.md are ignored.

2. Prepare a PDF registry/database (any mapping or objects with pdf_id, title_from_filename, and size fields). Your own attributes can be configured.

3. Plan updates:
- Compare note front matter with the PDF registry.
- Produce a list of “plans” (proposed changes) plus a summary of missing notes and orphans.

4. Apply updates:
- Run once with dry_run=True to preview what would change.
- Run with dry_run=False to write changes atomically to disk.

### Key concepts:
- Plan: a proposed change for a specific note file (which fields to set and their desired values).
- Missing notes: PDFs in your registry that don’t have a corresponding note.
- Orphan notes: Notes that don’t have a corresponding PDF in your registry.
- Dry run: preview mode that computes changes but does not write files.

## Example (Python)
```python
from pdf_annot.notes_db import NotesDB

# 1) Build the notes index
notes = NotesDB.build("/path/to/your/vault")

# 2) Your PDF registry (any mapping or objects with attributes/keys)
class PdfInfo:
    def __init__(self, pdf_id, title_from_filename, size):
        self.pdf_id = pdf_id
        self.title_from_filename = title_from_filename
        self.size = size

pdfs = {
    "keating 1995": PdfInfo("Keating 1995", "Open Mind, Open Heart", 123456),
    "das 2000b":    PdfInfo("Das 2000b", "Some Book", 234567),
}

# 3) Plan front matter updates
plan_summary = notes.plan_frontmatter_updates(pdfs)
plans = plan_summary.plans

print("Would update:", [p.note_path for p in plans])
print("Missing notes (in PDFs but not notes):", plan_summary.missing_notes)
print("Orphan notes (in notes but not PDFs):", plan_summary.orphan_notes)

# 4) Apply with a dry run to preview
preview = notes.apply_frontmatter_updates(plans, dry_run=True)
print("Dry-run updates:", preview.updated)

# 5) Apply for real
result = notes.apply_frontmatter_updates(plans, dry_run=False)
print("Updated:", result.updated)
print("Errors:", result.errors)
```

## Project layout
- src/pdf_annot/: library code and CLI entry points
- tests/: unit, integration, and end-to-end tests
- requirements.txt: dependencies (project installed in editable mode with -e .)
- pyproject.toml: packaging and console scripts

## Troubleshooting
### Local imports during development
If you run short Python snippets directly (without installing the package), set PYTHONPATH:
```bash
PYTHONPATH=src python -c "import pdf_annot; print(pdf_annot.__package__)"
```

### Recreate environment
```bash
rm -rf .venv .pytest_cache
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
find . -name "*.egg-info" -type d -prune -exec rm -rf {} +
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Check installation
```bash
python - <<'PY'
import sys, fitz, pdf_annot
print("PyMuPDF:", (fitz.__doc__ or "").splitlines()[0] if fitz.__doc__ else "import ok")
print("pkg:", pdf_annot.__file__)
print("python:", sys.executable)
PY
```
