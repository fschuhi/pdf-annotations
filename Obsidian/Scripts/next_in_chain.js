// next_in_chain.js
//
// Usage: await dv.view("Scripts/next_in_chain", { current: dv.current() });
//
// Finds all Idea notes that continue from the current note via 'Continues::'.
// Displays the Folgezettel (follow-up notes) in a table.

const currentFile = input.current.file;

// Find idea notes that point to THIS note via 'Continues::'
const nextInChain = dv.pages()
    .where(p => p.note_type === "idea")
    .where(p => p.Continues)
    .where(p => {
        const targets = Array.isArray(p.Continues) ? p.Continues : [p.Continues];
        return targets.some(t => t.path === currentFile.path);
    })
    .sort(p => p.file.mtime, "desc");

// Render
if (nextInChain.length > 0) {
    dv.table(
        ["Idea Note", "Last Modified"],
        nextInChain.map(p => [
            p.file.link,
            p.file.mtime.toFormat("yyyy-MM-dd HH:mm")
        ])
    );
} else {
    dv.paragraph("N/A");
}
