# Currency Monitor API

Полнофункциональный асинхронный backend на **FastAPI** для мониторинга курсов валют в реальном времени.

## Возможности

- **REST API** для управления данными о валютах
- **WebSocket** для real-time обновлений в браузере
- **Фоновая задача** для автоматического обновления курсов (каждые N секунд)
- **NATS** интеграция для pub/sub событий
- **SQLite** асинхронная база данных
- **Docker Compose** для быстрого запуска
- **Swagger API** документация

## Технологический стек

- **FastAPI** - современный веб-фреймворк
- **Uvicorn** - ASGI сервер
- **SQLAlchemy** + **aiosqlite** - асинхронная работа с БД
- **Pydantic** - валидация данных
- **httpx** - асинхронный HTTP клиент
- **nats-py** - NATS брокер
- **WebSockets** - real-time коммуникация
- **Docker** - контейнеризация

## Структура проекта

```
currency-monitor/
├── app/
│   ├── api/
│   │   └── routes.py           # REST endpoints
│   ├── db/
│   │   ├── database.py         # БД конфигурация
│   │   └── models.py           # SQLAlchemy модели
│   ├── nats/
│   │   └── client.py           # NATS интеграция
│   ├── services/
│   │   └── currency_service.py # Бизнес-логика
│   ├── tasks/
│   │   └── background.py       # Фоновые задачи
│   ├── ws/
│   │   └── manager.py          # WebSocket менеджер
│   ├── schemas/
│   │   └── currency.py         # Pydantic модели
│   ├── config.py               # Конфигурация
│   └── main.py                 # Точка входа
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Быстрый старт

### Вариант 1: Docker Compose (Рекомендуется)

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd currency-monitor

# 2. Запустить с Docker Compose
docker-compose up -d

# 3. Проверить логи
docker-compose logs -f app
```

Приложение будет доступно:
- **API**: http://localhost:8000
- **Swagger**: http://localhost:8000/docs
- **NATS**: nats://localhost:4222

### Вариант 2: Локальный запуск

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить NATS (если нет Docker)
# Скачать с https://nats.io/download/
nats-server

# 3. Запустить приложение
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker Commands

```bash
# Запустить контейнеры
docker-compose up -d

# Посмотреть логи
docker-compose logs -f app

# Остановить контейнеры
docker-compose down

# Пересоздать контейнеры
docker-compose up -d --build

# Удалить контейнеры и волюмы
docker-compose down -v
```

## Мониторинг

### Metrics

- Активные WebSocket соединения
- Количество валют в БД
- Статус фоновой задачи
- Логи всех операций

## Полезные ссылки

- [FastAPI Документация](https://fastapi.tiangolo.com/)
- [NATS.io](https://nats.io/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Open Exchange Rates API](https://openexchangerates.org/)

## Лицензия

MIT License

## Автор

Разработано как учебный проект по асинхронному программированию на Python.
