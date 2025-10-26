from pathlib import Path
from pdf_annot.env import load_env

def test_load_env_from_fixture_file():
    here = Path(__file__).parent
    cfg = (here / "fixtures" / "env" / "test_pdf_annot.toml").resolve()
    env = load_env(cfg)
    assert env.paths.notes_root.exists()
    assert env.paths.backup_dir and env.paths.backup_dir.exists()
    assert env.paths.pdf_dirs and all(p.exists() for p in env.paths.pdf_dirs)
