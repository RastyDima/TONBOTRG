from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.common import back_button


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Выдать TON", callback_data="admin_give"),
            InlineKeyboardButton(text="💎 Выдать рубины", callback_data="admin_give_rubies"),
        ],
        [
            InlineKeyboardButton(text="🏷 Выдать титул", callback_data="admin_give_title"),
            InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos"),
        ],
        [
            InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_block"),
            InlineKeyboardButton(text="✅ Разблокировать", callback_data="admin_unblock"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="🗑 Сброс БД", callback_data="admin_reset"),
        ],
        [back_button("menu")],
    ])


def admin_reset_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, снести всё", callback_data="admin_reset_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="admin_reset_no"),
        ],
    ])
