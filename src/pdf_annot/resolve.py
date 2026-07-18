# src/pdf_annot/resolve.py
"""
Resolver CLI: map a `crc32_az7` hash (from a `pdf://<HASH>` URL) to a PDF path.

This is pdf-annotations' public interface for toolchain consumers (notably Anima).
The contract -- invocation, stdout/stderr, exit codes, message shapes -- is frozen
in TARGET_ARCHITECTURE.md section 3. The messages below ARE that contract; they are
shown verbatim in Anima's alert, so they must stay deliberate prose, never a traceback.

Invocation (section 3.1):
    <pdfAnnotationsRoot>/.venv/bin/python3 -m pdf_annot.resolve <HASH>

Success (section 3.2): print the absolute path (one line), exit 0.
Failure (section 3.3): empty stdout, a human-readable message on stderr, exit 1.

Intentionally lightweight: imports only config machinery and pdf_registry -- no fitz,
no heavy modules -- because per-click subprocess latency depends on import time.
"""
from __future__ import annotations

import sys

from .env import load_env
from .pdf_registry import DuplicatePdfIdError, build_pdf_index

# --- Contract message templates (TARGET_ARCHITECTURE.md section 3.3) ----------
# Single source of truth: tests import these and assert against them, so the
# wording cannot drift from what the code emits.

NO_MATCH_MSG = "Cannot resolve pdf://{hash}: no PDF with this id found in the indexed folders."

DUPLICATE_MSG = 'Cannot resolve pdf://{hash}: duplicate PDF id "{pdf_id}"\n{paths}'

CONFIG_ERROR_MSG = "Cannot resolve: configuration error -- {detail}"

# Exit codes: 1 for all failures; no code taxonomy in v1 (section 3.3).
EXIT_OK = 0
EXIT_FAIL = 1

# Usage message for the one shape of argv error we can hit.
USAGE_MSG = "Usage: python -m pdf_annot.resolve <HASH>"


def _fail(message: str) -> int:
    """Print a contract-shaped failure message to stderr and return the failure code."""
    print(message, file=sys.stderr)
    return EXIT_FAIL


def resolve(hash_arg: str) -> int:
    """Resolve one hash to a path, printing per the section 3 contract.

    Returns the process exit code. Kept separate from main() so the argv handling
    and the resolution logic are testable independently.
    """
    normalized = hash_arg.strip().upper()

    # 1) Load config. Any failure here is a configuration error (section 3.3).
    try:
        env = load_env()
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: any config failure maps to one message
        return _fail(CONFIG_ERROR_MSG.format(detail=exc))

    pdf_dirs = [str(d) for d in env.paths.pdf_dirs]

    # 2) Build the index. Strict duplicate handling: ANY duplicate anywhere fails
    #    ALL resolutions (section 3.4).
    try:
        index = build_pdf_index(pdf_dirs)
    except DuplicatePdfIdError as exc:
        paths = "\n".join(f"  {p}" for p in sorted(exc.paths))
        return _fail(DUPLICATE_MSG.format(hash=normalized, pdf_id=exc.pdf_id, paths=paths))

    # 3) Look up by hash. The index is keyed by pdf_id.lower(), so scan values for
    #    a matching pdf_hash (case-insensitive). Cheap: the walk already dominated.
    for info in index.values():
        if info.pdf_hash.upper() == normalized:
            print(info.abs_path)
            return EXIT_OK

    return _fail(NO_MATCH_MSG.format(hash=normalized))


def main(argv: list[str] | None = None) -> int:
    """Entry point for both `-m pdf_annot.resolve` and the console script."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return _fail(USAGE_MSG)
    return resolve(args[0])


if __name__ == "__main__":
    sys.exit(main())
