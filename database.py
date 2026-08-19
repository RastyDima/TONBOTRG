import os
import sqlite3
from contextlib import closing
from datetime import date

from config import ADMIN_IDS, DATABASE_PATH, STARTING_BALANCE


class Database:
    """Слой работы с SQLite: пользователи, статистика, транзакции, игры."""

    def __init__(self, path: str = DATABASE_PATH):
        self.path = path
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance INTEGER NOT NULL DEFAULT 0,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    last_daily TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    user_id INTEGER PRIMARY KEY,
                    total_games INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    total_bet INTEGER NOT NULL DEFAULT 0,
                    total_won INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    bet INTEGER NOT NULL,
                    win_amount INTEGER NOT NULL DEFAULT 0,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            """)
            conn.commit()

    # ---------- Пользователи ----------

    def register_user(self, user_id: int, username, first_name) -> None:
        is_admin = 1 if user_id in ADMIN_IDS else 0
        with closing(self._connect()) as conn, conn:
            new = conn.execute(
                "SELECT 1 FROM users WHERE id = ?", (user_id,)
            ).fetchone() is None
            conn.execute(
                """
                INSERT INTO users (id, username, first_name, balance, is_admin, last_daily)
                VALUES (?, ?, ?, ?, ?, NULL)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
                """,
                (user_id, username, first_name, STARTING_BALANCE, is_admin),
            )
            conn.execute("INSERT OR IGNORE INTO stats (user_id) VALUES (?)", (user_id,))
            if new:
                conn.execute(
                    "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                    (user_id, STARTING_BALANCE, "bonus", "Приветственный бонус"),
                )

    def get_user(self, user_id: int) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_user_by_username(self, username: str) -> dict | None:
        username = (username or "").lstrip("@").lower()
        if not username:
            return None
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE lower(username) = ? LIMIT 1", (username,)
            ).fetchone()
            return dict(row) if row else None

    def is_user_blocked(self, user_id: int) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT is_blocked FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return bool(row and row["is_blocked"])

    def set_blocked(self, user_id: int, blocked: bool) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE users SET is_blocked = ? WHERE id = ?",
                (1 if blocked else 0, user_id),
            )

    def add_balance(self, user_id: int, amount: int, txn_type: str, description: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id)
            )
            conn.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                (user_id, amount, txn_type, description),
            )

    # ---------- Транзакции ----------

    def get_transactions(self, user_id: int, limit: int = 10) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ---------- Статистика ----------

    def _ensure_stats(self, conn: sqlite3.Connection, user_id: int) -> None:
        conn.execute("INSERT OR IGNORE INTO stats (user_id) VALUES (?)", (user_id,))

    def get_stats(self, user_id: int) -> dict:
        with closing(self._connect()) as conn, conn:
            self._ensure_stats(conn, user_id)
            row = conn.execute(
                "SELECT * FROM stats WHERE user_id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else {
                "user_id": user_id,
                "total_games": 0,
                "wins": 0,
                "losses": 0,
                "total_bet": 0,
                "total_won": 0,
            }

    def update_stats(self, user_id: int, result: str, bet: int, win_amount: int) -> None:
        with closing(self._connect()) as conn, conn:
            self._ensure_stats(conn, user_id)
            if result == "win":
                conn.execute(
                    """
                    UPDATE stats
                    SET total_games = total_games + 1,
                        wins = wins + 1,
                        total_bet = total_bet + ?,
                        total_won = total_won + ?
                    WHERE user_id = ?
                    """,
                    (bet, win_amount, user_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE stats
                    SET total_games = total_games + 1,
                        losses = losses + 1,
                        total_bet = total_bet + ?
                    WHERE user_id = ?
                    """,
                    (bet, user_id),
                )

    # ---------- Игры ----------

    def add_game(self, user_id: int, game_type: str, bet: int, win_amount: int, result: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO games (user_id, game_type, bet, win_amount, result) VALUES (?, ?, ?, ?, ?)",
                (user_id, game_type, bet, win_amount, result),
            )

    # ---------- Ежедневный бонус ----------

    def claim_daily(self, user_id: int, amount: int) -> bool:
        today = date.today().isoformat()
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                "SELECT last_daily FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row is None or row["last_daily"] == today:
                return False
            conn.execute(
                "UPDATE users SET balance = balance + ?, last_daily = ? WHERE id = ?",
                (amount, today, user_id),
            )
            conn.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                (user_id, amount, "daily", "Ежедневный бонус"),
            )
            return True

    # ---------- Рейтинг ----------

    def top_balance(self, limit: int = 10) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, username, first_name, balance FROM users ORDER BY balance DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def top_wins(self, limit: int = 10) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT u.id, u.username, u.first_name, u.balance, s.wins
                FROM users u JOIN stats s ON s.user_id = u.id
                ORDER BY s.wins DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ---------- Админ ----------

    def admin_overview(self) -> dict:
        with closing(self._connect()) as conn:
            users = conn.execute(
                "SELECT COUNT(*) AS c, COALESCE(SUM(balance), 0) AS b FROM users"
            ).fetchone()
            games = conn.execute("SELECT COUNT(*) AS c FROM games").fetchone()
            wins = conn.execute(
                "SELECT COUNT(*) AS c FROM games WHERE result = 'win'"
            ).fetchone()
            tx = conn.execute(
                "SELECT COUNT(*) AS c, COALESCE(SUM(amount), 0) AS s FROM transactions"
            ).fetchone()
            return {
                "users": users["c"],
                "balance": users["b"],
                "games": games["c"],
                "wins": wins["c"],
                "tx_count": tx["c"],
                "tx_volume": tx["s"],
            }


db = Database()
