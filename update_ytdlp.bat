@echo off
chcp 65001 > nul
echo ====================================================
echo    Обновление yt-dlp до последней версии...
echo ====================================================

call .venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo [!] Виртуальное окружение не найдено, пытаюсь обновить глобально...
    python -m pip install -U yt-dlp
) else (
    pip install -U yt-dlp
)

echo.
echo Обновление завершено!
pause
