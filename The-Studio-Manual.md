# The Studio Manual

A PDF-integrated Zettelkasten system for Obsidian.

---

## Overview

The Studio is a Zettelkasten-inspired knowledge management system that bridges PDF reading and idea development. It uses Obsidian as its foundation, with custom scripts that surface connections, track reading progress, and capture fleeting notes directly from PDF annotations.

### Core Principles

1. **PDFs as primary sources** — Your library of academic papers and books feeds the system
2. **Fleeting notes in context** — Capture ideas where they arise (in PDF comments), process them later
3. **Atomic ideas** — One idea per note, connected through Folgezettel chains
4. **Workbenches as projects** — Thematic collections that organize reading and writing

---

## Note Types

The Studio uses three note types, identified by the `note_type` frontmatter property.

### Bibnote (`note_type: bibnote`)

Represents one PDF. Generated and maintained by `pdf-annotations`.

**Structure:**
```
---
pdf_id: (Author Year)
pdf_title: Title of the PDF
pdf_hash: XXXXXXX
status: to-read | reading | blocked | done
note_type: bibnote
---
#topic/...

[Free Text Area - user controlled]
- Your notes about this PDF
- Links to related materials
- Section headers for organization

<hr class="pdf-annot-sep">

[Annotations Area - managed by pdf-annotations]
## Section from PDF
> Highlighted text <span class="pdf-annot-date">DD.MM.YY HH:MM</span> [page](pdf://...)

> [!note] <span class="pdf-annot-date">DD.MM.YY HH:MM</span>
> Your comment on the highlight
```

**Status values:**
| Status | Icon | Meaning |
|--------|------|---------|
| `to-read` | 🔵 | Not yet started |
| `reading` | 🟢 | Currently active |
| `blocked` | ⛔️ | Waiting for another PDF |
| `done` | — | Completed |

**Key properties:**
- `pdf_hash` — Unique identifier, used in `pdf://` links
- `Unblocks::` — Points to bibnote(s) this PDF enables (when you finish reading this, you can continue those)

### Idea Note (`note_type: idea`)

An atomic insight extracted from reading or thinking.

**Template:**
```
---
date: {{date}}
time: {{time}}
note_type: idea
---
#topic/
**DerivedFrom**:: [[(Source Bibnote)]]
**Continues**:: [[(Previous Idea)]]

### The Idea
[Your atomic idea, written for your future self]

### Next in Chain
```dataviewjs
await dv.view("Scripts/next_in_chain", { current: dv.current() });
```
```

**Inline fields:**
- `DerivedFrom::` — Links to the source (bibnote, workbench, or another idea)
- `Continues::` — Links to the idea this one builds upon (Folgezettel)

### Workbench (`note_type: workbench`)

An active project or theme that collects related materials and ideas.

**Template:**
```
---
date: {{date}}
time: {{time}}
note_type: workbench
status: active
---
### Source Material
>[!tldr] Let's read!
- [[(Bibnote 1)]]
- [[(Bibnote 2)]]

### Ideas
>[!attention] Let's write!
- [[Idea - First Insight]]
- [[Idea - Second Insight]]

### Fleeting Notes
```dataviewjs
await dv.view("Scripts/fleeting_block_markers", { current: dv.current(), marker: "idea" });
```

### TODOs
```dataviewjs
await dv.view("Scripts/fleeting_block_markers", { current: dv.current(), marker: "todo" });
```

### Reading List
```dataviewjs
await dv.view("Scripts/workbench_list", { current: dv.current() });
```
```

**Status values:**
- `active` — Currently being worked on
- `dormant` — Paused, but not finished

---

## The Studio Dashboard

The Studio note serves as the entry point to all workbenches.

```dataviewjs
await dv.view("Scripts/active_workbenches", { current: dv.current() });
```

This displays all active workbenches with their connected idea counts.

---

## Fleeting Notes System

The key innovation: capture fleeting notes as PDF comments, then surface them in Obsidian for processing.

### Adding Fleeting Notes

In your PDF reader (e.g., PDF-XChange), add a comment to a highlight with a block marker:

```
This could become an idea about extended cognition ^idea-extended-cognition
```

Or for todos/questions:

```
Find the original source for this claim ^todo-find-source
```

### Processing Fleeting Notes

1. Run `pdf-annotations` to sync comments to bibnotes
2. Open the Workbench — fleeting notes appear in the query tables
3. Create an Idea Note from the fleeting note
4. Return to PDF, remove the `^idea-*` marker (optionally replace with link to the new Idea Note)

### Marker Conventions

| Prefix | Purpose | Example |
|--------|---------|---------|
| `^idea-` | Insight worth developing | `^idea-folders-self-defeating` |
| `^todo-` | Action item or question | `^todo-check-citation` |

---

## Relationships and Links

### Attention-Based Convention

Inline fields live on the note where your attention is focused, pointing to context you need to remember:

- **`Unblocks::`** on Bibnote A → "I'm reading A to enable progress on B"
- **`Continues::`** on Idea B → "B builds upon A"

### Link Types in Bibnotes

**From Free Text to PDF annotations:**
```markdown
[[#^longchenpa-block]]  — links to a block-marked comment
[[#Section Header]]     — links to a section from PDF
```

