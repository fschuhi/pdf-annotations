# LINK_REFACTOR.md -- Old Entry Page Links in Bibnotes

Status: deferred, not started. Execute **after** the `AUDIT.md` agenda is complete. Nothing in the audit depends on this, and this depends on nothing in the audit.

This document is self-contained in the spirit of `AUDIT.md` and `TARGET_ARCHITECTURE.md`: a future session should be able to execute it from this file plus the standard filesdump, without conversational context. `CRITICAL_RULES.md` applies to any work derived from it.

---

## 1. Charter

Records a known, bounded cleanup job in the Obsidian bibnotes: wikilinks in the free-text area still use the pre-`pdf-annotations` id form and therefore point nowhere. The job is one-off, the population is closed, and the conclusion of the analysis is that **no tool needs to be built** -- PyCharm's "Replace in Path" does the work, and PyCharm's "Find in Path" produces the follow-up report.

Scope is bibnotes only. Idea notes and workbenches are out of scope.

---

## 2. Backstory

Under the pre-`pdf-annotations` workflow the PDFs lived in Zotero, and each work had two Obsidian pages:

- an **Entry Page**, holding a link to the PDF, a link to the sidecar, and manually written notes -- including wikilinks to other Entry Pages;
- a sidecar **Annotations** page, generated from Zotero's "export markdown".

Entry Pages were named without a space before the year: `(Fink2012)`, `(Gollwitzer-Schwarz+Sheeran2006b)`. Bibnotes use the spaced form: `(Fink 2012)`, `(Gollwitzer-Schwarz+Sheeran 2006b)`.

Migration went: `make run` generated the bibnote from the well-formed PDF filename (e.g. `(Fink 2012) The 'Scent' of a Self - Buddhism and the First-Person Perspective.pdf`), then the Entry Page content was copied by hand into the bibnote's free-text area, then the old Entry Page was deleted.

**244 Entry Pages, all migrated. The population is closed -- there is no further migration work that would produce more of these links.**

What was not done, because it would have been hundreds of manual edits: inserting the missing space into every copied wikilink. That is the whole of the remaining job.

### Why Obsidian did not fix this itself

Renaming the 244 Entry Pages **before** deleting them would have made Obsidian rewrite every inbound link automatically. That is exactly how the Fasching and Zahavi links in the sample below came to be correct -- they date from the first prototype work in The Studio. The option existed and was consciously declined as not worth 244 renames. This is recorded so that a future session does not "discover" the missed opportunity and treat it as an accident.

---

## 3. Worked example

From `(Fink 2012).md`, free-text area, verbatim:

```
cites
- [[(Fasching 2009)]]
-  [[(Fasching 2011)]]
-  [[(Klawonn 2009)]]
- [[(Gallagher2012)]] The phenomenological mind
- [[(Gunaratana1992)]] Mindfulness in plain English
- [[(MacKenzie2008)]] Self-awareness without a self: Buddhism and the reflexivity of awareness
- [[(Zahavi 2005a)]]  Subjectivity and selfhood: Investigating the first-person perspective
- [[(Zahavi 2011a)]] The experiential self: Objections and clarifications
```

The stray spaces and the fact that some links are trailed by a loose title are **not** part of this job. Only the links are in scope.

`[[(Gallagher 2012)]]` exists as a bibnote and contains the migrated content of the old `[[(Gallagher2012)]]`. The old page itself is gone.

---

## 4. Inventory of the two sample notes

Sample: `(Fink 2012).md` and `(Deroche+Sheehy 2022).md`.

### Above the separator (user territory, free text)

1. `[[(Fasching 2009)]]`, `[[(Zahavi 2005a)]]` -- new-style, already correct. Must survive untouched, disambiguation letter included.
2. `[[(Gallagher2012)]]`, `[[(Dunne2011)]]` -- the target class.
3. `[[Deroche and Sheehy - 2022 - The Distinctive Mindfulness of Dzogchen Jigme Lingpa's Advice on Meta-Awareness and Nondual Meditation#^Shardrol|Shardrol]]` -- a third legacy link form: Zotero dash-format page name, with a block reference and an alias. Untouched by any `(AuthorYear)` pattern. After this job runs, this is the remaining broken-link class.
4. `![[Deroche-2022-1.png]]` -- image embed carrying both a year and a dash. Must not be touched.
5. `([Fink, 2012, p. 301](zotero://select/library/items/FQ2AT3CW))` -- residue of the old Zotero markdown export. Parenthesised, has a year, is not a wikilink. Must not be touched.

