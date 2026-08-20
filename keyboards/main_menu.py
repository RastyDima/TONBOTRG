from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _b(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def main_menu(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.row(
        _b("💣 Мины", "mines"),
        _b("🃏 Джокер", "joker"),
        _b("⚗️ Алхимик", "alchemist"),
    )
    kb.row(
        _b("👤 Профиль", "profile"),
        _b("🏆 Рейтинг", "rating"),
    )
    kb.row(
        _b("🎁 Бонус", "daily"),
        _b("💳 Баланс", "balance"),
        _b("📜 История", "history"),
    )
    if is_admin:
        kb.row(_b("⚙️ Админ-панель", "admin"))
    return kb.as_markup()