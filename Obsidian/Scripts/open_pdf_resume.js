// open_pdf_resume.js

// 1. Notice how we deleted "const app = ...".
// 'app' is implicitly available in this environment.

// new Notice("Script started");

const file = app.workspace.getActiveFile();

if (!file) {
    new Notice("No active file found");
    return;
}

// new Notice(`File: ${file.path}`);

// 2. Get frontmatter
const cache = app.metadataCache.getFileCache(file);
const pdfHash = cache?.frontmatter?.pdf_hash;

if (!pdfHash) {
    new Notice("No pdf_hash found in frontmatter");
    return;
}

// 3. Read file content
const content = await app.vault.read(file);

// 4. Find most recent annotation page
const regex = /<span class="pdf-annot-date">(\d{2}\.\d{2}\.\d{2} \d{2}:\d{2})<\/span>.*?page=(\d+)/g;
let match;
let latestDate = 0;
let lastPage = null; // null means "no annotation found yet"

while ((match = regex.exec(content)) !== null) {
    const [day, month, shortYear, hour, min] = match[1].split(/[. :]/);
    const dateObj = new Date(`20${shortYear}-${month}-${day}T${hour}:${min}:00`);

    if (dateObj > latestDate) {
        latestDate = dateObj;
        lastPage = match[2];
    }
}

// 5. Open the PDF — only jump to a page if we actually found an annotation
let finalUrl;

if (lastPage !== null) {
    new Notice(`Resuming on page: ${lastPage}`);
    finalUrl = `pdf://${pdfHash}?page=${lastPage}`;
} else {
    new Notice("No annotations found — opening without a page number");
    finalUrl = `pdf://${pdfHash}`;
}

// Create a temporary link and click it
const a = document.createElement("a");
a.href = finalUrl;
a.target = '_blank';
a.rel = 'noopener';
document.body.appendChild(a);
a.click();
document.body.removeChild(a);
