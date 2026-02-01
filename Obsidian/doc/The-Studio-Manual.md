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
time_spent: 0
---
#topic/...

`BUTTON[time-spent-increment]` `BUTTON[resume-pdf]`

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

**Key properties:**
- `pdf_hash` — Unique identifier, used in `pdf://` links
- `time_spent` — Reading time in minutes, tracked via Meta Bind button
- `Unblocks::` — Points to bibnote(s) this PDF enables (when you finish reading this, you can continue those)

### Idea Note (`note_type: idea`)

An atomic insight extracted from reading or thinking.

**Template:**
```
---
date: {{date}}
time: {{time}}
note_type: idea
derived_from: "[[(Source Bibnote)]]"
status: placeholder  # optional, omit for fully developed ideas
---
#topic/

## The Idea
[Your atomic idea, written for your future self]

## Next in Chain
```dataviewjs
await dv.view("Scripts/next_in_chain", { current: dv.current() });
```
```

**Key properties:**
- `derived_from` — Links to the source (bibnote, workbench, or another idea)
- `status` — Set to `placeholder` for underdeveloped ideas; omit entirely for fully developed ideas

**Inline fields:**
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
time_spent: 0
---

`BUTTON[time-spent-increment]`

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

**Key properties:**
- `time_spent` — Writing/organizing time in minutes, tracked via Meta Bind button

**Status values:**
- `active` — Currently being worked on
- `dormant` — Paused, but not finished

---

## Status Values Reference

| Status | Note Type | Meaning |
|--------|-----------|---------|
| `to-read` | Bibnote | Not yet started |
| `reading` | Bibnote | Currently active |
| `blocked` | Bibnote | Waiting for another PDF |
| `done` | Bibnote | Completed |
| `placeholder` | Idea | Not a fully-fledged idea yet; needs development |
| (absent) | Idea | Fully developed idea |
| `active` | Workbench | Working on it |
| `dormant` | Workbench | Currently inactive |

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
3. For each fleeting note, decide: **promote** (create idea note), **decline** (remove marker), or **placeholder** (create minimal idea note)
4. Create an Idea Note using the Templater template (trigger from the bibnote to auto-fill `derived_from`)
5. Return to PDF, replace the `^idea-*` marker with a link to the new Idea Note

### Marker Conventions

| Prefix | Purpose | Example |
|--------|---------|---------|
| `^idea-` | Insight worth developing | `^idea-folders-self-defeating` |
| `^todo-` | Action item or question | `^todo-check-citation` |

### Fleeting Note Resolution

Every fleeting note should be resolved to keep the queue short:

| Resolution | When to use | Action |
|------------|-------------|--------|
| **Promote** | The note has substance or makes a connection | Create full idea note |
| **Placeholder** | Worth tracking but not yet developed | Create idea note with `status: placeholder` |
| **Decline** | Not actually generative for your thinking | Remove `^idea-` prefix, keep comment text if useful |

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

**From PDF comments to other parts of the same PDF:**
```markdown
see [[#^some-block-anchor]]  — internal cross-reference within the document
```

### Folgezettel Chains

Ideas can form chains where each idea builds on the previous:

```
Idea A  ←(Continues)—  Idea B  ←(Continues)—  Idea C
```

The `next_in_chain.js` script shows all ideas that continue from the current one.

### Citations in Free Text

Track what a paper cites using a `## Cites` section in the bibnote's Free Text:

```markdown
## Cites
- [[(Zahavi 2005)]] — subjectivity, for-me-ness
- [[(Klawonn 2009)]] — I-dimension origin
- (Madell 1981) — not in library yet
```

**Conventions:**
- Wiki-links `[[(Author Year)]]` for papers with bibnotes (creates backlinks)
- Plain text `(Author Year)` for papers not yet in the library
- Emdash `—` followed by relevance note (why this citation matters, not just the title)

### Embedding Headers in Workbenches

Pull sections from bibnotes into workbenches for project organization:

```markdown
![[(Fasching 2012c)#eliminativism, reductionism, naturalism]]
```

This embeds the entire section, useful for building argument outlines from multiple sources.

---

## Scripts Reference

All scripts live in `Scripts/` and are called via `dv.view()`.

### active_workbenches.js

Displays all active workbenches with idea counts.

**Usage:**
```dataviewjs
await dv.view("Scripts/active_workbenches", { current: dv.current() });
```

**Output:** Table with Active Workbench, Ideas, Writing, Reading, Last Touched

