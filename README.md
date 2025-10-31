# pdf_annot

Toolkit to extract and streamline PDF highlight annotations using PyMuPDF, with utilities to automatically keep Obsidian note frontmatter and annotation blocks in sync with your PDFs.

## Features
- Extract annotations from PDFs into newline-delimited JSON (NDJSON)
- Streamline annotations: merge adjacent "link" notes with hyphenation handling, extract headings
- Maintain a lightweight NotesDB over Markdown notes named like `(Author Year).md`
- Automatically update note frontmatter (pdf_title, pdf_size, pdf_mtime, etc.) when PDFs change
- Automatically update annotation blocks in notes when PDF annotations change
- Safe, atomic writes with optional dry-run preview
- Comprehensive end-to-end testing with fixtures

## Quick start (macOS/Linux)
Prerequisites: Python 3.11+

```bash
# 1) Clone and enter the project
git clone https://github.com/fschuhi/pdf-annotations
cd pdf-annotations

# 2) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# For development, install in editable mode:
pip install -e .

# 4) Run tests
pytest -q

# 5) Use the CLIs
pdf-annot-extract -p tests/fixtures/test1.pdf
pdf-annot-streamline -i tests/fixtures/test1.ndjson -o /tmp/streamlined.ndjson
```

## Architecture overview

### Core workflow: PDF → Note synchronization

When a PDF's annotations change, the workflow automatically:
1. **Detects changes** by comparing PDF mtime/size with note frontmatter
2. **Extracts annotations** from the PDF using PyMuPDF
3. **Streamlines** them (merges links, handles hyphenation)
4. **Renders markdown** annotation blocks
5. **Updates notes atomically** (frontmatter + annotation block)

This workflow is tested end-to-end in `tests/test_single_pdf_explicit_assertions.py`.

### Library modules

#### `src/pdf_annot/env.py`
Configuration management via TOML files.

```python
from pdf_annot.env import load_env

env = load_env("pdf_annot.toml")
# env.paths.notes_root, env.paths.pdf_dirs, env.paths.backup_dir, env.paths.temp_dir
# env.frontmatter.title_field, size_field, has_annots_field, last_run_field
# env.io.atomic_writes, create_missing_dirs
```

**Configuration structure:**
```toml
[paths]
notes_root = "./vault"
pdf_dirs = ["./pdfs"]
backup_dir = "./backups"  # optional
temp_dir = "./tmp"        # optional (for tests)

[frontmatter]
title_field = "pdf_title"
size_field = "pdf_size"
has_annots_field = "has_annotations"
last_run_field = "last_run_at"

[io]
atomic_writes = true
create_missing_dirs = true
```

#### `src/pdf_annot/extract.py`
PDF annotation extraction with header/footer awareness and column detection.

**Library API:**
```python
from pdf_annot.extract import extract_annotations_to_list

# Returns sorted list of annotation dicts in visual reading order
annotations = extract_annotations_to_list(
    pdf_path,
    header_height=60.0,  # skip annotations in header
    footer_height=50.0   # skip annotations in footer
)
```

**CLI:**
```bash
pdf-annot-extract -p document.pdf --header-height 60 --footer-height 50
# Creates document.ndjson with raw annotations
```

#### `src/pdf_annot/streamline_annotations.py`
Post-processes raw annotations: keeps highlights, merges link annotations, extracts headings.

**Library API:**
```python
from pdf_annot.streamline_annotations import streamline_annotations_list

streamlined = streamline_annotations_list(raw_annotations)
```

**CLI:**
```bash
pdf-annot-streamline -i raw.ndjson -o streamlined.ndjson
```

**Key features:**
- Merges "link" annotations into previous highlights
- Handles hyphenated line breaks intelligently
- Extracts H1-H6 headers from comment text
- Outputs compact NDJSON

#### `src/pdf_annot/frontmatter.py`
YAML frontmatter parsing and manipulation for Markdown notes.

```python
from pdf_annot.frontmatter import parse_note, upsert_fields, format_note

# Parse
parsed = parse_note(note_text)
# parsed.front_matter (dict), parsed.body (str), parsed.has_fm (bool)

# Update (returns (changed: bool, new_text: str))
changed, updated_text = upsert_fields(note_text, {
    "pdf_title": "New Title",
    "pdf_size": 123456,
    "pdf_mtime": "2025-10-30T20:00:00",
    "has_annotations": True,
    "last_run_at": "2025-10-30T20:01:00"
})

# Format (create note from scratch)
note_text = format_note({"key": "value"}, "Body content")
```

**Supported fields:** `pdf_id`, `pdf_title`, `pdf_size`, `pdf_hash`, `has_annotations`, `pdf_mtime`, `last_run_at`

#### `src/pdf_annot/notes.py`
Note-level operations for working with annotation blocks.

```python
from pdf_annot.notes import extract_info_text, replace_annotation_block

# Extract custom info text (preserves user edits)
info_text = extract_info_text(note_text)
# Returns text from <span class="pdf-annot-info">...</span>

# Replace annotation block
updated_note = replace_annotation_block(note_text, new_annotation_block)
# Replaces everything from <hr class="pdf-annot-sep"> onward
```

