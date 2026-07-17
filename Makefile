# --- Variables ---
VENV_DIR = .venv
VENV_ACTIVATE = $(VENV_DIR)/bin/activate
ACTIVATE = . $(VENV_ACTIVATE)
PIP = $(ACTIVATE) && pip
# RUN_WITH_PATH sets PYTHONPATH to find the 'src' directory (src-layout)
RUN_WITH_PATH = $(ACTIVATE) && PYTHONPATH=src
# The sentinel file to check if setup is complete
SETUP_STAMP = $(VENV_DIR)/.setup_stamp

# --- Phony targets ---
.PHONY: all setup test test-verbose run extract streamline hash discover-pdfs clean showtree gentree filesdump help

# Default target runs 'setup'
all: setup

# --- Virtual Environment & Setup ---

$(VENV_ACTIVATE):
	python3 -m venv $(VENV_DIR)

# Smart 'setup' target
# Depends on venv existence and config files.
$(SETUP_STAMP): $(VENV_ACTIVATE) requirements.txt pyproject.toml
	@echo "--- Installing dependencies ---"
	$(PIP) install -r requirements.txt
	@echo "--- Installing project in editable mode ---"
	$(PIP) install -e .
	@# Auto-create config if missing
	@if [ ! -f pdf_annot.toml ]; then \
		echo "--- Creating default configuration (pdf_annot.toml) ---"; \
		cp pdf_annot.example.toml pdf_annot.toml; \
	fi
	@echo "--- Setup complete ---"
	@touch $(SETUP_STAMP)

setup: $(SETUP_STAMP) ## Create venv, install dependencies, and init config

# --- Testing Targets ---

test: $(SETUP_STAMP) ## Run all tests (quiet mode)
	$(RUN_WITH_PATH) pytest -q

test-verbose: $(SETUP_STAMP) ## Run tests with verbose output
	$(RUN_WITH_PATH) pytest -v -s

# --- Application/Tool Targets ---

run: $(SETUP_STAMP) ## Run the main sync workflow (pass ARGS="-c ...")
	$(RUN_WITH_PATH) python -m pdf_annot.sync $(ARGS)

hash: $(SETUP_STAMP) ## Calculate 7-char hash for a string or filename (ARGS="...")
	$(RUN_WITH_PATH) python tools/print_hashes.py $(ARGS)

extract: $(SETUP_STAMP) ## Run extraction on the fixture PDF (dev test)
	$(RUN_WITH_PATH) python -m pdf_annot.extract -p tests/fixtures/pdf_to_markdown_e2e/input.pdf

streamline: $(SETUP_STAMP) ## Run streamline on fixture NDJSON (dev test)
	$(RUN_WITH_PATH) python -m pdf_annot.streamline_annotations -i tests/fixtures/pdf_to_markdown_e2e/expected_raw.ndjson -o tmp/final_streamlined.ndjson

discover-pdfs: $(SETUP_STAMP) ## List all PDFs found by current config
	$(RUN_WITH_PATH) python tools/discover_pdfs.py --env pdf_annot.toml --relative-to .

# --- Utility Targets ---

clean: ## Remove venv, cache, and tmp files
	rm -rf $(VENV_DIR) .pytest_cache tmp
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.egg-info" -type d -prune -exec rm -rf {} +

showtree: ## Show project directory structure
	@tree -I "node_modules|dist|build|.git|.idea|.vscode|.venv|__pycache__|tmp|cache|*egg-info" -L 3

gentree: ## Save tree structure to tmp/project_tree.txt
	@mkdir -p tmp
	@tree -I "node_modules|dist|build|.git|.idea|.vscode|.venv|__pycache__|tmp|cache|*egg-info" > tmp/project_tree.txt
	@echo "Project tree saved to tmp/project_tree.txt"

filesdump: gentree ## Create context dump for LLMs
	@echo "--- Generating filesdump ---"
	$(RUN_WITH_PATH) python tools/concat_files.py manifest.lst > tmp/filesdump.txt
	@echo "Filesdump created at tmp/filesdump.txt"

filesdump-compact: gentree ## Create context dump for LLMs
	@echo "--- Generating filesdump ---"
	$(ACTIVATE) && python tools/concat_files.py manifest-compact.lst > tmp/filesdump-compact.txt
	@echo "Filesdump created at tmp/filesdump-compact.txt"

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
