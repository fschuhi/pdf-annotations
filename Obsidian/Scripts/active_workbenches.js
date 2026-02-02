// active_workbenches.js
//
// Usage: await dv.view("Scripts/active_workbenches", { current: dv.current() });
//
// Displays all active workbenches with their connected idea count and time spent.
// Used on The Studio dashboard.

// ---------------------------------------------------------
// Helper: Format minutes compactly
// ---------------------------------------------------------
function formatTime(minutes) {
    if (!minutes || minutes === 0) return "–";
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h${mins}m` : `${hours}h`;
}

// ---------------------------------------------------------
// Main View Logic
// ---------------------------------------------------------

const activeWorkbenches = dv.pages()
    .where(p => p.note_type === "workbench")
    .where(p => p.status === "active")
    .where(p => !p.file.path.includes("Template"))  // Exclude templates
    .sort(p => p.file.mtime, "desc");

let grandTotalWriting = 0;
let grandTotalReading = 0;

const rows = activeWorkbenches.map(p => {
    // Count outgoing links that point to idea notes
    const outlinks = p.file.outlinks;
    const ideaCount = outlinks
        .map(link => dv.page(link))
        .filter(page => page && page.note_type === "idea")
        .length;

    // Time spent on workbench itself (writing/organizing)
    const writingTime = Number(p.time_spent || 0);
    grandTotalWriting += writingTime;

    // Total reading time from linked bibnotes
    let readingTime = 0;
    outlinks.forEach(link => {
        const page = dv.page(link);
        if (page && page.note_type === "bibnote") {
            readingTime += Number(page.time_spent || 0);
        }
    });
    grandTotalReading += readingTime;

    return [
        p.file.link,
        ideaCount,
        formatTime(writingTime),
        formatTime(readingTime),
        p.file.mtime
    ];
});

dv.table(["Active Workbench", "Ideas", "Writing", "Time Spent", "Last Touched"], rows);

// Summary below table
if (grandTotalWriting > 0 || grandTotalReading > 0) {
    const totalTime = grandTotalWriting + grandTotalReading;
    dv.paragraph(`**Total time:** ${formatTime(totalTime)} (writing: ${formatTime(grandTotalWriting)}, reading: ${formatTime(grandTotalReading)})`);
}
