"""Генератор профиль-карточки в стиле TON Casino."""
import io
import os
from PIL import Image, ImageDraw, ImageFont

SCALE = 2
W, H = 580 * SCALE, 720 * SCALE

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

BG = (14, 10, 28)
CARD_BG = (20, 16, 38)
SECTION_BG = (26, 22, 48)
BORDER = (100, 60, 220)
GLOW = (130, 80, 255)
WHITE = (240, 240, 255)
GRAY = (150, 140, 180)
GOLD = (255, 210, 60)
PINK = (255, 100, 180)
CYAN = (100, 200, 255)
PURPLE = (160, 100, 255)
GREEN = (80, 220, 120)
RED = (255, 80, 80)

_NOTO = os.path.join(FONT_DIR, "noto_cjk.otf")
_ARIAL_BD = os.path.join(FONT_DIR, "arialbd.ttf")
_ARIAL = os.path.join(FONT_DIR, "arial.ttf")


def _font(size: int, bold=True) -> ImageFont.FreeTypeFont:
    if os.path.exists(_NOTO):
        return ImageFont.truetype(_NOTO, size * SCALE)
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = os.path.join(FONT_DIR, name)
    if os.path.exists(path):
        return ImageFont.truetype(path, size * SCALE)
    return ImageFont.load_default()


