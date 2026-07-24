# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

A9 landed 2026-07-24. The audit's dead freight is gone: Dropbox-relative registry state, the unused hash command and legacy dash parser, inactive configuration profiles and field aliases, and the `atomic_writes` knob. Registry and diagnostic discovery now share one case-insensitive PDF walker, including `.PDF` files. A10 is next; it closes the audit's documentation work before its outcomes are harvested into `HISTORY.md`.

**What's next:**

1. **A10 (`AUDIT.md`) -- doc edits only.** Update `TARGET_ARCHITECTURE.md` with resolver configuration lookup and the `PDF_ANNOT_ENV_PATH` precedence; add the live sync call path and source-of-truth philosophy to `README.md`. Then harvest the audit's durable outcomes into `HISTORY.md`, including D1's plan/apply retirement entry and its resurrection SHA.
2. **Batch `pdf_ctime`:** (`TODO.md`) Create a tool that adds the creation time of a PDF as frontmatter `pdf_ctime`. No longer blocked -- A3 has landed, and `frontmatter.as_timestamp` is the normalizer to reuse wherever `pdf_ctime` and `pdf_mtime` get compared.
3. **Add `pdf_ctime` in frontmatter generation:** (`TODO.md`) A newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.

Everything else sits in `TODO.md` until it earns a place here; `LINK_REFACTOR.md` waits for the audit to finish.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.
