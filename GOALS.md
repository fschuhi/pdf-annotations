# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

Page-1 thumbnails landed 2026-07-26: `sync.py` auto-adds them for new/changed bibnotes, `tools/backfill_thumbnails.py` retrofitted the existing ~1600-book corpus. See `HISTORY.md`.

**What's next:**
1. Add the "synopsis" from `~/Obsidian/Papers/Collection/Synopsis` (probably add this path to the `pdf_annot.toml`) to a bibnote, below the `<span class="pdf-thumbnail"...`. The beginning of the synopsis is separated by an empty line from the thumbnail; there is one empty line after the synopsis. The name of the synopsis file is `<pdf_id>.txt`. Do not add anything in case the size of the file is `0`. The synopsis is put into a `>[!abstract]` callout. The first line of the callout is "Synopsis", followed by `>` and the first paragraph of the synopsis, a new line consisting of `>` for whitespace, then a new line starting with `>` and the second paragraph of the synopsis, and so on. The synopses can contain `<br>` and other formattings. I'm interested in capturing the correct behaviour in tests first, because we will add multiple lines for bibnotes, which is difficult to roll back.
2. Review and prioritize the backlog in `TODO.md`.

Everything else sits in `TODO.md` until it earns a place here.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.
