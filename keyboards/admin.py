from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.common import back_button


def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Выдать валюту", callback_data="admin_give")
    kb.button(text="🚫 Заблокировать", callback_data="admin_block")
    kb.button(text="✅ Разблокировать", callback_data="admin_unblock")
    kb.button(text="📊 Статистика", callback_data="admin_stats")
    kb.adjust(2)
    kb.row(back_button("menu"))
    return kb.as_markup()