# Buddhist Practitioner's Library: Database Design & Taxonomy

## 1. Introduction & Core Philosophy
This document outlines the structural logic for a practitioner-focused library database. Unlike a strict academic or doxographical catalog, this database prioritizes the "on-the-cushion" reality of a text. If a book serves the spiritual journey of a specific path (e.g., reading a master's life story to inspire Dzogchen practice), it is categorized within that functional path rather than being relegated to a generic "Biography" bucket.

## 2. The Top-Level Taxonomy (Practice Systems)
The `Practice System` column acts as the primary macro-filter. To accurately reflect spiritual mechanics and maintain database scalability, we divide the texts into the following overarching buckets:
* **Dzogchen**: Pure Atiyoga / Great Perfection texts and practice manuals.
* **Vajrayana**: Buddhist Tantra utilizing Deity Yoga, Subtle Body Yogas, and empowerment.
* **Mahayana**: Sutrayana texts focused on the Bodhisattva path, Emptiness, Madhyamaka, and Yogacara.
* **Theravada**: Early Buddhism, Pali Canon, Vipassana, Jhana, and Thai Forest traditions.
* **Shaiva Tantra**: Non-Buddhist Indian Tantra (e.g., Kashmiri Shaivism, Trika), kept strictly separated from Buddhist Vajrayana.
* **General**: Broad anthologies, secularized modern syntheses, or pan-Buddhist overviews.

## 3. Column Architecture & Schema
The database utilizes a mix of universal columns applied to every book and system-specific columns that activate only for certain Practice Systems.

**Universal Columns**
* `PDF`: The exact file name.
* `Practice System`: The top-level taxonomy (listed above).
* `Subgroup`: The specific activity, philosophical school, or text type (e.g., Deity Yoga, Madhyamaka, Biography / Namtar).
* `Lineage`: The historical tradition (e.g., Nyingma, Gelug, Thai Forest).

**System-Specific Columns**
* `Dzogchen Series` (Dzogchen only): Mengagde, Semde, or Longde.
* `Tantra Class` (Vajrayana only): Action / Performance, Highest Yoga Tantra, Mahayoga, etc.
* `Yidam` (Vajrayana only): The focal meditational deity (e.g., Vajrasattva, Heruka).
* `Text Category` (Mahayana only - Proposed): Sutra or Shastra.

## 4. The "Translation Triad" & Authorship Rules
Tracking root texts is critical. The triad consists of `Translation` (count), `Source Author`, and `Source Text`.
* **The Delimiter Rule**: Strictly use a forward slash (`/`) with spaces to separate multiple texts, authors, or classes. Never use commas (`,`) or ampersands (`&`).
* **The "Anonymous" Rule**: Ancient canonical texts or revealed termas (treasures) that lack a historical human author must be prefaced with `Anonymous / ` when listed alongside a human commentator (e.g., `Anonymous / Jamgon Mipham`).
* **Missing Data**: All empty or inapplicable cells must be filled with `N/A`.

## 5. The Evolving Definition of "Cycle"
The `Cycle` column adapts its meaning depending on the `Practice System`.
* **Dzogchen Cycle**: Specific visionary revelations or mind-treasures (e.g., *Longchen Nyingtik*, *Aro gTér*).
* **Vajrayana Cycle**: Overarching tantric mandalas or systems (e.g., *Guhyagarbha*, *Chakrasamvara*).
* **Mahayana Cycle**: Generally `N/A`, as Sutrayana relies on overarching Sutras and Shastras rather than discrete mandalas or terma revelations.

## 6. Edge Cases & Precedents (The "Tricky Stuff")
To calibrate decision-making, adhere to these established precedents:
* **Biographies**: Categorized by their spiritual tradition (e.g., `Practice System: Dzogchen`) rather than a generic bucket, using `Subgroup: Biography / Namtar`.
* **Modern Overviews / Psychology**: Western adaptations (e.g., Tarthang Tulku, Ken McLeod) receive their tradition's Practice System but get `N/A` for the Translation Triad.
* **Embedded Root Texts**: Commentaries that translate the root verses line-by-line (e.g., Mipham's *Luminous Essence*) are tagged as `Translations: two` and combine the authors and texts (e.g., `Source Text: gsang ba'i snying po / gsang snying 'grel pa 'od gsal snying po`).
