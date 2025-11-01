@echo off
REM PDF URL Handler Server Startup Script

REM Get the directory where this batch file is located
cd /d "%~dp0"

REM --- NEW: Add the project's 'src' folder to the Python path ---
REM This allows importing 'pdf_annot'
set PYTHONPATH=%~dp0\..\src

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Start the server
echo Starting PDF URL Handler Server...
python server.py

REM Keep window open if there's an error
pause