**Features:**
- Shows connected idea count per workbench
- Displays writing time (from workbench's `time_spent`)
- Displays total reading time (summed from linked bibnotes)
- Shows grand total below table

### workbench_list.js

Shows the reading queue for a workbench with status, blockers, and resume links.

**Usage:**
```dataviewjs
await dv.view("Scripts/workbench_list", { current: dv.current() });
```

**Output:** Table with Status, Document, Action, Time, Waiting For

**Features:**
- Calculates last-read page from annotation timestamps
- Shows blocking relationships
- Direct `pdf://` links to resume reading
- Displays time spent per bibnote
- Shows total reading time below table

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

### open_pdf_resume.js

Opens the current bibnote's PDF at the most recently annotated page.

**Usage:** Called via Meta Bind button on bibnotes.

**Features:**
- Reads `pdf_hash` from frontmatter
- Scans annotations for most recent timestamp
- Opens PDF at that page via `pdf://` URL

---

## Time Tracking

The Studio tracks time spent on reading (bibnotes) and writing (workbenches) using Meta Bind buttons.

### Time Increment Button

Add to Meta Bind button templates:

```yaml
label: ⏱️ +30 min
id: time-spent-increment
style: default
actions:
  - type: updateMetadata
    bindTarget: time_spent
    evaluate: true
    value: Number(x || 0) + 30
```

Place the button in bibnotes and workbenches: `BUTTON[time-spent-increment]`

### Resume Reading Button

For bibnotes, add a button to open the PDF at the last-read page:

```yaml
label: 📖 Resume reading
id: resume-pdf
style: primary
actions:
  - type: js
    file: Scripts/open_pdf_resume.js
```

Place in bibnotes: `BUTTON[resume-pdf]`

### Time Display

- **Reading List** (workbench): Shows time per bibnote and total reading time
- **Studio Dashboard**: Shows writing time, reading time, and grand total per workbench

---

## Properties Reference

### Frontmatter Properties

| Property | Used On | Values | Purpose |
|----------|---------|--------|---------|
| `note_type` | all | `bibnote`, `idea`, `workbench` | Classification |
| `status` | bibnote | `to-read`, `reading`, `blocked`, `done` | Reading state |
| `status` | idea | `placeholder` or absent | Development state |
| `status` | workbench | `active`, `dormant` | Project state |
| `derived_from` | idea | wiki-link | Source of the idea |
| `time_spent` | bibnote | minutes | Reading time tracked via button |
| `time_spent` | workbench | minutes | Writing/organizing time tracked via button |
| `date` | idea, workbench | ISO date | Creation date |
| `time` | idea, workbench | HH:MM | Creation time |
| `pdf_*` | bibnote | various | Managed by pdf-annotations |

### Inline Fields

| Field | Used On | Points To | Meaning |
|-------|---------|-----------|---------|
| `Unblocks::` | bibnote | bibnote(s) | "Reading me enables progress on X" |
| `Continues::` | idea | idea(s) | "I am a Folgezettel of X" |

### Tags

Reserved for multi-valued classification:
- `#topic/dzogchen`
- `#topic/phenomenology`
- `#topic/zettelkasten`

---

## Templater Integration

The Idea Note template uses Templater to streamline creation:

**Template: `Idea Note from Bibnote.md`**
```
<%*
const sourceFile = tp.config.active_file;
const title = await tp.system.prompt("Idea title");
const fileName = "Idea - " + title;
await tp.file.rename(fileName);
await tp.file.move("Ideas/" + fileName);
-%>
---
date: <% tp.date.now("YYYY-MM-DD") %>
time: <% tp.date.now("HH:mm") %>
note_type: idea
derived_from: "[[<% sourceFile.basename %>]]"
---
#topic/

## The Idea
<% tp.file.cursor() %>

## Next in Chain
```dataviewjs
await dv.view("Scripts/next_in_chain", { current: dv.current() });
```

**Workflow:** Trigger the template while viewing a bibnote. The `derived_from` field auto-populates with the bibnote name, and the cursor lands in the Idea section ready for writing.

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
3. For each fleeting note, decide: promote, placeholder, or decline
4. For promotions/placeholders: trigger the Templater template from the bibnote
5. Write the idea (or minimal placeholder text)
6. Add `status: placeholder` if underdeveloped
7. Return to PDF, replace `^idea-*` marker with link to the Idea Note

### Managing Blockers

When PDF A requires reading PDF B first:

1. Set `status: blocked` on A
2. Add `Unblocks:: [[(A)]]` to B
3. The Reading List shows A as blocked, waiting for B
4. When B is done, unblock A

---

## Query Candidates (Future)

See `Query-Candidates.md` for the full list of future queries to implement as The Studio grows, including:

- Hygiene queries (orphaned ideas, dangling links, placeholder ideas)
- Growth queries (chain endpoints, lonely ideas, workbench ideas auto-population)
- Reading management (reading queue, workbench progress)
- Discovery (random idea, ideas by topic)

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
