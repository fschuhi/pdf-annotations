#!/usr/bin/env python3
"""
PDF URL Handler Service - Windows Only
Listens for HTTP POST requests with pdf:// URLs (using 7-char hashes)
and opens them in PDF-XChange-Viewer.
"""

import os
import sys
import subprocess
import configparser
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import re
import argparse

# --- NEW: Import shared logic from pdf_annotations ---
# This works because of the PYTHONPATH set in start_server.bat
try:
    from pdf_annot.pdf_registry import build_pdf_index
except ImportError:
    print("=" * 60)
    print("FATAL ERROR: Could not find the 'pdf_annot' library.")
    print("Please ensure this server is in a subfolder of the main")
    print("'pdf-annotations' project and that 'start_server.bat' is used.")
    print("=" * 60)
    build_pdf_index = None
    time.sleep(10)
    sys.exit(1)

try:
    import win32gui
    import win32con

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    win32gui = None
    win32con = None


class Config:
    """Configuration manager"""

    def __init__(self, config_path="pdf_server.ini"):
        self.config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        self.config.read(config_path)

    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)


class PDFHandler(BaseHTTPRequestHandler):
    """HTTP request handler for PDF URLs"""

    # Class variables populated by main()
    config = None
    hash_to_filename = {}

    def log_message(self, format_str, *args):  # --- FIX: Renamed 'format' ---
        """Override to customize logging"""
        if self.config and self.config.get("logging", "verbose", fallback="true").lower() == "true":
            sys.stdout.write(f"[{self.log_date_time_string()}] {format_str % args}\n")

    def send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def parse_pdf_url(self, url):
        """
        Parse a hash-based pdf:// URL and extract filename and page number
        Example: pdf://VQGPEHE?page=4
        Returns: (filename, page_number, hash_key)
        """
        # Remove pdf:// prefix
        if url.startswith("pdf://"):
            url = url[6:]

        # Split by ?page= (case-insensitive)
        parts = re.split(r"\?page=", url, maxsplit=1, flags=re.IGNORECASE)

        # The hash is the first part
        hash_key = parts[0].upper()

        # Extract page number if present
        page_number = int(parts[1]) if len(parts) > 1 else 1

        filename = self.hash_to_filename.get(hash_key)

        if not filename:
            raise FileNotFoundError(f"Hash '{hash_key}' not found in PDF registry. (Is server index up to date?)")

        return filename, page_number, hash_key  # Return hash_key for logging

    def construct_pdf_path(self, filename):
        """Construct full path to PDF file"""
        base_path = self.config.get("windows", "pdf_base_path")
        if not base_path:
            raise ValueError("pdf_base_path not configured in config.ini")

        # Construct full path
        pdf_path = os.path.join(base_path, filename)
        return pdf_path

    def open_pdf(self, pdf_path, page_number):
        """Open PDF file at specified page using PDF-XChange-Viewer"""
        viewer_path = self.config.get("windows", "viewer_path")

        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not os.path.exists(viewer_path):
            raise FileNotFoundError(f"PDF-XChange-Viewer not found at: {viewer_path}")

        cmd = [viewer_path, "/A", f"page={page_number}", pdf_path]
        print(f"Executing: {' '.join(repr(arg) for arg in cmd)}")

        # Launch PDF viewer
        _ = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
        )

        # Bring the PDF viewer window to the foreground
        if HAS_WIN32:
            time.sleep(0.5)  # Wait for window to appear

            def find_window_by_title(title_part):
                """Find window handle by partial title match"""
                windows = []

                def callback(hwnd_cb, _):
                    if win32gui.IsWindowVisible(hwnd_cb):  # type: ignore
                        window_title = win32gui.GetWindowText(hwnd_cb)  # type: ignore
                        if title_part.lower() in window_title.lower():
                            windows.append(hwnd_cb)
                    return True

                win32gui.EnumWindows(callback, None)  # type: ignore
                return windows[0] if windows else None

            # Try to find the PDF viewer window
            # PDF-XChange typically shows filename in title
            filename = os.path.basename(pdf_path)
            hwnd = find_window_by_title(filename)

            if not hwnd:
                # Fallback: try to find by viewer name
                hwnd = find_window_by_title("PDF-XChange")

            if hwnd:
                # Bring window to foreground
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)  # type: ignore
                win32gui.SetForegroundWindow(hwnd)  # type: ignore
                print(f"Brought PDF viewer to foreground")
            else:
                print(f"Could not find PDF viewer window to focus")
        else:
            print("pywin32 not available, cannot bring window to foreground")

        return True

    def do_POST(self):  # noqa
        """Handle POST requests"""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            # Parse JSON body
            try:
                data = json.loads(body)
                pdf_url = data.get("url", "")
            except json.JSONDecodeError:
                # Fallback: treat body as plain URL
                pdf_url = body.strip()

            if not pdf_url:
                self.send_json_response(400, {"status": "error", "message": "No URL provided"})
                return

            print(f"Received request: {pdf_url}")

            # Parse PDF URL
            filename, page_number, hash_key = self.parse_pdf_url(pdf_url)
            print(f"Parsed: hash='{hash_key}', page={page_number} -> filename='{filename}'")

            # Construct full path
            pdf_path = self.construct_pdf_path(filename)

            # Open PDF
            self.open_pdf(pdf_path, page_number)

            # Send success response
            self.send_json_response(
                200, {"status": "success", "filename": filename, "page": page_number, "path": pdf_path}
            )

        except Exception as e:
            print(f"Error: {e}")
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def do_GET(self):  # noqa
        """Handle GET requests - just return status"""
        if self.path == "/status":
            self.send_json_response(
                200,
                {
                    "status": "running",
                    "config": {
                        "pdf_base_path": self.config.get("windows", "pdf_base_path"),
                        "viewer_path": self.config.get("windows", "viewer_path"),
                    },
                    "indexed_pdfs": len(self.hash_to_filename),
                },
            )
        else:
            self.send_json_response(
                404,
                {"status": "error", "message": "Not found. Use POST to open PDFs or GET /status for server status."},
            )


