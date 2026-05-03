from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from fsm.tz_states import TZStates
from models import TZData
from services import tz_generator, db
from services.openrouter import OpenRouterError

router = Router()

STEPS = [
    ("goal", "🎯 Шаг 1/5", "Опиши основную цель продукта (1–2 предложения)\n\n_Например: Телеграм-бот, который помогает трекать расходы и присылает еженедельный отчёт._"),
    ("audience", "👥 Шаг 2/5", "Кто целевая аудитория?\n\n_Например: фрилансеры 25–35 лет, которые хотят контролировать бюджет без Excel._"),
    ("features", "⚙️ Шаг 3/5", "Перечисли ключевые функции через запятую\n\n_Например: добавить расход, категории, еженедельный отчёт, экспорт в CSV._"),
    ("tech_constraints", "🔧 Шаг 4/5", "Технические ограничения (стек, бюджет, API-ключи)\n\n_Если нет ограничений — напиши «нет» или пропусти._"),
    ("desired_result", "🏁 Шаг 5/5", "Желаемый результат?\n\n_Например: рабочий MVP бот, задеплоенный на Railway с базовым функционалом._"),
]

STEP_KEYS = [s[0] for s in STEPS]


def _progress_bar(step: int, total: int = 5) -> str:
    filled = "█" * step
    empty = "░" * (total - step)
    pct = int(step / total * 100)
    return f"{filled}{empty} {pct}%"


def _step_message(index: int) -> str:
    _, header, question = STEPS[index]
    bar = _progress_bar(index + 1)
    return f"{header}  `{bar}`\n\n{question}"


def _back_button(step_index: int) -> InlineKeyboardMarkup | None:
    if step_index == 0:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Изменить предыдущий ответ", callback_data=f"tz_back_{step_index}")]
    ])


@router.message(F.text == "📝 Создать ТЗ")
async def start_tz_wizard(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TZStates.goal)
    await message.answer(
        "📝 *Конструктор технического задания*\n\nЯ задам тебе 5 вопросов и на выходе ты получишь готовое ТЗ для Claude Code.\n\nНапиши /cancel чтобы прервать.",
        parse_mode="Markdown",
    )
    await message.answer(_step_message(0), parse_mode="Markdown")


async def _handle_step(
    message: Message, state: FSMContext, key: str, next_state, next_index: int
) -> None:
    text = message.text.strip() if message.text else ""
    if len(text) < 3:
        await message.answer("📝 Расскажи подробнее — хотя бы несколько слов.")
        return

    await state.update_data(**{key: text})

    if next_index < len(STEPS):
        await state.set_state(next_state)
        await message.answer(
            _step_message(next_index),
            parse_mode="Markdown",
            reply_markup=_back_button(next_index),
        )
    else:
        await _generate_tz(message, state)


@router.message(TZStates.goal)
async def step_goal(message: Message, state: FSMContext) -> None:
    await _handle_step(message, state, "goal", TZStates.audience, 1)


@router.message(TZStates.audience)
async def step_audience(message: Message, state: FSMContext) -> None:
    await _handle_step(message, state, "audience", TZStates.features, 2)


@router.message(TZStates.features)
async def step_features(message: Message, state: FSMContext) -> None:
    await _handle_step(message, state, "features", TZStates.tech_constraints, 3)


@router.message(TZStates.tech_constraints)
async def step_tech(message: Message, state: FSMContext) -> None:
    await _handle_step(message, state, "tech_constraints", TZStates.desired_result, 4)


@router.message(TZStates.desired_result)
async def step_result(message: Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else ""
    if len(text) < 3:
        await message.answer("📝 Расскажи подробнее — хотя бы несколько слов.")
        return
    await state.update_data(desired_result=text)
    await _generate_tz(message, state)


async def _generate_tz(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tz_data = TZData(
        goal=data.get("goal", ""),
        audience=data.get("audience", ""),
        features=data.get("features", ""),
        tech_constraints=data.get("tech_constraints", "нет"),
        desired_result=data.get("desired_result", ""),
    )

    thinking_msg = await message.answer("🧠 Генерирую ТЗ... Это займёт 10–20 секунд.")
    await state.set_state(TZStates.confirming)

    try:
        tz_text, tokens = await tz_generator.generate_tz(tz_data)
        await db.save_tz(message.from_user.id, tz_text)
        await db.log_generation(
            message.from_user.id, "tz", "claude-3.5-sonnet", True, tokens
        )
    except OpenRouterError as e:
        await thinking_msg.delete()
        await message.answer(f"❌ Ошибка генерации: сервис перегружен, попробуй через минуту.")
        await state.clear()
        return

    await thinking_msg.delete()

    result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Скопировать", callback_data="tz_copy"),
            InlineKeyboardButton(text="📝 Создать ещё", callback_data="tz_new"),
        ],
        [InlineKeyboardButton(text="⭐ Оценить качество", callback_data="tz_rate")],
    ])

    await message.answer(
        f"✅ *ТЗ готово!* Сохранено в базе.\n\n{tz_text}",
        parse_mode="Markdown",
        reply_markup=result_keyboard,
    )
    await state.update_data(last_tz=tz_text)


@router.callback_query(F.data == "tz_copy")
async def cb_copy(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    tz_text = data.get("last_tz", "")
    if tz_text:
        await callback.message.answer(
            f"```\n{tz_text[:4000]}\n```",
            parse_mode="Markdown",
        )
        await callback.answer("Скопируй текст выше 👆")
    else:
        await callback.answer("ТЗ не найдено — создай новое.")


@router.callback_query(F.data == "tz_new")
async def cb_new(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(TZStates.goal)
    await callback.message.answer(
        "📝 Начнём новое ТЗ!\n\n" + _step_message(0),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "tz_rate")
async def cb_rate(callback: CallbackQuery) -> None:
    rating_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"tz_rating_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text=str(i), callback_data=f"tz_rating_{i}") for i in range(6, 11)],
    ])
    await callback.message.answer("⭐ Оцени качество ТЗ от 1 до 10:", reply_markup=rating_kb)
    await callback.answer()


@router.callback_query(F.data.startswith("tz_rating_"))
async def cb_rating_value(callback: CallbackQuery) -> None:
    rating = int(callback.data.split("_")[-1])
    await db.update_tz_rating(callback.from_user.id, rating)
    emoji = "🔥" if rating >= 8 else "👍" if rating >= 5 else "📝"
    await callback.message.edit_text(f"{emoji} Спасибо за оценку: *{rating}/10*", parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("tz_back_"))
async def cb_back(callback: CallbackQuery, state: FSMContext) -> None:
    step_index = int(callback.data.split("_")[-1])
    prev_index = step_index - 1
    states_map = [TZStates.goal, TZStates.audience, TZStates.features, TZStates.tech_constraints, TZStates.desired_result]
    await state.set_state(states_map[prev_index])
    await callback.message.answer(
        f"↩️ Вернулся к шагу {prev_index + 1}. Введи новый ответ:\n\n{_step_message(prev_index)}",
        parse_mode="Markdown",
        reply_markup=_back_button(prev_index),
    )
    await callback.answer()


@router.message(TZStates.confirming)
async def step_in_confirming(message: Message) -> None:
    await message.answer("Твоё ТЗ уже сгенерировано ☝️ Используй кнопки выше.")
