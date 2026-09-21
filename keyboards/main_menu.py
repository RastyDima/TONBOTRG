from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import PUBLIC_BASE_URL


def main_menu(is_admin: bool = False):
    rows = []
    rows.append([
        InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games"),
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
    ])
    rows.append([
        InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
        InlineKeyboardButton(text="🎁 Бонус", callback_data="daily"),
    ])
    rows.append([
        InlineKeyboardButton(text="👥 Рефералы", callback_data="ref"),
        InlineKeyboardButton(text="🏆 Рейтинг", callback_data="rating"),
    ])
    rows.append([
        InlineKeyboardButton(text="📜 История", callback_data="history"),
        InlineKeyboardButton(text="🛒 Магазин", callback_data="shop"),
    ])
    if is_admin:
        rows.append([
            InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin"),
        ])
    if PUBLIC_BASE_URL:
        rows.append([
            InlineKeyboardButton(text="🌐 Играть в Mini App", web_app=WebAppInfo(url=f"{PUBLIC_BASE_URL.rstrip('/')}/app/")),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
