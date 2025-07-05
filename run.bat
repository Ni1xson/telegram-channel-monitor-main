@echo off
echo Telegram Channel Monitor
echo =======================
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Установите Python 3.9+ с https://python.org
    pause
    exit /b 1
)

REM Проверяем наличие .env файла
if not exist .env (
    echo ВНИМАНИЕ: Файл .env не найден!
    echo Скопируйте .env.example в .env и заполните настройки
    pause
    exit /b 1
)

REM Загружаем переменные из .env
for /f "usebackq tokens=1* delims==" %%A in (".env") do set "%%A=%%B"

REM Проверяем наличие Telethon сессии
set "SESSION_FILE=%TELEGRAM_SESSION_NAME%.session"
if not exist "%SESSION_FILE%" (
    echo.
    echo Не найдена сессия Telethon. Запуск авторизации...
    python -m scripts.cli_login
    if errorlevel 1 goto login_error
)

REM Устанавливаем зависимости
echo Установка зависимостей...
pip install -r requirements.txt

REM Запускаем приложение
echo.
echo Запуск Telegram Monitor...
echo Для остановки нажмите Ctrl+C
echo.
python main.py

pause

goto :eof

:login_error
echo Ошибка авторизации!
pause
exit /b 1
