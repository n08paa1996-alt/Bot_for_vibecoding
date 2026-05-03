import io
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from fsm.deploy_states import DeployStates, AuditStates
from services.openrouter import chat, OpenRouterError
from services import db

router = Router()

DEPLOY_SYSTEM_PROMPT = """Ты опытный DevOps-инженер и помогаешь вайб-кодерам задеплоить их проекты.

На основе типа проекта и кода/зависимостей:
1. Проанализируй зависимости и определи нужный стек
2. Порекомендуй лучшую бесплатную/дешёвую платформу (Railway, Render, Vercel, Fly.io, Netlify и т.д.)
3. Дай пошаговый гайд из 3–5 шагов

Формат ответа:
**📦 Анализ проекта:**
{что нашёл: язык, фреймворк, нужна ли БД, тип приложения}

**🏆 Рекомендация: [Название платформы]**
{почему именно эта платформа для этого проекта}

**📋 Шаги для деплоя:**
1. {шаг}
2. {шаг}
...

**💡 Полезные советы:**
{специфичные советы для этого проекта}

Отвечай на русском языке. Будь конкретным и практичным."""

AUDIT_SYSTEM_PROMPT = """Ты опытный Python/JS разработчик. Проведи аудит кода пользователя:

1. Найди все ошибки (синтаксические, логические, runtime)
2. Найди потенциальные уязвимости безопасности
3. Укажи на проблемы с производительностью
4. Предложи улучшения

Формат ответа:
**🔍 Найденные проблемы:**
{список проблем с объяснением}

**✅ Исправленный код:**
```python
{полный исправленный код}
```

**💡 Дополнительные рекомендации:**
{что можно улучшить дополнительно}

Отвечай на русском языке."""


def _type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 Telegram-бот", callback_data="deploy_type_bot"),
            InlineKeyboardButton(text="🌐 Веб-сайт", callback_data="deploy_type_web"),
        ],
        [InlineKeyboardButton(text="🔌 API-сервис", callback_data="deploy_type_api")],
    ])


def _after_deploy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Аудит кода", callback_data="deploy_audit"),
            InlineKeyboardButton(text="🔄 Другой проект", callback_data="deploy_restart"),
        ]
    ])


@router.message(F.text == "🚀 Деплой")
async def start_deploy(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(DeployStates.choosing_type)
    await message.answer(
        "🚀 *Помощник по деплою*\n\n"
        "Я помогу выбрать лучшую платформу и дам пошаговый гайд.\n\n"
        "Что запускаем?",
        parse_mode="Markdown",
        reply_markup=_type_keyboard(),
    )


@router.callback_query(F.data.startswith("deploy_type_"))
async def cb_deploy_type(callback: CallbackQuery, state: FSMContext) -> None:
    type_map = {
        "deploy_type_bot": "Telegram-бот",
        "deploy_type_web": "Веб-сайт",
        "deploy_type_api": "API-сервис",
    }
    project_type = type_map.get(callback.data, "Проект")
    await state.update_data(project_type=project_type)
    await state.set_state(DeployStates.waiting_code)

    await callback.message.edit_text(
        f"✅ Тип: *{project_type}*\n\n"
        "Скинь основной файл кода или `requirements.txt`/`package.json`.\n\n"
        "Можно:\n"
        "• Прикрепить файл `.py`, `.txt`, `.json`\n"
        "• Вставить код текстом\n"
        "• Прислать ссылку на GitHub-репозиторий\n\n"
        "_Если файл > 5МБ — отправь код текстом или ссылкой на gist._",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(DeployStates.waiting_code)
async def handle_code_for_deploy(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    project_type = data.get("project_type", "Проект")

    code_content = ""

    if message.document:
        if message.document.file_size and message.document.file_size > 5 * 1024 * 1024:
            await message.answer("❌ Слишком большой файл. Отправь код текстом или ссылкой на gist.")
            return
        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        try:
            code_content = file_bytes.read().decode("utf-8", errors="ignore")
        except Exception:
            await message.answer("❌ Не удалось прочитать файл. Попробуй отправить текстом.")
            return
    elif message.text:
        code_content = message.text.strip()
    else:
        await message.answer("Пожалуйста, отправь файл или текст с кодом.")
        return

    thinking = await message.answer("🔍 Анализирую проект и подбираю платформу...")

    user_content = f"Тип проекта: {project_type}\n\nКод/зависимости:\n{code_content[:3000]}"

    try:
        answer, tokens = await chat(
            messages=[
                {"role": "system", "content": DEPLOY_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        await db.log_generation(message.from_user.id, "deploy", "claude-3.5-sonnet", True, tokens)
    except OpenRouterError:
        await thinking.edit_text("❌ Сервис перегружен. Попробуй через минуту.")
        return

    await thinking.delete()
    await state.set_state(DeployStates.showing_recommendation)
    await state.update_data(deploy_code=code_content)

    await message.answer(answer, parse_mode="Markdown", reply_markup=_after_deploy_keyboard())


@router.callback_query(F.data == "deploy_audit")
async def cb_start_audit_from_deploy(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    code = data.get("deploy_code", "")

    if code:
        await callback.answer()
        await _run_audit(callback.message, callback.from_user.id, code)
    else:
        await state.set_state(AuditStates.waiting_code)
        await callback.message.answer(
            "🔍 *Аудит кода*\n\nОтправь код который нужно проверить (текстом или файлом).",
            parse_mode="Markdown",
        )
        await callback.answer()


@router.callback_query(F.data == "deploy_restart")
async def cb_deploy_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(DeployStates.choosing_type)
    await callback.message.answer(
        "🚀 Новый проект — что запускаем?",
        reply_markup=_type_keyboard(),
    )


@router.message(AuditStates.waiting_code)
async def handle_audit_code(message: Message, state: FSMContext) -> None:
    code_content = ""

    if message.document:
        if message.document.file_size and message.document.file_size > 5 * 1024 * 1024:
            await message.answer("❌ Слишком большой файл. Отправь код текстом.")
            return
        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        try:
            code_content = file_bytes.read().decode("utf-8", errors="ignore")
        except Exception:
            await message.answer("❌ Не удалось прочитать файл.")
            return
    elif message.text:
        code_content = message.text.strip()
    else:
        await message.answer("Отправь код текстом или файлом.")
        return

    await _run_audit(message, message.from_user.id, code_content)
    await state.clear()


async def _run_audit(message: Message, user_id: int, code: str) -> None:
    thinking = await message.answer("🔍 Провожу аудит кода...")

    try:
        answer, tokens = await chat(
            messages=[
                {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Проверь этот код:\n\n{code[:4000]}"},
            ],
            max_tokens=2000,
            temperature=0.2,
        )
        await db.log_generation(user_id, "code_audit", "claude-3.5-sonnet", True, tokens)
    except OpenRouterError:
        await thinking.edit_text("❌ Сервис перегружен. Попробуй через минуту.")
        return

    await thinking.delete()

    import re
    code_match = re.search(r"```(?:python|js|javascript)?\n(.*?)```", answer, re.DOTALL)
    if code_match:
        fixed_code = code_match.group(1)
        text_part = answer[:answer.find("```")].strip()

        await message.answer(text_part or "✅ Аудит завершён. Исправленный код:", parse_mode="Markdown")

        code_file = BufferedInputFile(
            fixed_code.encode("utf-8"),
            filename="fixed_code.py",
        )
        await message.answer_document(
            document=code_file,
            caption="📄 Исправленный код",
        )
    else:
        await message.answer(answer, parse_mode="Markdown")
