# The Obsidian Dharma Vault: Database Architecture

## 1. Current Roadmap (Next Steps)
Before expanding to new categories, the following immediate steps remain:
1. Fill in `Author Typology` for the "Vajrayana" and "Mahayana" sheets.
2. Review the set of 4 completed sheets to audit for structural inconsistencies.
3. Review the remaining 626 books in the backlog to target and build out new functional groups.

## 2. Introduction & Core Philosophy
This document outlines the structural logic for a practitioner-focused library database. Unlike a strict academic or doxographical catalog, this database prioritizes the "on-the-cushion" reality of a text. If a book serves the spiritual journey of a specific path (e.g., reading a master's life story to inspire Dzogchen practice), it is categorized within that functional path rather than being relegated to a generic "Biography" bucket.

## 3. The Top-Level Taxonomy (Practice Systems)
The `Practice System` column acts as the primary macro-filter. To accurately reflect spiritual mechanics and maintain database scalability, we divide the texts into the following overarching buckets:
* **Dzogchen**: Pure Atiyoga / Great Perfection texts and practice manuals.
* **Vajrayana**: Buddhist Tantra utilizing Deity Yoga, Subtle Body Yogas, and empowerment.
* **Mahayana**: Sutrayana texts focused on the Bodhisattva path, Emptiness, Madhyamaka, and Yogacara.
* **Theravada**: Early Buddhism, Pali Canon, Vipassana, Jhana, and Thai Forest traditions.
* **Shaiva Tantra**: Non-Buddhist Indian Tantra (e.g., Kashmiri Shaivism, Trika), kept strictly separated from Buddhist Vajrayana.
* **General**: Broad anthologies, secularized modern syntheses, or pan-Buddhist overviews.

## 4. Column Architecture & Schema
The database utilizes a mix of universal columns applied to every book and system-specific columns that activate only for certain Practice Systems.

**THE N/A MANDATE:** Every single empty or inapplicable cell across the entire database must be explicitly filled with `N/A` without exception.

### Universal Columns
* `#`: Index number.
* `PDF`: The exact file name / bibnote ID.
* `Practice System`: The top-level taxonomy (listed above).
* `Subgroup`: The specific function or format of the text. **Rule:** This must define the text type (e.g., *Practice Manual, Commentary, Biography / Namtar, Lamrim / Foundational, Academic / Comparative*) and must never lazily duplicate doxographical classifications like the Dzogchen Series or Tantra Class.
* `Lineage`: The historical tradition (e.g., Nyingma, Gelug, Thai Forest).
* `Author Typology`: The specific vantage point or authority of the author.
    * *Tibetan Contexts:* Ngakpa / Mahasiddha, Tertön, Monastic / Scholar, Geshe.
    * *Western / General Contexts:* Academic Scholar, Lay Teacher / Translator, Pragmatic Dharma.
* `Synopsis`: Book description.

### System-Specific Columns
* **Dzogchen**:
    * `Dzogchen Series` (Mengagde, Semde, or Longde).
* **Vajrayana**:
    * `Tantra Class` (Action / Performance, Highest Yoga Tantra, Mahayoga, etc.).
    * `Yidam` (The focal meditational deity, e.g., Vajrasattva, Heruka).
* **Mahayana**:
    * `Text Category` (Sutra or Shastra).
* **Theravada (Bespoke Architecture)**:
    * `Jhana / Insight Paradigm` (e.g., Sutta Jhana, Commentarial / Visuddhimagga, Mahasi / Dry Insight).
    * `Primary Textual Basis` (e.g., Pali Suttas, Visuddhimagga, Abhidhamma).
    * `Key Figures / Influences` (e.g., Mahasi Sayadaw, Nagarjuna).
    * `Text Category` (Sutta, Abhidhamma, Commentary, or Modern).

## 5. The "Translation Triad" & Authorship Rules
Tracking root texts is critical. The triad consists of `Translation`, `Source Author`, and `Source Text`.
* **Translation Vocabulary:** Use *one* or *two* to count discrete root texts translated. For Theravada or complex scholarly works, use *Full*, *Anthology*, or *Embedded / Extensive*.
* **The Delimiter Rule:** Strictly use a forward slash (`/`) with spaces to separate multiple texts, authors, or classes. Never use commas (`,`) or ampersands (`&`).
* **The "Anonymous" Rule:** Ancient canonical texts or revealed termas (treasures) that lack a historical human author must be prefaced with `Anonymous / ` when listed alongside a human commentator (e.g., `Anonymous / Jamgon Mipham`).

## 6. The Evolving Definition of "Cycle"
The `Cycle` column adapts its meaning depending on the `Practice System`.
* **Dzogchen Cycle:** Specific visionary revelations or mind-treasures (e.g., *Longchen Nyingtik*, *Aro gTér*).
* **Vajrayana Cycle:** Overarching tantric mandalas or systems (e.g., *Guhyagarbha*, *Chakrasamvara*).
* **Mahayana & Theravada Cycle:** Defaults to `N/A`, as Sutrayana and Early Buddhism rely on overarching texts and sutras rather than discrete mandalas or terma revelations.

## 7. Edge Cases & Precedents (The "Tricky Stuff")
To calibrate decision-making, adhere to these established precedents:
* **The "Tibetan Hinayana" Rule:** Texts laying the foundational groundwork for Tantra (e.g., Chögyam Trungpa's *Path of Individual Liberation*) are categorized strictly under `Practice System: Vajrayana` with a `Foundational / Lamrim` Subgroup, keeping them entirely isolated from historical Theravada.
* **The Wylie Mandate:** To avoid cross-translation ambiguity, the `Source Text` and `Cycle` fields must always use Wylie transliteration for Tibetan works, rather than localized English titles.
* **The Cross-Tradition Isolation Rule:** If a text is a comparative study (e.g., Zen / Dzogchen), it defaults to the Tibetan practice system to ensure the eventual "Backlog" strictly isolates non-Buddhist or generic Non-dual literature.
* **Biographies:** Categorized by their spiritual tradition (e.g., `Practice System: Dzogchen`) rather than a generic bucket, using `Subgroup: Biography / Namtar`.
* **Modern Overviews / Psychology:** Western adaptations receive their tradition's Practice System but get `N/A` for the Translation Triad.
* **Embedded Root Texts:** Commentaries that translate the root verses line-by-line are tagged in the translation column (e.g., `Translation: two`) and combine the authors and texts (e.g., `Source Text: gsang ba'i snying po / gsang snying 'grel pa 'od gsal snying po`).
