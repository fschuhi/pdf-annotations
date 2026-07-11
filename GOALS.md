# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** We stopped working on this project a while ago.

**What's next:**
- We need to get back to it, first step: review, inventory, brainstorming, touch-up artefacts.
- Move done tasks to new `HISTORY.md`.
- Think about what should go into `GOALS.md` and what in `TODO.md`.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.

## PDF Annotations Quality
- ~~**Margin Detection**: For some PDFs the first line(s) are missing.~~
- ~~**Spurious Artefacts**: Comparing the output to Zotero's extracted annotations, there are a lot of bigger and smaller problems.~~

## Code Review & Scalability
- **Code Audit**: Review `src/pdf_annot/` for "production readiness" against 1600 files.
- **Large File Strategy**: Develop handling for PDFs with massive highlight counts (300+) to prevent Obsidian UI lag (e.g., splitting notes, folding).

## Highlight Color as Metadata
- **Highlight Color as Metadata**: Add a `highlight_color` field to the PDF metadata to allow for color-coded highlighting in Obsidian. Will affect the `ndjson` files and the callout colors.

## Advanced PDF Handling
- **Multi-Column Support**: Implement a frontmatter flag (e.g., `reading_order: columns`) to correctly sort annotations in 2-column papers.
- **Frontmatter Management**: Ensure `has_annotations`, `pdf_pages`, and layout flags are correctly synced.
