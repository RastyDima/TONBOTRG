from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def back_button(callback_data: str = "menu") -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)


def cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")


def cancel_kb():
    kb = InlineKeyboardBuilder()
    kb.row(cancel_button())
    return kb.as_markup()