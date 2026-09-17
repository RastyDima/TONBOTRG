"""Монетка — орёл/решка, ×2."""
import hashlib
import hmac
import random
import time


class CoinFlipGame:
    def __init__(self, user_id: int, bet: int):
        self.user_id = user_id
        self.bet = bet
        self.choice: str | None = None
        self.result: str | None = None
        self.won = False
        self.payout = 0
        self.seed = hmac.new(
            b"coinflip", f"{user_id}:{time.time()}:{random.random()}".encode(),
            hashlib.sha256,
        ).hexdigest()[:16]

    def flip(self, choice: str) -> str:
        self.choice = choice
        self.result = random.choice(["орёл", "решка"])
        self.won = self.result == choice
        self.payout = self.bet * 2 if self.won else 0
        return self.result

    @property
    def is_over(self) -> bool:
        return self.result is not None

    @property
    def multiplier(self) -> float:
        return 2.0 if self.won else 0
