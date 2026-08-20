from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎮 Игры", callback_data="menu_games")
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.button(text="💰 Баланс", callback_data="balance")
    kb.button(text="🎁 Бонус", callback_data="daily")
    kb.button(text="🏆 Рейтинг", callback_data="rating")
    kb.button(text="📜 История", callback_data="history")
    kb.button(text="🛒 Магазин", callback_data="shop")
    if is_admin:
        kb.button(text="⚙️ Админ-панель", callback_data="admin")
    kb.adjust(2)
    return kb.as_markup()