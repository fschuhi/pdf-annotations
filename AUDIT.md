# AUDIT.md -- Production-Readiness Audit of `src/pdf_annot/`

Status: audit complete (2026-07-21). Findings dispositioned, implementation agenda ready.

This document is self-contained in the spirit of `TARGET_ARCHITECTURE.md`: implementation sessions should not require conversational context beyond this file plus the project filesdump. `CRITICAL_RULES.md` applies to all work derived from this document -- in particular Rule 3 (Discuss -> Approve -> Implement), Rule 4 (step-by-step), and Rule 5 (tests are the spec).

---

## 1. Charter and Protocol

**What this audit was:** a module-by-module walk of every production module, triggered by the system going into real use (Zotero retired, 244 bibnotes migrated, ~1361 PDFs still to transfer, target scale 1600+).

**Axes, in priority order:** (1) data safety, especially free-text preservation -- Anima modifies the PDF on every open, so the merge path is the hot path; (2) partial-failure behavior -- one bad PDF among 1600 must not kill or corrupt a run; (3) idempotency; (4) performance only where pathological. Measured baseline: full run over 244 files < 1s; worst single PDF ~10s.

**Walk order:** `env.py` -> `pdf_discovery.py` + `pdf_registry.py` + `utils.py` (identity half) -> `notes_db.py` -> `sync.py` -> `notes.py` + `frontmatter.py` -> `annotation.py` + `extract.py` -> `streamline_annotations.py` + `ndjson_to_md_block.py` -> `resolve.py` + `utils.py` (remainder).

**Disposition vocabulary:** *closed* (no action, rationale recorded); *record-only* (known, deliberately not acted on); *act* (agreed change, assigned to an implementation session); *open decision* (needs a strategy discussion before it is actionable). Findings are labeled distinctly from preferences throughout.

**The systemic diagnosis, in one paragraph:** the domain logic (extraction heuristics, streamline state machine, merge, resolver) is sound and often carefully documented. The recurring weakness is one pattern appearing five ways (F18, F19, F30, profiles, identity freight): dormant twins and dead parameters left standing after direction changes, undocumented as such. They confuse sessions and, in the worst case (F18/F19), absorbed the atomic writer while the production path went unprotected. The counter-evidence is `resolve.py`, the newest and best module: built against a frozen, detailed contract (`TARGET_ARCHITECTURE.md`), it had fewer degrees of freedom and shows no fuzziness. This document applies the same technique to the audit findings.

---

## 2. Verified Strengths (no action)

- `_atomic_write_file` (`notes_db.py`): textbook durable write -- temp file in same dir, fsync file, `os.replace`, fsync directory. Correct; currently mis-homed (see F18).
- Partial-failure design (`sync.py`): per-PDF try/except returning `UpdateResult(error)`, error counting, run continues, exit code 1 on any error. A corrupt or dematerialized PDF degrades to one error line.
- Idempotency (`frontmatter.upsert_fields`): byte-identical return when nothing changed.
- Page-numbering contract: single 0-based -> 1-based conversion in `render_block`; URL carries 1-based; Anima converts back at URL parse (`TARGET_ARCHITECTURE.md` section 4). Verified end to end.
- `resolve.py`: contract messages as test-imported constants, deliberate error taxonomy, lightweight imports honored.
- Extraction docstrings (`extract.py`): the three-problem rationale (stray characters, footnote leakage, ordering) is genuinely good documentation.

---

## 3. Act Ledger -- The Implementation Agenda (approved order)

Each item: what, why, spec-first test note. Work one item per step; Discuss -> Approve -> Implement applies within each.

**A1 (F18) -- Route production writes through the atomic writer.** `sync_pdf_to_note` step 9 uses plain `note_path.write_text(...)`. Move `_atomic_write_file` to a shared home (e.g. `utils.py`) and use it in sync. The config knob `io.atomic_writes` is consulted nowhere; make the behavior unconditionally atomic and remove the knob (fold into A9/open decision D2 scope). Test: hard to test crash-atomicity directly; assert the write path calls the atomic helper (or refactor so the direct write no longer exists). **Split and partly landed 2026-07-22.** A1a: `atomic_write_file` moved to `utils.py`, `sync.py` step 9 routes through it; covered by a spy test and a source tripwire in `test_sync_cli.py`. A1b (remove the `io.atomic_writes` knob) deferred into A9/D2 scope -- two tests in `test_env.py` assert on the knob, so removing it is not free and does not belong in a data-safety step.

