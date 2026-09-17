"""Генератор профиль-карточки с помощью Pillow."""
import io
import os
from PIL import Image, ImageDraw, ImageFont

CARD_W, CARD_H = 600, 400
BG_COLOR = (18, 18, 30)
ACCENT = (120, 80, 255)
GOLD = (255, 200, 50)
WHITE = (255, 255, 255)
GRAY = (140, 140, 160)
DARK_BG = (24, 24, 42)

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf"):
        path = os.path.join(FONT_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


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

    _draw_rounded_rect(draw, (0, 0, CARD_W - 1, CARD_H - 1), radius=24, fill=DARK_BG)

    _draw_rounded_rect(draw, (20, 20, CARD_W - 20, 120), radius=16, fill=ACCENT)

    font_lg = _get_font(28)
    font_md = _get_font(20)
    font_sm = _get_font(16)

    draw.text((40, 40), f"👤 {name}", fill=WHITE, font=font_lg)
    draw.text((40, 78), f"ID: {user_id}", fill=(200, 200, 255), font=font_sm)

    y = 140

    draw.text((40, y), "💳 Баланс", fill=GRAY, font=font_sm)
    draw.text((40, y + 20), f"{balance:,} TON".replace(",", " "), fill=GOLD, font=font_lg)

    draw.text((320, y), "💎 Рубины", fill=GRAY, font=font_sm)
    draw.text((320, y + 20), f"{rubies}", fill=(255, 100, 150), font=font_lg)

    y += 70
    _draw_rounded_rect(draw, (30, y, CARD_W - 30, y + 1), radius=0, fill=(50, 50, 70))

    y += 15
    draw.text((40, y), "📊 Статистика", fill=ACCENT, font=font_md)
    y += 30

    stats_left = [
        f"🎮 Игр: {total_games}",
        f"✅ Побед: {wins}",
        f"❌ Поражений: {losses}",
    ]
    winrate = round(wins * 100 / total_games, 1) if total_games else 0
    stats_right = [
        f"🎯 Винрейт: {winrate}%",
        f"💸 Ставки: {total_bet:,}".replace(",", " "),
        f"🏆 Выигрыши: {total_won:,}".replace(",", " "),
    ]

    for i, (left, right) in enumerate(zip(stats_left, stats_right)):
        draw.text((40, y + i * 28), left, fill=WHITE, font=font_sm)
        draw.text((320, y + i * 28), right, fill=WHITE, font=font_sm)

    if ref_count > 0:
        y += 90
        _draw_rounded_rect(draw, (30, y, CARD_W - 30, y + 1), radius=0, fill=(50, 50, 70))
        y += 10
        draw.text((40, y), f"👥 Рефералы: {ref_count}", fill=(100, 200, 255), font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
