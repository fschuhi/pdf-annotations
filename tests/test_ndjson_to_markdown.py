# tests/test_md_converter_e2e.py
import os
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "ndjson_to_md_block.py"
FIXT = ROOT / "tests" / "fixtures"
INPUT = FIXT / "final_streamlined.ndjson"
EXPECTED = FIXT / "expected_test1_markdown.md"


def test_ndjson_to_md_block_matches_golden():
    assert TOOLS.exists(), f"Missing converter: {TOOLS}"
    assert INPUT.exists(), f"Missing input NDJSON: {INPUT}"
    assert EXPECTED.exists(), f"Missing expected markdown: {EXPECTED}"

    # Run the converter with PYTHONPATH=src so imports work in dev
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    proc = subprocess.run(
        [sys.executable, str(TOOLS), "--pdf-id", "VQGPEHE", "--in", str(INPUT)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, f"converter failed: {proc.stderr}"
    got = proc.stdout.strip()
    want = EXPECTED.read_text(encoding="utf-8").strip()

    # If this fails, it will print a readable unified diff via pytest
    assert got == want
