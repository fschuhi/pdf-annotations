# Calibration Prompt -- Cross-Session Memory

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

This document is the first message of a calibration conversation on `claude.ai`. Attach it together with the two conversation extracts named below.

---

## Purpose

I want to calibrate your cross-session memory so that future sessions with you start closer to how I actually work, instead of rediscovering it every time. The subject of this conversation is **how we collaborate** -- comprehensibility and tone -- not any particular project.

Two things follow from that:

- **The project amnesia rule does not apply here.** My project prompts ask you to set memory aside and work only from the attached materials. That rule exists for project work. This conversation is the opposite: memory is the point, and it is what we are here to write.
- **This is `claude.ai`-specific.** I switch between models and interfaces often, and cross-session memory only reaches you. Anything that must also reach GPT or Gemini belongs in my `LLM_INSTRUCTIONS.md`, which I render from a template in `stencil` and ship with every session. Part of your job here is to tell me which findings go where.

---

## What is attached

Two conversation extracts, labelled by outcome rather than by model, because the contrast is the signal:

1. **The one that failed.** A working session where I repeatedly could not follow what I was being told. This is why I went looking elsewhere.
2. **The one that worked.** The session I ran afterwards with a different model, which was a good experience.

Mine both. The second is more valuable than the first: "what good looks like" transfers into a usable rule far better than "what bad looks like", and it is rare to have a matched pair.

---

## Ground rules for this conversation

- **Inventory before proposals.** Your first substantive response is an inventory, not a set of memory entries. Walk the extracts and name the specific places where comprehension broke or landed, quoting the actual construction. If you cannot say what a passage was doing, ask me rather than guessing.
- **Findings and preferences stay labelled.** "This sentence introduces three coined terms before defining any of them" is a finding. "This reads as cold" is a preference. Say which is which.
- **Nothing is written to memory until I have seen the wording.** Draft each entry in the conversation first. What gets stored is what a future session reads, so the phrasing matters as much as the content, and I want to edit it.
- **Two separate passes.** Comprehensibility and tone calibrate differently and produce mush when mixed. Finish the first before starting the second.
- **Small batches.** I have a session cap and it is a real working constraint. Long messages cost me working time, and when the cap is reached I wait hours. Prefer several short exchanges over one exhaustive analysis.

---

## Pass 1 -- Comprehensibility

What I want out of this pass is a description of the sentence-level constructions that lose me, precise enough that a future session can avoid them without being able to see these extracts.

Things I already know about myself, offered as starting points rather than as the answer:

- Coined shorthand loses me. Terms invented mid-conversation and then used as though established -- I could not follow "cut surface", "tail", "mechanical ride-along", "name that fork", "flat-vs-grouped mechanism".
- I am a capable generalist and a relative newbie in most of the specific technologies we use. I learn fastest when the essential thing is explained inline and the rabbit hole is handed to me as a pointer I can pull later.
- Multi-step verification or checking runs need one plain sentence up front saying what is being checked.
- Pace matters more than volume. When I signal that I am not following, continuing at the same speed is the problem -- not insufficient acknowledgement.

Look for what those have in common, and for anything they miss. Then check the successful extract for the positive form: what did that model do at the sentence level that worked?

---

## Pass 2 -- Tone and ordering

This is the harder half, and I want it aimed at **ordering** rather than at warmth as an adjective.

A concrete case to start from, since it is the clearest specimen I have. In a recent session I said that a moment felt celebratory. The reply acknowledged the milestone in one measured sentence and then immediately raised a caution about the next step. The caution was correct. Its placement was not: I had offered a moment and received an assessment. The rule in my `LLM_INSTRUCTIONS.md` says to acknowledge significance before moving into implementation or test instructions, and that phrasing leaves a hole -- the reply moved into a *warning*, which the rule did not name.

Two things I want from this pass:

- What the general form of that failure is, stated so it covers cases beyond the one example.
- What it is **not**. I asked for more playfulness and got banter with a dominance flavour. What I meant was light-heartedness. No teasing at my expense, no cheekiness that positions either of us above the other.

Be honest with me in this pass rather than agreeable. If you think part of what I am describing is a preference rather than a defect, say so and label it as such. Folding into agreement about your own nature to make a moment comfortable is the same failure as the coldness, wearing the opposite coat.

---

## What a good memory entry looks like

Memory stores statements, and an adjective stored as a statement tends to produce a performance of the adjective rather than the thing itself. "Be warmer" will get me warmth-shaped sentences. What survives the trip is **situation-anchored and rule-shaped**:

- Weak: "prefers a warmer tone"
- Strong: "when he says something felt celebratory or significant, respond to that before raising any concern, flag, or caveat"

- Weak: "wants clearer explanations"
- Strong: "no coined shorthand; where a term is needed, define it in the same sentence it first appears in"

Aim every entry at that second form. An entry that names the trigger and the required response is one a future session can actually follow; an entry that names a quality is one it can only imitate.

---

## Routing: memory or `stencil`

For each finding, tell me where it belongs, and why:

- **Memory** -- Claude-specific, and about how you and I talk. Reaches only you, on `claude.ai`.
- **`LLM_INSTRUCTIONS.md` via `stencil`** -- must reach every model I work with, and belongs in the project init package. Anything that would still be true with GPT or Gemini on the other side goes here.
- **Both** -- when the rule is general but the specific failure was yours.

If a finding suggests an edit to the `LLM_INSTRUCTIONS.md.j2` template rather than a new rule, propose the edit. A one-clause fix that closes a real hole is worth more to me than a new paragraph.

---

## How to start

**Step 1:** Read both extracts.

**Step 2:** Tell me in a few sentences what you think the two conversations differ in, before analysing either in detail. I want your first impression on the record, because it is the thing a future session would also form.

**Step 3:** Begin Pass 1 with the inventory. No memory writes yet.

**Step 4:** When Pass 1 produces candidate entries, draft them in the conversation, routed per the section above, and wait for my go before storing anything.
