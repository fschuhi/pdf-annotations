> **⚠️ macOS users: this component is no longer needed.**
> The `pdf://` URL scheme is now handled natively by **Anima** together with `pdf_annot.resolve`.
> This folder documents the legacy Windows VM route, which remains functional for the Windows machine only.

# PDF URL Handler (Windows Server)

This is the Windows server component for the `pdf-annotations` project. It runs on a Windows VM (e.g., Parallels), listens for `pdf://` hash-based URLs from macOS/Obsidian, and opens the correct PDF in a native Windows viewer.

## Architecture

**macOS (Obsidian)** → `pdf://HASH?page=1` → **macOS URL Handler** (AppleScript) → HTTP POST → **Windows Service** (Python) → **PDF-XChange-Viewer**

This server uses the *same* `pdf_annot` library as the main project to build an index of all your PDFs. It maps the 7-character hash (e.g., `VQGPEHE`) back to the full filename (e.g., `(Albini 2013) On dealing with destructive emotions.pdf`), ensuring links always work.

## System Requirements

* **macOS**: Obsidian, Parallels Desktop
* **Windows VM**: Python 3.11+, PDF-XChange-Viewer
* **Network**: Parallels shared networking between macOS and Windows

## Project Structure

This server lives *inside* the main `pdf-annotations` project. The `start_pdf_server.bat` automatically uses the main project's `src/` folder to import the necessary hashing and indexing logic.

```
pdf-annotations/
├── src/
│   └── pdf_annot/  <-- (Main project, provides hash logic)
├── windows_server/
│   ├── .venv/
│   ├── windows_pdf_server.py  <-- (This server)
│   ├── start_pdf_server.bat   <-- (Use this to run)
│   ├── pdf_server.ini         <-- (Your local config)
│   ├── requirements.txt       <-- (Windows-only deps: pywin32)
│   └── README.md              <-- (This file)
...
```

## Initial Setup

### Part 1: Windows Service Setup

#### 1. Configure Paths

Edit `pdf_server.ini`:

```ini
[server]
# Port for the HTTP server to listen on
port = 8765
# Host to bind to (0.0.0.0 is required for Parallels)
host = 0.0.0.0

[windows]
# PDF base path - adjust to your Dropbox/shared folder location
pdf_base_path = X:\Papers
# PDF-XChange-Viewer executable path
viewer_path = C:\Program Files\Tracker Software\PDF Viewer\pdfxcview.exe

[logging]
# Enable detailed logging
verbose = true
```

**Important**:
* `host = 0.0.0.0` makes the server accessible from macOS.
* Adjust `pdf_base_path` and `viewer_path` to match your system.

#### 2. Find Windows VM IP Address

In Windows `cmd.exe`:
```cmd
ipconfig
```

Look for the Parallels network adapter, typically `10.211.55.x`. Note this IP address.

#### 3. Start the Server (Auto-Setup)

On your Windows VM, navigate to this `windows_server` directory and double-click `start_pdf_server.bat`.

The **first time** you run this, it will automatically:
1.  Create a local `.venv` folder.
2.  Install the `pywin32` dependency from `requirements.txt`.

After setup, it will start the server, scan your `pdf_base_path` to build the hash index, and begin listening for requests.

#### 4. Test the Server

From your **macOS Terminal**, test the connection (replace IP with your actual Windows IP):
```bash
curl http://10.211.55.3:8765/status
```
You should see a JSON response with server status and `indexed_pdfs`.

Now, test opening a file using a **hash** (replace with a real hash from your index):
```bash
curl -X POST http://10.211.55.3:8765 \
  -H "Content-Type: application/json" \
  -d '{"url": "pdf://VQGPEHE?page=4"}'
```

This should open the correct PDF on your Windows VM.

### Part 2: macOS URL Handler Setup

This part is unchanged from the original project.

#### 1. Create the Handler Application

