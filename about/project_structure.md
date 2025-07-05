ANOMALY PARSING TG TELETHON/
│
├── config/
│   ├── __init__.py
│   ├── config.py          # Конфигурация и константы
│   └── settings.py        # Настройки приложения
│
├── database/
│   ├── __init__.py
│   ├── db.py              # Основной класс для работы с базой данных
│   ├── models.py          # Модели и схема базы данных
│   └── queries.py         # SQL запросы и методы
│
├── admin_bot/
│   ├── __init__.py
│   ├── bot.py             # Основной файл бота-админки
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py       # Обработчики команд /start и /help
│   │   ├── filters.py     # Обработчики для управления фильтрами
│   │   ├── channels.py    # Обработчики для управления каналами
│   │   └── settings.py    # Обработчики для настройки
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── keyboards.py   # Клавиатуры и кнопки
│   └── utils/
│       ├── __init__.py
│       └── helpers.py     # Вспомогательные функции
│
├── monitor/
│   ├── __init__.py
│   ├── client.py          # Клиент Telethon для мониторинга
│   ├── filters.py         # Классы фильтров сообщений
│   └── handlers.py        # Обработчики новых сообщений
│
├── utils/
│   ├── __init__.py
│   ├── logging.py         # Настройка логирования
│   └── text_utils.py      # Утилиты для работы с текстом
│
└── main.py                # Главный файл для запуска приложения
