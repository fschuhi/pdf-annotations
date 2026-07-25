User:
Hi GPT! This is a continuation of previous conversations on `pdf-annotations`. Please read the guide `FIRST_PROMPT.md`.

Assistant:
Hi! I have read `CRITICAL_RULES.md` first, then `FIRST_PROMPT.md`, and reviewed the supplied `filesdump.txt`.

-   **Integrity check passed:** the dump declares 68 documents in its header and ends with the matching `END OF FILESDUMP: 68 document(s)` trailer.
-   I understand the project structure, including the `Extract -> Streamline -> Render` sync pipeline, the fast mtime/size gate, the atomic production write, and the resolver's frozen CLI contract.
-   I will follow **Discuss -> Approve -> Implement**, work in small steps, avoid unsolicited file creation or edits, provide complete drop-in replacements after approval, and preserve the green test suite.
-   I understand the collaboration priorities: clean rollback points, learning and local ownership, source-based reasoning rather than assumptions, scope skepticism, and respectful technical dialogue.

## Current position

`GOALS.md` says **A9 landed on July 24, 2026**. The next item is **A10**, a documentation-only audit closeout:

1.  Update `TARGET_ARCHITECTURE.md` with resolver configuration lookup and the `PDF_ANNOT_ENV_PATH` precedence.
2.  Update `README.md` with the live production sync call path and the PDF-as-source-of-truth philosophy.
3.  Harvest the audit's durable outcomes into `HISTORY.md`, including the A8 plan/apply retirement and resurrection commit `615200c`.

## Local ownership for A10

-   `env.py::load_env` owns the actual configuration resolution order: explicit source -> `PDF_ANNOT_ENV_PATH` -> default filenames in the current working directory.
-   `resolve.py` deliberately calls `load_env()` without an explicit source, making its working directory and subprocess environment part of the resolver's operational contract.
-   `sync.py::sync_pdf_to_note` owns the live write path. It coordinates the registry, read-only note index, extraction, streamlining, rendering, free-text preservation, annotation replacement, and atomic write.
-   `README.md` is the durable architecture and behavioral-contract home.
-   `TARGET_ARCHITECTURE.md` and `HISTORY.md` are not present in this dump -- they are commented out of `manifest.lst` -- so I cannot safely draft drop-in replacements for them yet.

## Two approaches

### Approach A -- Complete A10 as one bounded documentation step

You provide the current `TARGET_ARCHITECTURE.md` and `HISTORY.md`. We first inventory the exact target sections and the current history structure, then, after approval, make the three coordinated documentation updates.

**Pros:** Completes the stated A10 milestone cleanly; no temporary gaps; `GOALS.md` can then advance with an accurate durable record.
**Cons:** Requires supplying two documents currently outside the filesdump.

### Approach B -- Split A10 into two small approved steps

First, discuss and update only the supplied `README.md`. Then, once you provide `TARGET_ARCHITECTURE.md` and `HISTORY.md`, handle resolver-contract documentation and audit harvesting as a second step.

**Pros:** Starts with material already in context and keeps each change very focused.
**Cons:** Leaves A10 incomplete between steps, and the README's resolver explanation should ideally be checked against the architecture contract at the same time.

My recommendation is **Approach A**: this is a deliberately small documentation milestone, and its three artefacts describe one settled audit outcome. Could you attach or paste the current `TARGET_ARCHITECTURE.md` and `HISTORY.md`, and then confirm whether you want Approach A?

User:
Attached the `TARGET_ARCHITECTURE.md` and the `HISTORY.md`.

Regarding `TARGET_ARCHITECTURE.md`, we should consider _not_ updating it, because its provenance is that it was a document like `AUDIT.md`. It's the current architecture that counts. There's no need to keep the markdown synchronized. Feel free to push back, especially on best practices ground.

`HISTORY.md` used to be a very big document, which I have recently cut down considerably. It's a trophy case, not a development log.