def main():
    """Main entry point"""
    # --- NEW: Add argument parsing for config file ---
    parser = argparse.ArgumentParser(description="PDF URL Handler Server")
    parser.add_argument(
        "-c", "--config", default="pdf_server.ini", help="Path to the configuration file (default: pdf_server.ini)"
    )
    args = parser.parse_args()

    try:
        # Load configuration
        config = Config(config_path=args.config)
        PDFHandler.config = config

        # Get server settings
        host = config.get("server", "host", fallback="127.0.0.1")
        port = int(config.get("server", "port", fallback="8765"))
        pdf_base_path = config.get("windows", "pdf_base_path")

        # --- NEW: Build the PDF Index on startup ---
        print(f"Scanning PDF directory: {pdf_base_path}...")
        try:
            # Use the *exact same function* as the main project
            pdf_index = build_pdf_index([pdf_base_path])
            # Create the reverse map for fast lookups
            PDFHandler.hash_to_filename = {info.pdf_hash: info.filename_with_ext for info in pdf_index.values()}
            print(f"Successfully indexed {len(PDFHandler.hash_to_filename)} PDFs.")
        except Exception as e:
            print(f"{'=' * 60}")
            print(f"FATAL ERROR: Could not build PDF index: {e}")
            print("Please check 'pdf_base_path' in config.ini and permissions.")
            print(f"{'=' * 60}")
            time.sleep(10)
            sys.exit(1)

        # Create and start server
        server = HTTPServer((host, port), PDFHandler)  # type: ignore

        print(f"{'=' * 60}")
        print(f"PDF URL Handler Service")
        print(f"{'=' * 60}")
        print(f"Listening on: http://{host}:{port}")
        print(f"PDF Base Path: {config.get('windows', 'pdf_base_path')}")
        print(f"Viewer Path: {config.get('windows', 'viewer_path')}")
        # --- FIX: Changed '6s' to '60' ---
        print(f"{'=' * 60}")
        print(f"Server ready. Waiting for requests...")
        print(f"Press Ctrl+C to stop\n")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            server.shutdown()

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        time.sleep(10)
        sys.exit(1)


if __name__ == "__main__":
    main()
