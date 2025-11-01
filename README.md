# pdf_annot

Toolkit to extract and streamline PDF highlight annotations using PyMuPDF, with utilities to automatically keep Obsidian note frontmatter and annotation blocks in sync with your PDFs.

## Features
- **New:** Main CLI (`pdf-annot-sync`) to automatically sync all PDFs to notes.
- Extract annotations from PDFs into newline-delimited JSON (NDJSON)
- Streamline annotations: merge adjacent "link" notes with hyphenation handling, extract headings
- Maintain a lightweight NotesDB over Markdown notes named like `(Author Year).md`
- Automatically update note frontmatter (pdf_title, pdf_size, pdf_mtime, etc.) when PDFs change
- Automatically update annotation blocks in notes when PDF annotations change
- Safe, atomic writes with optional dry-run preview (planned)
- Comprehensive end-to-end testing with fixtures

## Quick start (macOS/Linux)
Prerequisites: Python 3.11+

```bash
# 1) Clone and enter the project
git clone https://github.com/fschuhi/pdf-annotations
cd pdf-annotations

# 2) Run the setup
# This creates a .venv, installs dependencies, and installs the project.
make setup

# 3) Activate the virtual environment
source .venv/bin/activate

# 4) Run tests
make test

# 5) Create a sandbox to run the main sync command
mkdir -p sandbox/notes
mkdir -p sandbox/pdfs
cp tests/fixtures/workflow_manual_edits/seeds/* ./sandbox/pdfs/
cp tests/fixtures/workflow_manual_edits/seeds/*.md ./sandbox/notes/
cp pdf_annot.example.toml pdf_annot.toml # Use the example config

# 6) Run the main sync workflow
# This will find pdf_annot.toml by default
# (Note: The default pdf_annot.toml points to ./sandbox)
pdf-annot-sync
```

## Architecture overview

### Core workflow: `pdf-annot-sync`

The main entry point is `pdf-annot-sync`, defined in `src/pdf_annot/sync.py`.
When run, it automatically:
1.  **Loads configuration** (e.g., `pdf_annot.toml`) to get `pdf_dirs` and `notes_root`.
2.  **Builds registries** for all PDFs (`PdfRegistry`) and all notes (`NotesDB`).
3.  **Loops over every PDF** and compares it to its corresponding note.
4.  **Detects changes** by comparing PDF mtime/size with note frontmatter.
5.  **Calls `sync_pdf_to_note`** for any new or changed PDFs. This function:
    * Extracts annotations from the PDF.
    * Streamlines them (merges links, handles hyphenation).
    * Renders the markdown annotation block.
    * Updates the note atomically (frontmatter + annotation block).

This workflow is tested end-to-end by library tests in `tests/test_core_workflow.py` and by a full CLI test in `tests/test_sync_cli.py`.

### Library modules

#### `src/pdf_annot/env.py`
Configuration management via TOML files.

```python
from pdf_annot.env import load_env

env = load_env("pdf_annot.toml")
# env.paths.notes_root, env.paths.pdf_dirs
# env.annotations.default_info_text
```

**Configuration structure:**
```toml
[paths]
notes_root = "./vault"
pdf_dirs = ["./pdfs"]
backup_dir = "./backups"  # optional
temp_dir = "./tmp"        # optional (for tests)

[annotations]
default_info_text = "below the automatically generated annotations from the PDF"

[frontmatter]
title_field = "pdf_title"
# ...
```

#### `src/pdf_annot/sync.py`
The core workflow logic and `main` CLI entry point.

**Library API:**
```python
from pdf_annot.sync import sync_pdf_to_note

# This is the core "god function"
result: UpdateResult = sync_pdf_to_note(
    env,
    pdf_info,
    note_path,
    current_time_iso
)
```

**CLI:**
```bash
pdf-annot-sync -c my_config.toml
```

#### `src/pdf_annot/extract.py`
PDF annotation extraction with header/footer awareness and column detection.

**Library API:**
`annotations = extract_annotations_to_list(pdf_path)`

**CLI:**
`pdf-annot-extract -p document.pdf`

#### `src/pdf_annot/streamline_annotations.py`
Post-processes raw annotations: keeps highlights, merges link annotations, extracts headings.

**Library API:**
`streamlined = streamline_annotations_list(raw_annotations)`

**CLI:**
`pdf-annot-streamline -i raw.ndjson -o streamlined.ndjson`

#### `src/pdf_annot/frontmatter.py`
YAML frontmatter parsing and manipulation for Markdown notes.

```python
from pdf_annot.frontmatter import parse_note, upsert_fields

# Parse
parsed = parse_note(note_text)
# parsed.front_matter (dict), parsed.body (str)

# Update (returns (changed: bool, new_text: str))
changed, updated_text = upsert_fields(note_text, {"pdf_title": "New"})
```

#### `src/pdf_annot/notes.py`
Note-level operations for working with annotation blocks.

```python
from pdf_annot.notes import extract_info_text, replace_annotation_block

# Extract custom info text (preserves user edits)
info_text = extract_info_text(note_text)

# Replace annotation block
updated_note = replace_annotation_block(note_text, new_annotation_block)
```

#### `src/pdf_annot/ndjson_to_md_block.py`
Renders streamlined annotations as Obsidian-compatible markdown.

```python
from pdf_annot.ndjson_to_md_block import render_block

markdown = render_block(
    streamlined_annotations,
    pdf_id_hash="VQGPEHE",
    info_text="Custom info text" # Caller must provide this
)
```

#### `src/pdf_annot/notes_db.py`
Mapping-like index of Markdown notes with case-insensitive lookups.

