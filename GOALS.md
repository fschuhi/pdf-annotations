# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

A7 and A8 landed 2026-07-24. V2 discharged, V1 partially done. D1 decided in favour of (a) DELETE and is now executed. Remaining agenda: A9 and A10, plus A1b, which rides with A9/D2.

**What's next:**

1. **A9 (`AUDIT.md`) -- remove dead freight.** Batch removal across registry, utils and env: `dropbox_root`, `PdfInfo.dropbox_rel_path`, `_posix_relpath_if_under`, `hash_text`, `pdf_id_from_filename`, the dash-format branch in `parse_filename`, the `[envs]` indirection and `CLI.default_env`. PRECONDITION, and A8 demonstrated why it is not optional: grep the **working tree** for importers, never the filesdump -- V1 already found `tools/print_hashes.py` importing `utils.pdf_id_from_filename`, which forces a decision about that function rather than a straight deletion. A1b (remove the `io.atomic_writes` knob, blocked by two `test_env.py` assertions) and ride-along F6 (the two PDF walkers) attach here. Then A10, doc edits only. `HISTORY.md` is written after A10 and takes D1's retirement entry from the A8 record, including its SHA.
2. **Batch `pdf_ctime`:** (`TODO.md`) Create a tool that adds the creation time of a PDF as frontmatter `pdf_ctime`. No longer blocked -- A3 has landed, and `frontmatter.as_timestamp` is the normalizer to reuse wherever `pdf_ctime` and `pdf_mtime` get compared.
3. **Add `pdf_ctime` in frontmatter generation:** (`TODO.md`) A newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.

Everything else sits in `TODO.md` until it earns a place here; `LINK_REFACTOR.md` waits for the audit to finish.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.
