# Project Goals & Roadmap

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.

## Code Review & Scalability
- [ ] **Code Audit**: Review `src/pdf_annot/` for "production readiness" against 1600 files.
- [ ] **Large File Strategy**: Develop handling for PDFs with massive highlight counts (300+) to prevent Obsidian UI lag (e.g., splitting notes, folding).

## Highlight Color as Metadata
- [ ] **Highlight Color as Metadata**: Add a `highlight_color` field to the PDF metadata to allow for color-coded highlighting in Obsidian. Will affect the `ndjson` files and the callout colors.

## Advanced PDF Handling
- [ ] **Multi-Column Support**: Implement a frontmatter flag (e.g., `reading_order: columns`) to correctly sort annotations in 2-column papers.
- [ ] **Frontmatter Management**: Ensure `has_annotations`, `pdf_pages`, and layout flags are correctly synced.

## Workflow & Process
- [ ] **Obsidian Integration**: Design Dataview queries to visualize the state of the library (e.g., "Inbox", "Processing", "Done").
- [ ] **Process Definition**: Define the lifecycle states: `PDF -> Inbox -> Highlighted -> Streamlined -> Zettelkasten`.
