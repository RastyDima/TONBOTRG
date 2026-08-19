"""Отправка исходящих уведомлений игрокам (начисления, напоминания о бонусах).

Использует глобальный экземпляр бота, который устанавливается при старте
(main.py вызывает notify.set_bot(bot)). Безопасен для вызова из веб-админки
и фоновых задач: ошибки отправки не роняют процесс.
"""
import logging

from aiogram import Bot

_bot: Bot | None = None


def set_bot(bot: Bot) -> None:
    global _bot
    _bot = bot


async def send(user_id: int, text: str, reply_markup=None) -> bool:
    if _bot is None:
        logging.warning("notify: бот не инициализирован, пропуск для user_id=%s", user_id)
        return False
    try:
        await _bot.send_message(user_id, text, reply_markup=reply_markup)
        return True
    except Exception as exc:  # noqa: BLE001
        logging.warning("notify: не удалось отправить user_id=%s: %s", user_id, exc)
        return False
