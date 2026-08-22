from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.common import back_button


def games_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 ТОН", callback_data="games_ton")
    kb.button(text="💎 РУБИНЫ", callback_data="games_rubies")
    kb.row(back_button("menu"))
    return kb.as_markup()


def ton_games():
    kb = InlineKeyboardBuilder()
    kb.button(text="💣 Мины", callback_data="mines")
    kb.button(text="🃏 Джокер", callback_data="joker")
    kb.button(text="⚗️ Алхимик", callback_data="alchemist")
    kb.row(back_button("menu_games"))
    return kb.as_markup()


def rubies_games():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎰 Рулетка", callback_data="ruby_roulette")
    kb.row(back_button("menu_games"))
    return kb.as_markup()
