# tests/test_resolve.py
"""
Contract tests for the `pdf_annot.resolve` CLI (TARGET_ARCHITECTURE.md, section 3).

These are *contract* tests: they run the resolver as a real subprocess and assert
on its observable surface -- stdout, stderr, and exit code -- because that surface
(not the Python API) is what Anima consumes. The error-message wording is part of
the frozen contract (it is shown verbatim in Anima's alert), so the tests assert
against the exact message templates that `resolve.py` declares, importing those
constants rather than duplicating the strings.

No PDF *content* is ever read by the resolver (it walks filenames and stats them),
so the dummy PDFs here carry only a couple of bytes, matching the convention in
tests/test_pdf_registry.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from pdf_annot.resolve import (
    CONFIG_ERROR_MSG,
    DUPLICATE_MSG,
    NO_MATCH_MSG,
)
from pdf_annot.utils import crc32_az7, parse_filename


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _write_dummy_pdf(path: Path, content: bytes = b"%PDF-1.4\n%...") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_config(project_dir: Path, pdf_dirs: list[Path], notes_root: Path) -> Path:
    """Write a minimal pdf_annot.toml pointing at the given folders."""
    pdf_dirs_toml = ", ".join(f'"{d.as_posix()}"' for d in pdf_dirs)
    config = "[paths]\n" f'notes_root = "{notes_root.as_posix()}"\n' f"pdf_dirs = [{pdf_dirs_toml}]\n"
    config_path = project_dir / "pdf_annot.toml"
    config_path.write_text(config)
    return config_path


def _hash_for(filename: str) -> str:
    """Compute the resolver hash for a controlled filename, exactly as the code does.

    Mirrors pdf_registry: pdf_hash = crc32_az7(pdf_id.lower()), where pdf_id is
    derived from the filename by parse_filename.
    """
    pdf_id = parse_filename(filename).pdf_id
    return crc32_az7(pdf_id.lower())


def _run_resolver(
    hash_arg: str,
    cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `python -m pdf_annot.resolve <hash>` as a subprocess and capture output."""
    env = dict(os.environ)
    # Ensure the resolver's config discovery is driven by CWD, not an inherited
    # PDF_ANNOT_ENV_PATH from the host environment.
    env.pop("PDF_ANNOT_ENV_PATH", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "pdf_annot.resolve", hash_arg],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """A self-contained mini-project: one PDF folder with one controlled PDF,
    plus a pdf_annot.toml discoverable via CWD. Returns the project root, which
    is also the working directory the resolver must be run from."""
    pdfs = tmp_path / "pdfs"
    notes = tmp_path / "notes"
    pdfs.mkdir()
    notes.mkdir()
    _write_dummy_pdf(pdfs / "(Albini 2013) On dealing with destructive emotions.pdf")
    _write_config(tmp_path, pdf_dirs=[pdfs], notes_root=notes)
    return tmp_path


# -----------------------------------------------------------------------------
# Tests -- one per contract behaviour (section 3)
# -----------------------------------------------------------------------------


def test_resolve_success(project_dir: Path):
    """Known hash resolves to the fully-qualified path, one line, exit 0."""
    expected_pdf = project_dir / "pdfs" / "(Albini 2013) On dealing with destructive emotions.pdf"
    h = _hash_for("(Albini 2013) On dealing with destructive emotions.pdf")

    result = _run_resolver(h, cwd=project_dir)

    assert result.returncode == 0
    assert result.stderr == ""
    # Fully-qualified path, exactly one line (its own terminating newline).
    assert result.stdout == str(expected_pdf.resolve()) + "\n"


def test_resolve_success_case_insensitive(project_dir: Path):
    """A lowercased hash (as it might appear in a URL host) still resolves (section 3.1)."""
    expected_pdf = project_dir / "pdfs" / "(Albini 2013) On dealing with destructive emotions.pdf"
    h = _hash_for("(Albini 2013) On dealing with destructive emotions.pdf").lower()

    result = _run_resolver(h, cwd=project_dir)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == str(expected_pdf.resolve()) + "\n"


def test_resolve_unknown_hash(project_dir: Path):
    """A hash with no matching PDF fails with the no-match message, empty stdout, exit 1."""
    unknown = "ZZZZZZZ"

    result = _run_resolver(unknown, cwd=project_dir)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == NO_MATCH_MSG.format(hash=unknown) + "\n"


def test_resolve_duplicate(tmp_path: Path):
    """The same controlled name in two indexed folders fails ALL resolutions
    (section 3.4 strictness), listing both absolute paths, exit 1."""
    pdfs_a = tmp_path / "pdfs_a"
    pdfs_b = tmp_path / "pdfs_b"
    notes = tmp_path / "notes"
    pdfs_a.mkdir()
    pdfs_b.mkdir()
    notes.mkdir()

    name = "(Albini 2013) On dealing with destructive emotions.pdf"
    dup_a = pdfs_a / name
    dup_b = pdfs_b / name
    _write_dummy_pdf(dup_a)
    _write_dummy_pdf(dup_b)
    _write_config(tmp_path, pdf_dirs=[pdfs_a, pdfs_b], notes_root=notes)

    # Resolving *any* hash must fail while a duplicate exists anywhere.
    h = _hash_for(name)
    result = _run_resolver(h, cwd=tmp_path)

    assert result.returncode == 1
    assert result.stdout == ""
    # Both absolute paths must appear in the message.
    assert str(dup_a.resolve()) in result.stderr
    assert str(dup_b.resolve()) in result.stderr
    # And the message must match the declared template shape.
    pdf_id = parse_filename(name).pdf_id.lower()
    indented_paths = "\n".join(f"  {p}" for p in sorted([str(dup_a.resolve()), str(dup_b.resolve())]))
    assert result.stderr == DUPLICATE_MSG.format(hash=h, pdf_id=pdf_id, paths=indented_paths) + "\n"


def test_resolve_config_error(tmp_path: Path):
    """With no discoverable config, the resolver reports a configuration error, exit 1."""
    # tmp_path deliberately contains no pdf_annot.toml, and _run_resolver clears
    # PDF_ANNOT_ENV_PATH, so load_env has nothing to find.
    result = _run_resolver("ABCDEFG", cwd=tmp_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("Cannot resolve: configuration error -- ")
    # The detail is dynamic (comes from load_env), but the prefix is contractually fixed.
    assert result.stderr.endswith("\n")
