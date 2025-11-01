#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ is on sys.path for direct script execution
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pdf_annot.env import load_env  # noqa: E402
from pdf_annot.pdf_discovery import discover_pdfs  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Discover PDFs using env.paths.pdf_dirs and print their paths.")
    p.add_argument("--env", dest="env_path", help="Path to TOML env file.")
    p.add_argument("--relative-to", dest="relative_to", help="Print paths relative to this directory.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    ns = parse_args(argv)
    env = load_env(ns.env_path)
    pdfs = discover_pdfs(env)
    base = Path(ns.relative_to).resolve() if ns.relative_to else None
    if not pdfs:
        print("(no PDFs found)")
        return 0
    for p in pdfs:
        rp = p.resolve()
        if base:
            try:
                print(rp.relative_to(base))
                continue
            # --- FIX: Catch the specific error ---
            except ValueError:
                pass
        print(rp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
