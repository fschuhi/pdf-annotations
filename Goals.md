# Project Goals & Roadmap

## 🎯 Strategic Vision
Create a robust, automated "drumbeat" for knowledge management that propels the reading, highlighting, and writing process (Zettelkasten) in Obsidian. The system must reliably handle 1600+ PDF files, including complex multi-column layouts, and integrate seamlessly with Obsidian Dataview for process tracking.

## Phase 1: Standardization & Baseline (Current)
- [ ] **Review Makefile**: Align with `rob-burbea-expert` standards (Help, Auto-config, robust cleaning).
- [ ] **Review README/Docs**: Modernize style and structure to serve as a baseline for future AI sessions.
- [ ] **Clean Project Structure**: Ensure file organization supports the migration to the `Projects/` folder.

## Phase 2: Code Review & Scalability
- [ ] **Code Audit**: Review `src/pdf_annot/` for "production readiness" against 1600 files.
- [ ] **Large File Strategy**: Develop handling for PDFs with massive highlight counts (300+) to prevent Obsidian UI lag (e.g., splitting notes, folding).

## Phase 3: Advanced PDF Handling
- [ ] **Multi-Column Support**: Implement a frontmatter flag (e.g., `reading_order: columns`) to correctly sort annotations in 2-column papers.
- [ ] **Frontmatter Management**: Ensure `has_annotations`, `pdf_pages`, and layout flags are correctly synced.

## Phase 4: Workflow & Process
- [ ] **Obsidian Integration**: Design Dataview queries to visualize the state of the library (e.g., "Inbox", "Processing", "Done").
- [ ] **Process Definition**: Define the lifecycle states: `PDF -> Inbox -> Highlighted -> Streamlined -> Zettelkasten`.

---
*Created: Jan 2026*
