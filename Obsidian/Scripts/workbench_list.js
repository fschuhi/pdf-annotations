// workbench_list.js
//
// Usage: await dv.view("Scripts/workbench_list", { current: dv.current() });
//
// Displays a reading list for a workbench, showing linked bibnotes
// with their status, blockers, resume links, and time spent.

// ---------------------------------------------------------
// Helper: Find page of most recent highlight
// ---------------------------------------------------------
async function getLastReadPage(filePath) {
    const tfile = app.vault.getAbstractFileByPath(filePath);
    if (!tfile) return 1;

    const content = await app.vault.read(tfile);
    const regex = /<span class="pdf-annot-date">(\d{2}\.\d{2}\.\d{2} \d{2}:\d{2})<\/span>.*?page=(\d+)/g;

    let match;
    let latestDate = 0;
    let lastPage = 1;

    while ((match = regex.exec(content)) !== null) {
        const [day, month, shortYear, hour, min] = match[1].split(/[. :]/);
        const dateObj = new Date(`20${shortYear}-${month}-${day}T${hour}:${min}:00`);

        if (dateObj > latestDate) {
            latestDate = dateObj;
            lastPage = match[2];
        }
    }
    return lastPage;
}

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

// 1. Get links from the workbench that called this view
const currentLinks = input.current.file.outlinks;

// 2. Filter to bibnotes that are in the reading pipeline
const workbenchReadings = dv.pages()
    .where(p => p.note_type === "bibnote")
    .where(p => p.status === "reading" || p.status === "blocked" || p.status === "to-read")
    .where(p => currentLinks.some(link => link.path === p.file.path))
    .sort(p => {
        // Sort by status first (reading=0, to-read=1, blocked=2), then alphabetically by filename
        let statusOrder;
        if (p.status === "reading") statusOrder = 0;
        else if (p.status === "to-read") statusOrder = 1;
        else statusOrder = 2; // blocked

        // Combine status order with filename for compound sort
        return `${statusOrder}-${p.file.name.toLowerCase()}`;
    })
    .values;

// 3. Calculate total time spent
let totalMinutes = 0;
workbenchReadings.forEach(p => {
    totalMinutes += Number(p.time_spent || 0);
});

// 4. Build rows asynchronously
const rows = await Promise.all(workbenchReadings.map(async p => {
    // A. Determine Page Number
    const page = await getLastReadPage(p.file.path);

    // B. Status logic
    const isToRead = p.status === "to-read";
	const isReading = p.status === "reading";
    const isBlocked = p.status === "blocked";
    const isDone = p.status === "done";

    let statusIcon;
    if (isBlocked) {
        statusIcon = "⛔️";
    } else if (isToRead) {
        statusIcon = "🔵";
    } else if (isReading) {
        statusIcon = "🟢";
	} else {
        statusIcon = "⚪";
    }

    // C. Action Link
    let actionLink;
    if (isToRead) {
        actionLink = dv.el(
            "a",
            "start on pg 1",
            { href: `pdf://${p.pdf_hash}?page=1` }
        );
    } else {
        actionLink = dv.el(
            "a",
            isBlocked ? `suspended (pg ${page})` : `resume on pg ${page}`,
            { href: `pdf://${p.pdf_hash}?page=${page}` }
        );
    }

    // D. Time spent
    const timeSpent = formatTime(p.time_spent);

    // E. Waiting For (only relevant for blocked)
    let waitingFor = "–";
    if (isBlocked) {
       const blockers = dv.pages()
           .where(b => b.note_type === "bibnote")
           .where(b => b.Unblocks)
           .where(b => {
               const targets = Array.isArray(b.Unblocks) ? b.Unblocks : [b.Unblocks];
               return targets.some(t => t.path === p.file.path);
           });

       if (blockers.length > 0) {
           waitingFor = blockers.file.link.values.join(", ");
       } else {
           waitingFor = "⚠️ (Missing 'Unblocks::' link)";
       }
    }

    return [
      statusIcon,
      p.file.link,
      actionLink,
      timeSpent,
      waitingFor
    ];
}));

// 5. Render table
dv.table(["Status", "Document", "Action", "Time", "Waiting For"], rows);

// 6. Show total time if any time has been tracked
if (totalMinutes > 0) {
    dv.paragraph(`**Total reading time:** ${formatTime(totalMinutes)}`);
}
