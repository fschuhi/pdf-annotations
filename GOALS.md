# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

A10 landed 2026-07-24. The production-readiness audit is now fully closed: its durable outcomes are harvested into `HISTORY.md`, `README.md` records the live sync path and source-of-truth philosophy, and `TARGET_ARCHITECTURE.md` remains unchanged as a completed historical design and acceptance artefact.

**What's next:**
1. **Batch `pdf_ctime`:** (`TODO.md`) Create a one-time tool that adds the creation time of each PDF as frontmatter `pdf_ctime`, as copy of `pdf_mtime`. For a new bibnote, `pdf_ctime` and `pdf_mtime` are the same. From then on, only the latter changes. A3 has landed, and `frontmatter.as_timestamp` is the normalizer to reuse wherever `pdf_ctime` and `pdf_mtime` get compared.
2. **Add `pdf_ctime` in frontmatter generation:** (`TODO.md`) A newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.

Everything else sits in `TODO.md` until it earns a place here; `LINK_REFACTOR.md` is no longer blocked by the audit, but it remains blocked on putting the vault under version control.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.
