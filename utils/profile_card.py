"""Генератор профиль-карточки в стиле TON Casino — v2 premium."""
import io
import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SCALE = 2
W, H = 580 * SCALE, 780 * SCALE

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

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


def _lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _gradient_v(img, xy, c1, c2):
    x0, y0, x1, y1 = xy
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0)
        color = _lerp_color(c1, c2, t)
        ImageDraw.Draw(img).line([(x0, y), (x1, y)], fill=color)


def _gradient_h(img, xy, c1, c2):
    x0, y0, x1, y1 = xy
    for x in range(x0, x1):
        t = (x - x0) / max(1, x1 - x0)
        color = _lerp_color(c1, c2, t)
        ImageDraw.Draw(img).line([(x, y0), (x, y1)], fill=color)


def _glow_rect(img, xy, radius, color, glow_radius=10):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = xy
    for i in range(glow_radius, 0, -1):
        alpha = int(70 * (1 - i / glow_radius))
        c = color + (alpha,)
        d.rounded_rectangle([x0 - i, y0 - i, x1 + i, y1 + i], radius=radius + i, fill=c)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def _circle_glow(img, cx, cy, r, color, glow_radius=16):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(glow_radius, 0, -1):
        alpha = int(60 * (1 - i / glow_radius))
        c = color + (alpha,)
        d.ellipse([cx - r - i, cy - r - i, cx + r + i, cy + r + i], fill=c)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def _dot(draw, x, y, r, color):
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _ring(draw, cx, cy, r, color, width=2):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=width)


def _progress_bar(draw, x, y, w, h, pct, bg_color, fill_color1, fill_color2, radius=6):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=bg_color)
    if pct > 0:
        fw = max(h, int(w * min(pct, 100) / 100))
        _gradient_h(Image.new("RGB", (1, 1)), (0, 0, 1, 1), fill_color1, fill_color2)
        draw.rounded_rectangle([x, y, x + fw, y + h], radius=radius, fill=fill_color1)


