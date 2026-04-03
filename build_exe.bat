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

set PYINSTALLER_CMD=venv\Scripts\pyinstaller.exe --noconsole --onefile --collect-all customtkinter --name "VideoDownloaderPro"

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
pause
