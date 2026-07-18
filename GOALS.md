# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** Phase A of the `pdf://` link-resolution work (`TARGET_ARCHITECTURE.md`) is complete and the CLI contract is frozen. `src/pdf_annot/resolve.py` maps a `pdf://<HASH>` to a PDF path, reusing `build_pdf_index` unchanged; it is pinned by `tests/test_resolve.py` and was accepted against the real collection (known hash, unknown hash, strict duplicate, and the section 3.6 CWD-discovery check). The `pdf-annot-resolve` console script is registered. See `HISTORY.md` for the full record.

**What's next:** Phase B (Anima) per `TARGET_ARCHITECTURE.md` section 8 -- register the `pdf` URL scheme and add the `pdfAnnotationsRoot` constant (step 4). That is an Anima-project session; per the "one project per session" rule, the contract stays frozen here and Anima adapts to it. Switch back to this project only if a contract inadequacy surfaces.

Everything else sits in `TODO.md` until it earns a place here.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.

## Code Review & Scalability
- **Code Audit**: Review `src/pdf_annot/` for "production readiness" against 1600 files.
- **Large File Strategy**: Develop handling for PDFs with massive highlight counts (300+) to prevent Obsidian UI lag (e.g., splitting notes, folding).

## Highlight Color as Metadata
- **Highlight Color as Metadata**: Add a `highlight_color` field to the PDF metadata to allow for color-coded highlighting in Obsidian. Will affect the `ndjson` files and the callout colors.

## Advanced PDF Handling
- **Multi-Column Support**: Implement a frontmatter flag (e.g., `reading_order: columns`) to correctly sort annotations in 2-column papers.
- **Frontmatter Management**: Ensure `has_annotations`, `pdf_pages`, and layout flags are correctly synced.
