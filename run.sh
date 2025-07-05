#!/bin/bash

echo "Telegram Channel Monitor"
echo "======================="
echo ""

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "ОШИБКА: Python3 не найден!"
    echo "Установите Python 3.9+ "
    exit 1
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "ВНИМАНИЕ: Файл .env не найден!"
    echo "Скопируйте .env.example в .env и заполните настройки"
    exit 1
fi

# Загружаем переменные окружения
source .env

# Проверяем наличие Telethon сессии
SESSION_FILE="${TELEGRAM_SESSION_NAME}.session"
if [ ! -f "$SESSION_FILE" ]; then
    echo "\nНе найдена сессия Telethon. Запуск авторизации..."
    python3 -m scripts.cli_login || exit 1
fi

# Устанавливаем зависимости
echo "Установка зависимостей..."
pip3 install -r requirements.txt

# Запускаем приложение
echo ""
echo "Запуск Telegram Monitor..."
echo "Для остановки нажмите Ctrl+C"
echo ""
python3 main.py
