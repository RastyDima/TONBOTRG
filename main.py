import asyncio
import logging

from aiohttp import web
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message, Update
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN, PORT, WEBHOOK_PATH, WEBHOOK_SECRET, WEBHOOK_URL
from database import db
from handlers import register_handlers
from utils import notify
from utils.helpers import format_number, get_daily_bonus, get_weekly_bonus
from webadmin import register_admin_routes

logging.basicConfig(level=logging.INFO)

REMINDER_INTERVAL = 30 * 60  # секунд


def _bonus_kb(action: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Забрать бонус", callback_data=action)
    return kb.as_markup()


async def reminder_loop() -> None:
    """Раз в полчаса напоминает игрокам о доступных бонусах (ежедневный/еженедельный)."""
    logging.info("Reminder loop started")
    while True:
        try:
            daily_amount = get_daily_bonus()
            for u in db.get_daily_eligible():
                await notify.send(
                    u["id"],
                    f"🎁 <b>Ежедневный бонус доступен!</b>\n\n"
                    f"Заберите {format_number(daily_amount)} монет, нажав кнопку ниже.",
                    _bonus_kb("daily"),
                )
                db.mark_daily_notified(u["id"])
            weekly_amount = get_weekly_bonus()
            for u in db.get_weekly_eligible():
                await notify.send(
                    u["id"],
                    f"🗓 <b>Еженедельный бонус доступен!</b>\n\n"
                    f"Вы можете получить {format_number(weekly_amount)} монет — нажмите кнопку ниже.",
                    _bonus_kb("weekly"),
                )
                db.mark_weekly_notified(u["id"])
        except Exception:  # noqa: BLE001
            logging.exception("reminder loop error")
        await asyncio.sleep(REMINDER_INTERVAL)


def start_reminder_loop() -> asyncio.Task:
    return asyncio.create_task(reminder_loop())


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


async def on_startup(bot: Bot) -> None:
    webhook_url = WEBHOOK_URL + WEBHOOK_PATH
    await bot.set_webhook(webhook_url, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)
    logging.info("Webhook set to %s", webhook_url)


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=False)


def build_app() -> web.Application:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(BlockedUserMiddleware())
    register_handlers(dp)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_requests = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests.register(app, path=WEBHOOK_PATH)

    async def health(request):
        return web.Response(text="OK")

    async def start_background(app) -> None:
        notify.set_bot(bot)
        app["reminder_task"] = start_reminder_loop()

    async def stop_background(app) -> None:
        task = app.get("reminder_task")
        if task:
            task.cancel()

    app.on_startup.append(start_background)
    app.on_cleanup.append(stop_background)
    app.router.add_get("/health", health)
    register_admin_routes(app)
    setup_application(app, dp)
    return app


async def main() -> None:
    db.init_db()
    if WEBHOOK_URL:
        app = build_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
        await site.start()
        logging.info("Webhook server running on port %d", PORT)
        await asyncio.Event().wait()
    else:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher(storage=MemoryStorage())
        dp.update.middleware(BlockedUserMiddleware())
        register_handlers(dp)
        notify.set_bot(bot)
        reminder_task = start_reminder_loop()

        # Открываем порт для Render (health check), чтобы деплой считался живым,
        # а старый инстанс не конфликтовал с новым.
        app = web.Application()

        async def health(request):
            return web.Response(text="OK")

        app.router.add_get("/health", health)
        register_admin_routes(app)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
        await site.start()
        logging.info("Health server running on port %d", PORT)

        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        finally:
            reminder_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())