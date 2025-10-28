from pathlib import Path
from pdf_annot.env import load_env
from pdf_annot.notes_db import NotesDB


def test_notesdb_from_env_works():
    here = Path(__file__).parent
    cfg = (here / "fixtures" / "env" / "test_pdf_annot.toml").resolve()
    env = load_env(cfg)
    db = NotesDB.from_env(env)
    assert isinstance(db, NotesDB)
