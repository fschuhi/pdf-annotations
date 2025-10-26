# tools/print_hashes.py
import os
import sys

# Ensure src/ is on sys.path for direct script execution
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from pdf_annot.utils import crc32_az7  # noqa: E402


def main():
    samples = ["", "a", "A", "hello", "authors", "doe+roe", "müller", "(smith 2015)"]
    for s in samples:
        print(f"{s!r} -> {crc32_az7(s)}")


if __name__ == "__main__":
    main()
