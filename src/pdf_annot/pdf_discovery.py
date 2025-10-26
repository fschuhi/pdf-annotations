# src/pdf_annot/pdf_discovery.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, List

from .env import Env

def iter_pdfs_in_dirs(dirs: Iterable[Path]) -> Iterator[Path]:
    """
    Yield all *.pdf files under the given directories (recursive).
    Skips non-files (e.g., directories, broken links).
    """
    for d in dirs:
        if not d.exists() or not d.is_dir():
            # Env.load already validates these, but be defensive
            continue
        for p in d.rglob("*.pdf"):
            if p.is_file():
                yield p

def discover_pdfs(env: Env) -> List[Path]:
    """
    Return a list of all *.pdf files found under env.paths.pdf_dirs.
    """
    return list(iter_pdfs_in_dirs(env.paths.pdf_dirs))
