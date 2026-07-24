from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from pdf_annot.env import Env, load_env


# =============================================================================
# Unit tests for Env loading and validation
# =============================================================================


def test_load_from_mapping_creates_notes_root(tmp_path: Path):
    data = {
        "paths": {"notes_root": str(tmp_path / "vault")},
        "io": {"create_missing_dirs": True},
    }
    env = load_env(data)
    assert isinstance(env, Env)
    assert env.paths.notes_root.exists()


def test_load_from_file_flat_and_grouped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    toml = textwrap.dedent(
        f"""
        notes_root = "{str(tmp_path / "vault")}"
        create_missing_dirs = true
        """
    )
    cfg = tmp_path / "pdf_annot.toml"
    cfg.write_text(toml, encoding="utf-8")

    env = load_env(cfg)
    assert env.paths.notes_root.exists()

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


def test_temp_dir_created_when_allowed(tmp_path: Path):
    """Test that temp_dir is created when create_missing_dirs is true."""
    cfg = tmp_path / "env.toml"
    cfg.write_text(
        f"""
        [paths]
        notes_root = "{str(tmp_path / "vault")}"
        temp_dir = "{str(tmp_path / "tmp")}"
        [io]
        create_missing_dirs = true
        """,
        encoding="utf-8",
    )
    env = load_env(cfg)
    assert env.paths.temp_dir and env.paths.temp_dir.exists()


def test_temp_dir_missing_raises_error_when_not_allowed(tmp_path: Path):
    """Test that missing temp_dir raises error when create_missing_dirs is false."""
    cfg = tmp_path / "env.toml"
    missing_temp = tmp_path / "missing_tmp"
    cfg.write_text(
        f"""
        [paths]
        notes_root = "{str(tmp_path / "vault")}"
        temp_dir = "{str(missing_temp)}"
        [io]
        create_missing_dirs = false
        """,
        encoding="utf-8",
    )
    # notes_root needs to exist first for this test
    (tmp_path / "vault").mkdir()

    with pytest.raises(ValueError) as exc:
        load_env(cfg)
    assert "temp_dir does not exist" in str(exc.value)


def test_temp_dir_optional(tmp_path: Path):
    """Test that temp_dir is optional and can be omitted."""
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
    env = load_env(cfg)
    assert env.paths.temp_dir is None


# =============================================================================
# Fixture-based tests (now self-contained with tmp_path)
# =============================================================================


def test_load_env_from_tmp_file(tmp_path: Path):
    """Test loading from a TOML file created in tmp_path."""
    # We need to create the dirs the config *points* to.
    vault = tmp_path / "vault"
    pdfs = tmp_path / "pdfs"

    # We only need to pre-create dirs that load_env validates
    vault.mkdir()
    pdfs.mkdir()

    cfg = tmp_path / "test_config.toml"
    cfg.write_text(
        f"""
    [paths]
    notes_root = "{vault}"
    pdf_dirs = ["{pdfs}"]
    [io]
    create_missing_dirs = true
    """
    )

    env = load_env(cfg)
    assert env.paths.notes_root.exists()
    assert env.paths.pdf_dirs and all(p.exists() for p in env.paths.pdf_dirs)
