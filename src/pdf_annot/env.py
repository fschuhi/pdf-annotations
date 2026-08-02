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
    temp_dir: Optional[Path] = Field(None, description="Optional directory for temporary test artifacts.")
    thumbnails_dir: Optional[Path] = Field(None, description="Optional directory for PDF page-1 thumbnail images.")
    synopses_dir: Optional[Path] = Field(
        None, description="Optional directory of <pdf_id>.txt synopsis files, written by isbndb_synopsis.py."
    )

    @field_validator("notes_root", mode="before")
    @classmethod
    def _norm_notes_root(cls, v: Any) -> Any:
        return _expand_path(v)

    @field_validator("temp_dir", mode="before")
    @classmethod
    def _norm_temp_dir(cls, v: Any) -> Any:
        return _expand_path(v)

    @field_validator("thumbnails_dir", mode="before")
    @classmethod
    def _norm_thumbnails_dir(cls, v: Any) -> Any:
        return _expand_path(v)

    @field_validator("synopses_dir", mode="before")
    @classmethod
    def _norm_synopses_dir(cls, v: Any) -> Any:
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


class IO(BaseModel):
    """
    I/O behavior flags.
    """

    create_missing_dirs: bool = Field(default=True, description="Create configured directories if they do not exist.")


class Env(BaseModel):
    """
    Top-level configuration object passed explicitly to APIs.

    Attributes:
        paths: Filesystem locations (notes_root, pdf_dirs, temp_dir).
        io: Directory-creation behavior.
    """

    paths: Paths
    io: IO = Field(default_factory=IO)

    model_config = {"frozen": True}  # make it effectively immutable after creation

    @model_validator(mode="after")
    def _validate_directories(self) -> "Env":
        # Ensure notes_root exists (create if allowed)
        if not self.paths.notes_root.exists():
            if self.io.create_missing_dirs:
                self.paths.notes_root.mkdir(parents=True, exist_ok=True)
            else:
                raise ValueError(f"notes_root does not exist: {self.paths.notes_root}")

        # Ensure temp_dir exists if set
        if self.paths.temp_dir is not None and not self.paths.temp_dir.exists():
            if self.io.create_missing_dirs:
                self.paths.temp_dir.mkdir(parents=True, exist_ok=True)
            else:
                raise ValueError(f"temp_dir does not exist: {self.paths.temp_dir}")

        # Ensure thumbnails_dir exists if set
        if self.paths.thumbnails_dir is not None and not self.paths.thumbnails_dir.exists():
            if self.io.create_missing_dirs:
                self.paths.thumbnails_dir.mkdir(parents=True, exist_ok=True)
            else:
                raise ValueError(f"thumbnails_dir does not exist: {self.paths.thumbnails_dir}")

        # synopses_dir, unlike the paths above, is never auto-created, even
        # when create_missing_dirs is True: this tool only ever reads from
        # it (isbndb_synopsis.py, a separate script, is what writes into
        # it). A missing synopses_dir almost always means that export/copy
        # step hasn't happened yet -- silently creating an empty directory
        # would turn one clear configuration error into 1600 identical
        # "no synopsis file" skips instead.
        if self.paths.synopses_dir is not None and not self.paths.synopses_dir.exists():
            raise ValueError(f"synopses_dir does not exist: {self.paths.synopses_dir}")

        # pdf_dirs are optional; if provided, they must exist (we do not create them)
        for p in self.paths.pdf_dirs:
            if not p.exists() or not p.is_dir():
                raise ValueError(f"pdf_dir not found or not a directory: {p}")

        return self


def load_env(
    source: Optional[Path | str | Mapping[str, Any]] = None,
    env_var: str = "PDF_ANNOT_ENV_PATH",
    default_filenames: tuple[str, ...] = ("pdf_annot.toml", "pdf-annotations.toml"),
) -> Env:
    """
    Load an Env from a TOML file or a mapping.

    Resolution order:
      1) Mapping passed directly.
      2) Explicit path passed in.
      3) Path from PDF_ANNOT_ENV_PATH env var.
      4) First existing file among default_filenames in CWD.
    """
    if isinstance(source, Mapping):
        data = _mapping_to_data(source)
        return _build_env_from_data(data)

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

    return _build_env_from_data(toml_data)


def _mapping_to_data(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return dict(mapping)


def _build_env_from_data(data: Mapping[str, Any]) -> Env:
    grouped = {
        "paths": {},
        "io": {},
    }

    # Copy grouped keys if present
    for section in grouped.keys():
        if isinstance(data.get(section), Mapping):
            grouped[section] = dict(data[section])

    # Allow flat keys too
    flat_to_group = {
        "notes_root": ("paths", "notes_root"),
        "pdf_dirs": ("paths", "pdf_dirs"),
        "temp_dir": ("paths", "temp_dir"),
        "thumbnails_dir": ("paths", "thumbnails_dir"),
        "synopses_dir": ("paths", "synopses_dir"),
        "create_missing_dirs": ("io", "create_missing_dirs"),
    }

    for k, v in data.items():
        if k in flat_to_group and not grouped[flat_to_group[k][0]].get(flat_to_group[k][1]):
            group, dest = flat_to_group[k]
            grouped[group][dest] = v

    try:
        return Env(
            paths=Paths(**grouped["paths"]),
            io=IO(**grouped["io"]),
        )
    # --- FIX: Renamed 'e' to 've' to avoid shadowing ---
    except ValidationError as ve:
        raise ValueError(f"Invalid configuration: {ve}") from ve