### Below the separator (machine territory, regenerated from the PDF)

6. `> see ((Norbu1980)), ((Norbu2014))` and `> This matches the presentation of ((Norbu1984)).` -- inside PDF highlight comments. Old-style ids in **double** parentheses; that was the convention at the time. Same problem, different location and different syntax.
7. `[[Semde]]` -- a real wikilink authored inside a PDF comment. Proof that wikilinks do occur below the separator.
8. `(Goodman 1992)`, `(Sogdogpa 1999)`, `(2008, p. 249)`, `(Guenther 1976, pp. 85, 124; Goodman 2020, pp. 110, 153-54)` -- verbatim author-date citations inside quoted PDF text.

---

## 5. Findings

**Finding -- restrict the rewrite to wikilink targets.** `TODO.md`'s "Fix old IDs" item says the replacement is "simply by pattern". Inventory items 5, 6 and 8 are counter-evidence: an unrestricted `(Word2011) -> (Word 2011)` rewrite reaches into Zotero export syntax and into text that is meant to be verbatim from the PDF. Requiring a leading `[[` eliminates that entire class by construction, at no cost.

**Finding -- the rewrite must not check whether the target exists.** Some `cites` links have wikilink structure but never pointed to an Entry Page at all: they are books and papers to be added to the library in future. They need to become bibnote-conform too, so that they resolve once the work arrives. This confirms `TODO.md`'s "it doesn't matter if there is actually such a new ID".

**Finding -- stop at the separator.** Item 7 shows wikilinks genuinely occur below it, so this is a rule rather than a happy accident. Rewriting there would be either transient or wrong: the annotation block is regenerated from the PDF whenever the change gate fires, and Anima updates `pdf_mtime` on every open, so the gate fires often.

**Finding -- comments cannot be durably fixed from the note.** Item 6 lives in the PDF, not in the Markdown. Any edit made to it in the bibnote is erased by the next re-extract. Fixing those means editing the PDF comments themselves. Estimated population: roughly 100 links across the whole body of highlighted comments. Some were already fixed by hand before the work was parked in favour of building The Studio.

**Finding -- the collateral is self-healing.** Because the annotation block is regenerated from the PDF, an unrestricted rewrite below the separator is undone by the next full re-extract. Section 6 turns this from a hazard into the mechanism of the report.

---

## 6. Execution plan

### Step 0 -- Version control or backup. Blocking.

The vault is currently **not** under git and has no versioned backup. Every step below performs a bulk write across 244 irreplaceable notes. Do this first, and treat it as a precondition rather than a nicety. This is its own piece of work and does not belong to this document.

### Step 1 -- Rewrite the free-text links (PyCharm "Replace in Path")

Scope: `notes_root`. Regex mode on.

```
find:    \[\[\(([^()\[\]]*[^()\[\]\s\d])(\d{4}[a-z]?)\)
replace: [[($1 $2)
```

Why this is self-limiting: the `[^\s\d]` immediately before the year group means the character preceding the digits must be neither a space nor a digit. `[[(Zahavi 2005a)]]` therefore cannot match, correct links are inert, and a second run is a no-op.

Why it stops at `)` rather than `]]`: aliases, block references and trailing titles inside the link then need no special cases. `[[(Fink2012)|Fink]]`, `[[(Fink2012)#^abc]]` and `[[(Gallagher2012) The phenomenological mind]]` all rewrite correctly.

What it cannot match: `![[Deroche-2022-1.png]]` and `((Norbu1980))` have no `[[(`; `([Fink, 2012, p. 301](zotero://...))` has none either.

Use the preview as the dry-run. It lists every match in context before anything is written, and one Undo covers the whole operation.

Known collateral: any old-style wikilink sitting **below** the separator is rewritten too, since a regex cannot express the boundary. Step 2 reverts it.