def _glow_rect(img, xy, radius, color, glow_radius=8):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = xy
    for i in range(glow_radius, 0, -1):
        alpha = int(60 * (1 - i / glow_radius))
        c = color + (alpha,)
        d.rounded_rectangle(
            [x0 - i, y0 - i, x1 + i, y1 + i],
            radius=radius + i,
            fill=c,
        )
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def _circle_glow(img, cx, cy, r, color, glow_radius=12):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(glow_radius, 0, -1):
        alpha = int(50 * (1 - i / glow_radius))
        c = color + (alpha,)
        d.ellipse([cx - r - i, cy - r - i, cx + r + i, cy + r + i], fill=c)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def _dot(draw, x, y, r, color):
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _clip_circle(img, cx, cy, r):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    result = Image.new("RGBA", img.size, (0, 0, 0, 0))
    result.paste(img.convert("RGBA"), mask=mask)
    return result


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
    avatar_bytes: bytes | None = None,
) -> io.BytesIO:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    _glow_rect(img, (18 * SCALE, 18 * SCALE, W - 18 * SCALE, H - 18 * SCALE), 28, GLOW, 14)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        (20 * SCALE, 20 * SCALE, W - 20 * SCALE, H - 20 * SCALE),
        radius=26 * SCALE, fill=CARD_BG, outline=BORDER, width=2 * SCALE,
    )

    avatar_cx, avatar_cy = 120 * SCALE, 140 * SCALE
    avatar_r = 60 * SCALE

    avatar_drawn = False
    if avatar_bytes:
        try:
            av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            av = av.resize((avatar_r * 2, avatar_r * 2), Image.LANCZOS)
            circle_mask = Image.new("L", av.size, 0)
            ImageDraw.Draw(circle_mask).ellipse([0, 0, av.size[0], av.size[1]], fill=255)
            avatar_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            avatar_layer.paste(av, (avatar_cx - avatar_r, avatar_cy - avatar_r), circle_mask)
            img = Image.alpha_composite(img.convert("RGBA"), avatar_layer).convert("RGB")
            draw = ImageDraw.Draw(img)
            draw.ellipse(
                [avatar_cx - avatar_r - 2, avatar_cy - avatar_r - 2,
                 avatar_cx + avatar_r + 2, avatar_cy + avatar_r + 2],
                outline=PURPLE, width=3 * SCALE,
            )
            avatar_drawn = True
        except Exception:
            pass

    if not avatar_drawn:
        _circle_glow(img, avatar_cx, avatar_cy, avatar_r, GLOW, 16)
        draw = ImageDraw.Draw(img)
        draw.ellipse(
            [avatar_cx - avatar_r, avatar_cy - avatar_r,
             avatar_cx + avatar_r, avatar_cy + avatar_r],
            fill=(30, 24, 55), outline=PURPLE, width=3 * SCALE,
        )
        f_avatar = _font(40)
        initials = name[:1].upper()
        bbox = draw.textbbox((0, 0), initials, font=f_avatar)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((avatar_cx - tw // 2, avatar_cy - th // 2 - 4 * SCALE), initials, fill=PURPLE, font=f_avatar)

    f_name = _font(28)
    f_id = _font(14, bold=False)
    f_lg = _font(26)
    f_md = _font(18)
    f_sm = _font(14, bold=False)
    f_xs = _font(12, bold=False)

    name_x = 210 * SCALE
    draw.text((name_x, 100 * SCALE), name, fill=WHITE, font=f_name)
    draw.text((name_x, 138 * SCALE), f"ID: {user_id}", fill=GRAY, font=f_id)

    ton_x = W - 180 * SCALE
    f_ton = _font(36, bold=True)
    draw.text((ton_x, 80 * SCALE), "TON", fill=PURPLE, font=f_ton)
    f_play = _font(10, bold=False)
    draw.text((ton_x + 10 * SCALE, 122 * SCALE), "PLAY  EARN  WIN", fill=GRAY, font=f_play)

    sy = 220 * SCALE
    draw.rounded_rectangle(
        (40 * SCALE, sy, W - 40 * SCALE, sy + 100 * SCALE),
        radius=14 * SCALE, fill=SECTION_BG, outline=BORDER, width=1 * SCALE,
    )

    draw.text((60 * SCALE, sy + 12 * SCALE), "Баланс", fill=GRAY, font=f_sm)
    _dot(draw, 60 * SCALE, sy + 50 * SCALE, 6 * SCALE, GOLD)
    draw.text((78 * SCALE, sy + 38 * SCALE), f"{balance:,}".replace(",", " "), fill=GOLD, font=f_lg)
    draw.text((78 * SCALE, sy + 72 * SCALE), "TON", fill=GOLD, font=f_sm)

    mid = W // 2
    draw.line([(mid, sy + 15 * SCALE), (mid, sy + 85 * SCALE)], fill=BORDER, width=1 * SCALE)

    draw.text((mid + 20 * SCALE, sy + 12 * SCALE), "Рубины", fill=GRAY, font=f_sm)
    _dot(draw, mid + 20 * SCALE, sy + 50 * SCALE, 6 * SCALE, PINK)
    draw.text((mid + 38 * SCALE, sy + 38 * SCALE), f"{rubies}", fill=PINK, font=f_lg)
    draw.text((mid + 38 * SCALE, sy + 72 * SCALE), "GEMS", fill=PINK, font=f_sm)

    sy2 = sy + 120 * SCALE
    draw.rounded_rectangle(
        (40 * SCALE, sy2, W - 40 * SCALE, sy2 + 220 * SCALE),
        radius=14 * SCALE, fill=SECTION_BG, outline=BORDER, width=1 * SCALE,
    )

    draw.text((60 * SCALE, sy2 + 14 * SCALE), "Статистика", fill=PURPLE, font=f_md)
    draw.line([(60 * SCALE, sy2 + 44 * SCALE), (W - 60 * SCALE, sy2 + 44 * SCALE)], fill=(50, 40, 80), width=1)

    winrate = round(wins * 100 / total_games, 1) if total_games else 0

    left_items = [
        (f"Игр: {total_games}", GRAY),
        (f"Побед: {wins}", GREEN if wins else GRAY),
        (f"Поражений: {losses}", RED if losses else GRAY),
    ]
    right_items = [
        (f"Винрейт: {winrate}%", PURPLE),
        (f"Ставки: {total_bet:,}".replace(",", " "), GRAY),
        (f"Выигрыш: {total_won:,}".replace(",", " "), GOLD),
    ]

    for i, ((lt, lc), (rt, rc)) in enumerate(zip(left_items, right_items)):
        ly = sy2 + 56 * SCALE + i * 30 * SCALE
        ry = ly
        draw.text((60 * SCALE, ly), lt, fill=lc, font=f_sm)
        draw.text((mid + 20 * SCALE, ry), rt, fill=rc, font=f_sm)

    if ref_count > 0:
        draw.text((60 * SCALE, sy2 + 150 * SCALE), f"Рефералы: {ref_count}", fill=CYAN, font=f_sm)

    footer_y = H - 60 * SCALE
    draw.text(
        (W // 2 - 100 * SCALE, footer_y),
        "TON  •  ИГРАЙ  •  ЗАРАБАТЫВАЙ",
        fill=(80, 70, 120), font=f_xs,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    return buf
