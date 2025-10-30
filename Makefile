.PHONY: venv test extract streamline clean showtree gentree filesdump discover-pdfs

# Create local venv (idempotent)
venv:
	python3 -m venv .venv

# Run tests (no package install needed)
test: venv
	. .venv/bin/activate && PYTHONPATH=src pytest -q

# Extract annotations using the module directly
extract: venv
	. .venv/bin/activate && PYTHONPATH=src python -m pdf_annot.extract -p tests/fixtures/pdf_to_markdown_e2e/input.pdf

# Streamline annotations using the module directly
streamline: venv
	. .venv/bin/activate && PYTHONPATH=src python -m pdf_annot.streamline -i tests/fixtures/pdf_to_markdown_e2e/expected_raw.ndjson -o /tmp/final_streamlined.ndjson

# Clean build/test artifacts and venv
clean:
	rm -rf .venv .pytest_cache
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.egg-info" -type d -prune -exec rm -rf {} +

# Show project tree (excluding common noise)
showtree:
	tree -I ".venv|__pycache__|.idea|.pytest-cache|*egg-info|tmp"

# Save a tree snapshot
gentree:
	tree -I ".venv|__pycache__|.idea|.pytest-cache|*egg-info|tmp" > project-tree.txt

# Concatenate files listed in files.lst into tmp/filesdump.txt
filesdump: venv
	. .venv/bin/activate && mkdir -p tmp && python tools/concat_files.py files.lst > tmp/filesdump.txt

discover-pdfs: venv
	. .venv/bin/activate && python tools/discover_pdfs.py --env tests/fixtures/env/test_pdf_annot.toml --relative-to .
