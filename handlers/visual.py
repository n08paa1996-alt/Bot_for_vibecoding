import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from services import prompt_engineer, db
from services.openrouter import generate_image, OpenRouterError

router = Router()


class VisualStates(StatesGroup):
    waiting_description = State()
    regenerating = State()


def _result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="visual_regen"),
            InlineKeyboardButton(text="✏️ Изменить описание", callback_data="visual_change"),
        ]
    ])


@router.message(F.text == "🎨 Визуал")
async def start_visual(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(VisualStates.waiting_description)
    await message.answer(
        "🎨 *Генерация изображений*\n\n"
        "Опиши что хочешь получить — я улучшу твой промпт и создам изображение.\n\n"
        "_Примеры: «иконка финтех-бота», «логотип для IT-стартапа в тёмных тонах», «обложка для Telegram-канала о вайбкодинге»_\n\n"
        "Напиши /cancel чтобы выйти.",
        parse_mode="Markdown",
    )


@router.message(VisualStates.waiting_description)
async def handle_description(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Пожалуйста, опиши изображение текстом.")
        return

    user_prompt = message.text.strip()
    await state.update_data(last_prompt=user_prompt)
    await _generate_and_send(message, state, user_prompt)


@router.callback_query(F.data == "visual_regen")
async def cb_regen(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("🔄 Перегенерирую...")
    data = await state.get_data()
    user_prompt = data.get("last_prompt", "")
    if not user_prompt:
        await callback.message.answer("Не нашёл предыдущий промпт. Напиши описание заново.")
        return
    await _generate_and_send(callback.message, state, user_prompt, from_callback=True)


@router.callback_query(F.data == "visual_change")
async def cb_change(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(VisualStates.waiting_description)
    await callback.message.answer("✏️ Напиши новое описание изображения:")


async def _generate_and_send(
    message: Message, state: FSMContext, user_prompt: str, from_callback: bool = False
) -> None:
    thinking_msg = await message.answer("🎨 Улучшаю промпт...")

    try:
        enhanced = await prompt_engineer.enhance_image_prompt(user_prompt)
    except OpenRouterError:
        await thinking_msg.edit_text("❌ Ошибка при улучшении промпта. Попробуй позже.")
        return

    await thinking_msg.edit_text("🖼 Генерирую изображение... Это может занять до 30 секунд.")

    slow_task = asyncio.create_task(_slow_warning(thinking_msg))

    try:
        image_bytes = await generate_image(enhanced)
        slow_task.cancel()
    except OpenRouterError as e:
        slow_task.cancel()
        await thinking_msg.edit_text("❌ Сервис генерации изображений перегружен. Попробуй через минуту.")
        await db.log_generation(message.from_user.id if message.from_user else 0, "image", "flux-pro", False)
        return

    await thinking_msg.delete()

    await db.log_generation(
        message.from_user.id if message.from_user else 0,
        "image", "flux-pro", True
    )

    await state.update_data(last_enhanced_prompt=enhanced)

    photo = BufferedInputFile(image_bytes, filename="vibemaster_image.png")
    await message.answer_photo(
        photo=photo,
        caption=f"✅ *Готово!*\n\n🔧 *Улучшенный промпт:*\n`{enhanced[:500]}`",
        parse_mode="Markdown",
        reply_markup=_result_keyboard(),
    )


async def _slow_warning(msg: Message) -> None:
    await asyncio.sleep(15)
    try:
        await msg.edit_text("🖼 Ещё немного... Генерация занимает больше времени чем обычно.")
    except Exception:
        pass
