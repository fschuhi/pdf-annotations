# src/pdf_annot/pdf_discovery.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, List

from .env import Env
from .pdf_registry import iter_pdf_files


def iter_pdfs_in_dirs(dirs: Iterable[Path]) -> Iterator[Path]:
    """
    Yield all PDF files under the given directories, recursively.

    The registry and this diagnostic discovery path deliberately share
    `pdf_registry.iter_pdf_files`, including its case-insensitive extension
    matching. This keeps `make discover-pdfs` aligned with what sync indexes.
    """
    for path in iter_pdf_files(dirs):
        yield Path(path)


def discover_pdfs(env: Env) -> List[Path]:
    """
    Return a list of all PDF files found under env.paths.pdf_dirs.
    """
    return list(iter_pdfs_in_dirs(env.paths.pdf_dirs))
