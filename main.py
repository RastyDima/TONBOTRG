import asyncio
import logging

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message, Update

from config import BOT_TOKEN
from database import db
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)


class BlockedUserMiddleware(BaseMiddleware):
    """Перехватывает все апдейты от заблокированных пользователей."""

    async def __call__(self, handler, event, data):
        inner = event.event if isinstance(event, Update) else event
        user = getattr(inner, "from_user", None)
        if user is not None and db.is_user_blocked(user.id):
            if isinstance(inner, Message):
                await inner.answer("🚫 Вы заблокированы. Обратитесь к администратору.")
            elif isinstance(inner, CallbackQuery):
                await inner.answer("🚫 Вы заблокированы.", show_alert=True)
            return
        return await handler(event, data)


async def main() -> None:
    db.init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(BlockedUserMiddleware())
    register_handlers(dp)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())