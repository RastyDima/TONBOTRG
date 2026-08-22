from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from games.ruby_roulette import SECTORS, RubyRouletteGame
from keyboards.common import back_button, cancel_kb
from utils.game_registry import registry
from utils.helpers import format_number

router = Router()


class RubyRouletteStates(StatesGroup):
    bet = State()


def choice_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔴 Красный (×2)", callback_data="rr_pick:красный")
    kb.button(text="⚫ Чёрный (×2)", callback_data="rr_pick:чёрный")
    kb.button(text="💎 Рубин (×10)", callback_data="rr_pick:рубин")
    kb.adjust(1)
    kb.row(back_button("menu_games"))
    return kb.as_markup()


def result_text(game: RubyRouletteGame, user_rubies: float) -> str:
    r = game.result
    if game.won:
        return (
            f"🎰 <b>Рубиновая рулетка</b>\n\n"
            f"Выпало: {r['emoji']} {r['name']}\n\n"
            f"🎉 <b>Победа!</b>\n"
            f"Множитель: ×{r['mult']}\n"
            f"Выигрыш: <b>{game.payout}</b> 💎\n\n"
            f"💎 Ваши рубины: {user_rubies}"
        )
    return (
        f"🎰 <b>Рубиновая рулетка</b>\n\n"
        f"Выпало: {r['emoji']} {r['name']}\n\n"
        f"💀 <b>Проигрыш!</b>\n"
        f"Ставка {game.bet} 💎 сгорела.\n\n"
        f"💎 Ваши рубины: {user_rubies}"
    )


@router.callback_query(F.data == "ruby_roulette", StateFilter("*"))
async def ruby_roulette_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if registry.is_active(callback.from_user.id):
        await callback.answer("Сначала завершите текущую игру!", show_alert=True)
        return
    user = db.get_user(callback.from_user.id)
    rubies = user.get("rubies", 0) or 0
    if rubies < 1:
        await callback.answer("❌ У вас нет рубинов. Получите их за крупные выигрыши!", show_alert=True)
        return
    await state.set_state(RubyRouletteStates.bet)
    await callback.answer()
    await callback.message.edit_text(
        f"🎰 <b>Рубиновая рулетка</b>\n\n"
        f"💎 Ваши рубины: <b>{rubies}</b>\n\n"
        f"Выберите цвет:\n"
        f"🔴 <b>Красный</b> — ×2\n"
        f"⚫ <b>Чёрный</b> — ×2\n"
        f"💎 <b>Рубин</b> — ×10 (редкий!)\n\n"
        f"Введите сумму ставки (рубины):",
        reply_markup=cancel_kb(),
    )


@router.message(F.text, RubyRouletteStates.bet)
async def ruby_roulette_process_bet(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    bet_text = (message.text or "").strip().replace(" ", "").replace(",", ".")
    try:
        bet = int(float(bet_text))
    except ValueError:
        await message.answer("❌ Введите целое число:")
        return

    if bet < 1:
        await message.answer("❌ Минимальная ставка: 1 рубин")
        return

    user = db.get_user(message.from_user.id)
    rubies = user.get("rubies", 0) or 0
    if bet > rubies:
        await message.answer(f"❌ Недостаточно рубинов. У вас: {rubies} 💎")
        return

    db.add_rubies(message.from_user.id, -bet)
    game = RubyRouletteGame(message.from_user.id, bet)
    registry.register(message.from_user.id, "ruby_roulette", game)

    await state.clear()
    await message.answer(
        f"🎰 <b>Рубиновая рулетка</b>\n\n"
        f"Ставка: <b>{bet}</b> 💎\n\n"
        f"Выберите цвет:",
        reply_markup=choice_kb(),
    )


@router.callback_query(F.data.startswith("rr_pick:"), StateFilter("*"))
async def ruby_roulette_pick(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    game = registry.game(user_id)
    if not game or game.type != "ruby_roulette":
        await callback.answer("Игра не найдена. Начните новую.", show_alert=True)
        return
    if game.is_over:
        await callback.answer("Игра уже завершена.")
        return

    choice = callback.data.split(":", 1)[1]
    game.spin(choice)

    if game.won:
        db.add_rubies(user_id, game.payout)

    user = db.get_user(user_id)
    rubies = user.get("rubies", 0) or 0

    registry.release(user_id)
    db.add_game(user_id, "ruby_roulette", game.bet, game.payout, "win" if game.won else "lose")
    db.update_stats(user_id, "win" if game.won else "lose", game.bet, game.payout)

    await callback.answer("💎" if game.won else "💀")
    await callback.message.edit_text(result_text(game, rubies), reply_markup=None)
