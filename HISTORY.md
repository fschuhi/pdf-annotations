# pdf-annotations -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file.

---

## Focused Architecture Review and Backlog Reset

- Focused production-path architecture review completed (2026-08-06): traced entry and indexing, structural and change-detection safety gates, annotation transformation, and preservation-aware composition through the single atomic note write. The review found no major architectural problems and no reason to expand into a broader subsystem audit. The remaining findings were local and bounded rather than signs of confused ownership.
- `TODO.md` was aggressively streamlined and prioritized around the role of the project: supporting work with books, highlights, PDFs, and ideas in Obsidian rather than becoming a development destination of its own. The active backlog now contains a few quick witnessed corrections and low-priority maintenance tasks; only highlight color/role metadata and per-PDF extraction controls remain parked behind concrete-use triggers.
- `HISTORY.md` was compressed into a lower-maintenance, append-oriented record. It retains milestone outcomes, architectural rationale, reversal warnings, measurements, and recovery pointers while leaving current contracts to `README.md` and forward work to `TODO.md`.

## Synopsis Feature

- ISBNdb synopses added to bibnotes (2026-08-02): `pdf_annot/synopsis.py` formats a `<pdf_id>.txt` file from `haddolib`'s `isbndb_synopsis.py` as an Obsidian abstract callout, while `notes.py` detects and inserts the callout without duplicating an existing hand-written synopsis. Insertion is handled only by `tools/fill_synopses.py` (`make fill-synopses`), not by ordinary sync: fetching a synopsis is a manual operation, and scanning the full collection during every `make run` would add work without value. Insertion is permanent rather than refreshable; to replace a synopsis, delete its callout manually and rerun the tool.
- The feature introduced `paths.synopses_dir`. The directory is read-only from this project's perspective and is never auto-created, because absence usually means the preceding ISBNdb export step was skipped; silently creating an empty directory would hide that configuration error. Individual bibnotes were live-tested successfully through the tool's `--pdf-id` option.

## Page-1 Thumbnails

- Page-1 thumbnails added (2026-07-26): sync creates them for new or changed bibnotes when `thumbnails_dir` is configured, while `tools/backfill_thumbnails.py` handles the existing collection and explicit regeneration. Thumbnails are optional derived sidecars, so rendering failure is reported without blocking the primary frontmatter and annotation update.
- JPEGs are named by `pdf_id`, not `pdf_hash`: the hash is Anima link-resolution plumbing and has no reason to surface in the vault. Display width, Retina render scale, and JPEG quality were tuned by eye and retained as code constants rather than configuration. New bibnotes can receive the resume-PDF button and thumbnail span as a header; existing bibnotes are only given the thumbnail span.

## `pdf_ctime` Frontmatter Field

- `pdf_ctime` added (2026-07-25): a one-time batch tool (`tools/add_pdf_ctime.py`) backfilled existing bibnotes from `pdf_mtime`; sync now seeds it for every new bibnote and leaves it untouched on existing ones.

## Vault under Version Control

- The Obsidian vault was placed under local Git version control (2026-07-25; not pushed remotely at that point). The workflows span Terminal operations such as `make run`, Anima, and Obsidian, all of which can modify notes or related files. `git diff` makes the effects of an operation inspectable across those moving parts, while rollback provides risk management and confidence when automated work touches a large collection.

## Post-Audit Cleanup

- Filesdump integrity restored (2026-07-24): `make gentree` wrote `tmp/project_tree.txt` while `manifest.lst` included a differently named stale file. This undermined the intended filesdump integrity check by presenting an obsolete project tree as current context. The manifest was corrected to include the file actually generated, and the remaining gaps between the tree and curated dump were closed.
- `NotesDB` retired for `build_notes_index` (2026-07-24): after the audit cleanup, the class had become a wrapper that mostly re-exposed the dictionary interface it contained. `notes_db.build_notes_index(notes_root)` now returns a plain `dict[str, NoteInfo]`, mirroring `pdf_registry.build_pdf_index`; callers own lowercase lookup normalization. Do not restore a container without a concrete responsibility that a dictionary cannot provide. The retired implementation remains recoverable from commit `615200c` with `git show 615200c:src/pdf_annot/notes_db.py` and `git show 615200c:tests/test_annotations.py`.
- `paths.backup_dir` retired (2026-07-24): it reserved configuration for a backup mechanism that never existed. Validation, directory creation, and tests made the setting appear consumed even though no production behavior used it. The durable lesson is that configuration can hide behind tests that only assert the configuration itself. Stale `backup_dir` keys in a live config are ignored by the Pydantic model.

## Production-Readiness Audit

- Production-readiness audit completed (2026-07-21 through 2026-07-24): note writes became atomic; sync gained decline guards for existing notes it could not safely recognize; timestamp comparison began normalizing Obsidian's quoted and unquoted YAML values; PDF and note discovery adopted shared identity rules; and list and NDJSON streamlining converged on one state machine. The live production path was simplified to direct extraction, streamlining, rendering, preservation-aware composition, and one protected note write.
- Extraction began caching page words and superscript regions lazily once per highlighted page, reducing the measured 244-PDF extraction pass from 362.67 seconds to 144.54 seconds. Dead configuration, legacy identity helpers, inactive pathways, and unearned abstractions were removed. The resulting source-of-truth contract was made explicit: PDFs are authoritative for highlights and comments, while bibnotes are useful derived services and extraction remains heuristic by design.
- `docs/AUDIT.md` preserves the full evidence ledger and development history. This entry records the durable outcome rather than duplicating that investigation.

## `pdf://` Resolution and Anima Integration

- Resolver CLI completed (2026-07-18): `src/pdf_annot/resolve.py` established the public subprocess contract that maps a `crc32_az7` hash from a `pdf://<HASH>` URL to an absolute PDF path. Anima consumes the CLI contract through stdout, stderr, and exit codes rather than depending on the Python API.
- The resolver was kept lightweight and stateless: it reuses configuration and PDF-index construction, imports no PyMuPDF code, and rebuilds the filesystem index for each click. Strict duplicate handling was retained so any ambiguous PDF identity prevents resolution rather than selecting an arbitrary file. Real-library acceptance confirmed known-hash resolution, unknown-hash reporting, duplicate detection, and the requirement that Anima launch the resolver with the project root as its working directory unless `PDF_ANNOT_ENV_PATH` explicitly selects another config.
- The macOS-native transition completed (2026-07-19): Anima became the sole `pdf://` handler, the former `PDFHandler.app` was retired, and the Windows-server path became legacy. `docs/TARGET_ARCHITECTURE.md` preserves the completed cross-project contract and acceptance record.
