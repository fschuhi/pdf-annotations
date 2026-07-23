#!/usr/bin/env python3
"""Time annotation extraction per PDF. Read-only.

Produces the ranked "slowest first" list that AUDIT.md V3 asks for, once before
the A4 per-page caching change and once after. The run is deliberately
read-only: each PDF is opened for reading only, nothing is written anywhere, no
note is touched, and no pdf_mtime changes -- so the sync change-gate stays
closed and a timing run costs nothing but time.

It walks the same index sync walks (build_pdf_index over env.paths.pdf_dirs)
rather than the discovery helper, so the measured set is the set sync actually
processes.

Progress goes to stderr, the report to stdout, so

    make time-extraction > before.txt

leaves the report in the file while you watch the run on screen.

MuPDF's own error messages ("format error: object ... was not found in its
object stream") go to STDOUT, not stderr, so they land in the redirected report
instead of next to the progress line that would identify the file they came
from. Attributing them needs fitz.TOOLS.mupdf_display_errors(False) plus a
per-file read of fitz.TOOLS.mupdf_warnings(); recorded in AUDIT.md, not done
here.

The report carries two independent cost drivers:

  hl/hlpg = highlights per page that carries highlights
      How many highlights share a page, and therefore share one page-text
      extraction. Before A4 this was the predicted speedup from per-page
      caching; since A4 landed it describes how much that change was worth for
      this file. It is NOT a forecast of any further gain -- the caching has
      already happened.

  ms/hl = milliseconds per highlight
      How expensive a single highlight is for this PDF. It varies by more than
      20x across the collection (born-digital text layers are cheap, OCR'd
      scans are not), A4 did not touch it, and since A4 it is the dominant
      remaining driver of extraction time.

Counting note: the highlight count here is true Highlight annotations only,
which is what drives the cost (extract_highlight_text runs for those alone).
It intentionally doesn't include Squiggly, StrikeOut and Underline.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Ensure src/ is on sys.path for direct script execution
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pdf_annot.env import load_env  # noqa: E402
from pdf_annot.extract import extract_annotations_to_list  # noqa: E402
from pdf_annot.pdf_registry import build_pdf_index  # noqa: E402

PROGRESS_NAME_WIDTH = 64


@dataclass(frozen=True)
class Timing:
    """One PDF's measurement."""

    seconds: float
    pages: int
    highlights: int
    highlight_pages: int
    filename: str

    @property
    def highlights_per_highlight_page(self) -> float:
        """Highlights divided by the pages carrying them. See the module docstring."""
        if self.highlight_pages == 0:
            return 1.0
        return self.highlights / self.highlight_pages

    @property
    def ms_per_highlight(self) -> float:
        """Cost of a single extract_highlight_text call, in milliseconds."""
        if self.highlights == 0:
            return 0.0
        return self.seconds / self.highlights * 1000.0


def time_one(pdf_path: str) -> Timing:
    """Extract one PDF and measure how long it took.

    Returns the timing plus the two numbers the prediction needs: how many
    highlights there are, and how many distinct pages carry them.
    """
    start = time.perf_counter()
    annotations, stats = extract_annotations_to_list(Path(pdf_path))
    seconds = time.perf_counter() - start

    highlights = [a for a in annotations if a["annotType"][1] == "Highlight"]
    highlight_pages = {a["pageNum"] for a in highlights}

    return Timing(
        seconds=seconds,
        pages=int(stats["pdf_pages"]),
        highlights=len(highlights),
        highlight_pages=len(highlight_pages),
        filename=Path(pdf_path).name,
    )


def _progress_start(index: int, total: int, name: str) -> None:
    """Announce the file before opening it, so MuPDF's own errors are attributable."""
    shown = name if len(name) <= PROGRESS_NAME_WIDTH else name[: PROGRESS_NAME_WIDTH - 3] + "..."
    print(f"[{index:>4}/{total}] {shown:<{PROGRESS_NAME_WIDTH}} ", end="", file=sys.stderr, flush=True)


def _progress_end(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def run(env_path: Optional[str]) -> Tuple[List[Timing], List[str]]:
    """Time every PDF in the index. Returns (timings, error lines).

    One bad PDF must not end the run -- same partial-failure stance as sync.
    """
    env = load_env(env_path)
    pdf_index = build_pdf_index([str(p) for p in env.paths.pdf_dirs])
    total = len(pdf_index)

    timings: List[Timing] = []
    errors: List[str] = []

    for index, (_pdf_id_lower, pdf_info) in enumerate(pdf_index.items(), start=1):
        _progress_start(index, total, pdf_info.filename_with_ext)
        try:
            timing = time_one(pdf_info.abs_path)
            timings.append(timing)
            _progress_end(f"{timing.seconds:>7.2f}s")
        except Exception as e:  # noqa: BLE001 -- report and continue, as sync does
            errors.append(f"{pdf_info.filename_with_ext}: {e}")
            _progress_end("  FAILED")

    timings.sort(key=lambda t: t.seconds, reverse=True)
    return timings, errors


def print_report(timings: List[Timing], errors: List[str], top: int) -> None:
    """Print the ranked list and the totals, in a shape that pastes into AUDIT.md."""
    shown = timings if top <= 0 else timings[:top]

    print(f"{'secs':>7}  {'pages':>5}  {'hl':>4}  {'hlpg':>4}  {'ms/hl':>6}  {'hl/hlpg':>7}  file")
    print("-" * 90)
    for t in shown:
        print(
            f"{t.seconds:>7.2f}  {t.pages:>5}  {t.highlights:>4}  {t.highlight_pages:>4}  "
            f"{t.ms_per_highlight:>6.1f}  {t.highlights_per_highlight_page:>7.1f}  {t.filename}"
        )

    if top > 0 and len(timings) > top:
        print(f"... {len(timings) - top} more (use --top 0 for the full list)")

    total_seconds = sum(t.seconds for t in timings)
    total_highlights = sum(t.highlights for t in timings)
    total_highlight_pages = sum(t.highlight_pages for t in timings)
    with_highlights = sum(1 for t in timings if t.highlights)

    print("-" * 90)
    print(f"PDFs measured:        {len(timings)} ({with_highlights} with highlights)")
    print(f"Total extraction:     {total_seconds:.2f}s")
    print(f"Slowest single file:  {timings[0].seconds:.2f}s" if timings else "Slowest single file:  n/a")
    print(f"Highlights / pages:   {total_highlights} on {total_highlight_pages} pages")

    if errors:
        print("-" * 90)
        print(f"Errors: {len(errors)}", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Time annotation extraction per PDF (read-only).")
    p.add_argument("--env", dest="env_path", help="Path to TOML env file.")
    p.add_argument("--top", type=int, default=0, help="Show only the N slowest files (0 = all). Default: 0.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    ns = parse_args(argv)
    timings, errors = run(ns.env_path)

    if not timings and not errors:
        print("(no PDFs found)")
        return 0

    print_report(timings, errors, ns.top)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
