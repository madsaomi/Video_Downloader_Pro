@echo off
cd /d "%~dp0"

REM Добавляем Deno в PATH (нужен для yt-dlp + YouTube)
set "PATH=%USERPROFILE%\.deno\bin;%PATH%"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python main.py
pause
