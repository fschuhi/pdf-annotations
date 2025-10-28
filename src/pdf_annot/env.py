from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

try:
    import tomllib  # Python 3.11+
except Exception as e:  # pragma: no cover
    raise RuntimeError("tomllib is required (Python 3.11+). You're on an unsupported interpreter.") from e

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


def _expand_path(value: Any) -> Optional[Path]:
    if value is None or value == "":
        return None
    return Path(os.path.expandvars(os.path.expanduser(str(value)))).resolve()


class Paths(BaseModel):
    """
    Filesystem locations used by the tool.
    """

    notes_root: Path = Field(..., description="Directory containing note files like '(ID).md'.")
    pdf_dirs: list[Path] = Field(
        default_factory=list,
        description="One or more directories containing PDFs to scan.",
    )
    backup_dir: Optional[Path] = Field(None, description="Optional directory to store backups (e.g., .bak files).")

    @field_validator("notes_root", mode="before")
    @classmethod
    def _norm_notes_root(cls, v: Any) -> Any:
        return _expand_path(v)

    @field_validator("backup_dir", mode="before")
    @classmethod
    def _norm_backup_dir(cls, v: Any) -> Any:
        return _expand_path(v)

    @field_validator("pdf_dirs", mode="before")
    @classmethod
    def _norm_pdf_dirs(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, (str, Path)):
            return [str(v)]
        if isinstance(v, Sequence):
            return [str(x) for x in v]
        return v

    @field_validator("pdf_dirs", mode="after")
    @classmethod
    def _expand_pdf_dirs(cls, v: list[str | Path]) -> list[Path]:
        out: list[Path] = []
        for item in v:
            p = _expand_path(item)
            if p is not None:
                out.append(p)
        return out


class Frontmatter(BaseModel):
    """
    Front-matter configuration defaults.
    """

    title_field: str = Field(default="pdf_title", description="YAML key for PDF title.")
    size_field: str = Field(default="pdf_size", description="YAML key for PDF file size in bytes.")
    has_annots_field: str = Field(
        default="has_annotations", description="YAML key for boolean flag: any annotations present."
    )
    last_run_field: str = Field(
        default="last_run_at", description="YAML key for ISO 8601 timestamp of last workflow run."
    )


class IO(BaseModel):
    """
    I/O behavior flags.
    """

    atomic_writes: bool = Field(default=True, description="Write files atomically where possible.")
    create_missing_dirs: bool = Field(default=True, description="Create configured directories if they do not exist.")


class CLI(BaseModel):
    """
    CLI-related defaults.
    """

    default_env: Optional[str] = Field(
        default=None,
        description="Optional profile name; useful if you add multiple env profiles later.",
    )


class Env(BaseModel):
    """
    Top-level configuration object passed explicitly to APIs.

    Attributes:
        paths: Filesystem locations (notes_root, pdf_dirs, backup_dir).
        frontmatter: Defaults for YAML front matter field names.
        io: Behavior flags for file I/O.
        cli: CLI defaults (optional).
    """

    paths: Paths
    frontmatter: Frontmatter = Field(default_factory=Frontmatter)
    io: IO = Field(default_factory=IO)
    cli: CLI = Field(default_factory=CLI)

    model_config = {"frozen": True}  # make it effectively immutable after creation

    @model_validator(mode="after")
    def _validate_directories(self) -> "Env":
        # Ensure notes_root exists (create if allowed)
        if not self.paths.notes_root.exists():
            if self.io.create_missing_dirs:
                self.paths.notes_root.mkdir(parents=True, exist_ok=True)
            else:
                raise ValueError(f"notes_root does not exist: {self.paths.notes_root}")

        # Ensure backup_dir exists if set
        if self.paths.backup_dir is not None and not self.paths.backup_dir.exists():
            if self.io.create_missing_dirs:
                self.paths.backup_dir.mkdir(parents=True, exist_ok=True)
            else:
                raise ValueError(f"backup_dir does not exist: {self.paths.backup_dir}")

        # pdf_dirs are optional; if provided, they must exist (we do not create them)
        for p in self.paths.pdf_dirs:
            if not p.exists() or not p.is_dir():
                raise ValueError(f"pdf_dir not found or not a directory: {p}")

        return self


def load_env(
    source: Optional[Path | str | Mapping[str, Any]] = None,
    profile: Optional[str] = None,
    env_var: str = "PDF_ANNOT_ENV_PATH",
    default_filenames: tuple[str, ...] = ("pdf_annot.toml", "pdf-annotations.toml"),
) -> Env:
    """
    Load an Env from a TOML file, a mapping, or defaults.

    Resolution order:
      1) Mapping passed directly.
      2) Explicit path passed in.
      3) Path from PDF_ANNOT_ENV_PATH env var.
      4) First existing file among default_filenames in CWD.
    """
    if isinstance(source, Mapping):
        data = _mapping_to_data(source)
        return _build_env_from_data(data, profile=profile)

    path = None

    if isinstance(source, (str, Path)):
        path = Path(str(source))
    elif source is None:
        env_path = os.environ.get(env_var)
        if env_path:
            path = Path(env_path)
        else:
            cwd = Path.cwd()
            for name in default_filenames:
                candidate = cwd / name
                if candidate.exists():
                    path = candidate
                    break

    if path is None:
        raise FileNotFoundError(
            "No configuration source found. Provide a mapping, set PDF_ANNOT_ENV_PATH, "
            f"or create one of {default_filenames} in the current directory."
        )

    with path.open("rb") as f:
        toml_data = tomllib.load(f)

    return _build_env_from_data(toml_data, profile=profile)


def _mapping_to_data(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return dict(mapping)


def _build_env_from_data(data: Mapping[str, Any], profile: Optional[str]) -> Env:
    if profile:
        envs = data.get("envs")
        if not isinstance(envs, Mapping) or profile not in envs:
            raise KeyError(f"Profile '{profile}' not found under [envs] in configuration.")
        data = envs[profile]

    grouped = {
        "paths": {},
        "frontmatter": {},
        "io": {},
        "cli": {},
    }

    # Copy grouped keys if present
    for section in grouped.keys():
        if isinstance(data.get(section), Mapping):
            grouped[section] = dict(data[section])

    # Allow flat keys too
    flat_to_group = {
        "notes_root": ("paths", "notes_root"),
        "pdf_dirs": ("paths", "pdf_dirs"),
        "backup_dir": ("paths", "backup_dir"),
        "title_field": ("frontmatter", "title_field"),
        "size_field": ("frontmatter", "size_field"),
        "has_annots_field": ("frontmatter", "has_annots_field"),
        "last_run_field": ("frontmatter", "last_run_field"),
        "atomic_writes": ("io", "atomic_writes"),
        "create_missing_dirs": ("io", "create_missing_dirs"),
        "default_env": ("cli", "default_env"),
    }

    for k, v in data.items():
        if k in flat_to_group and not grouped[flat_to_group[k][0]].get(flat_to_group[k][1]):
            group, dest = flat_to_group[k]
            grouped[group][dest] = v

    try:
        return Env(
            paths=Paths(**grouped["paths"]),
            frontmatter=Frontmatter(**grouped["frontmatter"]),
            io=IO(**grouped["io"]),
            cli=CLI(**grouped["cli"]),
        )
    except ValidationError as e:
        raise ValueError(f"Invalid configuration: {e}") from e
