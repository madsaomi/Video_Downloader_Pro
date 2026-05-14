@echo off
REM Use UTF-8 for display
chcp 65001 > nul
color 0a

echo ===================================================
echo   Building Portable Video Downloader Pro
echo ===================================================
echo.

cd /d "%~dp0"

REM --- Activate venv ---
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    color 0c
    echo [ERROR] Virtual environment not found!
    echo Please create it: python -m venv .venv
    pause
    exit /b
)

REM --- Check PyInstaller ---
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] PyInstaller not found. Installing...
    pip install pyinstaller
)

REM --- Step 1: Download FFmpeg ---
echo.
echo [1/5] Checking FFmpeg...
if exist ffmpeg.exe (
    echo    [OK] ffmpeg.exe found
) else (
    echo    [..] Downloading FFmpeg...
    python download_ffmpeg.py
    if exist ffmpeg.exe (
        echo    [OK] FFmpeg downloaded successfully
    ) else (
        color 0e
        echo    [WARN] Failed to download FFmpeg.
        color 0a
    )
)

REM --- Step 2: Check Deno ---
echo.
echo [2/5] Checking Deno...
if exist deno.exe (
    echo    [OK] deno.exe found
) else (
    echo    [..] Downloading Deno...
    powershell -Command "$ErrorActionPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip' -OutFile 'deno.zip'; Expand-Archive -Path 'deno.zip' -DestinationPath '.' -Force; Remove-Item 'deno.zip' -Force; echo '   [OK] Deno downloaded' } catch { echo '   [WARN] Deno download failed' }"
    if not exist deno.exe (
        color 0e
        echo    [WARN] Deno not found.
        color 0a
    )
)

REM --- Step 3: Build ---
echo.
echo [3/5] Running PyInstaller...
echo.

set "OPTS=--noconsole --onefile --clean"
set "OPTS=%OPTS% --collect-all customtkinter"
set "OPTS=%OPTS% --hidden-import=yt_dlp"
set "OPTS=%OPTS% --hidden-import=requests"
set "OPTS=%OPTS% --hidden-import=PIL"
set "OPTS=%OPTS% --add-data downloader.py;."
set "OPTS=%OPTS% --add-data history_manager.py;."
set "OPTS=%OPTS% --add-data download_ffmpeg.py;."
set "OPTS=%OPTS% --name VideoDownloaderPro"

if exist ffmpeg.exe set "OPTS=%OPTS% --add-binary ffmpeg.exe;."
if exist ffprobe.exe set "OPTS=%OPTS% --add-binary ffprobe.exe;."
if exist deno.exe set "OPTS=%OPTS% --add-binary deno.exe;."

pyinstaller %OPTS% main.py

REM --- Step 4: Verify ---
echo.
echo [4/5] Verifying results...

if exist dist\VideoDownloaderPro.exe (
    copy /y "dist\VideoDownloaderPro.exe" "VideoDownloaderPro.exe" > nul
    echo.
    echo ===================================================
    echo   SUCCESS!
    echo.
    echo   File: VideoDownloaderPro.exe
    echo   Ready to use on any PC!
    echo ===================================================
) else (
    color 0c
    echo.
    echo [ERROR] Build failed!
)

REM --- Step 5: Cleanup ---
echo.
echo [5/5] Cleaning up...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
if exist VideoDownloaderPro.spec del /q VideoDownloaderPro.spec

echo.
pause
