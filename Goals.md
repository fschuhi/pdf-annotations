# Project Goals & Roadmap

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.

## PDF Annotations Quality
- [ ] **Margin Detection**: For some PDFs the first line(s) are missing.
- [ ] **Spurious Artefacts**: Comparing the output to Zotero's extracted annotations, there are a lot of bigger and smaller problems.

## Code Review & Scalability
- [ ] **Code Audit**: Review `src/pdf_annot/` for "production readiness" against 1600 files.
- [ ] **Large File Strategy**: Develop handling for PDFs with massive highlight counts (300+) to prevent Obsidian UI lag (e.g., splitting notes, folding).

## Highlight Color as Metadata
- [ ] **Highlight Color as Metadata**: Add a `highlight_color` field to the PDF metadata to allow for color-coded highlighting in Obsidian. Will affect the `ndjson` files and the callout colors.

## Advanced PDF Handling
- [ ] **Multi-Column Support**: Implement a frontmatter flag (e.g., `reading_order: columns`) to correctly sort annotations in 2-column papers.
- [ ] **Frontmatter Management**: Ensure `has_annotations`, `pdf_pages`, and layout flags are correctly synced.

## Workflow & Process
- [x] **Obsidian Integration**: Design Dataview queries to create a Zettelkasten system for Obsidian.
- [x] **Process Definition**: Define and implement lifecycle states - - see Obsidian/doc/The-Studio-Manual.md
