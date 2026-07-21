# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** Production-readiness audit of `src/pdf_annot/` complete (2026-07-21). Findings, dispositions, and the implementation agenda live in `AUDIT.md` -- self-contained, `TARGET_ARCHITECTURE.md`-style. Notable outcomes: production writes are currently non-atomic (A1), the tags-trigger mystery is solved (A3), the slow-PDF mechanism is identified (A4).

**What's next:**

1. **Implementation sessions per `AUDIT.md`:** work the act ledger A1-A10 in order; decide D1 (plan/apply fork) at the first session's start. Preconditions V0-V2 before touching code.
2. **Batch `pdf_ctime`:** (`TODO.md`) Create a tool that adds the creation time of a PDF as frontmatter `pdf_ctime` -- implement after A3, whose normalization work is adjacent.
3. **Add `pdf_ctime` in frontmatter generation:** (`TODO.md`) A newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.

Everything else sits in `TODO.md` until it earns a place here.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.