**A2 (F12 + F23) -- Decline-guards: sync writes only to notes it fully understands.** Two conditions, one rule: (a) existing non-empty note whose body lacks `<hr class="pdf-annot-sep">` -> decline, report, write nothing (rationale: an accidentally deleted sep otherwise causes silently recurring block duplication on every PDF touch); (b) existing note whose frontmatter fails YAML parsing -> decline, report (currently a fresh frontmatter is prepended above the broken one -- no loss, but mangling). Tests are the spec: seed each condition, golden expects the file byte-identical plus an error entry in the run report. This retires the `TODO.md` scenario item "note is missing its frontmatter entirely" with a defined answer. **Landed 2026-07-22.** The rule got simpler during implementation than as specified above: the `<hr>` alone answers "is this a bibnote", so the info span carries no diagnostic weight (a fresh extract always supplies a fresh info message). Two conditions, checked in order, in `sync._decline_reason`, ahead of the change gate. A decline reports on its own line with a reason and a `Declined:` counter, and deliberately does not affect the exit code -- errors are transient, declines are standing, and mixing them would make the error count permanently non-zero. Fixture: `tests/fixtures/workflow_declines/`.

**A3 (F22, retires F21) -- Normalized change-detection comparison.** Mechanism, confirmed: Obsidian's property editor rewrites frontmatter on any property edit and unquotes `pdf_mtime`; `yaml.safe_load` then yields a `datetime` instead of a string; `_pdf_has_changed` compares datetime != string, always true -> full re-extract; sync rewrites the value quoted, re-arming the trap. Empirically verified 2026-07-21: adding free text does not unquote; editing `tags` does. Fix: compare normalized values (parse both sides to a common type) instead of raw. Side benefit: also removes the machine-timezone-change re-extract class (plain DST switches were never a problem -- `fromtimestamp` applies the offset valid at the timestamp). Retires the `TODO.md` mystery item "Just changing tags should not trigger update". Test: frontmatter with unquoted timestamp, unchanged PDF -> gate stays closed.

**A4 (F26 + F27) -- Extraction performance: per-page caching; close documents.** `extract_highlight_text` calls `page.get_text("words")` and `_get_superscript_regions` (which runs `page.get_text("dict")`) once PER HIGHLIGHT. Compute both once per page in `extract_annotations` and pass them in; expected 5-10x on highlight-dense pages, the ~10s outliers should drop to seconds. Also: `fitz.open` results are never closed -- add try/finally or context manager (matters for full-library passes). Instrument FIRST: one timing line around `sync_pdf_to_note` in the main loop, printing durations above ~1s -- ranked culprit list before the fix, victory lap after, permanent early-warning sensor. Test: existing extraction fixtures must stay green (behavior-neutral refactor); timing is manual evidence.

**A5 (F9 + F17) -- Tighten the id gates; share the predicate.** `is_controlled_pdf_name` must require a year (`\d{4}` plus optional disambiguation letter, e.g. `2006b`) after the authors -- the gate is the discriminator between old-system and new-system references, and year-less old ids like `(Smilek2011)` currently pass silently as a different identity. The notes-side gate (`CONTROLLED_MD_RE` in `notes_db.py`) accepts any parenthesized id; extract one shared id-validation predicate used by both gates so they cannot drift. PRECONDITION: sanity-pass the 244 migrated filenames against the stricter pattern before landing (see section 5, V2). Update the `is_controlled_pdf_name` docstring (its `(OnlyAuthors)` example inverts). Tests: year-less bracket name -> not controlled; both gates driven by the same predicate.

