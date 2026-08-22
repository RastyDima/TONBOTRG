from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.common import back_button


def games_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲🎮 ИГРЫ НА ТОН", callback_data="noop")
    kb.button(text="💣 Мины", callback_data="mines")
    kb.button(text="🃏 Джокер", callback_data="joker")
    kb.button(text="⚗️ Алхимик", callback_data="alchemist")
    kb.button(text="", callback_data="noop")
    kb.button(text="💎 ИГРЫ НА РУБИНЫ", callback_data="noop")
    kb.button(text="🎰 Рулетка", callback_data="ruby_roulette")
    kb.row(back_button("menu"))
    return kb.as_markup()