### Step 2 -- Force a full re-extract

Set `pdf_size` to zero in every bibnote, then run `make run`.

`sync._pdf_has_changed` compares `pdf_mtime` and `pdf_size`; a mismatch on either forces the re-extract. Zeroing the size is therefore enough, and it does not disturb `pdf_mtime`.

This also needs no tool -- the same PyCharm dialog does it, scoped to `notes_root`:

```
find:    ^pdf_size: \d+$
replace: pdf_size: 0
```

`pdf_size` appears only in frontmatter, so the line anchors are sufficient.

Effect: every annotation block is rebuilt from its PDF, which restores the below-separator text byte for byte and undoes step 1's collateral. Free text is preserved by `notes.replace_annotation_block` and is not at risk.

Caveats, none of them blocking:

- A bibnote that `sync._decline_reason` declines (missing separator, unparseable frontmatter -- `AUDIT.md` A2) is never written, so its block keeps whatever step 1 left there. Declines are reported per line during the run; check the run output.
- A bibnote whose PDF is missing or errors is never visited, with the same consequence.
- The run costs a full extraction pass over the collection -- roughly 145s post-A4 for 244 files (`AUDIT.md` V3).

An alternative to zeroing would be a real `--force` flag on `sync`. Not proposed here: `--dry-run` is still a no-op (F20) and gets made real by A8, so a flags discussion belongs there and not in a one-off cleanup.

### Step 3 -- Report the remaining work (PyCharm "Find in Path", read-only)

After step 2, every un-spaced id above the separator has been fixed and every one below it has been restored. So a search for the un-spaced form now isolates exactly the comments that need manual attention in the PDFs.

**The step 1 pattern is the wrong search here.** Comment references use double parentheses, not wikilinks, so `\[\[\(` would find nothing and report a clean vault. Search broadly instead -- this is read-only, so over-matching costs only a glance:

```
find: \([^()\[\]]*[^()\[\]\s\d]\d{4}[a-z]?\)
```

This catches `((Norbu1980))`, bare `(Gallagher2012)` and any wikilinked survivor. It does not catch `(Goodman 1992)` or `(Guenther 1976, pp. 85, 124; ...)`, because the space before the year excludes the first and the trailing page numbers exclude the second.

Expect a small number of false positives above the separator: un-spaced ids in plain prose rather than in wikilinks. They are visible at a glance in the results list.

### Step 4 -- Fix the PDF comments by hand

Open each PDF surfaced by step 3 in Anima and correct the comment text there. Roughly 100 links. No deadline; the bibnote text repairs itself on the next re-extract of that file.

---

## 7. Out of scope

These are real and known, and this job does not address any of them:

- **Zotero dash-format links** (inventory item 3), including block references and aliases. This is the link class that remains broken after steps 1 to 4.
- **Zotero markdown citation links** (item 5), the `([Author, Year, p. N](zotero://...))` residue in migrated free text.
- The loose titles trailing some `cites` entries, and the stray double spaces. Cosmetic, deliberately untouched.

---

## 8. Open questions

- **Does the reporting utility still have a job?** The original wish was a tool that lists which bibnotes carry highlight comments pointing at Entry Pages. Section 6 step 3 delivers the same list with no code. A utility would only be worth building if this needs re-running periodically -- which, given a closed population of roughly 100 comments fixed once, it probably does not. Decide before writing anything.
- **Is `((...))` the only comment-side form?** The sample shows double parentheses consistently, but the sample is two notes. Step 3's broad pattern covers single, double and wikilinked forms, so this resolves itself when the report is run.

---

## 9. Correlation with other documents

- `TODO.md` "Fix old IDs" under Tooling: superseded by this document. Its "create a tool" framing is retired -- the analysis concludes no tool is needed. Its "the replacement is simply by pattern" is corrected by section 5.
- `TODO.md` needs one new item: put the vault under version control (section 6, step 0). It blocks this job and is worth having regardless.
- `AUDIT.md`: no interaction. This work waits until the audit agenda is complete.
- `GOALS.md`: not on the Current Session Pointer, and should not be until the audit finishes.