**A6 (F29 + F32 revised) -- Tighten annotation types; keep the textbox signal.** Drop Squiggly, StrikeOut, Underline from `TEXTUAL_ANNOTS` and from the stats counting (Anima emits only highlights and comments; zero real-world usage of the other marker types). KEEP Text/FreeText in extraction so `pdf_textboxes` continues to count them -- the stat is retained permanently: it is the Dataview migration-debt tracker for PDFs with unconverted legacy textboxes AND the signal for author-supplied textboxes. The streamliner keeps filtering them from rendering. Document the counted-but-never-rendered asymmetry as intent in `README.md`. Also sharpen the wording of the `TODO.md` item "Highlight Color as Metadata" while in the area. Tests: stats fixture with a squiggly -> not counted; with a textbox -> counted, not rendered.

**A7 (F30) -- One streamline state machine.** `process_objects` (list twin) has no production caller; `streamline_annotations_list` serializes the list to NDJSON, runs `process_stream`, and parses the output back. Refactor: `process_objects` becomes the single state machine; `process_stream` becomes a thin parse -> call -> dump wrapper; delete the round-trip. Upgrades the existing `TODO.md` refactor item from "fix duplication" to this concrete target. Tests are the spec: all streamline fixtures and unit tests must pass unchanged.

**A8 (F19, decision D1 first) -- Resolve the plan/apply fork.** See open decision D1. Whichever branch wins, the end state is one pathway and no dormant twin, with the retired branch recorded in `HISTORY.md` (pattern name, retirement date, commit reference for resurrection).

**A9 (F10 + F4) -- Remove dead freight.** Batch: `dropbox_root` parameter, `PdfInfo.dropbox_rel_path`, `_posix_relpath_if_under` (registry); `hash_text`, `pdf_id_from_filename`, dash-format branch in `parse_filename` (utils); profile machinery -- `[envs]` indirection, `CLI.default_env` (env). PRECONDITION: grep `tools/` (outside the standard filesdump) for imports of any of these before deleting (section 5, V1). Tests: suite green after each removal.

**Ride-alongs (attach to whichever agenda item touches the file, never standalone):** F8 collect-all duplicate reporting instead of first-only (registry and notes_db, rides with A5); F6 unify the two PDF walkers -- `rglob("*.pdf")` in `pdf_discovery.py` is case-sensitive on macOS while the registry walker is not, so the diagnostic can under-report vs sync (rides with A9); F24 single owner for the default info text -- `extract_info_text` hardcodes what `env.py`'s `DEFAULT_INFO_TEXT` owns (rides with D2's outcome); F16/P7 docstring drift in `notes_db.py` and `frontmatter.py`; P1/P2/P8/P9/P10 cosmetic items (scar comments, duplicate validators, parallel type-name lists) -- only on lines an approved change already touches.

**A10 (F35) -- Doc edits (no code).** (a) `TARGET_ARCHITECTURE.md` section 3.6: record the outcome -- CWD dependence confirmed from `load_env` source (resolution order: explicit source -> `PDF_ANNOT_ENV_PATH` env var -> default filenames in CWD); section 3.1 stands as written. Add one sentence noting `PDF_ANNOT_ENV_PATH` as an undocumented precedence that would silently override the CWD convention if ever set in Anima's subprocess environment. (b) `README.md`: add the production call-path contract -- which functions `sync.py` actually calls (`build_pdf_index`, `NotesDB` as index only, `extract_annotations_to_list`, `streamline_annotations_list`, `render_block`, `extract_info_text`, `replace_annotation_block`) -- so pathway drift like F18/F19 cannot go unnoticed again. (c) `README.md` philosophy: add the source-of-truth sentence -- the PDF is the single source of truth for highlights and comments; the bibnote is a service (cross-book search, citation raw material); extraction is heuristic and will never be perfect, by design.

---

## 4. Open Decisions

