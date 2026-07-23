# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** Implementing the `AUDIT.md` act ledger. A1a, A2, A3 and A4 landed 2026-07-22; A5 and its ride-along F8 landed 2026-07-23, with V2 discharged. D1 decided in favour of (a) DELETE. Remaining agenda: A6-A10 plus A1b, which rides with A9/D2. Two open decisions block nothing: D5 (per-call extraction cost) and D6 (Unicode normalization of ids, new 2026-07-23).

**What's next:**

1. **A6 (`AUDIT.md`) -- tighten annotation types; keep the textbox signal.** Drop the unused marker types, keep Text/FreeText so `pdf_textboxes` survives as the migration-debt tracker, and document the counted-but-never-rendered asymmetry in `README.md`. Then A7 ff. in ledger order; V1 still blocks A9.
2. **Batch `pdf_ctime`:** (`TODO.md`) Create a tool that adds the creation time of a PDF as frontmatter `pdf_ctime`. No longer blocked -- A3 has landed, and `frontmatter.as_timestamp` is the normalizer to reuse wherever `pdf_ctime` and `pdf_mtime` get compared.
3. **Add `pdf_ctime` in frontmatter generation:** (`TODO.md`) A newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.

Everything else sits in `TODO.md` until it earns a place here; `LINK_REFACTOR.md` waits for the audit to finish.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.
