from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.common import back_button


def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Выдать TON", callback_data="admin_give")
    kb.button(text="💎 Выдать рубины", callback_data="admin_give_rubies")
    kb.button(text="🎟 Промокоды", callback_data="admin_promos")
    kb.button(text="🚫 Заблокировать", callback_data="admin_block")
    kb.button(text="✅ Разблокировать", callback_data="admin_unblock")
    kb.button(text="📊 Статистика", callback_data="admin_stats")
    kb.button(text="🗑 Сброс БД", callback_data="admin_reset")
    kb.adjust(2)
    kb.row(back_button("menu"))
    return kb.as_markup()


def admin_reset_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, снести всё", callback_data="admin_reset_yes")
    kb.button(text="❌ Нет", callback_data="admin_reset_no")
    kb.adjust(2)
    return kb.as_markup()
