@echo off
chcp 65001 > nul
color 0b

echo ===================================================
echo   Updating yt-dlp to the latest version
echo ===================================================
echo.

cd /d "%~dp0"

REM Activate venv
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo.
echo Current version:
python -m yt_dlp --version 2>nul || echo Not installed

echo.
echo Updating...
pip install -U yt-dlp

echo.
echo New version:
python -m yt_dlp --version

echo.
echo ===================================================
echo   Update complete!
echo ===================================================
pause