**D1 -- Plan/apply fork (blocks A8; decide at session start, five minutes, `GOALS.md`-grade).** The `notes_db.py` plan/apply layer (~300 lines: frontmatter and annotation planning, apply with dry-run, the atomic writer, `_compose_new_note_text`) has no production caller; `sync.py` uses the direct `notes.py` path. Options: (a) DELETE plan/apply; port atomicity (A1) and dry-run into the direct path; preserve the pattern via git history plus a `HISTORY.md` entry. (b) RECONNECT plan/apply as the production path; it already has dry-run, atomic writes, and structured summaries; but its annotation merge (`_compose_new_note_text`) discards the body when the sep is missing (the original F12 wipe) and would need the A2 decline-guard semantics ported into it; its frontmatter planner carries speculative generality (dict-or-attr duck typing, a default `title_from_filename` attribute no producer has). Auditor's recommendation: (a) -- the pattern's payoffs are portable in ~30 lines, standing unused machinery is what caused F18/F19, and resurrection-from-git when a future tool genuinely needs batch preview is the same speed-bump philosophy as the PDF-identity-module note in `TODO.md`. Note: `--dry-run` currently parses and silently does nothing (F20) -- worse than absent; whichever branch wins must make it real. **DECIDED 2026-07-22: (a) DELETE.** Execution belongs to A8. `HISTORY.md` gets the retirement entry with the commit reference when the code is actually removed -- not before.

