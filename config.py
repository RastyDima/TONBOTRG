import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Токен бота из переменной окружения или вставьте сюда
BOT_TOKEN = os.getenv("BOT_TOKEN", "8857900559:AAE2WVuuCQ6VbZUsvi9O3GNjanMkjg9h2Uw")

# ID администраторов (через запятую)
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "8762966170").split(",") if x.strip().isdigit()
]

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "bot.db"))

# URL PostgreSQL — если задан, используется Postgres, иначе локальный SQLite.
DATABASE_URL = os.getenv("DATABASE_URL") or None

# На Render (устанавливает RENDER=true) всегда используем прод-БД: иначе бот
# молча работает на SQLite во временном диске контейнера и все данные (бонусы,
# балансы, промокоды) теряются при каждом перезапуске.
if not DATABASE_URL and os.getenv("RENDER", "").lower() == "true":
    DATABASE_URL = "postgresql://u_tenant_18451181:qw654321rty1@db.armordb.org:6432/db_tenant_9eb5a222"

# Публичный URL сервиса для само-пинга /health (нужен, чтобы бесплатный Render
# не усыплял инстанс из-за 15 минут без входящих запросов).
if os.getenv("RENDER", "").lower() == "true":
    PUBLIC_BASE_URL = (
        os.getenv("RENDER_EXTERNAL_URL")
        or f"https://{os.getenv('RENDER_SERVICE_NAME', 'tonbotrg')}.onrender.com"
    )
else:
    PUBLIC_BASE_URL = ""

# Логин/пароль веб-админки
ADMIN_PANEL_USER = os.getenv("ADMIN_PANEL_USER", "admin")
ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "admin123")

# Настройки вебхука (для облачного хостинга). Если WEBHOOK_URL не задан — бот работает в polling-режиме.
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or None
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ton-bot-secret")
PORT = int(os.getenv("PORT", "8080"))

# Стартовый баланс и бонусы
STARTING_BALANCE = 1000
DAILY_BONUS = 1000
WEEKLY_BONUS = 5000

# Ограничения ставок
MIN_BET = 1
MAX_BET = 10_000_000