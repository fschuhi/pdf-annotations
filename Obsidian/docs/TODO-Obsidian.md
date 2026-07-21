# TODO - Obsidian / The Studio

Open tasks from the Studio setup session (January 2026).

---

## 1. Query CSS: Custom Classes

**Goal:** Enable per-table CSS styling by wrapping script output in custom containers.

**Why:** Currently all Dataview tables share the same styling. With custom classes, we could:
- Set fixed column widths per table type (2-column vs 3-column vs 4-column)
- Apply different colors to different query types
- Ensure vertical alignment across multiple tables on the same page

**Approach:**
- Modify each script to wrap its output in a `<div class="studio-{scriptname}">`
- Add CSS rules targeting `.studio-workbench-list`, `.studio-fleeting-notes`, etc.
- Define column width percentages per table type

**Scripts to modify:**
- `active_workbenches.js`
- `workbench_list.js`
- `fleeting_block_markers.js`
- `next_in_chain.js`

---

## 2. Colorful Queries

**Goal:** Visual differentiation of query types through background colors.

**Ideas:**
- Light blue (current) for general queries
- Light green for reading-related (`workbench_list.js`)
- Light yellow/amber for fleeting notes (`^idea-*`)
- Light orange for TODOs (`^todo-*`)

**Depends on:** Task #1 (custom classes) — need class selectors before we can apply different colors.

**Implementation:**
- Could be parameter-driven in `fleeting_block_markers.js` (pass color hint with marker type)
- Or purely CSS-based using `:has()` selectors if supported

---

## 3. Implement Query Candidates

**Goal:** Build out the 14 identified queries as the Zettelkasten grows.

**Reference:** [[Query-Candidates]]

**Priority suggestions:**
1. **Blocked with completed blockers** (#4) — immediate workflow value
2. **Idea chain endpoints** (#6) — identifies growth points
3. **Stale workbenches** (#3) — project hygiene
4. **Random idea** (#13) — serendipity, fun to use

**Approach:**
- Implement as separate scripts in `Scripts/`
- Add to Studio dashboard or create a "Maintenance" note
- Some queries (like #13 Random Idea) could be a button/command rather than a table

---

## Completed (last session)

- [x] Define canonical structure (note types, properties, inline fields)
- [x] Create `fleeting_block_markers.js` for `^idea-*` and `^todo-*`
- [x] Refactor all scripts to use `note_type` instead of tags
- [x] Add `to-read` status with blue indicator
- [x] Create `active_workbenches.js` for The Studio
- [x] Style Dataview tables with CSS
- [x] Create Workbench Note Template
- [x] Create Idea Note Template
- [x] Write The Studio Manual
