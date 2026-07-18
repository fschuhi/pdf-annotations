# TARGET_ARCHITECTURE.md -- `pdf://` Link Resolution (Obsidian -> Anima)

Status: agreed design, ready for implementation.

This document is self-contained. Implementation sessions should not require any conversational context beyond this file plus the respective project's filedump.

---

## 1. Purpose and Scope

Clicking a `pdf://` link in Obsidian (macOS) opens the referenced PDF in Anima at the requested page. This replaces two legacy mechanisms:

- **PDFHandler.app** (macOS): to be decommissioned (§7).
- **windows_pdf_server.py** (Windows): remains for the Windows machine but is no longer the reference implementation; its README gains a note (§7).

**Explicitly out of scope (deferred, deliberate):** multi-window/tab support; tolerant duplicate handling (§3.4); JumpStack persistence in PDF metadata; any state-machine formalization of the opening flow; folder monitoring of any kind.

## 2. System Overview

Two projects, one contract:

- **pdf-annotations** (Python) owns PDF identity: controlled filenames, `pdf_id` parsing, `crc32_az7` hashing, folder registry. It gains a resolver CLI -- its public API for toolchain consumers.
- **Anima** (Swift) owns presentation: URL scheme registration, the opening flow, far jumps, alerts.

Anima never imports `pdf_annot`. The boundary is a subprocess: Anima runs the resolver inside pdf-annotations' own venv and consumes stdout/stderr. The contract is the CLI (§3), not the code. Any change to the contract is made and verified in pdf-annotations first; Anima adapts second.

## 3. The Resolver CLI Contract (FROZEN)

### 3.1 Invocation

    <pdfAnnotationsRoot>/.venv/bin/python3 -m pdf_annot.resolve <HASH>

- Working directory MUST be `<pdfAnnotationsRoot>` so that `load_env`finds `pdf_annot.toml` (default-filename-in-CWD resolution).
- `<HASH>` is the `crc32_az7` string as it appears in the URL host. Matching is case-insensitive; the resolver normalizes before comparison.- A console script `pdf-annot-resolve = "pdf_annot.resolve:main"` is also registered in `pyproject.toml` for human terminal use. The bridge uses the `-m` form (no dependence on script installation).

### 3.2 Success

- stdout: the fully qualified path to the PDF, exactly one line, no decoration.
- exit code: 0.

### 3.3 Failure

- stdout: empty.
- stderr: a human-readable message -- this text is shown verbatim in Anima's alert, so it must be deliberate prose, never a traceback.
- exit code: nonzero (1 for all failures; no code taxonomy in v1).

Failure cases and message shapes:

    Cannot resolve pdf://XXXXXXX: no PDF with this id found in the indexed folders.

    Cannot resolve pdf://XXXXXXX: duplicate PDF id "(albini 2013)"
      /Users/frank/Papers/(Albini 2013) On dealing with destructive emotions.pdf
      /Users/frank/Papers/Inbox/(Albini 2013) On dealing with destructive emotions.pdf

    Cannot resolve: configuration error -- <detail from load_env>

### 3.4 Strictness (decided)

The resolver reuses `pdf_registry.build_pdf_index` unchanged. Consequently ANY duplicate `pdf_id` anywhere in `pdf_dirs` fails ALL resolutions, even for unrelated hashes (`DuplicatePdfIdError` is caught and formatted per §3.3). This is intentional: strict enforces diligence. Necessary duplicates are kept outside the indexed folders. A tolerant mode (fail only on duplicates involving the requested hash) is a known, deliberately deferred relaxation.

### 3.5 Statelessness (decided)

The index (hash -> path dictionary) is built per invocation from filenames only (no file contents are read; the walk is `os.walk` + `os.stat`), used for one lookup, and discarded with the process. There is no persisted index, no cache, and no folder monitoring. Every click sees current truth.

### 3.6 Config discovery -- CWD dependence (verify in Phase A)

Working hypothesis: `load_env` locates `pdf_annot.toml` via the process's current working directory, which is why §3.1 mandates CWD = `<pdfAnnotationsRoot>`. This was inferred from the filedump, not verified.

**Instruction to the Phase A implementation session:** verify this before declaring Phase A complete. Run the resolver twice with a known hash: once with CWD inside the repo, once with CWD elsewhere (e.g. `/tmp`) using the absolute path to the venv interpreter. If the second run fails with a config error, the hypothesis is confirmed and §3.1 stands as written. If it succeeds, determine how config is actually found, record it here, and downgrade §3.1's CWD requirement to "harmless but not required."

Provide the user with exact copy-pasteable commands and interpret the output for them. The user does not need to understand the mechanics; the session is responsible for drawing the conclusion and updating this section with the result.

## 4. URL Scheme

    pdf://<HASH>            -> open PDF, restore last position (normal open)
    pdf://<HASH>?page=<N>   -> open PDF, far-jump to page N

- `<N>` is **1-based**. Everything the user sees -- URLs, alerts, UI -- is 1-based; everything internal is 0-based. The single conversion happens at URL parsing time in Anima, nowhere else.
- Malformed or out-of-range `page` values: show alert, do not open/jump.
- URL always wins over restore when `page` is present (decided).

## 5. pdf-annotations: Implementation Notes

- New module `src/pdf_annot/resolve.py` with `main()`: argv parsing -> `load_env` -> `build_pdf_index(pdf_dirs)` -> lookup -> print path / format error per §3.3. Import only `pdf_registry`, `utils`, and config machinery -- nothing heavy (no fitz); per-click subprocess latency depends on it.
- `pyproject.toml`: add the console script alongside the existing three; re-run `make setup` (editable install picks it up).
- No changes to `pdf_registry` or `utils`.

