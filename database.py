import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import date

from config import ADMIN_IDS, DATABASE_PATH, DATABASE_URL, STARTING_BALANCE

if DATABASE_URL:
    import psycopg2
    import psycopg2.pool
    from psycopg2.extras import RealDictCursor


def current_week() -> str:
    """Идентификатор текущей недели в формате 'YYYY-Www'."""
    iso = date.today().isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


class Database:
    """Слой работы с SQLite (локальная разработка без Postgres)."""

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
                    rubies REAL NOT NULL DEFAULT 0,
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS promos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    amount INTEGER NOT NULL,
                    max_uses INTEGER NOT NULL DEFAULT 1,
                    used_count INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS promo_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    UNIQUE(promo_id, user_id)
                )
            """)
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
            if "daily_notified" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN daily_notified INTEGER NOT NULL DEFAULT 0")
            if "last_weekly" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN last_weekly TEXT")
            if "weekly_notified" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN weekly_notified INTEGER NOT NULL DEFAULT 0")
            if "max_balance" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN max_balance INTEGER NOT NULL DEFAULT 0")
                conn.execute("UPDATE users SET max_balance = balance WHERE max_balance = 0")
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

    def search_users(self, query: str, limit: int = 50) -> list[dict]:
        """Поиск игроков по ID, имени или username (для веб-админки)."""
        query = (query or "").strip().lstrip("@")
        with closing(self._connect()) as conn:
            if not query:
                rows = conn.execute(
                    "SELECT * FROM users ORDER BY balance DESC LIMIT ?", (limit,)
                ).fetchall()
            elif query.isdigit():
                row = conn.execute(
                    "SELECT * FROM users WHERE id = ? LIMIT 1", (int(query),)
                ).fetchone()
                rows = [row] if row else []
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM users
                    WHERE lower(username) LIKE ? OR lower(first_name) LIKE ?
                    ORDER BY balance DESC LIMIT ?
                    """,
                    (f"%{query.lower()}%", f"%{query.lower()}%", limit),
                ).fetchall()
            return [dict(r) for r in rows]

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
                "UPDATE users SET balance = balance + ?, max_balance = MAX(COALESCE(max_balance, 0), balance + ?) WHERE id = ?",
                (amount, amount, user_id),
            )
            conn.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                (user_id, amount, txn_type, description),
            )

    def add_rubies(self, user_id: int, amount: float) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE users SET rubies = rubies + ? WHERE id = ?",
                (amount, user_id),
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
                "UPDATE users SET balance = balance + ?, last_daily = ?, daily_notified = 0, "
                "max_balance = MAX(COALESCE(max_balance, 0), balance + ?) WHERE id = ?",
                (amount, today, amount, user_id),
            )
            conn.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                (user_id, amount, "daily", "Ежедневный бонус"),
            )
            return True

    def claim_weekly(self, user_id: int, amount: int) -> bool:
        week = current_week()
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                "SELECT last_weekly FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row is None or row["last_weekly"] == week:
                return False
            conn.execute(
                "UPDATE users SET balance = balance + ?, last_weekly = ?, weekly_notified = 0, "
                "max_balance = MAX(COALESCE(max_balance, 0), balance + ?) WHERE id = ?",
                (amount, week, amount, user_id),
            )
            conn.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                (user_id, amount, "weekly", "Еженедельный бонус"),
            )
            return True

    def get_daily_eligible(self) -> list[dict]:
        """Игроки, которым можно напомнить про ежедневный бонус (забрали раньше, сегодня ещё нет)."""
        today = date.today().isoformat()
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT id FROM users
                WHERE is_blocked = 0
                  AND last_daily IS NOT NULL
                  AND last_daily != ?
                  AND daily_notified = 0
                """,
                (today,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_weekly_eligible(self) -> list[dict]:
        """Игроки, которым можно напомнить про еженедельный бонус (забирали раньше, в эту неделю ещё нет)."""
        week = current_week()
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT id FROM users
                WHERE is_blocked = 0
                  AND last_weekly IS NOT NULL
                  AND last_weekly != ?
                  AND weekly_notified = 0
                """,
                (week,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_daily_notified(self, user_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE users SET daily_notified = 1 WHERE id = ?", (user_id,)
            )

    def mark_weekly_notified(self, user_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE users SET weekly_notified = 1 WHERE id = ?", (user_id,)
            )

    # ---------- Рейтинг ----------

    def top_balance(self, limit: int = 10) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, username, first_name, balance FROM users ORDER BY balance DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def top_max_balance(self, limit: int = 10) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, username, first_name, max_balance FROM users ORDER BY max_balance DESC LIMIT ?",
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

    # ---------- Настройки ----------

    def get_setting(self, key: str, default) -> str:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )

    # ---------- Промокоды ----------

    def create_promo(self, code: str, amount: int, max_uses: int) -> bool:
        code = (code or "").strip().upper()
        if not code or amount <= 0 or max_uses < 1:
            return False
        with closing(self._connect()) as conn, conn:
            try:
                conn.execute(
                    "INSERT INTO promos (code, amount, max_uses) VALUES (?, ?, ?)",
                    (code, amount, max_uses),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def get_promo(self, code: str) -> dict | None:
        code = (code or "").strip().upper()
        if not code:
            return None
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM promos WHERE code = ?", (code,)
            ).fetchone()
            return dict(row) if row else None

    def get_promo_by_id(self, promo_id: int) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM promos WHERE id = ?", (promo_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_promos(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM promos ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_promo(self, promo_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM promo_claims WHERE promo_id = ?", (promo_id,))
            conn.execute("DELETE FROM promos WHERE id = ?", (promo_id,))

    def toggle_promo(self, promo_id: int, active: bool) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE promos SET is_active = ? WHERE id = ?",
                (1 if active else 0, promo_id),
            )

    def redeem_promo(self, user_id: int, code: str) -> tuple[str, int]:
        """Активирует промокод. Возвращает (статус, сумма).
        Статусы: ok, not_found, inactive, used_up, already."""
        promo = self.get_promo(code)
        if not promo:
            return ("not_found", 0)
        if not promo["is_active"]:
            return ("inactive", 0)
        if promo["used_count"] >= promo["max_uses"]:
            return ("used_up", 0)
        with closing(self._connect()) as conn, conn:
            claimed = conn.execute(
                "SELECT 1 FROM promo_claims WHERE promo_id = ? AND user_id = ?",
                (promo["id"], user_id),
            ).fetchone()
            if claimed:
                return ("already", 0)
            conn.execute(
                "INSERT INTO promo_claims (promo_id, user_id) VALUES (?, ?)",
                (promo["id"], user_id),
            )
            conn.execute(
                "UPDATE promos SET used_count = used_count + 1 WHERE id = ?",
                (promo["id"],),
            )
            conn.execute(
                "UPDATE users SET balance = balance + ?, max_balance = MAX(COALESCE(max_balance, 0), balance + ?) WHERE id = ?",
                (promo["amount"], promo["amount"], user_id),
            )
            conn.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                (user_id, promo["amount"], "promo", f"Промокод {promo['code']}"),
            )
        return ("ok", promo["amount"])

    def reset_database(self) -> None:
        """Полный сброс: всем баланс на стартовый, обнуление статистики и истории."""
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE users SET balance = ?, max_balance = ?, "
                "last_daily = NULL, last_weekly = NULL, "
                "daily_notified = 0, weekly_notified = 0",
                (STARTING_BALANCE, STARTING_BALANCE),
            )
            conn.execute(
                "UPDATE stats SET total_games = 0, wins = 0, losses = 0, "
                "total_bet = 0, total_won = 0"
            )
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM games")
            conn.execute("DELETE FROM promo_claims")
            conn.execute("UPDATE promos SET used_count = 0")


