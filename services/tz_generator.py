from models import TZData
from services import openrouter

SYSTEM_PROMPT = """Ты опытный технический архитектор и бизнес-аналитик.
Твоя задача — создать профессиональное техническое задание на основе ответов пользователя.

Формат вывода — строго Markdown, структура:

# Техническое задание: {цель продукта}

## 1. Контекст и цель
{описание проблемы и решения}

## 2. Целевая аудитория
{кто будет использовать, их боли и потребности}

## 3. Функциональные требования
{пронумерованный список конкретных функций и User Stories}

## 4. Технические ограничения
{стек, бюджет, временные ограничения, API}

## 5. Критерии приёмки (Definition of Done)
{чек-лист: что должно работать, чтобы считать задачу выполненной}

## 6. Приоритеты (MVP)
{что обязательно для первой версии, что можно отложить}

Пиши конкретно, избегай воды. Используй глаголы действия. Пиши на русском языке."""


async def generate_tz(data: TZData) -> tuple[str, int]:
    user_content = f"""Цель продукта: {data.goal}

Целевая аудитория: {data.audience}

Ключевые функции: {data.features}

Технические ограничения: {data.tech_constraints}

Желаемый результат: {data.desired_result}"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    result, tokens = await openrouter.chat(messages, max_tokens=2000, temperature=0.5)
    return result.strip(), tokens
