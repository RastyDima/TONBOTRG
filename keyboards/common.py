from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def back_button(callback_data: str = "menu") -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)


def cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")


def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[cancel_button()]])
