from __future__ import annotations

import os
from pathlib import Path
import textwrap

import pytest

from pdf_annot.env import Env, load_env


def test_load_from_mapping_creates_notes_root(tmp_path: Path):
    data = {
        "paths": {"notes_root": str(tmp_path / "vault")},
        "io": {"create_missing_dirs": True},
    }
    env = load_env(data)
    assert isinstance(env, Env)
    assert env.paths.notes_root.exists()
    assert env.io.atomic_writes is True  # default


def test_load_from_file_flat_and_grouped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    toml = textwrap.dedent(
        f"""
        notes_root = "{str(tmp_path / "vault")}"
        atomic_writes = true
        create_missing_dirs = true
        """
    )
    cfg = tmp_path / "pdf_annot.toml"
    cfg.write_text(toml, encoding="utf-8")

    env = load_env(cfg)
    assert env.paths.notes_root.exists()
    assert env.io.atomic_writes is True

    # Now test grouped style
    grouped = textwrap.dedent(
        f"""
        [paths]
        notes_root = "{str(tmp_path / "vault2")}"

        [io]
        create_missing_dirs = true
        """
    )
    cfg2 = tmp_path / "grouped.toml"
    cfg2.write_text(grouped, encoding="utf-8")
    env2 = load_env(cfg2)
    assert env2.paths.notes_root.exists()


def test_env_var_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = tmp_path / "env.toml"
    cfg.write_text(
        f"""
        [paths]
        notes_root = "{str(tmp_path / "vault")}"
        [io]
        create_missing_dirs = true
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("PDF_ANNOT_ENV_PATH", str(cfg))
    env = load_env()
    assert env.paths.notes_root.exists()


def test_missing_pdf_dir_is_error(tmp_path: Path):
    cfg = tmp_path / "env.toml"
    missing_dir = tmp_path / "not_there_dir"
    cfg.write_text(
        f"""
        [paths]
        notes_root = "{str(tmp_path / "vault")}"
        pdf_dirs = ["{str(missing_dir)}"]
        [io]
        create_missing_dirs = true
        """,
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as exc:
        load_env(cfg)
    assert "pdf_dir not found or not a directory" in str(exc.value)


def test_backup_dir_created_when_allowed(tmp_path: Path):
    cfg = tmp_path / "env.toml"
    cfg.write_text(
        f"""
        [paths]
        notes_root = "{str(tmp_path / "vault")}"
        backup_dir = "{str(tmp_path / "baks")}"
        [io]
        create_missing_dirs = true
        """,
        encoding="utf-8",
    )
    env = load_env(cfg)
    assert env.paths.backup_dir and env.paths.backup_dir.exists()
