from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 База Claude"), KeyboardButton(text="📝 Создать ТЗ")],
        [KeyboardButton(text="🎨 Визуал"), KeyboardButton(text="🚀 Деплой")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери режим или напиши вопрос...",
)

WELCOME_TEXT = """🤖 *VibeMaster AI* — твой операционный центр вайб-кодера

Я помогу тебе:
🧠 *Создать ТЗ* — превращу твою идею в структурированное техзадание для Claude
🎨 *Сгенерировать визуал* — улучшу промпт и создам изображение
📚 *Объяснить Claude Code* — команды, лимиты, лучшие практики
🚀 *Выбрать деплой* — расскажу куда и как запустить твой продукт

*Выбери режим 👇*"""


async def show_main_menu(message: Message, text: str = WELCOME_TEXT) -> None:
    await message.answer(text, reply_markup=MAIN_MENU, parse_mode="Markdown")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_main_menu(message)


@router.message(Command("cancel"))
@router.message(F.text.lower() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await show_main_menu(message, "Ты уже в главном меню 👇")
        return
    await state.clear()
    await show_main_menu(message, "❌ Отменено. Возвращаюсь в главное меню 👇")


@router.message(Command("reload_kb"))
async def cmd_reload_kb(message: Message) -> None:
    from services import knowledge_base
    knowledge_base.reload()
    await message.answer("✅ База знаний Claude Code перезагружена.")


@router.message(F.text & ~F.text.startswith("/"))
async def unknown_text(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer(
            "Используй кнопки меню 👇\nИли напиши /start чтобы перезапустить бота.",
            reply_markup=MAIN_MENU,
        )
