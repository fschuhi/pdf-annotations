# tools/print_hashes.py
import os
import sys

# --- FIX: Removed unused 'from pathlib import Path' ---

# Ensure src/ is on sys.path for direct script execution
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from pdf_annot.utils import crc32_az7  # noqa: E402
from pdf_annot.utils import pdf_id_from_filename  # noqa: E402


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print("Usage: python tools/print_hashes.py <string_or_filename_1> [...]")
        print("\nPrints the 7-character A-Z hash for each input.")
        print("If input is a filename like '(ID) Title.pdf',")
        print("it extracts and hashes the '(ID)' part.")
        print('Example: python tools/print_hashes.py "(Albini 2013)"')
        print('Example: python tools/print_hashes.py "(Albini 2013) Title.pdf"')
        return

    for s in args:
        # --- NEW: Check if the input is a filename ---
        if s.lower().endswith(".pdf") and s.startswith("("):
            pdf_id = pdf_id_from_filename(s)
            if pdf_id:
                print(f"File: {s!r} -> ID: {pdf_id!r} -> {crc32_az7(pdf_id)}")
            else:
                print(f"Error: Could not parse pdf_id from filename: {s!r}", file=sys.stderr)
        else:
            # --- Original logic: hash the string directly ---
            print(f"ID: {s!r} -> {crc32_az7(s)}")


if __name__ == "__main__":
    main()
