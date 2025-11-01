@echo off
REM Cleans the virtual environment and caches

cd /d "%~dp0"

echo Cleaning virtual environment...
IF EXIST .venv (
    rmdir /s /q .venv
)

echo Cleaning __pycache__ directories...
FOR /d /r . %%d IN (__pycache__) DO (
    IF EXIST "%%d" (
        echo Deleting "%%d"
        rmdir /s /q "%%d"
    )
)

echo Clean complete.
pause
