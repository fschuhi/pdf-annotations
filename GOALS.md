# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** We stopped working on this project a while ago. The locus of attention switched to `anima`, a lightweight PDF editor. This is the moment to bring this project and `anima` together.

**What's next:**
- Read `TARGET_ARCHITECTURE.md`. Other than the model I collaborated with to arrive at the file, you are literally the first model which will start implementing it. Exciting!
- In parallel, please help me to get back to this project. Where necessary, do a review, create an inventory, engage in brainstorming, and particularly touch-up artefacts.
- At the end of the session I'd like to start a `HISTORY.md` which will have then captured what we do in this session.
- As part of the end-of-session work, we need to streamline `GOALS.md` and `TODO.md` and decide what goes where.

Let's thus pick a small first task from `TARGET_ARCHITECTURE.md`, so that we get some momentum going, including brushing up the artefacts.

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