class PostgresDatabase:
    """Слой работы с PostgreSQL (для облачного хостинга)."""

    def __init__(self, url: str = DATABASE_URL):
        self.url = url
        self._pool = None
        self.init_db()

    def _get_conn(self):
        if self._pool is None:
            self._pool = psycopg2.pool.SimpleConnectionPool(1, 10, self.url)
        return self._pool.getconn()

    def _put_conn(self, conn) -> None:
        self._pool.putconn(conn)

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        try:
            with conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                yield cur
        finally:
            self._put_conn(conn)

    def init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance BIGINT NOT NULL DEFAULT 0,
                    rubies DOUBLE PRECISION NOT NULL DEFAULT 0,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    last_daily TEXT,
                    created_at TEXT NOT NULL DEFAULT (to_char(LOCALTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    user_id BIGINT PRIMARY KEY,
                    total_games INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    total_bet BIGINT NOT NULL DEFAULT 0,
                    total_won BIGINT NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT (to_char(LOCALTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    game_type TEXT NOT NULL,
                    bet BIGINT NOT NULL,
                    win_amount BIGINT NOT NULL DEFAULT 0,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (to_char(LOCALTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_notified INTEGER NOT NULL DEFAULT 0"
            )
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_weekly TEXT")
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_notified INTEGER NOT NULL DEFAULT 0"
            )
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_balance BIGINT NOT NULL DEFAULT 0"
            )
            cur.execute(
                "UPDATE users SET max_balance = balance WHERE max_balance = 0"
            )
            cur.execute("""
                CREATE TABLE IF NOT EXISTS promos (
                    id BIGSERIAL PRIMARY KEY,
                    code TEXT NOT NULL UNIQUE,
                    amount BIGINT NOT NULL,
                    max_uses INTEGER NOT NULL DEFAULT 1,
                    used_count INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (to_char(LOCALTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS promo_claims (
                    id BIGSERIAL PRIMARY KEY,
                    promo_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (to_char(LOCALTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')),
                    UNIQUE(promo_id, user_id)
                )
            """)

    # ---------- Пользователи ----------

    def register_user(self, user_id: int, username, first_name) -> None:
        is_admin = 1 if user_id in ADMIN_IDS else 0
        with self._cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
            new = cur.fetchone() is None
            cur.execute(
                """
                INSERT INTO users (id, username, first_name, balance, is_admin, last_daily)
                VALUES (%s, %s, %s, %s, %s, NULL)
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name
                """,
                (user_id, username, first_name, STARTING_BALANCE, is_admin),
            )
            cur.execute(
                "INSERT INTO stats (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (user_id,),
            )
            if new:
                cur.execute(
                    "INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, %s, %s)",
                    (user_id, STARTING_BALANCE, "bonus", "Приветственный бонус"),
                )

    def get_user(self, user_id: int) -> dict | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_username(self, username: str) -> dict | None:
        username = (username or "").lstrip("@").lower()
        if not username:
            return None
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE lower(username) = %s LIMIT 1", (username,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def search_users(self, query: str, limit: int = 50) -> list[dict]:
        """Поиск игроков по ID, имени или username (для веб-админки)."""
        query = (query or "").strip().lstrip("@")
        with self._cursor() as cur:
            if not query:
                cur.execute(
                    "SELECT * FROM users ORDER BY balance DESC LIMIT %s", (limit,)
                )
                return [dict(r) for r in cur.fetchall()]
            if query.isdigit():
                cur.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (int(query),))
                row = cur.fetchone()
                return [dict(row)] if row else []
            cur.execute(
                """
                SELECT * FROM users
                WHERE lower(username) LIKE %s OR lower(first_name) LIKE %s
                ORDER BY balance DESC LIMIT %s
                """,
                (f"%{query.lower()}%", f"%{query.lower()}%", limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def is_user_blocked(self, user_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute("SELECT is_blocked FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return bool(row and row["is_blocked"])

    def set_blocked(self, user_id: int, blocked: bool) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET is_blocked = %s WHERE id = %s",
                (1 if blocked else 0, user_id),
            )

    def add_balance(self, user_id: int, amount: int, txn_type: str, description: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET balance = balance + %s, max_balance = GREATEST(COALESCE(max_balance, 0), balance + %s) WHERE id = %s",
                (amount, amount, user_id),
            )
            cur.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, %s, %s)",
                (user_id, amount, txn_type, description),
            )

    def add_rubies(self, user_id: int, amount: float) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET rubies = rubies + %s WHERE id = %s",
                (amount, user_id),
            )

    # ---------- Транзакции ----------

    def get_transactions(self, user_id: int, limit: int = 10) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM transactions WHERE user_id = %s ORDER BY id DESC LIMIT %s",
                (user_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    # ---------- Статистика ----------

    def _ensure_stats(self, cur, user_id: int) -> None:
        cur.execute(
            "INSERT INTO stats (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
            (user_id,),
        )

    def get_stats(self, user_id: int) -> dict:
        with self._cursor() as cur:
            self._ensure_stats(cur, user_id)
            cur.execute("SELECT * FROM stats WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else {
                "user_id": user_id,
                "total_games": 0,
                "wins": 0,
                "losses": 0,
                "total_bet": 0,
                "total_won": 0,
            }

    def update_stats(self, user_id: int, result: str, bet: int, win_amount: int) -> None:
        with self._cursor() as cur:
            self._ensure_stats(cur, user_id)
            if result == "win":
                cur.execute(
                    """
                    UPDATE stats
                    SET total_games = total_games + 1,
                        wins = wins + 1,
                        total_bet = total_bet + %s,
                        total_won = total_won + %s
                    WHERE user_id = %s
                    """,
                    (bet, win_amount, user_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE stats
                    SET total_games = total_games + 1,
                        losses = losses + 1,
                        total_bet = total_bet + %s
                    WHERE user_id = %s
                    """,
                    (bet, user_id),
                )

    # ---------- Игры ----------

    def add_game(self, user_id: int, game_type: str, bet: int, win_amount: int, result: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO games (user_id, game_type, bet, win_amount, result) VALUES (%s, %s, %s, %s, %s)",
                (user_id, game_type, bet, win_amount, result),
            )

    # ---------- Ежедневный бонус ----------

    def claim_daily(self, user_id: int, amount: int) -> bool:
        today = date.today().isoformat()
        with self._cursor() as cur:
            cur.execute("SELECT last_daily FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row is None or row["last_daily"] == today:
                return False
            cur.execute(
                "UPDATE users SET balance = balance + %s, last_daily = %s, daily_notified = 0, "
                "max_balance = GREATEST(COALESCE(max_balance, 0), balance + %s) WHERE id = %s",
                (amount, today, amount, user_id),
            )
            cur.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, %s, %s)",
                (user_id, amount, "daily", "Ежедневный бонус"),
            )
            return True

    def claim_weekly(self, user_id: int, amount: int) -> bool:
        week = current_week()
        with self._cursor() as cur:
            cur.execute("SELECT last_weekly FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row is None or row["last_weekly"] == week:
                return False
            cur.execute(
                "UPDATE users SET balance = balance + %s, last_weekly = %s, weekly_notified = 0, "
                "max_balance = GREATEST(COALESCE(max_balance, 0), balance + %s) WHERE id = %s",
                (amount, week, amount, user_id),
            )
            cur.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, %s, %s)",
                (user_id, amount, "weekly", "Еженедельный бонус"),
            )
            return True

    def get_daily_eligible(self) -> list[dict]:
        today = date.today().isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT id FROM users
                WHERE is_blocked = 0
                  AND last_daily IS NOT NULL
                  AND last_daily != %s
                  AND daily_notified = 0
                """,
                (today,),
            )
            return [dict(r) for r in cur.fetchall()]

    def get_weekly_eligible(self) -> list[dict]:
        week = current_week()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT id FROM users
                WHERE is_blocked = 0
                  AND last_weekly IS NOT NULL
                  AND last_weekly != %s
                  AND weekly_notified = 0
                """,
                (week,),
            )
            return [dict(r) for r in cur.fetchall()]

    def mark_daily_notified(self, user_id: int) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE users SET daily_notified = 1 WHERE id = %s", (user_id,))

    def mark_weekly_notified(self, user_id: int) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE users SET weekly_notified = 1 WHERE id = %s", (user_id,))

    # ---------- Рейтинг ----------

    def top_balance(self, limit: int = 10) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, username, first_name, balance FROM users ORDER BY balance DESC LIMIT %s",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def top_max_balance(self, limit: int = 10) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, username, first_name, max_balance FROM users ORDER BY max_balance DESC LIMIT %s",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def top_wins(self, limit: int = 10) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.username, u.first_name, u.balance, s.wins
                FROM users u JOIN stats s ON s.user_id = u.id
                ORDER BY s.wins DESC LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    # ---------- Админ ----------

    def admin_overview(self) -> dict:
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c, COALESCE(SUM(balance), 0) AS b FROM users"
            )
            users = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS c FROM games")
            games = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS c FROM games WHERE result = 'win'")
            wins = cur.fetchone()
            cur.execute(
                "SELECT COUNT(*) AS c, COALESCE(SUM(amount), 0) AS s FROM transactions"
            )
            tx = cur.fetchone()
            return {
                "users": users["c"],
                "balance": users["b"],
                "games": games["c"],
                "wins": wins["c"],
                "tx_count": tx["c"],
                "tx_volume": tx["s"],
            }

    # ---------- Настройки ----------

    def get_setting(self, key: str, default) -> str:
        with self._cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                (key, str(value)),
            )

    # ---------- Промокоды ----------

    def create_promo(self, code: str, amount: int, max_uses: int) -> bool:
        code = (code or "").strip().upper()
        if not code or amount <= 0 or max_uses < 1:
            return False
        with self._cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO promos (code, amount, max_uses) VALUES (%s, %s, %s)",
                    (code, amount, max_uses),
                )
            except psycopg2.errors.UniqueViolation:
                return False
        return True

    def get_promo(self, code: str) -> dict | None:
        code = (code or "").strip().upper()
        if not code:
            return None
        with self._cursor() as cur:
            cur.execute("SELECT * FROM promos WHERE code = %s", (code,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_promo_by_id(self, promo_id: int) -> dict | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM promos WHERE id = %s", (promo_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_promos(self) -> list[dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM promos ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    def delete_promo(self, promo_id: int) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM promo_claims WHERE promo_id = %s", (promo_id,))
            cur.execute("DELETE FROM promos WHERE id = %s", (promo_id,))

    def toggle_promo(self, promo_id: int, active: bool) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE promos SET is_active = %s WHERE id = %s",
                (1 if active else 0, promo_id),
            )

    def redeem_promo(self, user_id: int, code: str) -> tuple[str, int]:
        """Активирует промокод. Возвращает (статус, сумма).
        Статусы: ok, not_found, inactive, used_up, already."""
        promo = self.get_promo(code)
        if not promo:
            return ("not_found", 0)
        if not promo["is_active"]:
            return ("inactive", 0)
        if promo["used_count"] >= promo["max_uses"]:
            return ("used_up", 0)
        with self._cursor() as cur:
            cur.execute(
                "SELECT 1 FROM promo_claims WHERE promo_id = %s AND user_id = %s",
                (promo["id"], user_id),
            )
            if cur.fetchone():
                return ("already", 0)
            cur.execute(
                "INSERT INTO promo_claims (promo_id, user_id) VALUES (%s, %s)",
                (promo["id"], user_id),
            )
            cur.execute(
                "UPDATE promos SET used_count = used_count + 1 WHERE id = %s",
                (promo["id"],),
            )
            cur.execute(
                "UPDATE users SET balance = balance + %s, max_balance = GREATEST(COALESCE(max_balance, 0), balance + %s) WHERE id = %s",
                (promo["amount"], promo["amount"], user_id),
            )
            cur.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, %s, %s)",
                (user_id, promo["amount"], "promo", f"Промокод {promo['code']}"),
            )
        return ("ok", promo["amount"])

    def reset_database(self) -> None:
        """Полный сброс: всем баланс на стартовый, обнуление статистики и истории."""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET balance = %s, max_balance = %s, "
                "last_daily = NULL, last_weekly = NULL, "
                "daily_notified = 0, weekly_notified = 0",
                (STARTING_BALANCE, STARTING_BALANCE),
            )
            cur.execute(
                "UPDATE stats SET total_games = 0, wins = 0, losses = 0, "
                "total_bet = 0, total_won = 0"
            )
            cur.execute("DELETE FROM transactions")
            cur.execute("DELETE FROM games")
            cur.execute("DELETE FROM promo_claims")
            cur.execute("UPDATE promos SET used_count = 0")


db = PostgresDatabase() if DATABASE_URL else Database()