import html

from config import DAILY_BONUS, MAX_BET, MIN_BET, WEEKLY_BONUS
from database import db


def get_daily_bonus() -> int:
    try:
        return int(db.get_setting("daily_bonus", str(DAILY_BONUS)))
    except (TypeError, ValueError):
        return DAILY_BONUS


def get_weekly_bonus() -> int:
    try:
        return int(db.get_setting("weekly_bonus", str(WEEKLY_BONUS)))
    except (TypeError, ValueError):
        return WEEKLY_BONUS


def format_number(n: int) -> str:
    return f"{int(n):,}".replace(",", " ")


def parse_bet(text, max_bet=MAX_BET):
    """Парсит ставку из текста: '30000', '30k', '30к', '3.5m'. Вернёт None, если вне лимитов."""
    text = (text or "").strip().replace(" ", "").replace(",", ".").lower()
    if not text:
        return None
    text = text.replace("к", "k").replace("м", "m")
    mult = 1
    if text.endswith("k"):
        mult = 1000
        text = text[:-1]
    elif text.endswith("m"):
        mult = 1_000_000
        text = text[:-1]
    try:
        value = int(float(text) * mult)
    except ValueError:
        return None
    if value < MIN_BET or value > max_bet:
        return None
    return value


def quick_command(text, commands, max_bet=MAX_BET):
    """Разбирает быструю команду: ('м', '30000'), ('дж', None) и т.п.
    Возвращает dict {'bet': int|None}, если текст является командой из commands."""
    t = (text or "").strip().lower()
    if not t:
        return None
    words = t.split()
    if len(words) == 1:
        word = words[0]
        if word in commands:
            return {"bet": None}
        for cmd in commands:
            if word.startswith(cmd):
                bet = parse_bet(word[len(cmd):], max_bet)
                if bet is not None:
                    return {"bet": bet}
        return None
    if len(words) == 2:
        cmd, amount = words
        if cmd in commands:
            bet = parse_bet(amount, max_bet)
            if bet is not None:
                return {"bet": bet}
    return None


TX_LABELS = {
    "daily": "🎁 Ежедневный бонус",
    "weekly": "🗓 Еженедельный бонус",
    "admin": "⚙️ Выдача администратором",
    "game_bet": "🎰 Ставка",
    "game_win": "🏆 Выигрыш",
    "bonus": "🎉 Приветственный бонус",
    "transfer_out": "💸 Перевод отправлен",
    "transfer_in": "💸 Перевод получен",
    "promo": "🎟 Промокод",
}


def menu_text(user: dict) -> str:
    return (
        f"🎰 <b>Казино-бот</b>\n\n"
        f"👤 {html.escape(str(user['first_name'] or 'Игрок'))}\n"
        f"💳 Баланс: <b>{format_number(user['balance'])}</b> монет\n\n"
        f"Выберите действие:"
    )


def balance_text(user: dict) -> str:
    return (
        f"💰 <b>Баланс</b>\n\n"
        f"💳 {format_number(user['balance'])} монет\n\n"
        f"💸 Перевести: ответьте на сообщение игрока — <code>п 12000</code>\n"
        f"📲 Быстрый запрос: просто напишите <code>б</code> в чате"
    )


def profile_text(user: dict, stats: dict) -> str:
    total = stats["total_games"]
    winrate = round(stats["wins"] * 100 / total, 1) if total else 0
    return (
        f"👤 <b>Профиль</b>\n"
        f"🆔 ID: <code>{user['id']}</code>\n"
        f"👤 Имя: {html.escape(str(user['first_name'] or 'Игрок'))}\n"
        f"💳 Баланс: <b>{format_number(user['balance'])}</b> монет\n\n"
        f"📊 <b>Общая статистика</b>\n"
        f"🎮 Игр сыграно: {total}\n"
        f"✅ Побед: {stats['wins']}\n"
        f"❌ Поражений: {stats['losses']}\n"
        f"🎯 Процент побед: {winrate}%\n"
        f"💸 Всего поставлено: {format_number(stats['total_bet'])}\n"
        f"🏆 Всего выиграно: {format_number(stats['total_won'])}"
    )


def history_text(transactions: list) -> str:
    if not transactions:
        return "📜 <b>История транзакций</b>\n\nПока нет записей."
    lines = ["📜 <b>История транзакций</b>\n"]
    for t in transactions:
        sign = "+" if t["amount"] > 0 else ""
        lines.append(f"{sign}{format_number(t['amount'])} · {TX_LABELS.get(t['type'], t['type'])}")
        lines.append(f"     <i>{t['created_at']}</i>")
    return "\n".join(lines)


def rating_text(top: list, mode: str = "balance") -> str:
    if mode == "balance":
        title = "💰 Максимальный баланс"
    else:
        title = "🎯 По победам"
    lines = [f"🏆 <b>Рейтинг</b> — {title}\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top, 1):
        name = html.escape(str(u["first_name"] or u["username"] or f"Игрок {u['id']}"))
        medal = medals[i - 1] if i <= 3 else f"{i}."
        stat = f"{format_number(u['max_balance'])} 💰" if mode == "balance" else f"{u['wins']} 🏆"
        lines.append(f"{medal} {name} — {stat}")
    if not top:
        lines.append("Пока нет данных.")
    return "\n".join(lines)