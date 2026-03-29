@echo off
chcp 65001 > nul
color 0a

echo ===================================================
echo   🚀 Сборка портативного Video Downloader Pro 🚀
echo ===================================================
echo.

REM Переходим в папку со скриптом
cd /d "%~dp0"

REM Проверяем наличие виртуального окружения и pyinstaller
if not exist .venv\Scripts\pyinstaller.exe (
    color 0c
    echo [ОШИБКА] Не найден PyInstaller в .venv\Scripts\
    echo Пожалуйста, установите его с помощью "pip install pyinstaller"
    pause
    exit /b
)

echo [1/3] Запуск PyInstaller (сборка может занять 1-3 минуты)...
echo.

.venv\Scripts\pyinstaller.exe --noconsole --onefile --add-binary "ffmpeg.exe;." --add-binary "ffprobe.exe;." --add-binary "deno.exe;." --collect-all customtkinter --name "VideoDownloaderPro" main.py

echo.
echo [2/3] Настройка путей...
if exist dist\VideoDownloaderPro.exe (
    echo [3/3] Копирование готового EXE файла на Рабочий стол...
    copy /y "dist\VideoDownloaderPro.exe" "%USERPROFILE%\Desktop\VideoDownloaderPro.exe" > nul
    echo.
    echo ===================================================
    echo   🎉 ГОТОВО!
    echo   Приложение успешно собрано и скопировано на 
    echo   ваш Рабочий стол как "VideoDownloaderPro.exe".
    echo ===================================================
) else (
    color 0c
    echo.
    echo [ОШИБКА] Произошла непредвиденная ошибка при сборке.
    echo EXE файл не найден в папке dist\.
)

echo.
pause