```python
from pdf_annot.notes_db import NotesDB

notes = NotesDB.from_env(env)
note_info = notes["(keating 1995)"] # case-insensitive
```

#### `src/pdf_annot/pdf_registry.py`
PDF discovery and metadata indexing.

```python
from pdf_annot.pdf_registry import build_pdf_index

pdf_index = build_pdf_index(env.paths.pdf_dirs)
pdf_info = pdf_index["(smith 2020)"] # case-insensitive
```

## Complete workflow example

The `src/pdf_annot/sync.py` file contains the `main()` function which implements the complete workflow. This is a simplified version of that loop:

```python
from datetime import datetime
from pdf_annot.env import load_env
from pdf_annot.pdf_registry import build_pdf_index
from pdf_annot.notes_db import NotesDB
from pdf_annot.sync import sync_pdf_to_note

# 1. Setup
env = load_env("pdf_annot.toml")
pdf_index = build_pdf_index(env.paths.pdf_dirs)
notes_db = NotesDB.from_env(env)
current_time_iso = datetime.now().isoformat(timespec="seconds")

# 2. Loop over all found PDFs
for pdf_id_lower, pdf_info in pdf_index.items():

    # 3. Find the matching note (or create a path for a new one)
    note_info = notes_db.get(pdf_id_lower)
    if note_info:
        note_path = Path(note_info.abs_path)
    else:
        note_path = env.paths.notes_root / f"{pdf_info.pdf_id}.md"

    # 4. Run the sync logic for this pair
    # This function handles checking mtime, extraction, rendering,
    # and atomically updating the file.
    result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)

    if result.note_updated:
        print(f"Updated: {note_path.name}")
    elif result.success:
        print(f"Skipped: {note_path.name}")
    else:
        print(f"Error: {note_path.name}: {result.error}")
```

## Testing

### Test structure
```
tests/
├── fixtures/
│   ├── workflow_manual_edits/  # E2E test fixture
│   │   ├── seeds/              # Initial state
│   │   │   ├── (Albini 2013).md
│   │   │   └── (Albini 2013) On dealing....pdf
│   │   ├── goldens/            # Expected output
│   │   │   └── (Albini 2013).md
│   │   └── config.toml         # Test-specific config
│   └── ... (many other fixtures)
├── tmp/                        # Generated during tests (gitignored)
├── test_core_workflow.py       # E2E test for the *library*
├── test_sync_cli.py            # E2E test for the *CLI*
├── test_frontmatter.py         # Frontmatter unit tests
└── ...
```

### Running tests
```bash
# Set up the environment (if first time)
make setup

# Run all tests
make test

# Run a specific test file
pytest -q tests/test_core_workflow.py
```

## Command-line tools

### `pdf-annot-sync`
Main workflow tool. Finds all PDFs and syncs them with notes.
```bash
# Run using config in current directory
pdf-annot-sync

# Run with a specific config
pdf-annot-sync -c /path/to/my_config.toml

# Preview changes without writing files (TODO)
pdf-annot-sync --dry-run
```

### `pdf-annot-extract`
```bash
pdf-annot-extract -p document.pdf [--header-height 60] [--footer-height 50]
```
Creates `document.ndjson` with raw annotations next to the PDF.

### `pdf-annot-streamline`
```bash
pdf-annot-streamline -i raw.ndjson -o streamlined.ndjson
```
Processes raw annotations into streamlined format.

### `tools/`
Developer utilities.
```bash
# Get the 7-char hash for a PDF ID
make hash ARGS="(Albini 2013)"
# > ID: '(Albini 2013)' -> VQGPEHE

# Get hash from a filename
make hash ARGS="(Albini 2013) Some Title.pdf"
# > File: '(Albini 2013) Some Title.pdf' -> ID: '(Albini 2013)' -> VQGPEHE
```

## Project layout
(See `project-tree.txt` for full layout)
```
pdf-annotations/
├── src/pdf_annot/              # Library code
│   ├── env.py                  # Configuration
│   ├── sync.py                 # <-- NEW: Main sync logic
│   ├── extract.py              # PDF extraction
│   ├── streamline_annotations.py  # Streamlining
│   ├── frontmatter.py          # YAML manipulation
│   ├── notes.py                # Note operations
│   ├── ndjson_to_md_block.py   # Markdown rendering
│   ├── notes_db.py             # Note indexing
│   └── pdf_registry.py         # PDF indexing
├── tests/                      # Test suite
│   ├── test_core_workflow.py   # Library E2E test
│   └── test_sync_cli.py        # <-- NEW: CLI E2E test
├── tools/                      # Dev utilities
│   └── print_hashes.py
├── Makefile                    # Project commands
├── requirements.txt            # Dependencies
├── pyproject.toml              # Package metadata
└── README.md                   # This file
```

## Development

### Setting up development environment
```bash
# Create venv, install deps, and install project in editable mode
make setup

# Activate the venv
source .venv/bin/activate

# Run tests
make test
```

### Troubleshooting

**Import issues during development:**
The `Makefile` targets (e.g., `make run`, `make test`) automatically set `PYTHONPATH=src` to ensure modules are found.

**Clean rebuild:**
```bash
# This removes venv, caches, and built files
make clean
# This rebuilds everything
make setup
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

### Info text preservation
The `<span class="pdf-annot-info">...</span>` text can be customized by users. The workflow preserves this custom text rather than overwriting with defaults.

## Future enhancements
- Implement `--dry-run` logic
- Additional edge case tests (missing frontmatter)
- Refactor `streamline_annotations.py` to remove duplicate logic

## License
[Your license here]

## Contributing
Pull requests welcome! Please ensure tests pass (`make test`) before submitting.