**From PDF comments to Free Text:**
```markdown
[[#My Analysis Section]]  — in a comment, links to free text header
```

**From PDF comments to other notes:**
```markdown
[[Other Note#section]]    — cross-reference to another note
```

### Folgezettel Chains

Ideas can form chains where each idea builds on the previous:

```
Idea A  ←(Continues)—  Idea B  ←(Continues)—  Idea C
```

The `next_in_chain.js` script shows all ideas that continue from the current one.

---

## Scripts Reference

All scripts live in `Scripts/` and are called via `dv.view()`.

### active_workbenches.js

Displays all active workbenches with idea counts.

**Usage:**
```dataviewjs
await dv.view("Scripts/active_workbenches", { current: dv.current() });
```

**Output:** Table with Active Workbench, Connected Ideas, Last Touched

### workbench_list.js

Shows the reading queue for a workbench with status, blockers, and resume links.

**Usage:**
```dataviewjs
await dv.view("Scripts/workbench_list", { current: dv.current() });
```

**Output:** Table with Status, Document, Waiting For, Action

**Features:**
- Calculates last-read page from annotation timestamps
- Shows blocking relationships
- Direct `pdf://` links to resume reading

### fleeting_block_markers.js

Surfaces `^idea-*` or `^todo-*` markers from PDF comments.

**Usage:**
```dataviewjs
await dv.view("Scripts/fleeting_block_markers", { current: dv.current(), marker: "idea" });
```

**Parameters:**
- `marker` — The prefix to search for (`idea` or `todo`)

**Context-aware:**
- On a Bibnote: shows markers from this PDF only, uses local links
- On a Workbench: shows markers from all linked bibnotes, includes source column

### next_in_chain.js

Shows ideas that continue from the current note (Folgezettel successors).

**Usage:**
```dataviewjs
await dv.view("Scripts/next_in_chain", { current: dv.current() });
```

**Output:** Table with Idea Note, Last Modified

---

## Properties Reference

### Frontmatter Properties

| Property | Used On | Values | Purpose |
|----------|---------|--------|---------|
| `note_type` | all | `bibnote`, `idea`, `workbench` | Classification |
| `status` | bibnote | `to-read`, `reading`, `blocked`, `done` | Reading state |
| `status` | workbench | `active`, `dormant` | Project state |
| `date` | idea, workbench | ISO date | Creation date |
| `time` | idea, workbench | HH:MM | Creation time |
| `pdf_*` | bibnote | various | Managed by pdf-annotations |

### Inline Fields

| Field | Used On | Points To | Meaning |
|-------|---------|-----------|---------|
| `Unblocks::` | bibnote | bibnote(s) | "Reading me enables progress on X" |
| `Continues::` | idea | idea(s) | "I am a Folgezettel of X" |
| `DerivedFrom::` | idea | bibnote, idea, or workbench | "I originated from X" |

### Tags

Reserved for multi-valued classification:
- `#topic/dzogchen`
- `#topic/phenomenology`
- `#topic/zettelkasten`

---

## CSS Styling

The Studio uses custom CSS in `.obsidian/snippets/studio.css` for:

- Compact frontmatter display
- Styled Dataview tables (light blue background, accent stripe, rounded corners)
- PDF annotation date styling

---

## Workflow Summary

### Daily Reading

1. Open a Workbench
2. Check the Reading List — pick a 🟢 or 🔵 document
3. Click the action link to open the PDF at your last position
4. Read, highlight, add `^idea-*` comments for insights
5. Run `pdf-annotations` to sync

### Idea Extraction

1. Open the Workbench
2. Review Fleeting Notes table
3. For each promising idea:
   - Create new Idea Note from template
   - Fill in `DerivedFrom::` and optionally `Continues::`
   - Write the atomic idea
4. Return to PDF, remove the `^idea-*` marker

### Managing Blockers

When PDF A requires reading PDF B first:

1. Set `status: blocked` on A
2. Add `Unblocks:: [[(A)]]` to B
3. The Reading List shows A as blocked, waiting for B
4. When B is done, unblock A

---

## Query Candidates (Future)

These queries could be added as the system grows:

**Hygiene:**
- Orphaned ideas (DerivedFrom points to bibnote, but no backlink)
- Bibnotes with no ideas extracted (status: done but no ideas link to them)
- Stale workbenches (active but untouched for X days)
- Blocked bibnotes with completed blockers

**Growth:**
- Idea chain endpoints (leaf nodes — growth points)
- Lonely ideas (not linked to any workbench)
- Most connected ideas (hubs)
- Ideas per bibnote (which PDFs are most generative?)

**Discovery:**
- Random idea (serendipity)
- Ideas by topic tag

---

## Appendix: pdf-annotations Integration

The `pdf-annotations` Python tool manages the synchronization between PDFs and bibnotes:

- Extracts highlights and comments from PDFs
- Generates/updates the annotations section of bibnotes
- Preserves the Free Text area above `<hr class="pdf-annot-sep">`
- Updates frontmatter metadata

Run with `make run` or configure a keyboard shortcut for quick syncing.

---

*The Studio — where reading becomes writing.*