**Key feature:** Preserves custom info text that users may have edited, rather than overwriting with defaults.

#### `src/pdf_annot/ndjson_to_md_block.py`
Renders streamlined annotations as Obsidian-compatible markdown.

```python
from pdf_annot.ndjson_to_md_block import render_block

markdown = render_block(
    streamlined_annotations,
    pdf_id_hash="VQGPEHE",  # 7-letter hash for pdf:// links
    info_text="Custom info text"  # Optional, defaults provided
)
```

**Output structure:**
```markdown
<hr class="pdf-annot-sep">

<span class="pdf-annot-info">below the automatically generated annotations from the PDF</span>

## Section Header

> Highlighted text <span class="pdf-annot-date">21.10.25 21:20</span> [1](pdf://VQGPEHE?page=1)

> [!note] <span class="pdf-annot-date">21.10.25 21:20</span>
> Comment text here
```

#### `src/pdf_annot/notes_db.py`
Mapping-like index of Markdown notes with case-insensitive lookups.

```python
from pdf_annot.notes_db import NotesDB

# Build from directory
notes = NotesDB.build("/path/to/vault")

# Or from env
notes = NotesDB.from_env(env)

# Access notes (case-insensitive)
note_info = notes["keating 1995"]  # -> NoteInfo object

# Plan frontmatter updates
plan_summary = notes.plan_frontmatter_updates(pdf_registry)
# Returns: plans, missing_notes, orphan_notes

# Apply updates
result = notes.apply_frontmatter_updates(plans, dry_run=True)  # Preview
result = notes.apply_frontmatter_updates(plans, dry_run=False) # Apply
```

**Key features:**
- Only includes notes named exactly `(ID).md`
- Case-insensitive ID lookups
- Raises `DuplicateNoteIdError` if multiple notes have same ID
- Planning utilities to compare notes with PDF registry
- Atomic writes with dry-run support

#### `src/pdf_annot/pdf_registry.py`
PDF discovery and metadata indexing.

```python
from pdf_annot.pdf_registry import build_pdf_index, PdfInfo

# Build index from directories
pdf_index = build_pdf_index(["/path/to/pdfs"])

# Access by lowercase pdf_id
pdf_info: PdfInfo = pdf_index["(smith 2020)"]
# pdf_info.pdf_id, .pdf_hash, .pdf_title, .size, .mtime, .abs_path
```

**PdfInfo fields:**
- `pdf_id`: e.g., "(Das 2000b)"
- `pdf_hash`: 7-letter hash for pdf:// links
- `pdf_title`: filename without id and extension
- `size`: file size in bytes
- `mtime`: modification time (epoch seconds)
- `abs_path`: absolute path to PDF

#### `src/pdf_annot/pdf_discovery.py`
Lightweight PDF discovery utilities.

```python
from pdf_annot.pdf_discovery import discover_pdfs

pdfs = discover_pdfs(env)  # Returns List[Path]
```

## Complete workflow example

```python
from datetime import datetime
from pdf_annot.env import load_env
from pdf_annot.pdf_registry import build_pdf_index
from pdf_annot.frontmatter import parse_note, upsert_fields
from pdf_annot.extract import extract_annotations_to_list
from pdf_annot.streamline_annotations import streamline_annotations_list
from pdf_annot.ndjson_to_md_block import render_block
from pdf_annot.notes import extract_info_text, replace_annotation_block

# 1. Setup
env = load_env("pdf_annot.toml")
pdf_index = build_pdf_index(["/path/to/pdfs"])

# 2. Get PDF and note
pdf_info = pdf_index["(albini 2013)"]
note_path = env.paths.notes_root / "(Albini 2013).md"
note_text = note_path.read_text()

# 3. Check if update needed
parsed = parse_note(note_text)
pdf_mtime_iso = datetime.fromtimestamp(pdf_info.mtime).isoformat(timespec='seconds')

updates = {
    "pdf_title": pdf_info.pdf_title,
    "pdf_size": pdf_info.size,
    "pdf_mtime": pdf_mtime_iso,
    "has_annotations": True,
    "last_run_at": datetime.now().isoformat(timespec='seconds')
}

fm_changed, updated_fm_text = upsert_fields(note_text, updates)

if fm_changed:
    # 4. Extract and streamline annotations
    raw_annotations = extract_annotations_to_list(pdf_info.abs_path)
    streamlined = streamline_annotations_list(raw_annotations)

    # 5. Render markdown (preserving custom info text)
    info_text = extract_info_text(note_text)
    annotation_block = render_block(streamlined, pdf_info.pdf_hash, info_text)

    # 6. Update note atomically
    updated_note = replace_annotation_block(updated_fm_text, annotation_block)
    note_path.write_text(updated_note)
```

## Testing

