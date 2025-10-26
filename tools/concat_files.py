# src/pdf_annot/tools/concat_files.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SEP_FMT = "==================== {name} ====================\n"

def concat(list_file: Path, out):
    if not list_file.exists():
        out.write(f"Error: Cannot read file '{list_file}'\n")
        return 1
    lines = list_file.read_text(encoding="utf-8").splitlines()
    for raw in lines:
        name = raw.strip()
        if not name:
            continue
        out.write(SEP_FMT.format(name=name))
        p = Path(name)
        if p.exists() and p.is_file():
            try:
                out.write(p.read_text(encoding="utf-8"))
            except Exception:
                out.write(f"Error: Cannot read file '{name}'\n")
        else:
            out.write(f"Error: Cannot read file '{name}'\n")
        out.write("\n")
    return 0

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Concatenate files listed in a file with separators.")
    ap.add_argument("listfile", help="Path to the file containing filenames (one per line).")
    ns = ap.parse_args(argv)
    return concat(Path(ns.listfile), sys.stdout)

if __name__ == "__main__":
    raise SystemExit(main())
