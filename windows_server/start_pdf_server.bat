@echo off
REM PDF URL Handler Server Startup Script

REM Get the directory where this batch file is located
cd /d "%~dp0"

REM --- NEW: Setup virtual environment if it doesn't exist ---
IF NOT EXIST .venv\Scripts\activate.bat (
    echo --- Virtual environment not found, creating...
    python -m venv .venv
    IF %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b %ERRORLEVEL%
    )

    echo --- Activating venv and installing requirements ---
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install requirements.
        pause
        exit /b %ERRORLEVEL%
    )
    echo --- Setup complete ---
) ELSE (
    REM Activate the existing virtual environment
    call .venv\Scripts\activate.bat
)

REM --- NEW: Add the project's 'src' folder to the Python path ---
REM This allows importing 'pdf_annot'
set PYTHONPATH=%~dp0\..\src

REM Start the server
echo Starting PDF URL Handler Server...
REM --- FIX: Pass the config file as an argument ---
python windows_pdf_server.py -c pdf_server.ini

REM Keep window open if there's an error
pause
