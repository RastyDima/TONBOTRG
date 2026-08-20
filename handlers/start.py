import html

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS, STARTING_BALANCE
from database import db
from keyboards.main_menu import main_menu
from utils.game_registry import cancel_game, clear_pending_bet, registry
from utils.helpers import format_number, menu_text

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    existing = db.get_user(user.id)
    db.register_user(user.id, (user.username or "").lower() or None, user.first_name)
    name = html.escape(user.first_name or "игрок")
    if existing:
        text = f"👋 С возвращением, {name}!\nВыберите действие в меню:"
    else:
        text = (
            f"👋 <b>Добро пожаловать, {name}!</b>\n\n"
            f"🎁 За регистрацию начислено {format_number(STARTING_BALANCE)} монет.\n\n"
            f"Выберите действие в меню:"
        )
    is_admin = user.id in ADMIN_IDS or bool(db.get_user(user.id)["is_admin"])
    await message.answer(text, reply_markup=main_menu(is_admin))


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>Помощь</b>\n\n"
        "🎮 <b>Игры:</b> Мины, Джокер (доступны из меню)\n"
        "⚡ <b>Быстрый старт:</b> <code>м 30000</code> — мины со ставкой, "
        "<code>дж 30000</code> — джокер со ставкой, "
        "<code>алх 30000</code> — алхимик со ставкой\n"
        "💸 <b>Перевод:</b> ответьте на сообщение игрока <code>п 12000</code>\n"
        "💰 <b>Баланс:</b> <code>б</code>\n"
        "👤 /profile — профиль и статистика\n"
        "🎁 /daily — ежедневный бонус\n"
        "🗓 /weekly — еженедельный бонус\n"
        "🎟 Промокод: введите <code>#КОД</code> в чате\n"
        "📜 /history — история транзакций\n"
        "🏆 /rating — рейтинг игроков\n"
        "❌ /cancel — отменить действие или выйти из игры\n\n"
        "Все действия доступны через кнопки меню."
    )


@router.callback_query(F.data == "menu", StateFilter("*"))
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    clear_pending_bet(callback.from_user.id)
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Используйте /start")
        return
    is_admin = callback.from_user.id in ADMIN_IDS or bool(user["is_admin"])
    await callback.message.edit_text(menu_text(user), reply_markup=main_menu(is_admin))


@router.callback_query(F.data == "cancel", StateFilter("*"))
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    cancel_game(callback.from_user.id)
    await callback.answer()
    await callback.message.edit_text("❌ Действие отменено.")


@router.message(Command("cancel"), StateFilter("*"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    if registry.game(message.from_user.id):
        cancel_game(message.from_user.id)
        await message.answer("❌ Игра отменена. Ставка возвращена на баланс.")
    else:
        await message.answer("❌ Отменено.")