from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.common import back_button


def games_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💣 Мины", callback_data="mines")
    kb.button(text="🃏 Джокер", callback_data="joker")
    kb.adjust(2)
    kb.row(back_button("menu"))
    return kb.as_markup()