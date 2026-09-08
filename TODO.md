# pdf-annotations -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## Tier 1 -- Quick Wins

- **Strengthen existing-note frontmatter safety and make declines operationally loud:** An existing bibnote may be synchronized only when its frontmatter parses as a YAML mapping and it contains the annotation separator. Continue declining notes with missing, malformed, or unclosed frontmatter, and also decline valid YAML whose value is not a mapping, such as a scalar or list. Never discard frontmatter material whose intent cannot be established. Add focused parser/workflow tests proving that non-mapping frontmatter is declined without changing the note. Make a batch containing any declined note exit nonzero so the required manual intervention cannot pass unnoticed, while continuing to report declines separately from unexpected processing errors. A missing bibnote file remains a different case: sync creates it from scratch with generated frontmatter.
- **Report duplicate ids as expected, user-fixable conditions:** `sync.main` currently lets `DuplicatePdfIdError` and `DuplicateNoteIdError` reach the broad handler, which reports them as an unexpected fatal error. Add a targeted handler that preserves the detailed collision report and nonzero exit code but describes the condition accurately. Add focused CLI tests proving that duplicate detection stops the run before synchronization begins and is not labeled unexpected.
- **Single-source the annotation separator and pin its replacement contract with focused tests:** `ANNOT_SEP` exists as a module constant in `sync.py` and as a local string in `notes.py::replace_annotation_block`. Export the separator from `notes.py`, which owns the note-body boundary, and import it in `sync.py`. Before changing the ownership, add focused tests for `replace_annotation_block`: no separator appends the managed block with the established spacing; an existing separator preserves everything before its first occurrence; everything from that separator through EOF is replaced; content below the separator is deliberately not preserved. Keep the existing byte-exact workflow tests green.

---

## Tier 2 -- Low-Priority Maintenance

- **Pin `black` in `requirements.txt`:** It is unpinned while `pre-commit` runs it, so a version bump can reformat unrelated files and produce a diff containing more than the approved change. Determine the formatter version currently used by the project, pin that exact version, and confirm the suite remains all green without accepting unrelated reformatting.
- **Identify the invisible character in `(Liljenberg 2012) A critical study of the thirteen later translations of the Dzogchen mind series.pdf`:** A normalization scan flagged the filename as non-ASCII although it reads as plain ASCII. Inspect and report its Unicode code point and position before deciding whether to rename the file. The character is not in the PDF id, so this is cosmetic library hygiene rather than an identity change.
- **Document the free-text ownership contract in `README.md`:** Establish "free text" as the name for the user-owned region between frontmatter and the first `<hr class="pdf-annot-sep">`. State that sync preserves this region as a whole and regenerates everything from the first separator through EOF. Keep the documentation aligned with `Obsidian/docs/The-Studio-Manual.md`, which already uses the term.
- **Make `render_block()`'s input contract honest:** Its signature promises arbitrary iterables, but it probes `next(iter(annots))`, which consumes the first item of a generator and raises for an empty generator. Decide between materializing the iterable exactly once or narrowing the accepted type to the sequence/list shape the production path actually supplies. Add focused tests for the chosen contract without changing rendered Markdown behavior.
- **Retire historical `FIX` and `NEW` labels:** Perform a dedicated behavior-neutral cleanup of comments that describe development history rather than current rationale. Preserve comments that still explain why the code behaves as it does. Do not combine this with functional changes, reformat unrelated code, or sweep existing typography.
- **Correct thumbnail and dry-run documentation contracts:** Document that ordinary sync performs thumbnail work only for new or changed PDFs; repairing or regenerating a thumbnail for an unchanged PDF belongs to the backfill tool. Qualify the full-fidelity dry-run description: annotation extraction, streamlining, rendering, and note composition are computed, but thumbnail rendering and thumbnail-dependent header composition are skipped because they would write a real JPEG. This is a documentation correction, not a request to move thumbnail handling ahead of the PDF change gate.

---

## Parked -- Concrete Trigger Required

- **Highlight color and role metadata:** Extraction already preserves `colors`, but `streamline_annotations.py::make_output_obj` drops it before rendering. Reconsider this feature only when color or annotation-author roles have become part of the actual PDF-reading practice. At that point, first decide what color and author each mean -- for example highlight function, reader role, or a combination -- then carry the required metadata through the streamlined schema and map it to Obsidian presentation. Do not implement RGB-to-callout behavior before the working convention exists.
- **Per-PDF extraction controls:** One future mechanism may need to support PDF-specific header/footer cutoffs and declarative reading-order sections for multi-column or triple-column pages. Start only with a concrete PDF whose extraction materially obstructs current reading or writing. Before implementation, decide the relationship between code defaults, optional global TOML defaults, and bibnote-frontmatter overrides. Do not build separate header/footer or multi-column frameworks in advance of that witnessed need.
