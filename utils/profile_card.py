"""Генератор профиль-карточки с помощью Pillow (без эмодзи)."""
import io
import os
from PIL import Image, ImageDraw, ImageFont

SCALE = 2
CARD_W, CARD_H = 600 * SCALE, 420 * SCALE
BG_COLOR = (18, 18, 30)
ACCENT = (120, 80, 255)
GOLD = (255, 200, 50)
WHITE = (255, 255, 255)
GRAY = (140, 140, 160)
DARK_BG = (24, 24, 42)
PINK = (255, 100, 150)
CYAN = (100, 200, 255)
GREEN = (80, 220, 120)
RED = (255, 80, 80)

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf", "arial.ttf"):
        path = os.path.join(FONT_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size * SCALE)
    return ImageFont.load_default()


def _rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius * SCALE, fill=fill)


def _dot(draw, x, y, r, color):
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _label(draw, x, y, text, color, font):
    draw.text((x * SCALE, y * SCALE), text, fill=color, font=font)


def generate_profile_card(
    user_id: int,
    name: str,
    balance: int,
    rubies: float,
    total_games: int,
    wins: int,
    losses: int,
    total_bet: int,
    total_won: int,
    ref_count: int = 0,
    frame: str | None = None,
) -> io.BytesIO:
    img = Image.new("RGB", (CARD_W, CARD_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    _rounded_rect(draw, (0, 0, CARD_W - 1, CARD_H - 1), 24, DARK_BG)

    _rounded_rect(draw, (20 * SCALE, 20 * SCALE, CARD_W - 20 * SCALE, 100 * SCALE), 16, ACCENT)

    f_lg = _font(24)
    f_md = _font(18)
    f_sm = _font(14)

    _label(draw, 36, 36, name, WHITE, f_lg)
    _label(draw, 36, 68, f"ID: {user_id}", (200, 200, 255), f_sm)

    y = 115

    _dot(draw, 40 * SCALE, (y + 4) * SCALE, 5 * SCALE, GOLD)
    _label(draw, 52, y, "TON", GRAY, f_sm)
    _label(draw, 52, y + 20, f"{balance:,}".replace(",", " "), GOLD, f_lg)

    _dot(draw, 320 * SCALE, (y + 4) * SCALE, 5 * SCALE, PINK)
    _label(draw, 332, y, "Rubies", GRAY, f_sm)
    _label(draw, 332, y + 20, f"{rubies}", PINK, f_lg)

    y += 70
    _rounded_rect(draw, (30 * SCALE, y * SCALE, (CARD_W // SCALE - 30) * SCALE, (y + 1) * SCALE), 0, (50, 50, 70))

    y += 12
    _label(draw, 36, y, "STATS", ACCENT, f_md)
    y += 30

    winrate = round(wins * 100 / total_games, 1) if total_games else 0

    rows = [
        (f"Games: {total_games}", f"Winrate: {winrate}%"),
        (f"Wins: {wins}", f"Bets: {total_bet:,}".replace(",", " ")),
        (f"Losses: {losses}", f"Won: {total_won:,}".replace(",", " ")),
    ]

    for i, (left, right) in enumerate(rows):
        _label(draw, 40, y + i * 26, left, WHITE, f_sm)
        _label(draw, 320, y + i * 26, right, WHITE, f_sm)

    if ref_count > 0:
        y += 85
        _rounded_rect(draw, (30 * SCALE, y * SCALE, (CARD_W // SCALE - 30) * SCALE, (y + 1) * SCALE), 0, (50, 50, 70))
        y += 10
        _dot(draw, 40 * SCALE, (y + 4) * SCALE, 5 * SCALE, CYAN)
        _label(draw, 52, y, f"Referrals: {ref_count}", CYAN, f_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
