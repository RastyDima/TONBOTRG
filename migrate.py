"""Перенос данных из локального SQLite (data/bot.db) в PostgreSQL.

Запуск:
    $env:DATABASE_URL="postgres://user:pass@host:5432/db"
    python migrate.py
"""
import os
import sqlite3

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Укажите DATABASE_URL с подключением к PostgreSQL")

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "data", "bot.db")

TABLES = {
    "users": ["id", "username", "first_name", "balance", "is_blocked", "is_admin", "last_daily", "created_at"],
    "stats": ["user_id", "total_games", "wins", "losses", "total_bet", "total_won"],
    "transactions": ["id", "user_id", "amount", "type", "description", "created_at"],
    "games": ["id", "user_id", "game_type", "bet", "win_amount", "result", "created_at"],
}


def main() -> None:
    src = sqlite3.connect(SQLITE_PATH)
    dst = psycopg2.connect(DATABASE_URL)
    dst.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with src, dst:
        for table, cols in TABLES.items():
            rows = src.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
            if not rows:
                print(f"{table}: пусто")
                continue
            placeholders = ", ".join(["%s"] * len(cols))
            dst_cur = dst.cursor()
            dst_cur.executemany(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
                f"ON CONFLICT DO NOTHING",
                [tuple(r) for r in rows],
            )
            dst_cur.close()
            print(f"{table}: перенесено {len(rows)} строк")

    if src.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        dst_cur = dst.cursor()
        dst_cur.execute(
            "SELECT setval('transactions_id_seq', COALESCE((SELECT MAX(id) FROM transactions), 1))"
        )
        dst_cur.execute(
            "SELECT setval('games_id_seq', COALESCE((SELECT MAX(id) FROM games), 1))"
        )
        dst_cur.close()

    src.close()
    dst.close()
    print("Готово. Проверьте данные в быстрой команде: б")


if __name__ == "__main__":
    main()