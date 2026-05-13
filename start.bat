@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ===================================================
echo   Video Downloader Pro - Start
echo ===================================================

REM Add Deno and local FFmpeg to PATH
set "PATH=%USERPROFILE%\.deno\bin;%PATH%"
if exist "%~dp0ffmpeg.exe" set "PATH=%~dp0;%PATH%"
if exist "%~dp0deno.exe" set "PATH=%~dp0;%PATH%"

REM Activate venv
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application crashed.
    pause
)