**D2 -- Config surface: constants vs knobs.** User position: fine with constants; the configurable frontmatter key names (`Frontmatter` model), `io.atomic_writes`, and profile machinery predate the Scope Skepticism principle. Scope: fold the frontmatter key names into code constants (single home, F24's info-text default joins them), remove dead knobs (A1, A9). Keep as config: paths, and (new) the per-PDF extraction knobs from D3. Decide the exact keep/fold list before A9 executes.

**D3 -- Per-PDF extraction knobs via frontmatter (promote to `TODO.md`/`GOALS.md`).** Pattern: bibnote frontmatter as per-PDF extraction config, read by sync before extraction -- `header_height: 45`, later `reading_order: ...`. Unifies two existing `TODO.md` items (header/footer config; multi-column) under one mechanism. Multi-column direction per user: declarative section maps ("pages 3-7: two columns", triple columns exist) rather than auto-detect (first tests failed); long-term, <2% of PDFs affected.

**D4 (F7) -- Hash-collision guard as a contract addition.** The resolver returns the first `pdf_hash` match; a CRC32 collision between two ids (~0.03% lifetime probability at 1600 files) would open the wrong PDF silently. Guard: collect all matches, fail with both paths if >1. This is a new failure case in the frozen section 3.3 contract, so it flows pdf-annotations-first (define message shape, test, implement), then Anima consumes it as another verbatim stderr alert. Small; approve the contract addition explicitly before coding.

---

## 5. Instructions to the Implementation Sessions (section-3.6-style)

**V0 -- Baseline.** Before any change: `make test`, record the green baseline. After every agenda item: `make test` again; a red suite after your change is your bug (Rule 5).

**V1 -- `tools/` grep (blocks A9).** The `tools/` scripts are outside the standard filesdump. Before deleting any A9 freight, grep `tools/concat_files.py`, `tools/discover_pdfs.py`, `tools/print_hashes.py` for: `hash_text`, `pdf_id_from_filename`, `dropbox_root`, `dropbox_rel_path`, `profile`, `default_env`, and the dash-format parsing. Record findings here; delete only what is confirmed orphaned.

**V2 -- Filename sanity pass (blocks A5).** Run the stricter year-required pattern against all current controlled PDF filenames (e.g. via `make discover-pdf-names`) BEFORE the gate lands. Every current file must still pass; any that would not is either a naming fix in the filesystem or a deliberate pattern widening -- surface it, do not silently widen.

**V3 -- Timing evidence (frames A4).** Add the timing instrumentation first, run over the full collection, capture the slow list. Apply the per-page caching. Re-run, capture again. Record before/after here; the slow-PDF gut feeling deserves numbers for its funeral.

**V4 -- Session bookkeeping.** Per `LLM_INSTRUCTIONS.md` session workflow: dated `HISTORY.md` entry per completed agenda item; strike through the corresponding `TODO.md` items; update the Current Session Pointer in `GOALS.md`; keep this document's ledger current (mark agenda items done with date).

---

## 6. Record-Only Ledger (known, deliberately not acted on)

- F2: `env.py` flat-key fallback uses a falsy check, so a grouped `atomic_writes = false` could be overridden by a flat key. Contrived; likely moot after D2.
- F11 (ops, not code): pin `Collection/PDFs` "available offline" in Dropbox -- dematerialized placeholders would fail per-file (gracefully, per sync's error handling) if the setting slips during disk-space fiddling. One-time user action.
- F21: machine-timezone change (not DST) would trigger a one-time full re-extract; self-healing; retired entirely by A3.
- F25: custom info text containing `<` silently reverts to the default (regex `[^<]+`). Muscle-memory protected.
- F31: consecutive `link` annotations after the first are dropped, per the `consecutive_links` fixture (tests are the spec). Real usage: at most one `link` per page, always the first annotation, page-boundary discipline (previous page ends at the last regular character, next page starts at the first; footnote content travels in comments as "fn N: ..." instead of footnote highlights). If this code is ever touched: the preferred semantics for a malformed consecutive link is unfused pass-through (own annotation), NOT the current silent drop -- a fused non-contiguous highlight would be malformed anyway (missing `(...)`).
- F33: `render_block`'s dict-vs-Annot sniff (`next(iter(annots))`) would consume the first element of a generator; production passes lists. API tripwire.
- Resolver loads the full `Env`, so a `pdf://` click validates (and with `create_missing_dirs`, would create) `notes_root`, which the resolver never uses. Harmless coupling; noted against surprise.
- P11: `streamline_annotations_list` ignores `process_stream`'s return code (silent truncation on malformed input); dies with A7's round-trip deletion.
- P12: synced files end without a trailing newline (`render_block` pops the final blank). POSIX pedantry.

---

## 7. Closed Ledger (rationale recorded)

- F1 (auto-create `notes_root`): accepted convenience -- exactly one root, stable config, flat note store by design (workbenches organize the Zettelkasten, not folders).
- F3 (symlinks vs `resolve()`): all configured paths normalize to real paths; true paths in config are the convention; symlinks remain a chat/terminal convenience.
- F12-original (body wipe on missing sep in `_compose_new_note_text`): exists only in the dormant plan/apply path; production merge (`notes.replace_annotation_block`) appends and never discards. Superseded by A2's decline-guard; D1 decides the dormant code's fate.
- F13 (machine territory): everything from the sep to EOF is regenerated tool property -- confirmed design; all commentary lives above the sep (muscle memory) or in The Studio. The single-sep pressure is a feature: it keeps a bibnote a bibnote. Second-sep "endnotes" region recorded as a future idea in `TODO.md`, deliberately not now.
- F28 (header/footer-clipped highlights extract empty): accepted -- extraction is heuristic by philosophy (see A10c); empty extractions render as visible stubs, honestly showing the failure; per-PDF knobs (D3) make the fiddling easier.
- P4 (nested parentheses in ids): excluded by convention; the id is a filing handle, not a bibliography entry.

---

## 8. Correlation with `TODO.md` and `GOALS.md`

`TODO.md` items affected: "Implement --dry-run" (resolved by D1/A8, either branch); "streamline refactor" (sharpened into A7); "Just changing tags should not trigger update" (explained and retired by A3); "New Scenarios ... missing frontmatter" (answered by A2); "Header/Footer Config" (subsumed by D3); "Multi-Column Support" (direction recorded in D3); "Highlight Color as Metadata" (wording sharpen rides with A6); "Fix old IDs" (related to A5's gate -- old-style ids in note filenames will surface as orphans once gates are strict).

New `TODO.md` entries to add: second-sep "endnotes" region (from F13, with the keep-bibnotes-short counterargument recorded as its own speed bump); per-PDF extraction knobs pattern (from D3, or `GOALS.md` if it needs strategy discussion first); F11 pin-offline one-time ops action (delete after doing it).

`GOALS.md`: Current Session Pointer update provided separately as a patch; the pending `pdf_ctime` items (batch tool; frontmatter generation) remain queued behind the audit agenda and are untouched by it -- note only that A3's normalization work is adjacent to how `pdf_ctime`/`pdf_mtime` values will be compared, so implement A3 first.
