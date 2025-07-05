#!/bin/bash

echo "🚀 Установка Telegram Monitor как службы на Linux сервере..."

# Создаем папку для логов
mkdir -p logs

# Получаем текущий путь
PROJECT_DIR=$(pwd)

# Обновляем пути в service файле
sed -i "s|/root/telegram-channel-monitor-main|$PROJECT_DIR|g" install/telegram-monitor.service

# Копируем службу в systemd
cp install/telegram-monitor.service /etc/systemd/system/

# Перезагружаем systemd
systemctl daemon-reload

# Останавливаем старую службу если есть
systemctl stop telegram-monitor 2>/dev/null || true

# Включаем автозапуск
systemctl enable telegram-monitor

# Запускаем службу
systemctl start telegram-monitor

echo "✅ Установка завершена!"
echo ""
echo "📋 Команды для управления:"
echo "  Статус: systemctl status telegram-monitor"
echo "  Логи: journalctl -u telegram-monitor -f"
echo "  Остановить: systemctl stop telegram-monitor"
echo "  Запустить: systemctl start telegram-monitor"
echo "  Перезапустить: systemctl restart telegram-monitor"
echo ""
echo "🔍 Проверка работы:"
systemctl status telegram-monitor --no-pager -l 