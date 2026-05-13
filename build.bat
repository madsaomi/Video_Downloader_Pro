@echo off
chcp 65001 > nul
color 0a

echo ===================================================
echo   🎬 Building Portable Video Downloader Pro
echo ===================================================
echo.

cd /d "%~dp0"

REM ─── Активация venv ───
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    color 0c
    echo [ERROR] Виртуальное окружение не найдено!
    echo Создайте: python -m venv .venv
    pause
    exit /b
)

REM ─── Проверка PyInstaller ───
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] PyInstaller не найден. Устанавливаю...
    pip install pyinstaller
)

REM ─── Шаг 1: Скачиваем FFmpeg если нет ───
echo.
echo [1/5] Проверка FFmpeg...
if exist ffmpeg.exe (
    echo    [✓] ffmpeg.exe найден
) else (
    echo    [↓] Скачиваю FFmpeg...
    python download_ffmpeg.py
    if exist ffmpeg.exe (
        echo    [✓] FFmpeg успешно скачан
    ) else (
        color 0e
        echo    [!] Не удалось скачать FFmpeg. Видео 1080p+ может быть без звука.
        echo    Скачайте вручную: https://ffmpeg.org/download.html
        color 0a
    )
)

REM ─── Шаг 2: Проверяем Deno ───
echo.
echo [2/5] Проверка Deno...
if exist deno.exe (
    echo    [✓] deno.exe найден
) else (
    echo    [↓] Скачиваю Deno...
    powershell -Command "try { Invoke-WebRequest -Uri 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip' -OutFile 'deno.zip' -UseBasicParsing; Expand-Archive -Path 'deno.zip' -DestinationPath '.' -Force; Remove-Item 'deno.zip' -Force; Write-Host '   [✓] Deno скачан' } catch { Write-Host '   [!] Не удалось скачать Deno' }"
    if not exist deno.exe (
        color 0e
        echo    [!] Deno не найден. YouTube может не работать без него.
        echo    Установите: winget install DenoLand.Deno
        color 0a
    )
)

REM ─── Шаг 3: Сборка ───
echo.
echo [3/5] Сборка PyInstaller...
echo.

set PYINSTALLER_CMD=pyinstaller --noconsole --onefile --clean ^
    --collect-all customtkinter ^
    --hidden-import=yt_dlp ^
    --hidden-import=requests ^
    --hidden-import=PIL ^
    --add-data "downloader.py;." ^
    --add-data "history_manager.py;." ^
    --add-data "download_ffmpeg.py;." ^
    --name "VideoDownloaderPro"

if exist ffmpeg.exe (
    set PYINSTALLER_CMD=%PYINSTALLER_CMD% --add-binary "ffmpeg.exe;."
)
if exist ffprobe.exe (
    set PYINSTALLER_CMD=%PYINSTALLER_CMD% --add-binary "ffprobe.exe;."
)
if exist deno.exe (
    set PYINSTALLER_CMD=%PYINSTALLER_CMD% --add-binary "deno.exe;."
)

%PYINSTALLER_CMD% main.py

REM ─── Шаг 4: Проверка ───
echo.
echo [4/5] Проверка результатов...

if exist dist\VideoDownloaderPro.exe (
    copy /y "dist\VideoDownloaderPro.exe" "VideoDownloaderPro.exe" > nul
    echo.
    echo ===================================================
    echo   ✅ СБОРКА ЗАВЕРШЕНА!
    echo.
    echo   Файл: VideoDownloaderPro.exe
    for %%A in (VideoDownloaderPro.exe) do echo   Размер: %%~zA байт
    echo.
    if exist ffmpeg.exe (
        echo   [✓] FFmpeg — встроен
    ) else (
        echo   [✗] FFmpeg — НЕ встроен
    )
    if exist deno.exe (
        echo   [✓] Deno   — встроен
    ) else (
        echo   [✗] Deno   — НЕ встроен
    )
    echo.
    echo   Этот .exe можно запустить на любом ПК
    echo   без установки Python и зависимостей!
    echo ===================================================
) else (
    color 0c
    echo.
    echo [ERROR] Сборка не удалась!
    echo Проверьте ошибки выше.
)

REM ─── Шаг 5: Очистка ───
echo.
echo [5/5] Очистка временных файлов...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
if exist VideoDownloaderPro.spec del /q VideoDownloaderPro.spec

echo.
pause
