"""Генератор профиль-карточки в стиле TON Casino — v3."""
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


def _draw_diamond(draw, cx, cy, size, color, outline=None):
    s = size
    points = [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)]
    draw.polygon(points, fill=color, outline=outline)


def _draw_gem(draw, cx, cy, size, color, shine=None):
    s = size
    top = [(cx, cy - s), (cx + s * 0.6, cy - s * 0.3), (cx - s * 0.6, cy - s * 0.3)]
    bot = [(cx - s * 0.6, cy - s * 0.3), (cx + s * 0.6, cy - s * 0.3), (cx + s * 0.8, cy + s * 0.1),
           (cx, cy + s), (cx - s * 0.8, cy + s * 0.1)]
    darker = tuple(max(0, c - 40) for c in color)
    draw.polygon(top, fill=color, outline=darker)
    draw.polygon(bot, fill=darker, outline=darker)
    if shine:
        small_top = [(cx, cy - s + 2), (cx + s * 0.25, cy - s * 0.4), (cx - s * 0.15, cy - s * 0.35)]
        draw.polygon(small_top, fill=shine)


def _draw_star(draw, cx, cy, size, color):
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = size if i % 2 == 0 else size * 0.45
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=color)


def _draw_badge(draw, cx, cy, text, bg_color, text_color, border_color):
    f = _font(10, bold=False)
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    y_offset = bbox[1]
    pad_x, pad_y = 8 * SCALE, 3 * SCALE
    x0 = cx - tw // 2 - pad_x
    y0 = cy - th // 2 - pad_y
    x1 = cx + tw // 2 + pad_x
    y1 = cy + th // 2 + pad_y
    draw.rounded_rectangle([x0, y0, x1, y1], radius=6 * SCALE, fill=bg_color, outline=border_color, width=1)
    draw.text((cx - tw // 2, cy - th // 2 - y_offset), text, fill=text_color, font=f)


def _decorative_dots(draw, cx, y_start, count=5, spacing=8, color=(60, 50, 100)):
    for i in range(count):
        dx = (i - count // 2) * spacing * SCALE
        _dot(draw, cx + dx, y_start, 2 * SCALE, color)


def _calc_level(total_games, wins, total_bet):
    score = total_games * 2 + wins * 5 + total_bet // 10000
    if score >= 500:
        return "DIAMOND", (100, 220, 255), (60, 180, 220), (80, 200, 240)
    if score >= 200:
        return "GOLD", (255, 210, 60), (200, 160, 30), (255, 220, 80)
    if score >= 50:
        return "SILVER", (200, 200, 220), (140, 140, 160), (220, 220, 240)
    return "BRONZE", (200, 140, 80), (150, 100, 50), (220, 160, 100)


FRAME_COLORS = {
    "frame_neon_green": (0, 255, 120),
    "frame_fire_red": (255, 60, 40),
    "frame_ice_blue": (60, 180, 255),
    "frame_gold": (255, 210, 60),
    "frame_diamond": (180, 230, 255),
}


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
    title: str | None = None,
) -> io.BytesIO:
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

    img = Image.new("RGB", (W, H), BG_TOP)
    _gradient_v(img, (0, 0, W, H), BG_TOP, BG_BOT)

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

    _glow_rect(img, (16 * SCALE, 16 * SCALE, W - 16 * SCALE, H - 16 * SCALE), 30, GLOW, 16)
    draw = ImageDraw.Draw(img)

    card_rect = (20 * SCALE, 20 * SCALE, W - 20 * SCALE, H - 20 * SCALE)
    draw.rounded_rectangle(card_rect, radius=28 * SCALE, fill=CARD_BG, outline=BORDER, width=2 * SCALE)

    line_y = 36 * SCALE
    draw.line([(60 * SCALE, line_y), (W - 60 * SCALE, line_y)], fill=NEON_LINE, width=1)
    _dot(draw, 60 * SCALE, line_y, 3 * SCALE, PURPLE)
    _dot(draw, W - 60 * SCALE, line_y, 3 * SCALE, PURPLE)

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

    if frame and frame in FRAME_COLORS:
        fc = FRAME_COLORS[frame]
        _circle_glow(img, avatar_cx, avatar_cy, avatar_r + 4 * SCALE, fc, 24)
        draw = ImageDraw.Draw(img)
        draw.ellipse(
            [avatar_cx - avatar_r - 5 * SCALE, avatar_cy - avatar_r - 5 * SCALE,
             avatar_cx + avatar_r + 5 * SCALE, avatar_cy + avatar_r + 5 * SCALE],
            outline=fc, width=3 * SCALE,
        )

    f_name = _font(30)
    f_id = _font(13, bold=False)
    name_x = 220 * SCALE
    draw.text((name_x, 85 * SCALE), name, fill=WHITE, font=f_name)
    if title:
        TITLE_DISPLAY = {
            "title_vip": ("VIP", GOLD, (60, 50, 20)),
            "title_legend": ("LEGEND", (255, 180, 50), (60, 40, 15)),
            "title_whale": ("WHALE", CYAN, (15, 40, 60)),
            "title_god": ("GOD", PURPLE2, (40, 20, 60)),
            "title_owner": ("OWNER", (255, 80, 80), (60, 15, 20)),
            "title_ket": ("KET", (100, 255, 200), (15, 50, 40)),
        }
        t_text, t_color, t_bg = TITLE_DISPLAY.get(title, (title, GOLD, (50, 40, 15)))
        name_w = draw.textbbox((0, 0), name, font=f_name)[2]
        t_x = name_x + name_w + 12 * SCALE
        t_y = 83 * SCALE
        f_title = _font(11, bold=False)
        t_bbox = draw.textbbox((0, 0), t_text, font=f_title)
        t_tw = t_bbox[2] - t_bbox[0]
        t_th = t_bbox[3] - t_bbox[1]
        pad_x, pad_y = 8 * SCALE, 4 * SCALE
        badge_x0 = t_x - pad_x
        badge_y0 = t_y - pad_y
        badge_x1 = t_x + t_tw + pad_x
        badge_y1 = t_y + t_th + pad_y
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for i in range(8, 0, -1):
            alpha = int(40 * (1 - i / 8))
            od.rounded_rectangle([badge_x0 - i, badge_y0 - i, badge_x1 + i, badge_y1 + i],
                                 radius=8 * SCALE, fill=t_color + (alpha,))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1],
                               radius=6 * SCALE, fill=t_bg, outline=t_color, width=1)
        draw.text((t_x, t_y), t_text, fill=t_color, font=f_title)

    level_name, level_color, level_bg, level_border = _calc_level(total_games, wins, total_bet)
    _draw_badge(draw, name_x, 120 * SCALE, level_name, level_bg, level_color, level_border)
    _draw_star(draw, name_x, 138 * SCALE, 4 * SCALE, level_color)

    draw.text((name_x, 150 * SCALE), f"ID: {user_id}", fill=GRAY, font=f_id)

    _decorative_dots(draw, W // 2, 195 * SCALE, 7, 10, (50, 35, 100))

    sy = 220 * SCALE
    sec_h = 110 * SCALE
    draw.rounded_rectangle(
        (36 * SCALE, sy, W - 36 * SCALE, sy + sec_h),
        radius=16 * SCALE, fill=SECTION_BG, outline=BORDER_DIM, width=1 * SCALE,
    )
    _gradient_h(img, (50 * SCALE, sy + 2 * SCALE, W - 50 * SCALE, sy + 3 * SCALE), BORDER_DIM, PURPLE)
    draw = ImageDraw.Draw(img)

    draw.text((56 * SCALE, sy + 14 * SCALE), "БАЛАНС", fill=GRAY, font=_font(10, bold=False))
    _draw_diamond(draw, 66 * SCALE, sy + 52 * SCALE, 9 * SCALE, GOLD, outline=GOLD2)
    f_bal = _font(28)
    draw.text((84 * SCALE, sy + 36 * SCALE), f"{balance:,}".replace(",", " "), fill=GOLD, font=f_bal)
    draw.text((84 * SCALE, sy + 74 * SCALE), "TON", fill=GOLD2, font=_font(11, bold=False))

    mid = W // 2
    draw.line([(mid, sy + 18 * SCALE), (mid, sy + sec_h - 18 * SCALE)], fill=BORDER_DIM, width=1)

    draw.text((mid + 20 * SCALE, sy + 14 * SCALE), "РУБИНЫ", fill=GRAY, font=_font(10, bold=False))
    _draw_gem(draw, mid + 30 * SCALE, sy + 52 * SCALE, 9 * SCALE, PINK, shine=(255, 180, 220))
    f_rub = _font(28)
    draw.text((mid + 48 * SCALE, sy + 36 * SCALE), f"{rubies}", fill=PINK, font=f_rub)
    draw.text((mid + 48 * SCALE, sy + 74 * SCALE), "GEMS", fill=PINK2, font=_font(11, bold=False))

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

    fin_y = bar_y + bar_h + 24 * SCALE
    draw.line([(56 * SCALE, fin_y - 8 * SCALE), (W - 56 * SCALE, fin_y - 8 * SCALE)],
              fill=(40, 30, 75), width=1)
    draw.text((56 * SCALE, fin_y), "Общие ставки", fill=GRAY, font=f_stat_label)
    draw.text((bar_x + bar_w - 80 * SCALE, fin_y), f"{total_bet:,}".replace(",", " "), fill=GRAY, font=f_stat_val)

    fin_y2 = fin_y + 28 * SCALE
    draw.text((56 * SCALE, fin_y2), "Общий выигрыш", fill=GRAY, font=f_stat_label)
    draw.text((bar_x + bar_w - 80 * SCALE, fin_y2), f"{total_won:,}".replace(",", " "), fill=GOLD, font=f_stat_val)

    if ref_count > 0:
        fin_y3 = fin_y2 + 28 * SCALE
        draw.text((56 * SCALE, fin_y3), "Рефералы", fill=GRAY, font=f_stat_label)
        draw.text((bar_x + bar_w - 80 * SCALE, fin_y3), f"{ref_count}", fill=CYAN, font=f_stat_val)

    line_y2 = H - 68 * SCALE
    draw.line([(60 * SCALE, line_y2), (W - 60 * SCALE, line_y2)], fill=NEON_LINE, width=1)
    _dot(draw, 60 * SCALE, line_y2, 3 * SCALE, PURPLE)
    _dot(draw, W - 60 * SCALE, line_y2, 3 * SCALE, PURPLE)

    f_footer = _font(11, bold=False)
    footer_text = "TON  \u2022  ИГРАЙ  \u2022  ЗАРАБАТЫВАЙ"
    bbox = draw.textbbox((0, 0), footer_text, font=f_footer)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, H - 50 * SCALE), footer_text, fill=(70, 60, 110), font=f_footer)

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