def _decorative_dots(draw, cx, y_start, count=5, spacing=8, color=(60, 50, 100)):
    for i in range(count):
        dx = (i - count // 2) * spacing * SCALE
        _dot(draw, cx + dx, y_start, 2 * SCALE, color)


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
    # ── Colors ──
    BG_TOP = (12, 8, 24)
    BG_BOT = (18, 12, 35)
    CARD_BG = (20, 16, 40)
    SECTION_BG = (24, 20, 48)
    BORDER_DIM = (60, 40, 140)
    BORDER = (90, 55, 200)
    GLOW = (120, 70, 255)
    WHITE = (240, 240, 255)
    GRAY = (140, 130, 175)
    GOLD = (255, 210, 60)
    GOLD2 = (255, 180, 30)
    PINK = (255, 90, 170)
    PINK2 = (220, 60, 255)
    CYAN = (80, 200, 255)
    PURPLE = (150, 90, 255)
    PURPLE2 = (180, 120, 255)
    GREEN = (60, 220, 130)
    RED = (255, 70, 90)
    NEON_LINE = (80, 50, 180)

    # ── Background gradient ──
    img = Image.new("RGB", (W, H), BG_TOP)
    _gradient_v(img, (0, 0, W, H), BG_TOP, BG_BOT)

    # ── Ambient glow spots ──
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    for gx, gy, gr, gc in [
        (W * 0.2, H * 0.15, 180, (60, 20, 140)),
        (W * 0.8, H * 0.1, 120, (40, 15, 120)),
        (W * 0.5, H * 0.85, 150, (50, 10, 130)),
    ]:
        for i in range(int(gr), 0, -2):
            alpha = int(25 * (1 - i / gr))
            gd.ellipse([gx - i, gy - i, gx + i, gy + i], fill=gc + (alpha,))
    img = Image.alpha_composite(img.convert("RGBA"), glow_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Main card ──
    _glow_rect(img, (16 * SCALE, 16 * SCALE, W - 16 * SCALE, H - 16 * SCALE), 30, GLOW, 16)
    draw = ImageDraw.Draw(img)

    card_rect = (20 * SCALE, 20 * SCALE, W - 20 * SCALE, H - 20 * SCALE)
    draw.rounded_rectangle(card_rect, radius=28 * SCALE, fill=CARD_BG, outline=BORDER, width=2 * SCALE)

    # ── Top decorative line ──
    line_y = 36 * SCALE
    draw.line([(60 * SCALE, line_y), (W - 60 * SCALE, line_y)], fill=NEON_LINE, width=1)
    _dot(draw, 60 * SCALE, line_y, 3 * SCALE, PURPLE)
    _dot(draw, W - 60 * SCALE, line_y, 3 * SCALE, PURPLE)

    # ── Avatar ──
    avatar_cx, avatar_cy = 130 * SCALE, 140 * SCALE
    avatar_r = 64 * SCALE

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
            # Gradient ring effect — outer glow + inner ring
            _circle_glow(img, avatar_cx, avatar_cy, avatar_r, GLOW, 20)
            draw = ImageDraw.Draw(img)
            draw.ellipse(
                [avatar_cx - avatar_r - 3 * SCALE, avatar_cy - avatar_r - 3 * SCALE,
                 avatar_cx + avatar_r + 3 * SCALE, avatar_cy + avatar_r + 3 * SCALE],
                outline=PURPLE2, width=3 * SCALE,
            )
            draw.ellipse(
                [avatar_cx - avatar_r - 1 * SCALE, avatar_cy - avatar_r - 1 * SCALE,
                 avatar_cx + avatar_r + 1 * SCALE, avatar_cy + avatar_r + 1 * SCALE],
                outline=(180, 140, 255), width=1 * SCALE,
            )
            avatar_drawn = True
        except Exception:
            pass

    if not avatar_drawn:
        _circle_glow(img, avatar_cx, avatar_cy, avatar_r, GLOW, 20)
        draw = ImageDraw.Draw(img)
        draw.ellipse(
            [avatar_cx - avatar_r, avatar_cy - avatar_r,
             avatar_cx + avatar_r, avatar_cy + avatar_r],
            fill=(28, 22, 52), outline=PURPLE, width=3 * SCALE,
        )
        f_avatar = _font(44)
        initials = name[:1].upper()
        bbox = draw.textbbox((0, 0), initials, font=f_avatar)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (avatar_cx - tw // 2, avatar_cy - th // 2 - 4 * SCALE),
            initials, fill=PURPLE2, font=f_avatar,
        )

    # ── Name + ID ──
    f_name = _font(30)
    f_id = _font(13, bold=False)
    name_x = 220 * SCALE
    draw.text((name_x, 90 * SCALE), name, fill=WHITE, font=f_name)
    draw.text((name_x, 128 * SCALE), f"ID: {user_id}", fill=GRAY, font=f_id)

    # ── TON badge ──
    ton_x = W - 180 * SCALE
    f_ton = _font(38, bold=True)
    draw.text((ton_x, 78 * SCALE), "TON", fill=PURPLE2, font=f_ton)
    f_sub = _font(10, bold=False)
    draw.text((ton_x + 8 * SCALE, 120 * SCALE), "PLAY  EARN  WIN", fill=GRAY, font=f_sub)

    # ── Decorative dots under header ──
    _decorative_dots(draw, W // 2, 195 * SCALE, 7, 10, (50, 35, 100))

    # ── Balance / Rubies section ──
    sy = 220 * SCALE
    sec_h = 110 * SCALE
    draw.rounded_rectangle(
        (36 * SCALE, sy, W - 36 * SCALE, sy + sec_h),
        radius=16 * SCALE, fill=SECTION_BG, outline=BORDER_DIM, width=1 * SCALE,
    )

    # Inner glow line at top of section
    _gradient_h(img, (50 * SCALE, sy + 2 * SCALE, W - 50 * SCALE, sy + 3 * SCALE), BORDER_DIM, PURPLE)
    draw = ImageDraw.Draw(img)

    # Balance
    draw.text((56 * SCALE, sy + 14 * SCALE), "БАЛАНС", fill=GRAY, font=_font(10, bold=False))
    _dot(draw, 56 * SCALE, sy + 52 * SCALE, 7 * SCALE, GOLD)
    draw.ellipse([56 * SCALE - 9 * SCALE, sy + 52 * SCALE - 9 * SCALE,
                  56 * SCALE + 9 * SCALE, sy + 52 * SCALE + 9 * SCALE],
                 outline=GOLD2, width=1)
    f_bal = _font(28)
    draw.text((78 * SCALE, sy + 36 * SCALE), f"{balance:,}".replace(",", " "), fill=GOLD, font=f_bal)
    draw.text((78 * SCALE, sy + 74 * SCALE), "TON", fill=GOLD2, font=_font(11, bold=False))

    # Divider
    mid = W // 2
    draw.line([(mid, sy + 18 * SCALE), (mid, sy + sec_h - 18 * SCALE)], fill=BORDER_DIM, width=1)

    # Rubies
    draw.text((mid + 20 * SCALE, sy + 14 * SCALE), "РУБИНЫ", fill=GRAY, font=_font(10, bold=False))
    _dot(draw, mid + 20 * SCALE, sy + 52 * SCALE, 7 * SCALE, PINK)
    draw.ellipse([mid + 20 * SCALE - 9 * SCALE, sy + 52 * SCALE - 9 * SCALE,
                  mid + 20 * SCALE + 9 * SCALE, sy + 52 * SCALE + 9 * SCALE],
                 outline=PINK2, width=1)
    f_rub = _font(28)
    draw.text((mid + 40 * SCALE, sy + 36 * SCALE), f"{rubies}", fill=PINK, font=f_rub)
    draw.text((mid + 40 * SCALE, sy + 74 * SCALE), "GEMS", fill=PINK2, font=_font(11, bold=False))

    # ── Stats section ──
    sy2 = sy + sec_h + 16 * SCALE
    stat_h = 260 * SCALE
    draw.rounded_rectangle(
        (36 * SCALE, sy2, W - 36 * SCALE, sy2 + stat_h),
        radius=16 * SCALE, fill=SECTION_BG, outline=BORDER_DIM, width=1 * SCALE,
    )
    _gradient_h(img, (50 * SCALE, sy2 + 2 * SCALE, W - 50 * SCALE, sy2 + 3 * SCALE), BORDER_DIM, PURPLE)
    draw = ImageDraw.Draw(img)

    f_stat_title = _font(16)
    draw.text((56 * SCALE, sy2 + 14 * SCALE), "СТАТИСТИКА", fill=PURPLE2, font=f_stat_title)
    draw.line([(56 * SCALE, sy2 + 42 * SCALE), (W - 56 * SCALE, sy2 + 42 * SCALE)],
              fill=(40, 30, 75), width=1)

    winrate = round(wins * 100 / total_games, 1) if total_games else 0

    f_stat_label = _font(12, bold=False)
    f_stat_val = _font(16)

    rows = [
        ("Игр", str(total_games), GRAY, GRAY),
        ("Побед", str(wins), GREEN, GREEN),
        ("Поражений", str(losses), RED, RED),
    ]
    for i, (label, val, lc, vc) in enumerate(rows):
        ry = sy2 + 52 * SCALE + i * 28 * SCALE
        draw.text((56 * SCALE, ry), label, fill=lc, font=f_stat_label)
        draw.text((240 * SCALE, ry), val, fill=vc, font=f_stat_val)

    # Winrate progress bar
    bar_label_y = sy2 + 140 * SCALE
    bar_y = sy2 + 160 * SCALE
    bar_x = 56 * SCALE
    bar_w = W - 112 * SCALE
    bar_h = 12 * SCALE
    draw.text((bar_x, bar_label_y), "Винрейт", fill=PURPLE, font=f_stat_label)
    draw.text((bar_x + bar_w - 70 * SCALE, bar_label_y), f"{winrate}%", fill=PURPLE2, font=f_stat_val)
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=6 * SCALE, fill=(30, 24, 55))
    if winrate > 0:
        fw = max(bar_h, int(bar_w * min(winrate, 100) / 100))
        _gradient_h(img, (bar_x, bar_y, bar_x + fw, bar_y + bar_h), PURPLE, PINK2)
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fw, bar_y + bar_h], radius=6 * SCALE, fill=PURPLE)

    # Financial stats
    fin_y = bar_y + bar_h + 24 * SCALE
    draw.line([(56 * SCALE, fin_y - 8 * SCALE), (W - 56 * SCALE, fin_y - 8 * SCALE)],
              fill=(40, 30, 75), width=1)
    draw.text((56 * SCALE, fin_y), "Общие ставки", fill=GRAY, font=f_stat_label)
    draw.text((bar_x + bar_w - 80 * SCALE, fin_y), f"{total_bet:,}".replace(",", " "), fill=GRAY, font=f_stat_val)

    fin_y2 = fin_y + 28 * SCALE
    draw.text((56 * SCALE, fin_y2), "Общий выигрыш", fill=GRAY, font=f_stat_label)
    draw.text((bar_x + bar_w - 80 * SCALE, fin_y2), f"{total_won:,}".replace(",", " "), fill=GOLD, font=f_stat_val)

    # Referrals
    if ref_count > 0:
        fin_y3 = fin_y2 + 28 * SCALE
        draw.text((56 * SCALE, fin_y3), "Рефералы", fill=GRAY, font=f_stat_label)
        draw.text((bar_x + bar_w - 80 * SCALE, fin_y3), f"{ref_count}", fill=CYAN, font=f_stat_val)

    # ── Bottom decorative line ──
    line_y2 = H - 68 * SCALE
    draw.line([(60 * SCALE, line_y2), (W - 60 * SCALE, line_y2)], fill=NEON_LINE, width=1)
    _dot(draw, 60 * SCALE, line_y2, 3 * SCALE, PURPLE)
    _dot(draw, W - 60 * SCALE, line_y2, 3 * SCALE, PURPLE)

    # ── Footer ──
    f_footer = _font(11, bold=False)
    footer_text = "TON  \u2022  ИГРАЙ  \u2022  ЗАРАБАТЫВАЙ"
    bbox = draw.textbbox((0, 0), footer_text, font=f_footer)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, H - 50 * SCALE), footer_text, fill=(70, 60, 110), font=f_footer)

    # ── Small sparkle dots ──
    sparkles = [
        (45 * SCALE, 45 * SCALE, 2, (100, 70, 200)),
        (W - 50 * SCALE, 50 * SCALE, 2, (80, 60, 180)),
        (55 * SCALE, H - 80 * SCALE, 2, (90, 60, 190)),
        (W - 55 * SCALE, H - 75 * SCALE, 2, (70, 50, 170)),
        (W // 2, 200 * SCALE, 2, (110, 80, 210)),
    ]
    for sx, sy_s, sr, sc in sparkles:
        _dot(draw, sx, sy_s, sr, sc)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    return buf
