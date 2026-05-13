@echo off
chcp 65001 > nul
color 0b

echo ===================================================
echo   🔄 Обновление yt-dlp до последней версии
echo ===================================================
echo.

cd /d "%~dp0"

REM Активируем виртуальное окружение
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo [✓] Виртуальное окружение активировано
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [✓] Виртуальное окружение активировано
) else (
    echo [!] Виртуальное окружение не найдено, обновляю глобально...
)

echo.
echo Текущая версия:
python -m yt_dlp --version 2>nul || echo    Не установлен

echo.
echo Обновление...
pip install -U yt-dlp

echo.
echo Новая версия:
python -m yt_dlp --version

echo.
echo ===================================================
echo   ✅ Обновление завершено!
echo ===================================================
pause
