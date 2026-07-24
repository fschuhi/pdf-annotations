# PDF Annotations

**Turn your PDF library into an active Obsidian knowledge base.**

A robust sync engine that extracts highlights and annotations from PDFs (using PyMuPDF) and renders them into
structured, frontmatter-rich Markdown notes.

---

## Vision

This is not just a file converter; it is the "drumbeat" of a Zettelkasten workflow. The goal is to manage a library of 1600+ academic papers and books, transforming static PDF highlights into a living network of ideas.

The PDF is the single source of truth for highlights and comments. The bibnote is a derived service: it supports cross-book search, Dataview process tracking, and raw material for citations and writing. Extraction is necessarily heuristic and will never be perfect by design; when the PDF and its derived note disagree, the PDF is authoritative.

**Core Philosophy:**

- **Idempotency**: Only update notes when the PDF actually changes.
- **Data Preservation**: Never overwrite manual user comments in the Markdown note.
- **Process Tracking**: Use frontmatter (`status`, `pdf_mtime`) to drive Obsidian Dataview dashboards.
- **Reliability**: Safe, atomic writes and consistent ID generation.

---

## Architecture

The system follows a strict "Extract -> Streamline -> Render" pipeline to ensure clean data.

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

### Extraction: Words-Based Approach

The extraction layer uses a **word-level overlap matching** strategy rather than raw rectangle clipping. For each
highlight annotation, the extractor:

1. **Merges quads by visual line** — highlight quads with similar y-coordinates (within 3pt) are grouped into a single rect per line, preventing typographic characters (curly quotes, apostrophes) from bleeding into adjacent lines.
2. **Matches words by overlap ratio** — page words from `get_text("words")` are matched against merged line rects. A word must have ≥50% area overlap to be included, which rejects stray characters from neighbouring lines.
3. **Detects superscript contamination** — font-size analysis via `get_text("dict")` identifies footnote reference numbers. Words partially overlapping superscript regions have trailing digits stripped; pure superscript words are skipped entirely.

This approach eliminates three classes of extraction artefacts: stray single characters (`g`, `p`), footnote number leakage (`of).4`), and intra-highlight misordering.

Page text is extracted once per page, not once per highlight. `extract_annotations` computes the page's words and its superscript regions when it meets the first highlight on a page, and hands both to every later highlight on that page. The computation is lazy on purpose: most pages in a book carry no highlights at all, and eager per-page extraction would make those pages pay for text nobody reads. Measured 2026-07-22 across the 244-file collection, a full extraction pass went from 363s to 145s.

### Annotation Types: Counted vs Rendered

Extraction reads three annotation types (`TEXTUAL_ANNOTS` in `annotation.py`): Text, FreeText and Highlight. Squiggly, StrikeOut and Underline are not read at all -- Anima emits only highlights and comments, and the collection contains no real use of the marker types.

Of the three that are read, only Highlight is ever rendered. Text and FreeText are extracted and counted into `pdf_textboxes`, then filtered out by the streamliner before anything reaches the block. The asymmetry is deliberate: `pdf_textboxes` is the Dataview tracker for PDFs whose legacy textboxes have not yet been converted into highlights and comments, and it is the signal that an author supplied textboxes of their own. The count is retained permanently -- do not remove the types on the grounds that nothing renders them.

### Change Detection: Fast Skip

The sync engine checks `pdf_mtime` and `pdf_size` against the note's frontmatter **before** opening the PDF. Unchanged files are skipped without any PDF parsing, making repeated `make run` calls fast even across 1600+ files.

The timestamp comparison is normalized, not raw. Obsidian's property editor rewrites the whole frontmatter block whenever any property is edited, and drops the quotes around `pdf_mtime`, so YAML parsing then yields a `datetime` where sync wrote a string. `frontmatter.as_timestamp` reduces both sides to a `datetime` before comparing, and a value it cannot interpret counts as changed -- failing toward a re-extract, which is cheap and idempotent, rather than toward a note frozen against updates. Only the read side normalizes: a timestamp Obsidian has unquoted stays unquoted.

> **Note:** For the future roadmap and planned features, see [`GOALS.md`](GOALS.md).

---

## Quick Start

The project is managed via a standardized `Makefile`.

### 1. Setup

Initialize the environment and configuration:

```bash
make setup
```

*This creates the virtual environment, installs dependencies, and generates `pdf_annot.toml` from the example if
missing.*

### 2. Configuration

Edit `pdf_annot.toml` to point to your files:

```toml
[paths]
notes_root = "/Users/me/Obsidian/Zettelkasten/References"
pdf_dirs = ["/Users/me/Documents/Papers"]

[io]
create_missing_dirs = true
```

### 3. Run Sync

Synchronize your library:

```bash
make run
```

---

## Project Navigation & Context

This project uses a curated "manifest" approach to manage context for AI collaboration.

* **[`manifest.lst`](manifest.lst)**: Single source of truth for project structure.
* **`make filesdump`**: Generates XML-wrapped context dump for LLM sessions.

---

## Architecture Overview & Modules

### Core Workflow: `pdf-annot-sync`

The main entry point is `src/pdf_annot/sync.py`. When run, it automatically:

1. **Loads configuration** (e.g., `pdf_annot.toml`) to get `pdf_dirs` and `notes_root`.
2. **Builds registries** for all PDFs (`PdfRegistry`) and all notes (`NotesDB`).
3. **Loops over every PDF** and compares it to its corresponding note.
4. **Detects changes** by comparing PDF mtime/size with note frontmatter (fast — no PDF parsing).
5. **Calls `sync_pdf_to_note`** only for new or changed PDFs.