1.  Open **Script Editor** (⌘+Space, type "Script Editor").
2.  Create a **New Document**.
3.  Paste this AppleScript (replace `10.211.55.3` with your Windows VM IP):

```applescript
on open location this_URL
	-- Extract the pdf:// URL
	set json_data to "{\"url\": \"" & this_URL & "\"}"

	-- POST to Windows service
	set windows_ip to "10.211.55.3"
	set server_port to "8765"

	try
		set response to do shell script "curl -X POST http://" & windows_ip & ":" & server_port & " -H 'Content-Type: application/json' -d " & quoted form of json_data

		-- Check if response contains error
		if response contains "\"status\": \"error\"" then
			-- Extract error message
			set AppleScript's text item delimiters to "\"message\": \""
			set temp to text item 2 of response
			set AppleScript's text item delimiters to "\""
			set error_msg to text item 1 of temp

			display dialog "Error opening PDF: " & error_msg buttons {"OK"} default button 1 with icon stop with title "PDF Handler Error"
		else
			-- Success: Switch to Parallels Desktop
			tell application "Parallels Desktop" to activate
		end if

	on error errMsg
		display dialog "Connection error: " & errMsg buttons {"OK"} default button 1 with icon stop with title "PDF Handler Error"
	end try
end open location
```

4.  **File** → **Export**
    * Save As: `PDFHandler`
    * Where: `~/Applications/` (create folder if needed)
    * File Format: **Application** (not Script!)
5.  Click **Save**.

#### 2. Register the URL Scheme

Edit the new app's `Info.plist`:
```bash
cd ~/Applications/PDFHandler.app/Contents
open -e Info.plist
```

Add these lines **before** the final `</dict></plist>` tags:

```xml
	<key>CFBundleURLTypes</key>
	<array>
		<dict>
			<key>CFBundleURLName</key>
			<string>PDF URL Handler</string>
			<key>CFBundleURLSchemes</key>
			<array>
				<string>pdf</string>
			</array>
		</dict>
	</array>
```

Save and close.

#### 3. Register with macOS

Run this in your macOS Terminal:
```bash
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f ~/Applications/PDFHandler.app
```

#### 4. Test the Handler

From macOS Terminal:
```bash
open "pdf://VQGPEHE?page=1"
```

The Windows service should receive the request and open the PDF.

## Daily Usage

**On Windows:**
1.  Navigate to the `windows_server` directory.
2.  Double-click `start_pdf_server.bat`.
3.  A console window will open, build the index, and show "Server ready."
4.  Minimize this window (e.g., using RBTray).

**Keep the server running** while working with Obsidian.

### Using in Obsidian

Create links in your notes using the hash-based format. The `pdf-annot-sync` tool generates these automatically.

```markdown
[Read Paper](pdf://VQGPEHE?page=5)
```

## Troubleshooting

### "Connection refused" error
* Ensure Windows server is running (`start_pdf_server.bat`).
* Check Windows IP hasn't changed (`ipconfig`).
* Update IP in PDFHandler AppleScript if needed.
* Verify Windows Firewall allows Python on private networks.

### "Hash '...' not found" error
* This means the server's index is out of date.
* **Solution**: Stop and restart `start_pdf_server.bat` to force it to re-scan your `pdf_base_path`.

### URL handler doesn't work
* Re-register: Run the `lsregister` command on macOS again.
* Check `Info.plist` has the URL scheme configuration.
* Verify PDFHandler.app is an Application (not Script).

## Files Reference

* **windows_pdf_server.py**: The main HTTP server script.
* **start_pdf_server.bat**: Starts the server, sets `PYTHONPATH`, and auto-installs the venv.
* **pdf_server.ini**: Configuration (paths, port, etc.).
* **requirements.txt**: Windows-only dependencies (`pywin32`).
* **clean.bat**: Removes the `.venv` and `__pycache__`.
* **PDFHandler.app**: macOS URL handler (in `~/Applications/`).
