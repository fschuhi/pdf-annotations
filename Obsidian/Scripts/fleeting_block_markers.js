// fleeting_block_markers.js
//
// Usage from Workbench (finds markers in all linked bibnotes):
//   await dv.view("Scripts/fleeting_block_markers", { current: dv.current(), marker: "idea" });
//
// Usage from Bibnote (finds markers in this bibnote only):
//   await dv.view("Scripts/fleeting_block_markers", { current: dv.current(), marker: "idea" });
//
// The script auto-detects based on note_type.

const marker = input.marker || "idea";
const currentPage = input.current;
const isFromBibnote = currentPage.note_type === "bibnote";

// Determine which bibnotes to search
let bibnotesToSearch = [];

if (isFromBibnote) {
    bibnotesToSearch = [currentPage];
} else {
    const currentLinks = currentPage.file.outlinks;
    bibnotesToSearch = dv.pages()
        .where(p => p.note_type === "bibnote")
        .where(p => currentLinks.some(link => link.path === p.file.path))
        .values;
}

// Regex: space, caret, marker prefix, then word chars/hyphens, at end of line
const blockPattern = new RegExp(` \\^(${marker}-[A-Za-z0-9-]+)$`);

const rows = [];

for (const bibnote of bibnotesToSearch) {
    const file = app.vault.getAbstractFileByPath(bibnote.file.path);
    if (!file) continue;

    const content = await app.vault.read(file);
    const lines = content.split('\n');

    for (const line of lines) {
        const match = line.match(blockPattern);

        if (match) {
            const blockId = match[1];

            // Extract fleeting note: text after "> " and before block marker
            const fleetingNote = line
                .replace(/^>\s*/, '')
                .replace(blockPattern, '')
                .trim();

            // Local link for bibnote context, full link for workbench context
            const blockLink = isFromBibnote
                ? `[[#^${blockId}]]`
                : `[[${bibnote.file.name}#^${blockId}]]`;

            if (isFromBibnote) {
                rows.push([
                    fleetingNote || "(no text)",
                    blockLink
                ]);
            } else {
                rows.push([
                    bibnote.file.link,
                    fleetingNote || "(no text)",
                    blockLink
                ]);
            }
        }
    }
}

if (rows.length > 0) {
    if (isFromBibnote) {
        dv.table(["Comment", "Link"], rows);
    } else {
        dv.table(["Source", "Comment", "Link"], rows);
    }
} else {
    dv.paragraph(`No unprocessed \`^${marker}-*\` markers found.`);
}
