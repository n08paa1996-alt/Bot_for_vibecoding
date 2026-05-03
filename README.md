# VibeMaster AI 🤖

Telegram-бот — личный ассистент вайб-кодера. Превращает идеи в ТЗ, генерирует визуал, обучает работе с Claude Code и помогает задеплоить продукт.

## Возможности

| Режим | Что делает |
|-------|-----------|
| 📝 Создать ТЗ | 5-шаговый опрос → структурированное Markdown ТЗ для Claude Code |
| 🎨 Визуал | Улучшает промпт + генерирует изображение через OpenRouter |
| 📚 База Claude | Команды, лимиты, советы по Claude Code с поиском + AI-ответы |
| 🚀 Деплой | Анализирует код и рекомендует платформу + аудит кода на ошибки |

## Быстрый старт

```bash
git clone <repo>
cd vibemaster
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
cp .env.example .env
# Заполни .env своими ключами
python bot.py
```

## Переменные окружения

| Переменная | Описание |
|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `OPENROUTER_API_KEY` | API-ключ OpenRouter (openrouter.ai) |
| `WEBHOOK_HOST` | URL для webhook (например `https://xxx.up.railway.app`). Если пусто — запускается Long Polling |
| `DEFAULT_TEXT_MODEL` | Модель для текста (по умолчанию `anthropic/claude-3.5-sonnet`) |
| `DEFAULT_IMAGE_MODEL` | Модель для изображений (по умолчанию `fal-ai/flux-pro`) |

## Деплой на Railway

1. Создай проект на [railway.app](https://railway.app)
2. Подключи GitHub репозиторий
3. Добавь переменные окружения в Dashboard
4. `WEBHOOK_HOST` = `https://<твой-домен>.up.railway.app`
5. Railway автоматически задеплоит через Dockerfile

## Структура проекта

```
vibemaster/
├── bot.py              # точка входа
├── config.py           # настройки (pydantic-settings)
├── handlers/           # обработчики Telegram-сообщений
├── fsm/                # состояния конечных автоматов
├── services/           # бизнес-логика и внешние API
├── middlewares/        # авторегистрация пользователей, rate limit
├── models/             # Pydantic схемы
├── data/               # claude_knowledge.json + SQLite БД
└── tests/              # pytest тесты
```

## Тесты

```bash
pytest tests/ -v
```

## Команды бота

- `/start` — главное меню
- `/cancel` — выйти из текущего режима
- `/reload_kb` — перезагрузить базу знаний Claude Code
