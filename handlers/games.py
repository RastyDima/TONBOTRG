from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.games import games_menu
from utils.game_registry import clear_pending_bet

router = Router()


@router.callback_query(F.data == "menu_games", StateFilter("*"))
async def games_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    clear_pending_bet(callback.from_user.id)
    await callback.answer()
    await callback.message.edit_text(
        "🎮 <b>Игры</b>\n\n"
        "💣 <b>Мины</b> — поле 5×5, от 1 до 10 мин\n"
        "🃏 <b>Джокер</b> — карточная игра с уровнями риска",
        reply_markup=games_menu(),
    )