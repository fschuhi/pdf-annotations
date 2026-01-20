Refactoring TODOs

- **Just changing tags should not trigger update**: Any change (add, remove, update) of the _tags_ frontmatter attribute triggers a full PDF read and update of the annotations. Why? Should not happen.
- **Implement `--dry-run` Flag**: We still need to implement the logic for the --dry-run argument in `src/pdf_annot/sync.py`.
- **Header/Footer Config**: Add `header_height` and `footer_height` settings to the Env model so they can be set in the `.toml` file.
- **Windows Server**: Dynamic Indexing: The Windows server should pick up additions, renames, and deletions in the PDF folder and recalculate the hash map.
- **`streamline_annotations.py` Refactor**: Refactor `streamline_annotations.py` to fix duplicated logic and inefficiencies (currently postponed).
- **New Scenarios**: Flesh out and test more workflow edge cases (e.g., what happens if a note is missing its frontmatter entirely).
