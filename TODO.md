# TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter
- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## Making the Workflow Fully MacOS-native

- ~~**`pdf://` resolver (Phase A)**: Implemented `src/pdf_annot/resolve.py` (hash -> PDF path), registered the `pdf-annot-resolve` console script, pinned by `tests/test_resolve.py` (5 contract tests), accepted against the real collection. Contract frozen per `TARGET_ARCHITECTURE.md` section 3. Next locus is Phase B in Anima.~~ Completed 2026-07-18; see `HISTORY.md`.

---

## Refactoring TODOs

- **Add `tags` frontmatter property**: should be `type/bibnote`. This should be configurable in the env.
- **Just changing tags should not trigger update**: Any change (add, remove, update) of the _tags_ frontmatter attribute triggers a full PDF read and update of the annotations. Why? Should not happen.
- **More workflows in README.md**: We should call the text between the frontmatter and the `<hr class="pdf-annot-sep">` the "free text".
- **Implement `--dry-run` Flag**: We still need to implement the logic for the --dry-run argument in `src/pdf_annot/sync.py`.
- **Header/Footer Config**: Add `header_height` and `footer_height` settings to the Env model so they can be set in the `.toml` file.
- **Windows Server**: Dynamic Indexing: The Windows server should pick up additions, renames, and deletions in the PDF folder and recalculate the hash map.
- **`streamline_annotations.py` Refactor**: Refactor `streamline_annotations.py` to fix duplicated logic and inefficiencies (currently postponed).
- **New Scenarios**: Flesh out and test more workflow edge cases (e.g., what happens if a note is missing its frontmatter entirely).
- **Initialize new bibnotes with workflow properties**: New bibnotes should include `status: to-read`, `note_type: bibnote`, `time_spent: 0` in frontmatter, plus the two buttons (`BUTTON[time-spent-increment]`, `BUTTON[resume-pdf]`) in the free text area. These should be configurable in the env.
- **Extract a PDF-identity module from `pdf-annotations`** -- _Needs investigation, deliberately deferred._ `resolve.py` depends on `pdf_registry`, `utils`, and config -- none of which are about annotations. This project is currently both the PDF-identity layer (hashes, index, lookups) and a consumer of it; Anima becoming a second consumer in 2026-07-18 is what made the dual role visible. The candidate shape: a standalone module owning the PDF "database" -- hashing, index construction, path lookup -- used by `pdf-annotations` for Obsidian bibnote generation and by Anima for `pdf://` resolution, with neither depending on the other. **Deferred on purpose, not overlooked.** The pull toward it is aesthetic ("the resolver sits in the wrong place") rather than driven by an observed problem: the resolver CLI contract is frozen, tested, and accepted, and Anima consumes it as a subprocess, so nothing is currently blocked. Scope Skepticism applies -- this is a plausible time sink whose payoff is tidiness. Note that Anima deliberately holds two independent absolute path constants (`projectRoot`, `pdfAnnotationsRoot`) rather than deriving both from a shared parent; the alternative was weighed partly as a deliberate speed bump against starting this refactoring on impulse, and rejected. That means the code contains no friction against it, and **this note is the speed bump instead**. Do not begin it as a side effect of another session. Reconsider when something concrete pushes: a third consumer appears, the resolver contract needs changes that force edits to annotation code, dependency or packaging needs diverge between the two roles, or the `windows_server` teardown reshuffles this project's structure anyway. If it survives that test, promote it to `GOALS.md` for a proper strategy discussion before any code moves.
