from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from services import knowledge_base
from services.openrouter import chat, OpenRouterError

router = Router()

AI_SYSTEM_PROMPT = (
    "Ты эксперт по Claude Code — AI-ассистенту для разработчиков от Anthropic. "
    "Отвечай кратко, конкретно и на русском языке. "
    "Если речь о командах — давай примеры использования."
)


class ClaudeBaseStates(StatesGroup):
    free_search = State()
    asking_ai = State()


def _main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⌨️ Команды", callback_data="kb_commands"),
            InlineKeyboardButton(text="📊 Лимиты", callback_data="kb_limits"),
        ],
        [
            InlineKeyboardButton(text="💡 Советы", callback_data="kb_tips"),
            InlineKeyboardButton(text="⚡ Effort-уровни", callback_data="kb_effort"),
        ],
        [InlineKeyboardButton(text="🤖 Задать вопрос AI", callback_data="kb_ask_ai")],
    ])


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад к разделам", callback_data="kb_main")]
    ])


@router.message(F.text == "📚 База Claude")
async def start_claude_base(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📚 *База знаний Claude Code*\n\n"
        "Выбери раздел или напиши свой вопрос (например: «что делает /compact?»)",
        parse_mode="Markdown",
        reply_markup=_main_keyboard(),
    )


@router.callback_query(F.data == "kb_main")
async def cb_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "📚 *База знаний Claude Code*\n\nВыбери раздел:",
        parse_mode="Markdown",
        reply_markup=_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "kb_commands")
async def cb_commands(callback: CallbackQuery) -> None:
    commands = knowledge_base.get_all_commands()
    buttons = [
        [InlineKeyboardButton(text=cmd["name"], callback_data=f"kb_cmd_{cmd['name'].lstrip('/')}")]
        for cmd in commands
    ]
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="kb_main")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        "⌨️ *Команды Claude Code*\n\nВыбери команду для подробного описания:",
        parse_mode="Markdown",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("kb_cmd_"))
async def cb_command_detail(callback: CallbackQuery) -> None:
    cmd_name = "/" + callback.data.removeprefix("kb_cmd_")
    result = knowledge_base.search(cmd_name)
    text = result if result else f"Информация о команде `{cmd_name}` не найдена."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "kb_limits")
async def cb_limits(callback: CallbackQuery) -> None:
    limits = knowledge_base.get_limits()
    text = (
        f"📊 *Лимиты Claude Code*\n\n"
        f"📦 Контекст: *{limits.get('context_tokens', 0):,}* токенов\n"
        f"📤 Один ответ: *{limits.get('output_tokens', 0):,}* токенов\n"
        f"⚠️ Предупреждение при: *{limits.get('warning_at_percent', 80)}%* заполнения\n\n"
        f"_{limits.get('description', '')}_"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "kb_tips")
async def cb_tips(callback: CallbackQuery) -> None:
    tips = knowledge_base.get_tips()
    numbered = "\n\n".join(f"{i+1}. {t}" for i, t in enumerate(tips))
    await callback.message.edit_text(
        f"💡 *Советы по работе с Claude Code*\n\n{numbered}",
        parse_mode="Markdown",
        reply_markup=_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "kb_effort")
async def cb_effort(callback: CallbackQuery) -> None:
    effort = knowledge_base.get_effort_levels()
    lines = [f"⚡ *Effort-уровни Claude Code*\n\n_{effort.get('description', '')}_\n"]
    for level in ("low", "medium", "high"):
        lvl = effort.get(level, {})
        lines.append(
            f"*{lvl.get('label', level)}*\n"
            f"{lvl.get('description', '')}\n"
            f"🕐 Скорость: {lvl.get('speed', '')}\n"
            f"✅ Для: {lvl.get('use_for', '')}"
        )
    await callback.message.edit_text(
        "\n\n".join(lines),
        parse_mode="Markdown",
        reply_markup=_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "kb_ask_ai")
async def cb_ask_ai(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ClaudeBaseStates.asking_ai)
    await callback.message.answer(
        "🤖 Задай любой вопрос о Claude Code — я отвечу с помощью AI.\n\nНапиши /cancel чтобы выйти."
    )
    await callback.answer()


@router.message(ClaudeBaseStates.asking_ai)
async def handle_ai_question(message: Message, state: FSMContext) -> None:
    thinking = await message.answer("🤖 Думаю...")
    try:
        answer, _ = await chat(
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": message.text},
            ],
            max_tokens=600,
            temperature=0.4,
        )
    except OpenRouterError:
        await thinking.edit_text("❌ AI-сервис перегружен. Попробуй позже.")
        return

    ask_more_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="kb_ask_ai"),
            InlineKeyboardButton(text="← В меню", callback_data="kb_main"),
        ]
    ])
    await thinking.delete()
    await message.answer(answer, reply_markup=ask_more_kb)


@router.message(ClaudeBaseStates.free_search)
async def handle_free_search(message: Message, state: FSMContext) -> None:
    query = message.text.strip() if message.text else ""
    result = knowledge_base.search(query)

    if result:
        await message.answer(result, parse_mode="Markdown", reply_markup=_back_keyboard())
    else:
        not_found_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Спросить AI", callback_data="kb_ask_ai")],
            [InlineKeyboardButton(text="← В меню", callback_data="kb_main")],
        ])
        await message.answer(
            f"🔍 Не нашёл «*{query}*» в базе знаний.\n\nМогу спросить у AI — он знает больше!",
            parse_mode="Markdown",
            reply_markup=not_found_kb,
        )