The live production path inside `sync_pdf_to_note` is deliberately direct: `build_pdf_index` supplies `PdfInfo`; `NotesDB` is a read-only note index; then sync calls `extract_annotations_to_list`, `streamline_annotations_list`, `render_block`, `extract_info_text`, and `replace_annotation_block` before making its one protected write through `atomic_write_file`. This call path is the actual sync contract. `NotesDB` does not plan or apply note updates, and no dormant alternate update path exists.

This function handles the extraction, streamlining, rendering, and atomic updating. This workflow is tested end-to-end
in `tests/test_core_workflow.py`.

### Library Modules

#### `src/pdf_annot/env.py`

Configuration management via TOML files.

```python
from pdf_annot.env import load_env

env = load_env("pdf_annot.toml")
# Access: env.paths.notes_root, env.paths.pdf_dirs
```

#### `src/pdf_annot/sync.py`

The core workflow logic and `main` CLI entry point. Performs a cheap mtime/size check before any PDF parsing, so unchanged files are skipped instantly. `--dry-run` is full-fidelity: it computes everything -- extraction, streamlining, rendering, composition -- and skips only the final write, so a preview reports exactly what a real run would do and leaves `pdf_mtime` untouched, which keeps the change gate armed for the run that follows.

```python
from pdf_annot.sync import sync_pdf_to_note

result = sync_pdf_to_note(env, pdf_info, note_path, current_time_iso)
```

#### `src/pdf_annot/extract.py`

PDF annotation extraction using words-based overlap matching. Handles header/footer exclusion, superscript footnote detection, and visual reading order sorting.

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

#### `src/pdf_annot/resolve.py`

Resolver CLI: maps a `crc32_az7` hash (as it appears in a `pdf://<HASH>` URL) to a fully-qualified PDF path. This is the public interface consumed by the macOS PDF viewer (Anima) as a subprocess -- the contract is the CLI surface (stdout / stderr / exit code), frozen in `TARGET_ARCHITECTURE.md`. It reuses `build_pdf_index` and imports nothing heavy (no PyMuPDF), so per-click latency stays low.

The resolver calls `load_env()` without an explicit source. Configuration resolution is therefore: an explicit source when one is passed by a caller, then `PDF_ANNOT_ENV_PATH` when that environment variable is set, then `pdf_annot.toml` or `pdf-annotations.toml` in the current working directory. The Anima bridge must run the resolver with the project root as its working directory so the normal project `pdf_annot.toml` is found. `PDF_ANNOT_ENV_PATH` has higher precedence than that CWD lookup; if it is inherited by Anima's subprocess environment, it silently selects that file instead.

```bash
# Prints the absolute path on success (exit 0); a one-line reason on stderr otherwise (exit 1)
pdf-annot-resolve VQGPEHE
```

---

## Key Concepts

### PDF URL Click Handler

This project generates hash-based `pdf://` links (e.g., `pdf://VQGPEHE?page=1`). Clicking one opens the referenced PDF at the requested page.

* **macOS (current):** the link is handled natively by the PDF viewer (Anima) together with `pdf_annot.resolve`, which turns the hash into a path. The resolver is stateless -- it rebuilds its index from the filesystem on every click, so there is no cache to refresh. See `TARGET_ARCHITECTURE.md` for the historical contract and acceptance record.
* **Windows (legacy):** a helper application in `windows_server/` intercepts `pdf://` URLs (via Parallels) and opens the PDF in PDF-XChange. See `windows_server/README.md` for setup. This path is retained for the Windows machine only.

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
pdf_pages: 12
pdf_highlights: 6
pdf_textboxes: 0
---

<hr class="pdf-annot-sep">

<span class="pdf-annot-info">below the automatically generated annotations from the PDF</span>

## Section Header

> Highlight <span class="pdf-annot-date">21.10.25 21:20</span> [1](pdf://VQGPEHE?page=1)
```

### Info Text Preservation

The `<span class="pdf-annot-info">...</span>` text is designed to be edited by the user. The sync workflow **preserves** this text rather than overwriting it with defaults.

---

## Makefile Targets

```bash
# Setup
make setup          # Create venv, install deps, generate config

# Core Workflow
make run            # Sync all PDFs to notes
make dry-run        # Preview the sync without writing anything

# Testing
make test           # Run tests (quiet)
make test-verbose   # Run tests with output

# Utilities
make discover-pdfs              # List all PDFs visible to config
make showtree                   # Display project structure
make filesdump                  # Create context dump for LLMs
make time-extraction            # Time extraction per PDF (read-only)
```

---

## Development

### Testing

We use strict TDD. Tests must pass before features are merged.

```bash
make test           # Run quiet
make test-verbose   # Run with detailed output
```

The test suite includes extraction quality regression tests using real academic PDFs (e.g., Fasching 2008) with golden file comparison to catch artefacts like stray characters, footnote leakage, and sort order issues.

### Utilities

```bash
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

### "Hash not found"

* **macOS:** the resolver rebuilds its index on every click, so there is nothing to restart. A hash that will not resolve means the PDF is not in a folder listed under `pdf_dirs`, or a duplicate `pdf_id` exists somewhere in those folders (any duplicate fails all resolutions by design). Run `make discover-pdfs` to see what the config actually indexes.
