"""Веб-админ-панель бота: статистика, игроки, настройки игр.

Работает на том же aiohttp-сервере, что и бот (URL /admin).
Вход: ADMIN_PANEL_USER / ADMIN_PANEL_PASSWORD (config.py).
"""
import html
import secrets
import time

from aiohttp import web

from config import ADMIN_PANEL_PASSWORD, ADMIN_PANEL_USER
from database import db
from games.joker import DEFAULT_JOKER_LEVELS, get_joker_levels
from games.mines import get_house_edge
from utils.helpers import format_number

SESSION_TTL = 60 * 60 * 12  # 12 часов
_sessions: dict[str, float] = {}  # token -> expires_at


def _page(title: str, body: str, active: str) -> str:
    tabs = [
        ("players", "Игроки", "/admin"),
        ("settings", "Настройки", "/admin/settings"),
    ]
    nav = "".join(
        f'<a class="tab {"on" if a == active else ""}" href="{u}">{t}</a>'
        for a, t, u in tabs
    )
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Админка</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:'Segoe UI',system-ui,sans-serif; background:#0f1521; color:#e6e9ef; }}
header {{ display:flex; align-items:center; gap:16px; padding:14px 22px; background:#151d2e;
         border-bottom:1px solid #253047; position:sticky; top:0; }}
header .logo {{ font-weight:700; font-size:18px; }}
.tab {{ color:#9aa7bd; text-decoration:none; padding:8px 14px; border-radius:8px; }}
.tab:hover {{ background:#1e2a41; }}
.tab.on {{ background:#1e6feb; color:#fff; }}
a.logout {{ margin-left:auto; color:#f0856e; text-decoration:none; }}
main {{ max-width:1100px; margin:0 auto; padding:22px; }}
h1 {{ font-size:22px; margin:6px 0 16px; }}
h2 {{ font-size:17px; margin:18px 0 8px; color:#c6cfdd; }}
.box {{ background:#171f30; border:1px solid #253047; border-radius:12px; padding:16px; margin-bottom:16px; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }}
.stat {{ background:#171f30; border:1px solid #253047; border-radius:12px; padding:14px 16px; }}
.stat b {{ display:block; font-size:22px; margin-top:4px; }}
.stat span {{ color:#9aa7bd; font-size:13px; }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }}
th,td {{ text-align:left; padding:9px 10px; border-bottom:1px solid #1f2940; }}
th {{ color:#9aa7bd; font-weight:600; font-size:13px; }}
input[type=text], input[type=password], input[type=number], input[type=search] {{
    background:#101828; border:1px solid #2c3a57; color:#e6e9ef; border-radius:8px;
    padding:9px 12px; font-size:14px; }}
button {{ background:#1e6feb; border:0; color:#fff; border-radius:8px; padding:9px 16px;
         font-size:14px; cursor:pointer; }}
button:hover {{ background:#2b7bff; }}
button.ghost {{ background:#253047; }}
button.danger {{ background:#c0392b; }}
form.inline {{ display:inline; }}
.msg {{ padding:12px 14px; border-radius:10px; margin-bottom:14px; font-size:14px; }}
.ok {{ background:#0f2e1d; color:#7ee2a8; border:1px solid #1f4d33; }}
.err {{ background:#3a1620; color:#ff9ca6; border:1px solid #5a2430; }}
.pill {{ display:inline-block; padding:2px 9px; border-radius:20px; font-size:12px; }}
.pill.red {{ background:#3a1620; color:#ff9ca6; }}
.pill.green {{ background:#0f2e1d; color:#7ee2a8; }}
.muted {{ color:#7c88a0; font-size:13px; }}
.login {{ max-width:360px; margin:90px auto; }}
.login .box {{ padding:26px; }}
label {{ display:block; font-size:13px; color:#9aa7bd; margin:12px 0 5px; }}
.login input {{ width:100%; margin-bottom:4px; }}
</style></head><body>
<header>
  <span class="logo">⚙️ Админка бота</span>
  {nav}
  <a class="logout" href="/admin/logout">Выйти</a>
</header>
<main>{body}</main>
</body></html>"""


def _flash(msg: str, ok: bool = True) -> str:
    return f'<div class="msg {"ok" if ok else "err"}">{html.escape(msg)}</div>'


def _set_cookie(resp: web.Response, token: str) -> None:
    resp.set_cookie("adm", token, max_age=SESSION_TTL, httponly=True, samesite="Lax")


# ---------- Авторизация ----------

def _auth_ok(request: web.Request) -> bool:
    token = request.cookies.get("adm")
    if not token:
        return False
    exp = _sessions.get(token)
    if not exp:
        return False
    if time.time() > exp:
        _sessions.pop(token, None)
        return False
    return True


# ---------- Вкладка «Игроки» ----------

def _player_row(u: dict) -> str:
    name = u["first_name"] or u["username"] or f"ID {u['id']}"
    nick = f"<span class='muted'>@{html.escape(u['username'])}</span>" if u["username"] else ""
    blocked = '<span class="pill red">заблокирован</span>' if u["is_blocked"] else '<span class="pill green">ок</span>'
    return f"""<tr>
<td><b>{html.escape(name)}</b><br>{nick}</td>
<td><span class="muted">{u['id']}</span></td>
<td><b>{format_number(u['balance'])}</b></td>
<td>{blocked}</td>
<td>
  <form class="inline" method="post" action="/admin/give" style="display:flex;gap:6px;align-items:center">
    <input type="hidden" name="uid" value="{u['id']}">
    <input type="number" name="amount" value="1000" style="width:110px">
    <button>+</button>
    <button class="danger" name="neg" value="1">−</button>
  </form>
</td>
<td>
  <form class="inline" method="post" action="/admin/{'unblock' if u['is_blocked'] else 'block'}">
    <input type="hidden" name="uid" value="{u['id']}">
    <button class="{'ghost' if u['is_blocked'] else 'danger'}">{'Разблокировать' if u['is_blocked'] else 'Заблокировать'}</button>
  </form>
</td>
</tr>"""


async def players_page(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.HTTPFound("/admin/login")
    q = request.query.get("q", "").strip()
    users = db.search_users(q, limit=100)
    body = f"""<h1>👥 Игроки {q and f'по запросу <span class="muted">«{html.escape(q)}»</span>' or ''}</h1>
{f'<div class="muted">Найдено: {len(users)}</div>' if q else ''}
<form class="box" method="get" action="/admin" style="display:flex;gap:8px">
  <input type="search" name="q" placeholder="Поиск: имя, @username, ID" style="flex:1" value="{html.escape(q)}">
  <button>Искать</button>
</form>
<div class="box" style="padding:0;overflow-x:auto"><table>
<tr><th>Игрок</th><th>ID</th><th>Баланс</th><th>Статус</th><th>Выдать / списать</th><th>Действия</th></tr>
{''.join(_player_row(u) for u in users) or '<tr><td colspan="6" class="muted">Никого не найдено</td></tr>'}
</table></div>"""
    return web.Response(text=_page("Игроки", body, "players"), content_type="text/html", charset="utf-8")


async def give_coins(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.HTTPFound("/admin/login")
    form = await request.post()
    uid, amount = form.get("uid", ""), form.get("amount", "")
    try:
        uid = int(uid)
        amount = int(amount)
    except (TypeError, ValueError):
        return web.HTTPFound("/admin")
    if amount <= 0 or amount > 10_000_000_000:
        return web.HTTPFound("/admin")
    user = db.get_user(uid)
    if not user:
        return web.HTTPFound("/admin")
    if form.get("neg"):
        amount = -amount
    db.add_balance(uid, amount, "admin", "Веб-админка: изменение баланса")
    return web.HTTPFound("/admin")


async def block_user(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.HTTPFound("/admin/login")
    form = await request.post()
    uid = form.get("uid", "")
    if uid.isdigit():
        db.set_blocked(int(uid), True)
    return web.HTTPFound("/admin")


async def unblock_user(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.HTTPFound("/admin/login")
    form = await request.post()
    uid = form.get("uid", "")
    if uid.isdigit():
        db.set_blocked(int(uid), False)
    return web.HTTPFound("/admin")


# ---------- Вкладка «Настройки» ----------

async def settings_page(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.HTTPFound("/admin/login")
    levels = get_joker_levels()
    current = {
        "mines_house_edge": get_house_edge(),
        "joker_mult_1": levels[1]["mult"],
        "joker_mult_2": levels[2]["mult"],
    }
    body = """<h1>⚠️ Настройки (опасно)</h1>
<div class="box">
<p class="muted">Здесь меняются коэффициенты выигрыша. От этих значений напрямую зависит, сколько «остаётся» боту, а сколько забирают игроки. Изменения применяются сразу.</p>
<form method="post" action="/admin/settings">
  <h2>🎮 Мины</h2>
  <label>Тема раздачи (house edge) — доля от честных шансов (0.1–2). <b>Выше = бот зарабатывает больше</b></label>
  <input type="number" step="0.01" min="0.1" max="2" name="mines_house_edge" value="{}">
  <h2>🃏 Джокер — множитель за каждую удачную дверь</h2>
  <label>Уровень 1 (💀 1): <input type="number" step="0.1" min="1" max="20" name="joker_mult_1" value="{}"></label>
  <label>Уровень 2 (💀 2): <input type="number" step="0.1" min="1" max="50" name="joker_mult_2" value="{}"></label>
  <div style="margin-top:16px"><button>Сохранить</button></div>
</form></div>""".format(
        current["mines_house_edge"], current["joker_mult_1"], current["joker_mult_2"]
    )
    return web.Response(text=_page("Настройки", body, "settings"), content_type="text/html", charset="utf-8")


async def save_settings(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.HTTPFound("/admin/login")
    form = await request.post()

    def _parse(name: str) -> float | None:
        raw = form.get(name, "")
        try:
            return float(raw.replace(",", "."))
        except (TypeError, ValueError):
            return None

    vals = {
        "mines_house_edge": _parse("mines_house_edge"),
        "joker_mult_1": _parse("joker_mult_1"),
        "joker_mult_2": _parse("joker_mult_2"),
    }
    ok = True
    if not vals["mines_house_edge"] or not 0.1 <= vals["mines_house_edge"] <= 2:
        ok = False
    if not vals["joker_mult_1"] or vals["joker_mult_1"] < 1:
        ok = False
    if not vals["joker_mult_2"] or vals["joker_mult_2"] < 1:
        ok = False
    if ok:
        for key, val in vals.items():
            db.set_setting(key, val)
    return web.HTTPFound("/admin/settings")


# ---------- Логин ----------

async def login_page(request: web.Request) -> web.Response:
    if _auth_ok(request):
        return web.HTTPFound("/admin")
    body = """
<h1 style="text-align:center">⚙️ Вход в админку</h1>
<div class="login">
<form class="box" method="post" action="/admin/login">
  <label>Логин</label>
  <input type="text" name="user" autocomplete="username" required>
  <label>Пароль</label>
  <input type="password" name="pass" autocomplete="current-password" required>
  <div style="margin-top:18px"><button style="width:100%">Войти</button></div>
</form>
</div>"""
    return web.Response(text=_page("Вход", body, ""), content_type="text/html", charset="utf-8")


async def login(request: web.Request) -> web.Response:
    form = await request.post()
    user = form.get("user", "")
    password = form.get("pass", "")
    if user == ADMIN_PANEL_USER and password == ADMIN_PANEL_PASSWORD:
        token = secrets.token_urlsafe(32)
        _sessions[token] = time.time() + SESSION_TTL
        resp = web.HTTPFound("/admin")
        _set_cookie(resp, token)
        return resp
    body = _flash("Неверный логин или пароль", ok=False) + """
<h1 style="text-align:center">⚙️ Вход в админку</h1>
<div class="login">
<form class="box" method="post" action="/admin/login">
  <label>Логин</label>
  <input type="text" name="user" autocomplete="username" required>
  <label>Пароль</label>
  <input type="password" name="pass" autocomplete="current-password" required>
  <div style="margin-top:18px"><button style="width:100%">Войти</button></div>
</form>
</div>"""
    return web.Response(text=_page("Вход", body, ""), content_type="text/html", charset="utf-8")


async def logout(request: web.Request) -> web.Response:
    token = request.cookies.get("adm")
    if token:
        _sessions.pop(token, None)
    resp = web.HTTPFound("/admin/login")
    resp.del_cookie("adm")
    return resp


def register_admin_routes(app: web.Application) -> None:
    app.router.add_get("/admin", players_page)
    app.router.add_get("/admin/", players_page)
    app.router.add_get("/admin/login", login_page)
    app.router.add_post("/admin/login", login)
    app.router.add_post("/admin/give", give_coins)
    app.router.add_post("/admin/block", block_user)
    app.router.add_post("/admin/unblock", unblock_user)
    app.router.add_get("/admin/settings", settings_page)
    app.router.add_post("/admin/settings", save_settings)
    app.router.add_get("/admin/logout", logout)
