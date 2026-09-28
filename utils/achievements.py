"""Определения достижений и проверка условий.

Каждое достижение: id -> {name, desc, icon, check(user, stats, extra)}.
check получает user dict, stats dict и extra dict (purchases, xp, level).
"""

from database import db, _calc_level


def _xp(user):
    return user.get("xp", 0) or 0


ACHIEVEMENTS = {
    "first_game": {
        "name": "Первые шаги",
        "desc": "Сыграть первую игру",
        "icon": "🎮",
        "check": lambda u, s, e: (s.get("total_games", 0) or 0) >= 1,
    },
    "first_win": {
        "name": "Первая кровь",
        "desc": "Одержать первую победу",
        "icon": "🏆",
        "check": lambda u, s, e: (s.get("wins", 0) or 0) >= 1,
    },
    "grinder_10": {
        "name": "Разогрев",
        "desc": "Сыграть 10 игр",
        "icon": "🎲",
        "check": lambda u, s, e: (s.get("total_games", 0) or 0) >= 10,
    },
    "grinder_100": {
        "name": "Марафонец",
        "desc": "Сыграть 100 игр",
        "icon": "💯",
        "check": lambda u, s, e: (s.get("total_games", 0) or 0) >= 100,
    },
    "winner_10": {
        "name": "Победитель",
        "desc": "Одержать 10 побед",
        "icon": "🥇",
        "check": lambda u, s, e: (s.get("wins", 0) or 0) >= 10,
    },
    "winner_50": {
        "name": "Чемпион",
        "desc": "Одержать 50 побед",
        "icon": "👑",
        "check": lambda u, s, e: (s.get("wins", 0) or 0) >= 50,
    },
    "turnover_100k": {
        "name": "Оборот",
        "desc": "Поставить суммарно 100 000 TON",
        "icon": "💰",
        "check": lambda u, s, e: (s.get("total_bet", 0) or 0) >= 100_000,
    },
    "turnover_1m": {
        "name": "Магнат",
        "desc": "Поставить суммарно 1 000 000 TON",
        "icon": "💎",
        "check": lambda u, s, e: (s.get("total_bet", 0) or 0) >= 1_000_000,
    },
    "rich_100k": {
        "name": "Богач",
        "desc": "Накопить баланс 100 000 TON",
        "icon": "💵",
        "check": lambda u, s, e: (u.get("balance", 0) or 0) >= 100_000,
    },
    "referrer": {
        "name": "Вербовщик",
        "desc": "Пригласить первого друга",
        "icon": "👥",
        "check": lambda u, s, e: (u.get("referral_count", 0) or 0) >= 1,
    },
    "magnet": {
        "name": "Магнит",
        "desc": "Пригласить 5 друзей",
        "icon": "🧲",
        "check": lambda u, s, e: (u.get("referral_count", 0) or 0) >= 5,
    },
    "level_5": {
        "name": "Растущий",
        "desc": "Достичь 5 уровня",
        "icon": "⭐",
        "check": lambda u, s, e: _calc_level(_xp(u)) >= 5,
    },
    "bonus_hunter": {
        "name": "Охотник за бонусами",
        "desc": "Забрать ежедневный бонус",
        "icon": "🎁",
        "check": lambda u, s, e: bool(u.get("last_daily")),
    },
    "shopper": {
        "name": "Стиляга",
        "desc": "Купить первый предмет в магазине",
        "icon": "🛒",
        "check": lambda u, s, e: len(e.get("purchases", [])) > 0,
    },
}

TOTAL = len(ACHIEVEMENTS)


def check_achievements(user_id: int) -> list[dict]:
    """Проверяет все ачивки, выдаёт новые. Возвращает список defs новых."""
    user = db.get_user(user_id)
    if not user:
        return []
    stats = db.get_stats(user_id)
    owned = set(db.get_achievements(user_id))
    try:
        purchases = db.get_purchases(user_id)
    except Exception:
        purchases = []
    extra = {"purchases": purchases}
    new = []
    for aid, adef in ACHIEVEMENTS.items():
        if aid in owned:
            continue
        try:
            if adef["check"](user, stats, extra):
                if db.grant_achievement(user_id, aid):
                    new.append({"id": aid, **adef})
        except Exception:
            continue
    return new


def achievements_text(user_id: int) -> str:
    """Текст списка достижений для /achievements."""
    import html
    owned = set(db.get_achievements(user_id))
    lines = [f"🏅 <b>Достижения</b> — {len(owned)}/{TOTAL}\n"]
    for aid, adef in ACHIEVEMENTS.items():
        mark = "✅" if aid in owned else "⬜"
        lines.append(f"{mark} {adef['icon']} <b>{adef['name']}</b> — {adef['desc']}")
    return "\n".join(lines)
