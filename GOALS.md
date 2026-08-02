# Project Goals & Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

Synopsis feature landed 2026-08-02: `pdf_annot/synopsis.py` + `notes.py` additions render and insert ISBNdb synopsis callouts, `tools/fill_synopses.py` (`make fill-synopses`) is the sole insertion mechanism (not wired into `sync.py`), gated on the new `synopses_dir` config. Live-tested successfully against individual bibnotes via `--pdf-id`. See `HISTORY.md`.

**What's next:**
1. Polishing pass on `format_synopsis_callout`'s paragraph-splitting, driven by real examples that surfaced edge cases during live testing (whitespace between break tags not collapsing, missing per-paragraph strip, `<p>`-tag variants) -- see `TODO.md`. Do this before running `make fill-synopses` against the full corpus: insertion is effectively permanent per note, so baking the current bugs into ~1600 bibnotes would mean undoing them by hand later.
2. Once the polishing pass is green, run `make fill-synopses` against the full corpus.
3. Review and prioritize the backlog in `TODO.md`.

Everything else sits in `TODO.md` until it earns a place here.

---

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.
