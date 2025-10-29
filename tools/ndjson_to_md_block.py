#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# Ensure src/ is importable when running as a script
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pdf_annot.ndjson_to_md_block import render_block  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert streamlined NDJSON to an Obsidian annotation markdown block.")
    p.add_argument("--pdf-id", required=True, help="7-letter document hash used in pdf:// links")
    p.add_argument("--in", dest="infile", default="-", help="NDJSON path or '-' for stdin")
    return p.parse_args(argv)


def main(argv=None) -> int:
    ns = parse_args(argv)

    if ns.infile == "-" or ns.infile is None:
        stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
        close_stream = False
    else:
        stream = open(ns.infile, "r", encoding="utf-8")
        close_stream = True

    try:
        objs = [json.loads(line) for line in stream if line.strip()]
    finally:
        if close_stream:
            stream.close()

    md = render_block(objs, ns.pdf_id)
    sys.stdout.write(md if md.endswith("\n") else md + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
