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
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print("Usage: python tools/print_hashes.py <string_to_hash_1> [<string_to_hash_2> ...]")
        print("\nPrints the 7-character A-Z hash for each input string.")
        print('Example: python tools/print_hashes.py "(Albini 2013)" "(Balbini 2014)"')
        return

    for s in args:
        print(f"{s!r} -> {crc32_az7(s)}")


if __name__ == "__main__":
    main()
