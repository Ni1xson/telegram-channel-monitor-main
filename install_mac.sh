#!/bin/zsh

echo "🚀 Установка Telegram Monitor как службы на Mac..."

# Создаем папку для логов
mkdir -p logs

# Получаем текущий путь
PROJECT_DIR=$(pwd)

# Обновляем путь в plist файле
sed -i '' "s|\$(pwd)|$PROJECT_DIR|g" install/ru.telegram.monitor.plist

# Копируем службу
cp install/ru.telegram.monitor.plist ~/Library/LaunchAgents/

# Останавливаем старую службу если есть
launchctl unload ~/Library/LaunchAgents/ru.telegram.monitor.plist 2>/dev/null || true

# Загружаем службу
launchctl load ~/Library/LaunchAgents/ru.telegram.monitor.plist

# Запускаем
launchctl start ru.telegram.monitor

echo "✅ Установка завершена!"
echo ""
echo "📋 Команды для управления:"
echo "  Статус: launchctl list | grep telegram.monitor"
echo "  Логи: tail -f logs/bot.log"
echo "  Остановить: launchctl stop ru.telegram.monitor"
echo "  Запустить: launchctl start ru.telegram.monitor"
echo ""
echo "🔍 Проверка работы:"
launchctl list | grep telegram.monitor 