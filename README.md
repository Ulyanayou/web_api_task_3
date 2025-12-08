# Асинхронный Backend: REST API + WebSocket + Фоновая задача + NATS

Проект: мониторинг сетевых устройств/серверов. Реализованы REST API для управления устройствами и историей проверок, WebSocket для realtime-уведомлений, фоновая задача с `httpx`, публикация/подписка через NATS, асинхронная БД SQLite.

## Стек
- FastAPI
- httpx
- NATS.io client (`asyncio-nats`)
- uvicorn
- SQLite (через `aiosqlite`)
- SQLAlchemy + SQLModel
- Pydantic
- WebSockets (FastAPI WebSocket)

## Структура проекта
```
web_api_task_3/
  app/
    api/                # REST-роуты
      routes/           # devices, tasks
    ws/                 # WebSocket менеджер и маршрут
    tasks/              # фоновые задачи: мониторинг
    db/                 # engine/session
    models/             # SQLModel
    nats/               # клиент NATS
    main.py             # точка входа FastAPI
    config.py           # настройки
  requirements.txt
  README.md
```

## Установка (Windows PowerShell)
```powershell
python -m pip install --upgrade pip
pip install -r .\requirements.txt
```

## NATS сервер (локально)
1) Скачайте бинарник `nats-server` для Windows с https://github.com/nats-io/nats-server/releases
2) Запустите сервер (стандартные порты: 4222 для клиентов, 8222 для мониторинга):
```powershell
# если nats-server.exe в текущей папке
.\nats-server.exe -p 4222 -m 8222
```
3) (Опционально) Установите CLI `nats` для публикации/просмотра:
- Cкачайте `nats.exe` с https://github.com/nats-io/natscli/releases

Проверка публикации:
```powershell
nats sub -s nats://127.0.0.1:4222 items.updates
```

## Запуск приложения
```powershell
# из корня проекта
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```
- Документация (Swagger): `http://localhost:8002/swagger`
- WebSocket: `ws://localhost:8002/ws/items`

## Что делает фоновая задача
- Автоматически запускается на старте приложения (в `on_startup`).
- Каждые 60 минут (настройка `MONITOR_PERIOD_SECONDS = 3600`) обходит активные устройства (`Device.is_active == True`).
- Делает HTTP GET на адрес устройства, фиксирует `status_up` и `latency_ms`.
- Сохраняет проверки в БД (`CheckResult`).
- Публикует событие в NATS: `{type: "monitor.cycle.finished", payload: {devices_checked: N}}`.
- Дополнительно рассылает в WebSocket отдельные результаты проверок: `{type: "check.created", payload: {device_id, status_up, latency_ms}}`.

## Ручной запуск фоновой задачи
- Один цикл (без запуска периодического лупа):
```powershell
# POST /tasks/run
curl -X POST http://localhost:8002/tasks/run
```
- Запустить периодический фон:
```powershell
# POST /tasks/run/background
curl -X POST http://localhost:8002/tasks/run/background
```

## REST API (тематика: устройства)
База:
- `Device`: `{id, name, address, is_active, created_at, updated_at}`
- `CheckResult`: `{id, device_id, status_up, latency_ms, checked_at}`

Эндпоинты:
- `GET /devices` — список устройств (`?is_active=true|false` для фильтра).
- `GET /devices/{id}` — получить устройство.
- `POST /devices` — создать устройство.
- `PATCH /devices/{id}` — обновить устройство.
- `DELETE /devices/{id}` — удалить устройство.
- `GET /devices/{id}/checks?limit=50` — история проверок по устройству.
- `POST /devices/{id}/checks` — добавить проверку вручную.

События:
- При `POST/PATCH/DELETE` публикуются события в NATS:
  - `device.created`, `device.updated`, `device.deleted`
- История проверок: при ручном добавлении `check.created` публикуется в NATS.

## WebSocket `/ws/items`
- Клиент подключается на `ws://localhost:8002/ws/items`.
- Сообщения, которые можно получить:
  - `tick` — периодический пинг от сервера каждые 30 секунд.
  - `device.created`, `device.updated`, `device.deleted` — изменения устройств.
  - `check.created` — новые результаты проверок (из фоновой задачи и ручных добавлений).
  - `nats.inbound` — входящие внешние сообщения из канала NATS `items.updates`.
- Обработка входящих от клиента:
  - `"ping"` → ответ `{"type":"pong"}`
  - другие строки → эхо `{"type":"echo","payload":"..."}`

## NATS интеграция
- Подписка: `items.updates` (в `app/nats/client.py`).
- Публикация: события CRUD и мониторинга отправляются в `items.updates`.
- При получении сообщения извне: логируется и дублируется всем WS-клиентам как `nats.inbound`.

## Хранилище
- SQLite (`monitoring.db` в корне проекта).
- URL БД по умолчанию: `sqlite+aiosqlite:///./monitoring.db` (см. `app/config.py`).

## Быстрый тест (PowerShell)
```powershell
# 1) Запуск NATS сервера
.\nats-server.exe -p 4222 -m 8222

# 2) Установка зависимостей
pip install -r .\requirements.txt

# 3) Запуск приложения
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```