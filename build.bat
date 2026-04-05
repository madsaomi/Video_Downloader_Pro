@echo off
color 0a

echo ===================================================
echo   Building Portable Video Downloader Pro
echo ===================================================
echo.

cd /d "%~dp0"

if not exist venv\Scripts\pyinstaller.exe (
    color 0c
    echo [ERROR] PyInstaller not found in venv\Scripts\
    echo Please install it using "pip install pyinstaller"
    pause
    exit /b
)

echo [1/3] Running PyInstaller...
set PYINSTALLER_CMD=venv\Scripts\pyinstaller.exe --noconsole --onefile --clean --collect-all customtkinter --name "VideoDownloaderPro"

if exist ffmpeg.exe (
    set PYINSTALLER_CMD=%PYINSTALLER_CMD% --add-binary "ffmpeg.exe;."
)
if exist ffprobe.exe (
    set PYINSTALLER_CMD=%PYINSTALLER_CMD% --add-binary "ffprobe.exe;."
)

%PYINSTALLER_CMD% main.py

echo.
echo [2/3] Checking build results...
if exist dist\VideoDownloaderPro.exe (
    echo [3/3] Copying EXE to Desktop...
    copy /y "dist\VideoDownloaderPro.exe" "%USERPROFILE%\Desktop\VideoDownloaderPro.exe" > nul
    echo.
    echo ===================================================
    echo   SUCCESS!
    echo   App compiled and copied to Desktop as
    echo   "VideoDownloaderPro.exe"
    echo ===================================================
) else (
    color 0c
    echo.
    echo [ERROR] Build failed. EXE not found in dist folder.
)

echo.
echo Cleaning up unnecessary build files...
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
if exist VideoDownloaderPro.spec del /q VideoDownloaderPro.spec

pause
