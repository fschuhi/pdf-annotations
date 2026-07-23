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
- **Fix old IDs:** Analysis moved to `LINK_REFACTOR.md`, which supersedes the "create a tool" framing here -- the job turned out to be two PyCharm regexes and a `make run`. Deferred until the `AUDIT.md` agenda is complete, and blocked on putting the vault under version control.
- **Put the vault under version control:** There is no git repository and no versioned backup for the Obsidian vault. `LINK_REFACTOR.md` treats this as blocking, since three of its four steps are bulk writes across 244 irreplaceable notes, but it earns its keep independently of that job.
- **Pin `black` in `requirements.txt`:** It is unpinned while `pre-commit` runs it, so a version bump can reformat unrelated files and produce a diff containing more than the change being made -- which collides with `CRITICAL_RULES.md` Rule 2. Noticed 2026-07-23: two black versions disagree about one `textwrap.dedent` block in `tests/test_notes_db.py`.
- **Rename `(Anyen Rinpoche+Graboski 2012)`:** "Rinpoche" is a title, not a surname, so the id should be `(Anyen+Graboski 2012)`. Not a filesystem rename: the id *is* the identity, so `crc32_az7` yields a new `pdf_hash`, the bibnote must be renamed to match, and every `pdf://` link inside its annotation block points at the old hash until that block is regenerated.
- **Identify the invisible character in `(Liljenberg 2012) A critical study of the thirteen later translations of the Dzogchen mind series.pdf`:** A normalization scan flagged the filename as non-ASCII although it reads as plain ASCII. Not in the id -- V2 came back empty -- so it is cosmetic, somewhere in the title.

## Frontmatter

- **Add `pdf_ctime` in frontmatter generation:** a newly created page adds `pdf_ctime` from the beginning, i.e. before opening the PDF with Anima both `pdf_ctime` and `pdf_mtime` are the same.
- **Add `tags` frontmatter property:** should be `type/bibnote`. This should be configurable in the env.
- ~~**Just changing tags should not trigger update:** Any change (add, remove, update) of the _tags_ frontmatter attribute triggers a full PDF read and update of the annotations. Why? Should not happen.~~ Retired by `AUDIT.md` A3 (landed 2026-07-22). Cause: Obsidian's property editor rewrites the frontmatter block on any property edit and unquotes `pdf_mtime`, so the change gate compared a `datetime` against a string and was unequal forever. The gate now normalizes both sides via `frontmatter.as_timestamp`; `make run` over 244 bibnotes reports no updates.
- **Initialize new bibnotes with workflow properties:** New bibnotes should include `status: to-read`, `note_type: bibnote`, `time_spent: 0` in frontmatter, plus the two buttons (`BUTTON[time-spent-increment]`, `BUTTON[resume-pdf]`) in the free text area. These should be configurable in the env.
- **Frontmatter Management**: Ensure `has_annotations`, `pdf_pages`, and layout flags are correctly synced.
- **Frontmatter that parses but is not a mapping:** `--- \n some string \n ---` gives `has_fm=True` with an empty dict, so it passes A2's decline-guard and sync writes into it as though it were fine. Rare enough to defer, but it needs a defined answer -- most likely a third decline condition.

## UX

- **Highlight Color as Metadata**: carry the highlight's stroke colour through to the rendered block so callouts can be colour-coded in Obsidian. The colour already survives extraction -- `Annotation.to_dict` emits `colors`, so it is present in the raw NDJSON -- and is then dropped by `make_output_obj` in `streamline_annotations.py`, which assembles its output dict from seven fixed keys. The work is therefore: carry `colors["stroke"]` through the streamliner, map RGB to a callout class in `render_block`, and decide where that mapping lives (code constant vs config -- see `AUDIT.md` D2). Since A6, Highlight is the only rendered type, so there is exactly one colour to carry.
- **Duplicate ids are not an "unexpected error":** `sync.main`'s broad handler reports `DuplicatePdfIdError` and `DuplicateNoteIdError` as "FATAL ERROR: An unexpected error occurred", which misdescribes a standing, user-fixable condition. A targeted `except` for the two would say so properly. Deliberately left out of `AUDIT.md` A5, because `sync.py` is not a file that item opens and ride-alongs never go standalone.

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