### Test structure
```
tests/
├── fixtures/
│   ├── single_pdf_explicit_assertions/          # E2E test fixture
│   │   ├── seeds/              # Initial state
│   │   │   ├── (Albini 2013).md
│   │   │   └── (Albini 2013) On dealing....pdf
│   │   ├── goldens/            # Expected output
│   │   │   └── (Albini 2013).md
│   │   └── config.toml         # Test configuration
│   └── pdf_to_markdown_e2e/    # Another E2E fixture
├── tmp/                        # Generated during tests (gitignored)
├── test_single_pdf_explicit_assertions.py      # E2E workflow test
├── test_frontmatter.py         # Frontmatter unit tests
├── test_notes_db.py            # NotesDB unit tests
└── ...
```

### Running tests
```bash
pytest -q                        # Quick run
pytest -v                        # Verbose
pytest tests/test_single_pdf_explicit_assertions.py  # Single test
```

### Key test patterns

**E2E test workflow:**
1. Copy seeds → temp directory
2. Load env, build registries
3. Run complete workflow
4. Compare output with golden files
5. Leave temp files for debugging (gitignored)

**Fixture organization:**
- `seeds/`: Initial state (before workflow)
- `goldens/`: Expected state (after workflow)
- `config.toml`: Test-specific configuration pointing to temp dirs

## Command-line tools

### pdf-annot-extract
```bash
pdf-annot-extract -p document.pdf [--header-height 60] [--footer-height 50]
```
Creates `document.ndjson` with raw annotations next to the PDF.

### pdf-annot-streamline
```bash
pdf-annot-streamline -i raw.ndjson -o streamlined.ndjson
```
Processes raw annotations into streamlined format.

### tools/discover_pdfs.py
```bash
python tools/discover_pdfs.py --env pdf_annot.toml --relative-to .
```
Lists all discovered PDFs (useful for debugging).

## Project layout
```
pdf-annotations/
├── src/pdf_annot/              # Library code
│   ├── env.py                  # Configuration
│   ├── extract.py              # PDF extraction
│   ├── streamline_annotations.py  # Streamlining
│   ├── frontmatter.py          # YAML manipulation
│   ├── notes.py                # Note operations
│   ├── ndjson_to_md_block.py   # Markdown rendering
│   ├── notes_db.py             # Note indexing
│   ├── pdf_registry.py         # PDF indexing
│   └── pdf_discovery.py        # PDF discovery
├── tests/                      # Test suite
├── tools/                      # Dev utilities
├── requirements.txt            # Dependencies
├── pyproject.toml             # Package metadata
└── README.md                  # This file
```

## Development

### Setting up development environment
```bash
# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest -q
```

### Troubleshooting

**Import issues during development:**
```bash
# Set PYTHONPATH for direct script execution
PYTHONPATH=src python -c "import pdf_annot; print(pdf_annot.__file__)"
```

**Clean rebuild:**
```bash
rm -rf .venv .pytest_cache
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
find . -name "*.egg-info" -type d -prune -exec rm -rf {} +
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

**Verify installation:**
```bash
python - <<'PY'
import sys, fitz, pdf_annot
print("PyMuPDF:", fitz.__version__)
print("Package:", pdf_annot.__file__)
print("Python:", sys.executable)
PY
```

## Key concepts

### PDF ID and hash
- **pdf_id**: Normalized identifier like "(Das 2000b)" extracted from filename
- **pdf_hash**: 7-letter CRC32-based hash of lowercase pdf_id for pdf:// links

### Controlled PDFs
PDFs must follow naming convention: `(Author Year) Title.pdf`
- Example: `(Albini 2013) On dealing with destructive emotions.pdf`
- pdf_id: "(Albini 2013)"
- pdf_title: "On dealing with destructive emotions"

### Note structure
```markdown
---
pdf_id: "(Albini 2013)"
pdf_title: "On dealing with destructive emotions"
pdf_size: 91354
pdf_hash: "VQGPEHE"
has_annotations: true
pdf_mtime: "2025-10-21T21:37:00"
last_run_at: "2025-10-30T20:01:00"
---
<hr class="pdf-annot-sep">

<span class="pdf-annot-info">below the automatically generated annotations from the PDF</span>

## Section Header

> Highlight <span class="pdf-annot-date">21.10.25 21:20</span> [1](pdf://VQGPEHE?page=1)
```

### Annotation ordering
Annotations are sorted by visual reading order:
1. Page number (ascending)
2. Y-coordinate (top to bottom)
3. X-coordinate (left to right)

This ensures consistent, readable output regardless of PDF internal ordering.

### Info text preservation
The `<span class="pdf-annot-info">...</span>` text can be customized by users. The workflow preserves this custom text rather than overwriting with defaults.

## Future enhancements
- Additional edge case tests (missing frontmatter, manual edits between blocks)
- Batch processing CLI for multiple PDFs
- Web interface for viewing/managing annotations
- Integration with Obsidian plugins

## License
[Your license here]

## Contributing
Pull requests welcome! Please ensure tests pass before submitting.
