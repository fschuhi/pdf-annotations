// bibnote_overview.js
//
// Builds one table row per bibnote: a clickable cover thumbnail, a clickable
// pdf_id (both open the note), plus a few frontmatter fields. Also adds a
// "copy table" button that puts the data on the clipboard as tab-separated
// values, so it pastes cleanly into Excel.
//
// Usage from any note:
//   ```dataviewjs
//   await dv.view("Scripts/bibnote_overview")
//   ```
//
// Optional overrides:
//   await dv.view("Scripts/bibnote_overview", { folder: "Papers/Collection/Notes", width: 60 });

const folder = input?.folder || "Papers/Collection/Notes"; // vault-relative path
const width = input?.width || 60;
const letterFilter = input?.startsWithLetter || null; // e.g. "A"

function normalizedFirstLetter(pdfId) {
    const author = (pdfId ?? "").replace(/^\(/, "");
    const firstChar = author.charAt(0);
    // NFD normalization splits an accented character into base letter +
    // combining mark (e.g. "Ä" becomes "A" + a combining diaeresis), so
    // stripping the marks afterward leaves a plain base letter -- "Ä",
    // "À", "Á" all become "A". toUpperCase also covers pdf_ids like
    // "(van Manen 1995)", where the surname prefix is lowercase.
    return firstChar.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
}

const bibnotes = dv.pages(`"${folder}"`)
    .where(p => p.pdf_id)
    .where(p => !letterFilter || normalizedFirstLetter(p.pdf_id) === letterFilter.toUpperCase())
    .sort(p => p.pdf_ctime, "desc")
    .values;

// Two parallel structures: `displayRows` (with clickable HTML) goes into the
// visible table; `plainRows` (plain text only) is what gets copied to the
// clipboard -- an <img> tag or a link doesn't mean anything once pasted
// into Excel, so the copy button works from plain values instead.
const displayRows = [];
const plainRows = [];

for (const page of bibnotes) {
    const file = app.vault.getAbstractFileByPath(page.file.path);
    if (!file) continue;

    const content = await app.vault.read(file);
    const imgMatch = content.match(/<img src="([^"]+)"/);

    // Obsidian's own internal-link mechanism: any element with
    // class="internal-link" and a data-href attribute gets picked up by
    // Obsidian's global click handler and opens that note. Building the
    // anchor by hand like this -- rather than going through Dataview's
    // Link object -- means it no longer depends on Dataview correctly
    // resolving names that contain parentheses, which looks like what was
    // silently failing before.
    const notePath = page.file.path;
    const openNote = (inner) =>
        `<a class="internal-link" data-href="${notePath}" href="${notePath}">${inner}</a>`;

    let imgCell = "";
    if (imgMatch) {
        const imgFilename = imgMatch[1];
        const imgFile = app.metadataCache.getFirstLinkpathDest(imgFilename, notePath);
        if (imgFile) {
            const resourcePath = app.vault.getResourcePath(imgFile);
            imgCell = openNote(`<img src="${resourcePath}" width="${width}">`);
        } else {
            imgCell = "(image not found)";
        }
    }

    const pdfId = page.pdf_id ?? "";
    const idCell = openNote(pdfId);

    displayRows.push([
        imgCell,
        idCell,
        page.pdf_title ?? "",
        page.pdf_ctime ?? "",
        page.pdf_pages ?? "",
        page.pdf_highlights ?? ""
    ]);

    plainRows.push([
        pdfId,
        String(page.pdf_title ?? ""),
        String(page.pdf_ctime ?? ""),
        String(page.pdf_pages ?? ""),
        String(page.pdf_highlights ?? "")
    ]);
}

// Scope the top-alignment fix to just this table, not every dataview table
// in the vault -- dv.container is the wrapper div for this specific block.
// 2026-07-27: aligning vertically doesn't work, or it does before the images appear, but then everything snaps to centered.
dv.container.querySelectorAll("td").forEach(td => {
    td.style.setProperty("vertical-align", "top", "important");
    td.style.setProperty("align-items", "flex-start", "important");
});

// Clipboard button. TSV (tab-separated values) is what Excel and Google
// Sheets both parse into columns on paste. No image column here, since a
// raw <img> tag or binary data doesn't survive a paste anyway.
const plainHeader = ["pdf_id", "pdf_title", "pdf_ctime", "pdf_pages", "pdf_highlights"];
const tsv = [plainHeader, ...plainRows]
    .map(row => row.map(cell => String(cell).replace(/\t/g, " ").replace(/\n/g, " ")).join("\t"))
    .join("\n");

const button = dv.el("button", "Copy table (TSV) for Excel");
button.addEventListener("click", async () => {
    await navigator.clipboard.writeText(tsv);
    button.textContent = "Copied!";
    setTimeout(() => { button.textContent = "Copy table (TSV) for Excel"; }, 1500);
});

dv.table(
    ["Cover", "pdf_id", "pdf_title", "pdf_ctime", "pdf_pages", "pdf_highlights"],
    displayRows
);
