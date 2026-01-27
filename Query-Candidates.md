# Query Candidates

Future queries to implement as The Studio grows.

---

## Hygiene / Housekeeping

### 1. Orphaned Ideas
Ideas where `DerivedFrom::` points to a bibnote, but there's no corresponding backlink in that bibnote's annotations (e.g., a `→ [[Idea - ...]]` in a processed fleeting note).

**Purpose:** Detect inconsistencies in the provenance trail.

### 2. Bibnotes with No Ideas Extracted
Bibnotes with `status: done` but no Idea Notes link to them via `DerivedFrom::`.

**Purpose:** Identify completed reading that hasn't generated any captured insights.

### 3. Stale Workbenches
Workbenches with `status: active` but no linked bibnotes touched in X days.

**Purpose:** Surface abandoned projects that should either be reactivated or marked dormant.

### 4. Blocked Bibnotes with Completed Blockers
Bibnote A has `status: blocked`, but the bibnote that has `Unblocks:: [[(A)]]` is `status: done`.

**Purpose:** Remind you to unblock PDFs that are now ready to continue.

### 5. Dangling Relationships
Inline fields (`Unblocks::`, `Continues::`, `DerivedFrom::`) that point to notes that don't exist.

**Purpose:** Catch broken links from deleted or renamed notes.

---

## Zettelkasten Growth / Health

### 6. Idea Chain Endpoints
Ideas that nothing continues from — leaf nodes in the Folgezettel tree.

**Purpose:** Identify growth points where new ideas could branch off.

### 7. Lonely Ideas
Ideas not linked from any Workbench.

**Purpose:** Find orphan ideas that should be integrated into a project.

### 8. Most Connected Ideas
Ideas with the most inbound and outbound links.

**Purpose:** Identify hubs in your thinking — central concepts that connect many threads.

### 9. Ideas per Bibnote
Count of Idea Notes with `DerivedFrom::` pointing to each bibnote.

**Purpose:** See which PDFs have been most generative for your thinking.

---

## Reading Management

### 10. Reading Queue
All bibnotes with `status: to-read`, optionally sorted by which Workbenches need them.

**Purpose:** Global view of unstarted reading material.

### 11. Recently Touched Bibnotes
Bibnotes sorted by most recent annotation timestamp.

**Purpose:** Quick access to what you've been actively reading.

### 12. Workbench Reading Progress
For each Workbench: count of bibnotes by status (done / reading / blocked / to-read).

**Purpose:** Dashboard view of project completion.

---

## Discovery / Serendipity

### 13. Random Idea
Surface a random Idea Note.

**Purpose:** Luhmann's "conversation partner" effect — encounter forgotten ideas.

### 14. Ideas by Topic Tag
Cluster ideas across Workbenches by `#topic/*` tags.

**Purpose:** Cross-project discovery of related concepts.

---

## Implementation Notes

- Queries 1-5 are housekeeping — run periodically to maintain system health
- Queries 6-9 help understand the shape of your Zettelkasten
- Queries 10-12 support daily reading workflow
- Queries 13-14 enable serendipitous discovery

Priority: Start with **#4** (blocked with completed blockers) and **#6** (chain endpoints) — these have immediate practical value.
