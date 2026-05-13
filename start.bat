@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ===================================================
echo   🎬 Video Downloader Pro — Запуск
echo ===================================================

REM Добавляем Deno в PATH (нужен для yt-dlp + YouTube)
set "PATH=%USERPROFILE%\.deno\bin;%PATH%"

REM Добавляем локальный FFmpeg/Deno если лежат рядом
if exist "%~dp0ffmpeg.exe" set "PATH=%~dp0;%PATH%"
if exist "%~dp0deno.exe" set "PATH=%~dp0;%PATH%"

REM Активируем виртуальное окружение
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [!] Виртуальное окружение не найдено, запускаю с системным Python...
)

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Приложение завершилось с ошибкой.
    echo Убедитесь, что установлены зависимости: pip install -r requirements.txt
    pause
)
