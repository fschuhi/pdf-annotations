# PDF Annotations

**Turn your PDF library into an active Obsidian knowledge base.**

A robust sync engine that extracts highlights and annotations from PDFs (using PyMuPDF) and renders them into structured, frontmatter-rich Markdown notes.

---

## Vision

This is not just a file converter; it is the "drumbeat" of a Zettelkasten workflow. The goal is to manage a library of 1600+ academic papers and books, transforming static PDF highlights into a living network of ideas.

**Core Philosophy:**
- **Idempotency**: Only update notes when the PDF actually changes.
- **Data Preservation**: Never overwrite manual user comments in the Markdown note.
- **Process Tracking**: Use frontmatter (`status`, `pdf_mtime`) to drive Obsidian Dataview dashboards.
- **Reliability**: Safe, atomic writes and consistent ID generation.

---

## Architecture

The system follows a strict "Extract → Streamline → Render" pipeline to ensure clean data.

```mermaid
graph LR
    PDF[PDF File] -->|PyMuPDF| Ex[Extraction Layer]
    Ex -->|Raw JSON| St[Streamliner]
    St -->|Cleaned Annotations| Ren[Renderer]
    Ren -->|Merge| Note[Obsidian Note]

    subgraph "Sync Logic"
        Check{Changed?}
        Meta[Frontmatter]
        Body[User Notes]
    end

    PDF --> Check
    Note --> Meta
    Check -->|Yes| Ex
    Check -->|No| Skip[Skip File]
    Ren --> Body
```

---

## Current Status

| Feature | Status | Notes |
|---|---|---|
| **Core Sync Engine** | ✅ Complete | Automatic sync of all PDFs to Notes |
| **Incremental Updates** | ✅ Complete | Time/Size based detection |
| **Highlight Extraction** | ✅ Complete | Header/Footer aware |
| **Frontmatter Mgmt** | ✅ Complete | Preserves non-PDF fields |
| **Windows Link Handler** | ✅ Complete | `pdf://` protocol support |
| **Multi-Column PDFs** | 🚧 Planned | Better reading order sorting |
| **Large File Strategy** | 🚧 Planned | Handling 300+ highlights |
| **CLI Profiles** | 🚧 Planned | Dev/Prod environment switching |

> **Note:** For the future roadmap and planned features, please refer to [`Goals.md`](Goals.md).

---

## Quick Start

The project is managed via a standardized `Makefile`.

### 1. Setup
Initialize the environment and configuration:
```bash
make setup
```
*This creates the virtual environment, installs dependencies, and generates `pdf_annot.toml` from the example if missing.*

### 2. Configuration
Edit `pdf_annot.toml` to point to your files:
```toml
[paths]
notes_root = "/Users/me/Obsidian/Zettelkasten/References"
pdf_dirs = ["/Users/me/Documents/Papers"]

[io]
atomic_writes = true
```

### 3. Run Sync
Synchronize your library:
```bash
make run
```

---

## Architecture Overview & Modules

### Core Workflow: `pdf-annot-sync`

The main entry point is `src/pdf_annot/sync.py`. When run, it automatically:
1.  **Loads configuration** (e.g., `pdf_annot.toml`) to get `pdf_dirs` and `notes_root`.
2.  **Builds registries** for all PDFs (`PdfRegistry`) and all notes (`NotesDB`).
3.  **Loops over every PDF** and compares it to its corresponding note.
4.  **Detects changes** by comparing PDF mtime/size with note frontmatter.
5.  **Calls `sync_pdf_to_note`** for any new or changed PDFs.

This function handles the extraction, streamlining, rendering, and atomic updating. This workflow is tested end-to-end in `tests/test_core_workflow.py`.

### Library Modules

#### `src/pdf_annot/env.py`
Configuration management via TOML files.
```python
from pdf_annot.env import load_env
env = load_env("pdf_annot.toml")
# Access: env.paths.notes_root, env.annotations.default_info_text
```

#### `src/pdf_annot/sync.py`
The core workflow logic and `main` CLI entry point.
```python
from pdf_annot.sync import sync_pdf_to_note
# Core "god function"
result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)
```

#### `src/pdf_annot/extract.py`
PDF annotation extraction with header/footer awareness.
```python
# Library API
annotations, stats = extract_annotations_to_list(pdf_path)
```
*CLI:* `pdf-annot-extract -p document.pdf`

#### `src/pdf_annot/streamline_annotations.py`
Post-processes raw annotations: keeps highlights, merges link annotations (e.g., across pages or hyphens), extracts headings.
```python
# Library API
streamlined = streamline_annotations_list(raw_annotations)
```
*CLI:* `pdf-annot-streamline -i raw.ndjson -o streamlined.ndjson`

#### `src/pdf_annot/frontmatter.py`
YAML frontmatter parsing and manipulation. Safely updates PDF-specific fields while preserving user-added tags or categories.
```python
changed, updated_text = upsert_fields(note_text, {"pdf_title": "New"})
```

#### `src/pdf_annot/notes.py` & `ndjson_to_md_block.py`
Handles extraction of custom info text (preserves user edits) and rendering of the annotation block.

#### `src/pdf_annot/pdf_registry.py` & `notes_db.py`
Indexing systems for discovering controlled PDFs (bracket format) and existing Markdown notes.

---

## Key Concepts

### PDF URL Click Handler (Windows)
This project generates hash-based `pdf://` links (e.g., `pdf://VQGPEHE?page=1`). To make these clickable, a helper application is required.

* **Location:** `windows_server/`
* **Function:** Intercepts `pdf://` URLs from macOS/Obsidian (via Parallels) and opens the correct PDF page in a native Windows viewer (PDF-XChange).
* **Documentation:** See `windows_server/README.md` for setup.

### PDF ID and Hash
* **pdf_id**: Normalized identifier extracted from filename, e.g., `(Das 2000b)`.
* **pdf_hash**: 7-letter CRC32-based hash of the lowercase ID. Used for stable linking even if files move.

### Controlled PDFs
PDFs must follow the naming convention: `(Author Year) Title.pdf`.
* Example: `(Albini 2013) On dealing with destructive emotions.pdf`

### Note Structure
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

### Info Text Preservation
The `<span class="pdf-annot-info">...</span>` text is designed to be edited by the user. The sync workflow **preserves** this text rather than overwriting it with defaults.

---

## Development

### Testing
We use strict TDD. Tests must pass before features are merged.
```bash
make test           # Run quiet
make test-verbose   # Run with detailed output
```

### Utilities
```bash
# Get the 7-char hash for a PDF ID
make hash ARGS="(Albini 2013)"

# Discover all PDFs visible to the config
make discover-pdfs
```

### Project Structure
```bash
make showtree
```
Displays the project layout (src-layout pattern).

---

## Troubleshooting

### "Files not updating"
* Check `pdf_annot.toml` paths.
* The system skips files where `pdf_mtime` in the note matches the PDF on disk. Touch the PDF to force an update.

### "ImportError: No module named..."
* Ensure you are using `make run` or `make test`, which handle `PYTHONPATH` automatically.

### "Hash not found" (Windows Server)
* Restart the Windows server script to rebuild its in-memory index of PDFs.
