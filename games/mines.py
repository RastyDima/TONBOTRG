import random
from math import comb

from database import db

FIELD_SIZE = 25
ROWS = 5
COLS = 5
MIN_MINES = 1
MAX_MINES = 10


def get_house_edge() -> float:
    try:
        return float(db.get_setting("mines_house_edge", 0.97))
    except (TypeError, ValueError):
        return 0.97


class MinesGame:
    """Игра «Мины»: поле 5×5, меняющаяся вероятность и множитель."""

    def __init__(self, user_id: int, bet: int, mines: int):
        if not MIN_MINES <= mines <= MAX_MINES:
            raise ValueError("Некорректное количество мин")
        self.type = "mines"
        self.user_id = user_id
        self.bet = bet
        self.mines = mines
        self.mine_positions = set(random.sample(range(FIELD_SIZE), mines))
        self.revealed = set()
        self.lost = False
        self.cashed_out = False

    @property
    def is_over(self) -> bool:
        return self.lost or self.cashed_out

    @property
    def safe_revealed(self) -> int:
        return len(self.revealed)

    @property
    def safe_total(self) -> int:
        return FIELD_SIZE - self.mines

    @property
    def multiplier(self) -> float:
        k = self.safe_revealed
        if k == 0:
            return 1.0
        p = comb(FIELD_SIZE - k, self.mines) / comb(FIELD_SIZE, self.mines)
        return round(get_house_edge() / p, 2)

    @property
    def payout(self) -> int:
        return int(self.bet * self.multiplier)