# TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter
- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## Tooling

- **Batch `pdf_ctime`:** Any opening of a PDF with Anima saves the current page to the PDF, i.e. `pdf_mtime` will change. This in itself needs to be thought-through, but even if we stick to those mechanics, it's nice to have the time when the page was created. Thus: create a tool which adds `pdf_ctime` from `pdf_mtime` to the frontmatter... or is there a _creation_ date saved with the file? That would be the better idea, because _some_ of the PDFs have already been touched by Anima (or PDF-Xchange-PDF, if I worked with them). Note that in Total Commander sometimes the creation date is _after_ the modified date (?). The tool is run once.
- **Fix old IDs:** Pre-`pdf-annotations` PDF IDs look like `[(Smilek2011)]` or `[(Gollwitzer-Schwarz+Sheeran2006b)]` (authored by Gollwitzer-Schwarz and co-authored by Sheeran, which have another paper in the collection from the same year, thus b). New IDs are `[(Smilek 2011)]` `Gollwitzer-Schwarz+Sheeran 2006b)]`. Thus: create a tool which goes through all Obsidian pages and replace old IDs with new IDs. It doesn't matter if there is actually such a new ID (or if there was such an old ID); the replacement is simply by pattern.

## Frontmatter

- **Add `pdf_ctime` in frontmatter generation:** a newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.
- **Add `tags` frontmatter property:** should be `type/bibnote`. This should be configurable in the env.
- **Just changing tags should not trigger update:** Any change (add, remove, update) of the _tags_ frontmatter attribute triggers a full PDF read and update of the annotations. Why? Should not happen.
- **Initialize new bibnotes with workflow properties:** New bibnotes should include `status: to-read`, `note_type: bibnote`, `time_spent: 0` in frontmatter, plus the two buttons (`BUTTON[time-spent-increment]`, `BUTTON[resume-pdf]`) in the free text area. These should be configurable in the env.
- **Frontmatter Management**: Ensure `has_annotations`, `pdf_pages`, and layout flags are correctly synced.
- **Frontmatter that parses but is not a mapping:** `--- \n some string \n ---` gives `has_fm=True` with an empty dict, so it passes A2's decline-guard and sync writes into it as though it were fine. Rare enough to defer, but it needs a defined answer -- most likely a third decline condition.

## UX

- **Highlight Color as Metadata**: Add a `highlight_color` field to the PDF metadata to allow for color-coded highlighting in Obsidian. Will affect the `ndjson` files and the callout colors.

## Testing

- **New Scenarios:** Flesh out and test more workflow edge cases. (The "note is missing its frontmatter entirely" case is answered as of A2: sync declines it. See `tests/fixtures/workflow_declines/`.)
- **Implement `--dry-run` Flag:** We still need to implement the logic for the --dry-run argument in `src/pdf_annot/sync.py`.

## Refactoring

- **More workflows in README.md**: We should call the text between the frontmatter and the `<hr class="pdf-annot-sep">` the "free text".
- **Large File Strategy**: Develop handling for PDFs with massive highlight counts (300+) to prevent Obsidian UI lag (e.g., splitting notes, folding).
- **Header/Footer Config:** Add `header_height` and `footer_height` settings to the Env model so they can be set in the `.toml` file.
- **`streamline_annotations.py` Refactor:** Refactor `streamline_annotations.py` to fix duplicated logic and inefficiencies (currently postponed).
- **Extract a PDF-identity module from `pdf-annotations`:**  _Needs investigation, deliberately deferred._ `resolve.py` depends on `pdf_registry`, `utils`, and config -- none of which are about annotations. This project is currently both the PDF-identity layer (hashes, index, lookups) and a consumer of it; Anima becoming a second consumer in 2026-07-18 is what made the dual role visible. The candidate shape: a standalone module owning the PDF "database" -- hashing, index construction, path lookup -- used by `pdf-annotations` for Obsidian bibnote generation and by Anima for `pdf://` resolution, with neither depending on the other. **Deferred on purpose, not overlooked.** The pull toward it is aesthetic ("the resolver sits in the wrong place") rather than driven by an observed problem: the resolver CLI contract is frozen, tested, and accepted, and Anima consumes it as a subprocess, so nothing is currently blocked. Scope Skepticism applies -- this is a plausible time sink whose payoff is tidiness. Note that Anima deliberately holds two independent absolute path constants (`projectRoot`, `pdfAnnotationsRoot`) rather than deriving both from a shared parent; the alternative was weighed partly as a deliberate speed bump against starting this refactoring on impulse, and rejected. That means the code contains no friction against it, and **this note is the speed bump instead**. Do not begin it as a side effect of another session. Reconsider when something concrete pushes: a third consumer appears, the resolver contract needs changes that force edits to annotation code, dependency or packaging needs diverge between the two roles. If it survives that test, promote it to `GOALS.md` for a proper strategy discussion before any code moves.
- **Multi-Column Support**: Implement a frontmatter flag (e.g., `reading_order: columns`) to correctly sort annotations in 2-column papers.
- **Home for `atomic_write_file`:** It lives in `utils.py`, chosen from an "e.g." in `AUDIT.md` A1 rather than decided. `notes.py` is arguably the better home -- it owns note-level operations, `sync.py` already imports from it, and the writer's hardcoded `suffix=".md"` for its temp file is honest in a notes module and a leaked assumption in a generic one. Decide rather than let it drift.
- **Tighten `atomic_write_file(path: Path | str)` to `Path`:** The `str` half was added on ergonomic speculation during A1a; after D1 = DELETE there is no caller that passes a `str`, and no test exercises that branch. Speculative generality of exactly the kind the audit diagnosed.
- **`ANNOT_SEP` exists in three places:** as a module constant in `sync.py`, as a local `separator` in `notes.py::replace_annotation_block`, and as a module constant in `notes_db.py`. If one copy ever drifts, sync declines every note. Export it from `notes.py` and import it in the others. (`notes_db.py`'s copy dies with A8.)
