# TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter
- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

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
