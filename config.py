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

# URL PostgreSQL — если задан, используется Postgres, иначе локальный SQLite
DATABASE_URL = os.getenv("DATABASE_URL") or None

# Настройки вебхука (для облачного хостинга). Если WEBHOOK_URL не задан — бот работает в polling-режиме.
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or None
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ton-bot-secret")
PORT = int(os.getenv("PORT", "8080"))

# Стартовый баланс и ежедневный бонус
STARTING_BALANCE = 1000
DAILY_BONUS = 1000

# Ограничения ставок
MIN_BET = 1
MAX_BET = 10_000_000