## 6. Anima: Implementation Notes

### 6.1 Registration and constants

- `Info.plist`: `CFBundleURLTypes` entry claiming the `pdf` scheme.
- `AppDelegate` gains `pdfAnnotationsRoot` alongside `projectRoot` -- same one-constant-to-move philosophy, now two projects.

### 6.2 PdfAnnotationsBridge

New type, named for what it is: Anima's dependency on the pdf-annotations project. Header comment states: *the contract is the CLI (§3), not the code*. It is NOT a sibling of `FitzBridge` -- FitzBridge calls Anima's own backend (same repo, same venv); this bridge consumes another project's declared interface. One method: `resolve(hash:) -> path or error-message`, implemented as `Process()` with CWD = `pdfAnnotationsRoot`, capturing stdout and stderr.

### 6.3 URL handler and opening flow

`application(_:open:)` receives the URL. The flow is a linear pipeline with early exits -- deliberately NOT a state machine (decided). Steps, in order, each with failure behavior:

1. **Modal guard** -- if a modal alert/sheet is up, reject the open (beep; no queueing in v1).
2. **Parse URL** -- extract hash and optional page; convert page to 0-based here and only here. Malformed -> alert, stop.
3. **Resolve** -- via bridge. Failure -> alert whose body is the resolver's stderr verbatim, stop. (Launch Services has activated Anima, so the alert appears exactly where the user is looking. This alert IS the replacement for the Windows server console.)
4. **Same-document check** -- if the resolved path equals the currently open document: with `page`, execute a far jump (§6.4); without, just activate. Done.
5. **Different document** -- persist outgoing document's page, clear per-document state (including the in-memory JumpStack, §6.5), load document, load bookmarks, install, then: `page` present -> jump to it; absent -> restore last position.

### 6.4 Far-jump integration

The `pdf://` jump is the **sixth** far-jump source, joining goto-page, both finds, F3, and bookmark jumps. It MUST route through the shared far-jump seam that the refactoring TODO already mandates as a prerequisite for JumpStack. `Cmd+R` after a link click returns to the pre-jump page -- "undoing the Obsidian click."

### 6.5 JumpStack contract (decided; supersedes TODO.md)

In-memory only. Cleared on document change. Therefore `Cmd+R` is within-document **by construction** -- no cross-document history exists or is needed; last-page restore is the cross-document return path (the Obsidian ↔ PDF back-and-forth workflow composes from these pieces).

**Action item:** revise the `TODO.md` JumpStack entry, which currently specifies persistence in private PDF metadata, to in-memory-first with persistence explicitly deferred.

## 7. Decommissioning

- **PDFHandler.app** is an AppleScript applet in `/Applications` that currently claims the `pdf://` scheme (created in an earlier LLM-assisted session; treat it as a black box -- nothing in it needs to be understood or preserved). Decommission procedure: quit it if running, move it to the Trash, empty the Trash, launch Anima once from Finder, then re-run acceptance 8(a)–(c). If clicks still route to the deleted app, log out and log back in -- Launch Services caches scheme routing, and a session restart rebuilds it.
- **Timing note:** while both apps claim the scheme, macOS picks one arbitrarily. If Phase B acceptance clicks open PDFHandler.app instead of Anima, perform this decommissioning immediately (pulling step 11 forward) and continue Phase B testing afterwards.
- **windows_server/README.md**: add a note that the macOS path is now served by Anima + `pdf_annot.resolve`; the server remains Windows-only legacy. Its "restart to rebuild the index" troubleshooting has no macOS equivalent -- the resolver is stateless.

## 8. Work Plan -- Locus of Attention

Rule: one project per session. Contract changes flow pdf-annotations-first, terminal-verified, then Anima adapts.

**Phase A -- pdf-annotations (START HERE):**

1. Implement `pdf_annot/resolve.py` per §5.
2. Register console script; `make setup`.
3. Acceptance (terminal): (a) known hash -> correct path, exit 0; (b) unknown hash -> §3.3 message, exit 1; (c) stage a duplicate by copying a PDF into a second indexed folder -> strict error listing both full paths; remove the copy afterwards; (d) confirm no fitz import (e.g. time it / inspect imports); (e) perform the CWD-dependence verification per §3.6 and record the outcome in that section.

**-> SWITCH to Anima when all of step 3 passes. Contract is now frozen.**

**Phase B -- Anima:**

4. `Info.plist` URL type; `pdfAnnotationsRoot` constant.
5. `PdfAnnotationsBridge` per §6.2.
6. URL handler + opening-flow integration per §6.3–6.4.
7. Alert plumbing: resolver stderr verbatim as alert body.
8. Acceptance (clicking real links in Obsidian): (a) link to open document + page -> far jump, `Cmd+R` returns; (b) link to different document + page -> opens at page; reopening the previous document restores its last page; (c) link without page -> opens with restore; (d) unknown hash -> alert with §3.3 text; (e) staged duplicate -> alert with both paths; (f) malformed page -> alert, no action.

**-> SWITCH back to pdf-annotations ONLY if a contract inadequacy surfaces in Phase B; fix and re-verify there first.**

**Phase C -- cleanup (either project's session, doc-only + Anima):**

9.  Revise `TODO.md` JumpStack entry per §6.5.
10. Windows server README note per §7.
11. Decommission PDFHandler.app per §7.
12. Re-run acceptance 8(a)–(c) once more after decommissioning (Launch Services can misroute schemes after handler changes).

## 9. Deferred Decisions Ledger

Tolerant duplicate resolution; JumpStack persistence in PDF metadata; multi-window/tabs; queueing URL opens behind modals; exit-code taxonomy; state-machine formalization of the opening flow. Each was consciously skipped, not forgotten.