Notice that we also need to update `TODO.md`. There are some struck-through paragraphs which need to be transferred to `HISTORY.md` (we've put that up until A10).

On with Approach A!

Assistant:
Agreed -- and I recommend **not updating `TARGET_ARCHITECTURE.md`**.

## Inventory and finding

### `TARGET_ARCHITECTURE.md`

Its current elements serve these roles:

-   Sections 1-2 establish the original problem and two-project boundary.
-   Section 3 freezes the resolver's CLI contract: invocation, output, errors, duplicate handling, and statelessness.
-   Section 3.6 is a **Phase A verification instruction**, written before the behavior was confirmed.
-   Sections 4-7 record URL behavior, Anima implementation design, and legacy-tool retirement.
-   Section 8 is a completed work plan.
-   Section 9 is a historical deferred-decisions ledger.
-   Its header explicitly says it is complete, archived in Anima, and retained here **for historical reference only**.

**Finding:** Updating only section 3.6 would turn a closed historical design/acceptance artefact into a partly live operational document. Its text would then mix "what the implementation session should verify" with a post-hoc result, while the file's stated purpose remains archival.

**Recommendation:** leave `TARGET_ARCHITECTURE.md` byte-for-byte unchanged. The confirmed configuration precedence belongs in current, code-adjacent documentation:

-   `env.py::load_env` already documents the full resolution order.
-   `resolve.py` documents that it calls `load_env()` without an explicit source.
-   `README.md` should become the user-facing operational home: resolver CWD requirement plus the important caveat that an inherited `PDF_ANNOT_ENV_PATH` overrides CWD default-file discovery.

That is not merely avoiding duplicate documentation as a preference. It preserves a clean distinction:

-   `TARGET_ARCHITECTURE.md` = historical contract/design record.
-   `README.md` = current system behavior and operating model.
-   `HISTORY.md` = durable milestones and decisions.
-   Code docstrings/tests = precise implementation-level contract.

This is the simpler maintenance model, and it fits the project's established source-of-truth philosophy.

### `HISTORY.md`

Its existing role is exactly as you describe: a selective trophy case, not a chronological debug journal. The current resolver entry is detailed because it records a cross-project public contract; the Phase D entry records the completed native macOS transition.

The three struck-through `TODO.md` items currently awaiting transfer are:

1.  **Normalized change detection / tags no longer trigger a sync** -- A3, landed July 22, 2026.
2.  **Real `--dry-run`** -- A8, landed July 24, 2026.
3.  **Single streamliner state machine** -- A7, landed July 24, 2026.

There is also the audit-wide completion material in `AUDIT.md`: A1 through A9, including the specific A8 retirement record required for the dormant plan/apply layer and its resurrection point, commit `615200c`.

## Two history approaches

### Option 1 -- One consolidated audit trophy entry

Add one reverse-chronological `HISTORY.md` entry, for example under a new heading such as "Production-readiness audit":

-   Records the audit period and the durable end state.
-   Summarizes the safety, correctness, performance, and simplification outcomes.
-   Names the important intentional decisions:
    -   atomic production writes;
    -   decline guards;
    -   normalized timestamps;
    -   extraction caching;
    -   strict shared ID gate;
    -   textbox-counting retention;
    -   one streamliner pathway;
    -   real full-fidelity dry run;
    -   retired dead configuration/identity freight.
-   Includes the required plan/apply retirement statement and resurrection commit `615200c`.
-   Links readers conceptually to `README.md` for the architecture and `AUDIT.md` for the full evidence ledger.

Then remove the three already-archived struck-through bullets from `TODO.md`, rather than copying each as a separate mini-entry.

**Pros:** Best fit for a trophy case; preserves the audit as one meaningful milestone; avoids inflating `HISTORY.md` with implementation-step granularity.
**Cons:** A future reader cannot scan individual A3/A7/A8 outcomes as separate history bullets.

### Option 2 -- Three small entries plus one retirement note

Add individual entries for A3, A7, and A8 because those correspond directly to the struck-through `TODO.md` items, then add a compact A1-A9 audit summary or a separate plan/apply retirement entry.

**Pros:** Maps visibly and directly from the three completed `TODO.md` bullets.
**Cons:** Moves `HISTORY.md` back toward a development log and treats three related audit slices as more historically important than the rest of the audit.

## Recommendation

I recommend **Option 1**: one carefully written audit trophy entry. It honors `HISTORY.md`'s newly narrowed purpose while still recording every decision that a future session might accidentally undo -- especially the plan/apply retirement and `615200c` resurrection point.

## Proposed bounded A10 implementation plan

If you confirm the recommendation, the approved documentation step would be:

1.  Update **only** `README.md`:

    -   Add the exact live production path from `sync.py`:
        `build_pdf_index` -> read-only `NotesDB` -> `extract_annotations_to_list` -> `streamline_annotations_list` -> `render_block` -> `extract_info_text` / `replace_annotation_block` -> `atomic_write_file`.
    -   Add the source-of-truth philosophy: PDF annotations/comments are authoritative; bibnotes are a useful derived service; extraction is heuristic by design.
    -   Document resolver configuration behavior in the current Resolver section, including `PDF_ANNOT_ENV_PATH` precedence.
2.  Update `HISTORY.md`:

    -   Add one concise audit-completion trophy entry, including the A8 plan/apply deletion and `615200c`.
3.  Update `TODO.md`:

    -   Remove the three previously struck-through, now-archived items: A3, A7, and A8.
    -   Leave all active items untouched.
4.  Update `GOALS.md`:

    -   Mark the audit documentation/harvesting complete.
    -   Move the current-session pointer to the next concrete work: batch `pdf_ctime`, followed by initial `pdf_ctime` generation.

No code changes and therefore no test changes are expected. Before committing, though, we should still run `make test` as the project standard requires.

Do you approve this **revised Approach A with Option 1**, including leaving `TARGET_ARCHITECTURE.md` unchanged?

User:
Yes, approved!

Assistant:
Denkt nach

Implemented the approved documentation-only A10 scope.

-   Left `TARGET_ARCHITECTURE.md` unchanged as a completed historical design/acceptance artefact.
-   Updated `README.md` with:
    -   the actual sync call path and ownership boundaries;
    -   the PDF-as-source-of-truth philosophy;
    -   the resolver configuration lookup behavior, including `PDF_ANNOT_ENV_PATH` precedence.
-   Added one consolidated production-readiness audit trophy entry to `HISTORY.md`, including the plan/apply retirement and resurrection commit `615200c`.
-   Removed the three now-archived A3, A7, and A8 struck-through items from `TODO.md`.
-   Advanced `GOALS.md` to the next work: batch `pdf_ctime`.

I cannot run the repository here, so please run `make test` before committing.

## `README.md`

markdown

```markdown
`# PDF Annotations
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
    PDF[PDF File] -->|PyMuPDF| Ex[Extraction Layer]    Ex -->|Raw JSON| St[Streamliner]    St -->|Cleaned Annotations| Ren[Renderer]    Ren -->|Merge| Note[Obsidian Note]
    subgraph "Sync Logic"        Check{Changed?}        Meta[Frontmatter]        Body[User Notes]    end
    PDF --> Check    Note --> Meta    Check -->|Yes| Ex    Check -->|No| Skip[Skip File]    Ren --> Body
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
* **macOS:** the resolver rebuilds its index on every click, so there is nothing to restart. A hash that will not resolve means the PDF is not in a folder listed under `pdf_dirs`, or a duplicate `pdf_id` exists somewhere in those folders (any duplicate fails all resolutions by design). Run `make discover-pdfs` to see what the config actually indexes.`

```

## `HISTORY.md`

markdown

```markdown
`# History
(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file.
---

## Production-Readiness Audit
- Production-readiness audit complete (2026-07-21 through 2026-07-24): the `src/pdf_annot/` audit closed with A1-A9 landed and A10 documentation/harvesting complete. Production note writes now go through `atomic_write_file`; sync declines existing notes it cannot safely identify as intact bibnotes; `pdf_mtime` comparison normalizes Obsidian's quoted and unquoted YAML timestamp shapes; and extraction caches page words and superscript regions lazily per highlighted page, reducing the measured 244-PDF full extraction pass from 362.67s to 144.54s. Controlled PDF and bibnote names now share one strict id predicate, registry and diagnostic discovery share one case-insensitive PDF walker, and marker annotation types no longer inflate `pdf_highlights` while Text and FreeText remain deliberately counted as `pdf_textboxes` migration debt. The streamliner has one state machine for both list and NDJSON entry points, accepting both real PyMuPDF tuple annotation types and JSON list shapes. `--dry-run` is now full-fidelity and diverges from a real run only at the one atomic write, so it neither changes notes nor closes the next real run's change gate. Dead freight was removed: Dropbox-relative registry state, legacy filename/hash helpers and dash parsing, inactive config profiles and aliases, the unused `atomic_writes` knob, and the unused hash tool. The dormant `NotesDB` plan/apply layer was retired in favor of the live direct sync path; it is recoverable if a concrete future need arises from commit `615200c` ("A8 first part") via `git show 615200c:src/pdf_annot/notes_db.py` and `git show 615200c:tests/test_annotations.py`. `README.md` now records the current production call path and the source-of-truth philosophy: PDFs are authoritative for highlights and comments, while bibnotes are a useful derived service and extraction is heuristic by design. `AUDIT.md` remains the full evidence ledger; this entry records the durable end state rather than reproducing the audit's development history.
## pdf:// Resolution (Obsidian -> Anima)
- Resolver CLI -- Phase A of the `pdf://` link-resolution contract (2026-07-18): added `src/pdf_annot/resolve.py`, the public interface that maps a `crc32_az7` hash (as it appears in a `pdf://<HASH>` URL host) to a fully-qualified PDF path. This is the pdf-annotations half of the two-project contract frozen in `TARGET_ARCHITECTURE.md` (section 3); Anima consumes it as a subprocess, so the contract is the CLI surface -- stdout, stderr, exit code -- not the Python API. `resolve.py` reuses `pdf_registry.build_pdf_index` and `env.load_env` unchanged and imports nothing heavy (no `fitz`), because per-click subprocess latency depends on import time; verified by inspecting the import chain. It owns only the hash-to-path action: `main()` handles argv and the process exit code, `resolve()` does load-config -> build-index -> scan `index.values()` for a matching `pdf_hash` (case-insensitive, normalized once at the top). Because `build_pdf_index` keys its dict by `pdf_id.lower()` rather than by hash, the lookup is a linear scan over values -- a non-issue at 1600 files, since the folder walk dominates and the in-memory scan is microseconds; re-keying the shared registry was rejected as an out-of-scope change to a working subsystem with other consumers. Strict duplicate handling is inherited verbatim: any duplicate `pdf_id` anywhere in `pdf_dirs` fails ALL resolutions (`DuplicatePdfIdError` caught and formatted), matching section 3.4. The three failure messages (no-match, duplicate, config-error) are declared as module constants so the tests assert against the same strings the code emits, with no drift; two small contract refinements were made here -- the duplicate message lists its paths sorted (walk order is not deterministic across machines), and the config-error message uses `--` rather than an em-dash. Registered the `pdf-annot-resolve` console script in `pyproject.toml` alongside the existing three; the bridge itself uses the `-m pdf_annot.resolve` form and does not depend on the script being installed. Pinned by `tests/test_resolve.py`: five subprocess-level contract tests (success, case-insensitive success, unknown hash, staged duplicate across two folders, missing-config error), each importing the message constants as the single source of truth. Acceptance was run against the real ~1600-file collection: a known hash resolved to its absolute path (exit 0); an unknown hash produced the no-match message (exit 1); a deliberately staged duplicate produced the strict two-path error and was then removed; and the section 3.6 config-discovery question was settled empirically -- with `PDF_ANNOT_ENV_PATH` unset, the same known hash resolves from the project root but fails with a configuration error from `/tmp`, confirming that `load_env` locates `pdf_annot.toml` via the current working directory and that section 3.1's "run with CWD = <pdfAnnotationsRoot>" requirement stands as written. With the contract frozen and Phase A accepted, the next locus of attention is Phase B in Anima.
- 2026-07-19: Phase D (`TARGET_ARCHITECTURE.md` cleanup) complete. `windows_server/README.md` banner added in pdf-annotations; `PDFHandler.app` decommissioned and trashed; Anima re-registered as sole `pdf://` handler via Finder launch; acceptance 8(a)-(c) passed. `TARGET_ARCHITECTURE.md` moved to `docs/` and marked complete. The macOS-native toolchain -- Anima + `pdf_annot.resolve` + Obsidian -- is now fully established.`

```

## `TODO.md`

markdown

```markdown
`# TODO
(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter
- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.
---

## Tooling
- **Batch `pdf_ctime`:** Any opening of a PDF with Anima saves the current page to the PDF, i.e. `pdf_mtime` will change. This in itself needs to be thought-through, but even if we stick to those mechanics, it's nice to have the time when the page was created. Thus: create a tool which adds `pdf_ctime` from `pdf_mtime` to the frontmatter... or is there a _creation_ date saved with the file? That would be the better idea, because _some_ of the PDFs have already been touched by Anima (or PDF-Xchange-PDF, if I worked with them). Note that in Total Commander sometimes the creation date is _after_ the modified date (?). The tool is run once.
- **Fix old IDs:** Analysis moved to `LINK_REFACTOR.md`, which supersedes the "create a tool" framing here -- the job turned out to be two PyCharm regexes and a `make run`. Deferred until the `AUDIT.md` agenda is complete, and blocked on putting the vault under version control.
- **Put the vault under version control:** There is no git repository and no versioned backup for the Obsidian vault. `LINK_REFACTOR.md` treats this as blocking, since three of its four steps are bulk writes across 244 irreplaceable notes, but it earns its keep independently of that job.
- **Pin `black` in `requirements.txt`:** It is unpinned while `pre-commit` runs it, so a version bump can reformat unrelated files and produce a diff containing more than the change being made -- which collides with `CRITICAL_RULES.md` Rule 2. Noticed 2026-07-23: two black versions disagree about one `textwrap.dedent` block in `tests/test_notes_db.py`. Second instance 2026-07-24: black 26.5.1 wants a blank line between the module docstring and `from __future__ import annotations` in `src/pdf_annot/notes.py`, which your version does not; left unapplied, since that reformat is not the change being made.
- **Rename `(Anyen Rinpoche+Graboski 2012)`:** "Rinpoche" is a title, not a surname, so the id should be `(Anyen+Graboski 2012)`. Not a filesystem rename: the id *is* the identity, so `crc32_az7` yields a new `pdf_hash`, the bibnote must be renamed to match, and every `pdf://` link inside its annotation block points at the old hash until that block is regenerated.
- **Identify the invisible character in `(Liljenberg 2012) A critical study of the thirteen later translations of the Dzogchen mind series.pdf`:** A normalization scan flagged the filename as non-ASCII although it reads as plain ASCII. Not in the id -- V2 came back empty -- so it is cosmetic, somewhere in the title.
- **Pin `Collection/PDFs` to "available offline" in Dropbox:** One-time ops action, not code (`AUDIT.md` F11). Dematerialized placeholders fail per-file -- gracefully, per sync's error handling -- if the setting slips during disk-space fiddling. Delete this item once done.
## Frontmatter
- **Add `pdf_ctime` in frontmatter generation:** a newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.
- **Add `tags` frontmatter property:** should be `type/bibnote`. This should be configurable in the env.
- **Initialize new bibnotes with workflow properties:** New bibnotes should include `status: to-read`, `note_type: bibnote`, `time_spent: 0` in frontmatter, plus the two buttons (`BUTTON[time-spent-increment]`, `BUTTON[resume-pdf]`) in the free text area. These should be configurable in the env.
- **Frontmatter Management**: Ensure `has_annotations`, `pdf_pages`, and layout flags are correctly synced.
- **Frontmatter that parses but is not a mapping:** `--- \n some string \n ---` gives `has_fm=True` with an empty dict, so it passes A2's decline-guard and sync writes into it as though it were fine. Rare enough to defer, but it needs a defined answer -- most likely a third decline condition.
## UX
- **Highlight Color as Metadata**: carry the highlight's stroke colour through to the rendered block so callouts can be colour-coded in Obsidian. The colour already survives extraction -- `Annotation.to_dict` emits `colors`, so it is present in the raw NDJSON -- and is then dropped by `make_output_obj` in `streamline_annotations.py`, which assembles its output dict from seven fixed keys. The work is therefore: carry `colors["stroke"]` through the streamliner, map RGB to a callout class in `render_block`, and decide where that mapping lives (code constant vs config -- see `AUDIT.md` D2). Since A6, Highlight is the only rendered type, so there is exactly one colour to carry.
- **Duplicate ids are not an "unexpected error":** `sync.main`'s broad handler reports `DuplicatePdfIdError` and `DuplicateNoteIdError` as "FATAL ERROR: An unexpected error occurred", which misdescribes a standing, user-fixable condition. A targeted `except` for the two would say so properly. Deliberately left out of `AUDIT.md` A5, because `sync.py` is not a file that item opens and ride-alongs never go standalone.
## Testing
- **New Scenarios:** Flesh out and test more workflow edge cases. (The "note is missing its frontmatter entirely" case is answered as of A2: sync declines it. See `tests/fixtures/workflow_declines/`.)
- **Unit tests for `notes.replace_annotation_block`:** it is the production annotation merge and has only fixture-level coverage (five workflow fixtures, all byte-compared). Not urgent -- that coverage is real and byte-exact -- but the function has no test that states its contract where it lives, which is what let the plan/apply twin look equally alive for so long.
## Refactoring
- **More workflows in README.md**: We should call the text between the frontmatter and the `<hr class="pdf-annot-sep">` the "free text".
- **Large File Strategy**: Develop handling for PDFs with massive highlight counts (300+) to prevent Obsidian UI lag (e.g., splitting notes, folding).
- **Header/Footer Config:** Add `header_height` and `footer_height` settings to the Env model so they can be set in the `.toml` file.
- **Extract a PDF-identity module from `pdf-annotations`:** _Needs investigation, deliberately deferred._ `resolve.py` depends on `pdf_registry`, `utils`, and config -- none of which are about annotations. This project is currently both the PDF-identity layer (hashes, index, lookups) and a consumer of it; Anima becoming a second consumer in 2026-07-18 is what made the dual role visible. The candidate shape: a standalone module owning the PDF "database" -- hashing, index construction, path lookup -- used by `pdf-annotations` for Obsidian bibnote generation and by Anima for `pdf://` resolution, with neither depending on the other. **Deferred on purpose, not overlooked.** The pull toward it is aesthetic ("the resolver sits in the wrong place") rather than driven by an observed problem: the resolver CLI contract is frozen, tested, and accepted, and Anima consumes it as a subprocess, so nothing is currently blocked. Scope Skepticism applies -- this is a plausible time sink whose payoff is tidiness. Note that Anima deliberately holds two independent absolute path constants (`projectRoot`, `pdfAnnotationsRoot`) rather than deriving both from a shared parent; the alternative was weighed partly as a deliberate speed bump against starting this refactoring on impulse, and rejected. That means the code contains no friction against it, and **this note is the speed bump instead**. Do not begin it as a side effect of another session. Reconsider when something concrete pushes: a third consumer appears, the resolver contract needs changes that force edits to annotation code, dependency or packaging needs diverge between the two roles. If it survives that test, promote it to `GOALS.md` for a proper strategy discussion before any code moves.
- **Multi-Column Support**: Implement a frontmatter flag (e.g., `reading_order: columns`) to correctly sort annotations in 2-column papers.
- **Home for `atomic_write_file`:** It lives in `utils.py`, chosen from an "e.g." in `AUDIT.md` A1 rather than decided. `notes.py` is arguably the better home -- it owns note-level operations, `sync.py` already imports from it, and the writer's hardcoded `suffix=".md"` for its temp file is honest in a notes module and a leaked assumption in a generic one. Decide rather than let it drift.
- **Tighten `atomic_write_file(path: Path | str)` to `Path`:** The `str` half was added on ergonomic speculation during A1a; after D1 = DELETE there is no caller that passes a `str`, and no test exercises that branch. Speculative generality of exactly the kind the audit diagnosed.
- **`ANNOT_SEP` exists in two places:** as a module constant in `sync.py` and as a local `separator` in `notes.py::replace_annotation_block`. If one copy ever drifts, sync declines every note. Export it from `notes.py` and import it in `sync.py`. (The third copy, in `notes_db.py`, died with A8 on 2026-07-24.)
- **Per-PDF extraction knobs via frontmatter:** _Needs a decision on where it lives before it is startable._ From `AUDIT.md` D3: bibnote frontmatter as per-PDF extraction config, read by sync before extraction -- `header_height: 45` first, `reading_order: ...` later. One mechanism subsuming the two items above it: "Header/Footer Config" and "Multi-Column Support". Multi-column direction is declarative section maps ("pages 3-7: two columns"; triple columns exist) rather than auto-detect, whose first tests failed; long-term this affects <2% of PDFs. D2 keeps this as config rather than folding it into constants. If the mechanism needs a strategy discussion before any code, promote it to `GOALS.md` instead of starting here.
- **Second-sep "endnotes" region:** _Idea, deliberately not now._ From `AUDIT.md` F13: everything from `<hr class="pdf-annot-sep">` to EOF is regenerated machine territory, and a second separator would open a hand-written region below it. The counterargument is its own speed bump and belongs in this item rather than in a future session's head: the single-sep pressure is a feature, because it is what keeps a bibnote a bibnote, and commentary already has two homes -- above the sep (muscle memory) and in The Studio. Do not start this as a side effect of another change.`

```

## `GOALS.md`

markdown

```markdown
`# Project Goals & Roadmap
(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.
---

## 📍 Current Session Pointer
A10 landed 2026-07-24. The production-readiness audit is now fully closed: its durable outcomes are harvested into `HISTORY.md`, `README.md` records the live sync path and source-of-truth philosophy, and `TARGET_ARCHITECTURE.md` remains unchanged as a completed historical design and acceptance artefact.
**What's next:**
1. **Batch `pdf_ctime`:** (`TODO.md`) Create a one-time tool that adds the creation time of each PDF as frontmatter `pdf_ctime`. A3 has landed, and `frontmatter.as_timestamp` is the normalizer to reuse wherever `pdf_ctime` and `pdf_mtime` get compared.
2. **Add `pdf_ctime` in frontmatter generation:** (`TODO.md`) A newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.
Everything else sits in `TODO.md` until it earns a place here; `LINK_REFACTOR.md` is no longer blocked by the audit, but it remains blocked on putting the vault under version control.
---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.`

```

User:
Thank you, GPT. This was an enjoyable collaboration -- not much for me to do, but you managed to keep me involved, love it.

Assistant:
Thank you -- that is exactly the kind of session structure I was aiming for.

A10 was a good bounded closeout: the audit's evidence stays in `AUDIT.md`, the historical resolver plan stays historical in `TARGET_ARCHITECTURE.md`, and the durable current contracts now have clear homes in `README.md` and `HISTORY.md`. That leaves the project at a clean rollback point before the `pdf_ctime` work begins.

When you are ready for the next step, we can start by inventorying what macOS filesystem timestamps and PDF-internal dates are actually available, then choose the smallest trustworthy one-time `pdf_ctime` tool.
