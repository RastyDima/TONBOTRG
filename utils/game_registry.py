from database import db

GAME_LABELS = {"mines": "Мины", "joker": "Джокер", "alchemist": "Алхимик"}


class GameRegistry:
    """Хранит активные игры, не позволяя пользователю играть в две сразу."""

    def __init__(self):
        self._active = {}

    def register(self, user_id: int, game_type: str, game) -> bool:
        if user_id in self._active:
            return False
        self._active[user_id] = {"type": game_type, "game": game}
        return True

    def release(self, user_id: int) -> None:
        self._active.pop(user_id, None)

    def is_active(self, user_id: int) -> bool:
        return user_id in self._active

    def get(self, user_id: int) -> dict | None:
        return self._active.get(user_id)

    def game(self, user_id: int):
        entry = self._active.get(user_id)
        return entry["game"] if entry else None


registry = GameRegistry()

# Ставки, которые пользователь задал текстовой командой («м 30000»),
# чтобы они подхватились при выборе количества мин / уровня риска.
_pending_bets: dict[int, int] = {}


def set_pending_bet(user_id: int, bet: int) -> None:
    _pending_bets[user_id] = bet


def get_pending_bet(user_id: int):
    return _pending_bets.pop(user_id, None)


def clear_pending_bet(user_id: int) -> None:
    _pending_bets.pop(user_id, None)


def cashout_game(user_id: int):
    """Забирает выигрыш: начисляет payout, фиксирует победу в БД и статистике."""
    entry = registry.get(user_id)
    if not entry:
        return None
    game = entry["game"]
    if game.is_over:
        return None
    game.cashed_out = True
    payout = game.payout
    label = GAME_LABELS.get(entry["type"], entry["type"])
    db.add_balance(user_id, payout, "game_win", f"Выигрыш в игре {label}")
    registry.release(user_id)
    db.add_game(user_id, entry["type"], game.bet, payout, "win")
    db.update_stats(user_id, "win", game.bet, payout)
    return game, payout


def lose_game(user_id: int):
    """Завершает игру поражением: ставка сгорает, фиксирует проигрыш."""
    entry = registry.get(user_id)
    if not entry:
        return None
    game = entry["game"]
    if game.is_over:
        return None
    game.lost = True
    registry.release(user_id)
    db.add_game(user_id, entry["type"], game.bet, 0, "lose")
    db.update_stats(user_id, "lose", game.bet, 0)
    return game


def cancel_game(user_id: int):
    """Отменяет игру: ставка возвращается на баланс."""
    entry = registry.get(user_id)
    if not entry:
        return None
    game = entry["game"]
    registry.release(user_id)
    db.add_balance(user_id, game.bet, "game_bet", "Возврат ставки")
    db.add_game(user_id, entry["type"], game.bet, game.bet, "cancel")
    return game