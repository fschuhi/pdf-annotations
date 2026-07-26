#!/usr/bin/env python3
"""
show_pdf_info.py

Extracts page count, highlights, and textboxes from a list of PDF files.

Unlike the original pdf_info.py template, this tool expects the file list
to contain full (or relative) paths to PDFs directly -- e.g. the output of
`find /some/folder -iname '*.pdf'`. In the output, each path is printed
relative to a given --base-folder, so the report doesn't leak the full
absolute path of every file.
"""

import argparse
import os
import sys
import unicodedata
from datetime import datetime
import fitz  # PyMuPDF


def count_annotations(pdf_path):
    """
    Count highlights and textboxes in a PDF file.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        tuple: (highlights_count, textboxes_count)
    """
    try:
        doc = fitz.open(pdf_path)
        highlights = 0
        textboxes = 0

        for page_num in range(doc.page_count):
            page = doc[page_num]
            annotations = page.annots()
            if annotations is None:
                continue

            for annot in annotations:
                annot_type = annot.type[1]  # Get annotation type name
                if annot_type in ("Highlight", "Squiggly", "StrikeOut", "Underline"):
                    highlights += 1
                elif annot_type in ("Text", "FreeText"):
                    textboxes += 1

        doc.close()
        return highlights, textboxes

    except Exception as e:
        print(f"Error processing annotations in {pdf_path}: {e}", file=sys.stderr)
        return 0, 0


def get_pdf_info(pdf_path, include_annotations=False):
    """
    Get information about a PDF file.

    Args:
        pdf_path (str): Path to the PDF file
        include_annotations (bool): Whether to count annotations

    Returns:
        dict: Dictionary with PDF information
    """
    try:
        doc = fitz.open(pdf_path)
        page_count = doc.page_count
        doc.close()

        result = {"pages": page_count}

        if include_annotations:
            highlights, textboxes = count_annotations(pdf_path)
            result["highlights"] = highlights
            result["textboxes"] = textboxes

        return result

    except Exception as e:
        print(f"Error processing {pdf_path}: {e}", file=sys.stderr)
        result = {"pages": 0}
        if include_annotations:
            result["highlights"] = 0
            result["textboxes"] = 0
        return result


def get_modified_date(pdf_path):
    """
    Return the file's last-modified timestamp as a 'YYYY-MM-DD HH:MM' string.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        str: Formatted modified date, or '' if it can't be determined
    """
    try:
        mtime = os.path.getmtime(pdf_path)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"Error reading modified date for {pdf_path}: {e}", file=sys.stderr)
        return ""


def read_file_list(file_list_path):
    """
    Read list of PDF paths from a file (one path per line).

    Args:
        file_list_path (str): Path to the file containing the list of PDF paths

    Returns:
        list: List of paths
    """
    try:
        with open(file_list_path, "r", encoding="utf-8") as f:
            paths = [line.strip() for line in f if line.strip()]
        return paths
    except Exception as e:
        print(f"Error reading file list from {file_list_path}: {e}", file=sys.stderr)
        sys.exit(1)


def display_name(pdf_path, base_folder):
    """
    Return pdf_path relative to base_folder for display purposes.
    Falls back to the original path if it isn't inside base_folder.
    """
    try:
        rel = os.path.relpath(pdf_path, base_folder)
        # If the path isn't actually under base_folder, relpath will
        # produce something starting with '..' -- keep the original
        # absolute path in that case rather than a confusing relative one.
        if rel.startswith(".."):
            name = pdf_path
        else:
            name = rel
    except ValueError:
        # Happens on Windows when paths are on different drives
        name = pdf_path

    # macOS (HFS+/APFS) stores filenames in NFD (decomposed) Unicode, e.g.
    # "ü" as "u" + a separate combining-diaeresis mark. That's invisible in
    # a terminal but confuses other tools (and can round-trip badly through
    # Excel). Normalize to NFC (precomposed) so accented characters are
    # single, standard code points.
    return unicodedata.normalize("NFC", name)


def main():
    parser = argparse.ArgumentParser(
        description="Extract information from a list of PDF files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/show_pdf_info.py --file-list tmp/pdf-list.txt \\
      --base-folder ~/Dropbox/Papers/Collection --output tmp/show_pdf_info.out
  python tools/show_pdf_info.py -f tmp/pdf-list.txt -b ~/Dropbox/Papers/Collection \\
      -o tmp/show_pdf_info.out --annotations
        """,
    )

    parser.add_argument(
        "--file-list",
        "-f",
        required=True,
        help="Path to file containing list of PDF paths (one per line, e.g. from `find`)",
    )

    parser.add_argument(
        "--base-folder",
        "-b",
        required=True,
        help="Base folder used to shorten displayed paths (paths are printed relative to this folder)",
    )

    parser.add_argument(
        "--output", "-o", default="pdf_info_results.txt", help="Output file path (default: pdf_info_results.txt)"
    )

    parser.add_argument("--annotations", "-a", action="store_true", help="Include count of highlights and textboxes")

    args = parser.parse_args()

    file_list_path = os.path.expanduser(args.file_list)
    base_folder = os.path.expanduser(args.base_folder)

    if not os.path.exists(file_list_path):
        print(f"Error: File list not found: {file_list_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(base_folder):
        print(f"Error: Base folder not found: {base_folder}", file=sys.stderr)
        sys.exit(1)

    pdf_paths = read_file_list(file_list_path)
    print(f"Found {len(pdf_paths)} files in the list")

    results = []
    processed = 0
    skipped = 0

    for raw_path in pdf_paths:
        pdf_path = os.path.expanduser(raw_path)

        if not os.path.exists(pdf_path):
            print(f"Warning: File not found: {pdf_path}", file=sys.stderr)
            skipped += 1
            continue

        if not pdf_path.lower().endswith(".pdf"):
            print(f"Warning: Skipping non-PDF file: {pdf_path}", file=sys.stderr)
            skipped += 1
            continue

        info = get_pdf_info(pdf_path, args.annotations)
        name = display_name(pdf_path, base_folder)
        modified = get_modified_date(pdf_path)

        if args.annotations:
            results.append((name, modified, info["pages"], info["highlights"], info["textboxes"]))
        else:
            results.append((name, modified, info["pages"]))

        processed += 1
        if processed % 100 == 0:
            print(f"Processed {processed} files...")

    try:
        # utf-8-sig writes a UTF-8 byte-order-mark (BOM). Excel on Windows
        # doesn't assume UTF-8 for plain text/CSV files -- without a BOM it
        # falls back to the system code page (e.g. Windows-1252), which
        # garbles any accented characters. The BOM makes Excel detect and
        # decode the file as UTF-8 correctly.
        with open(args.output, "w", encoding="utf-8-sig") as f:
            if args.annotations:
                f.write("Filename\tModified\tPages\tHighlights\tTextboxes\n")
                for result in results:
                    f.write(f"{result[0]}\t{result[1]}\t{result[2]}\t{result[3]}\t{result[4]}\n")
            else:
                f.write("Filename\tModified\tPages\n")
                for result in results:
                    f.write(f"{result[0]}\t{result[1]}\t{result[2]}\n")

        print(f"\nCompleted!")
        print(f"Processed: {processed} files")
        print(f"Skipped: {skipped} files")
        print(f"Results written to: {args.output}")

    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
