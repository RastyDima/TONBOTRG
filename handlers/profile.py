from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import logging
import urllib.request
import ssl
import json
from functools import partial

from config import BOT_TOKEN
from database import db
from keyboards.common import back_button
from utils.helpers import balance_text
from utils.profile_card import generate_profile_card

router = Router()
log = logging.getLogger(__name__)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def profile_kb():
    kb = InlineKeyboardBuilder()
    kb.row(back_button("menu"))
    return kb.as_markup()


def balance_kb():
    kb = InlineKeyboardBuilder()
    kb.row(
        back_button("menu"),
    )
    return kb.as_markup()


def _fetch_avatar_sync(user_id: int) -> bytes | None:
    try:
        base = f"https://api.telegram.org/bot{BOT_TOKEN}"

        photos_url = f"{base}/getUserProfilePhotos?user_id={user_id}&limit=1"
        req1 = urllib.request.Request(photos_url)
        with urllib.request.urlopen(req1, context=_SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read())
        log.info("getUserProfilePhotos for %s: ok=%s", user_id, data.get("ok"))
        if not data.get("ok") or not data["result"]["photos"]:
            return None

        photo_entry = data["result"]["photos"][0]
        last = photo_entry[-1]

        if "video" in last:
            thumb = last["video"].get("thumb")
            if not thumb:
                photo_obj = last.get("photo")
                if photo_obj:
                    file_id = photo_obj["file_id"]
                else:
                    return None
            else:
                file_id = thumb["file_id"]
        else:
            file_id = last["file_id"]

        file_url = f"{base}/getFile?file_id={file_id}"
        req2 = urllib.request.Request(file_url)
        with urllib.request.urlopen(req2, context=_SSL_CTX, timeout=10) as resp2:
            data2 = json.loads(resp2.read())
        log.info("getFile: ok=%s", data2.get("ok"))
        if not data2.get("ok"):
            return None

        file_path = data2["result"]["file_path"]
        dl_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        req3 = urllib.request.Request(dl_url)
        with urllib.request.urlopen(req3, context=_SSL_CTX, timeout=10) as resp3:
            avatar = resp3.read()
        log.info("avatar downloaded: %d bytes", len(avatar))
        return avatar
    except Exception as e:
        log.warning("Sync avatar fetch failed for %s: %s", user_id, e)
        return None


async def _get_avatar(user_id: int) -> bytes | None:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_fetch_avatar_sync, user_id))


async def _make_card(user, stats, ref_count, from_user):
    avatar = await _get_avatar(user["id"])
    card_buf = generate_profile_card(
        user_id=user["id"],
        name=user["first_name"] or "Игрок",
        balance=user["balance"],
        rubies=user.get("rubies", 0) or 0,
        total_games=stats["total_games"],
        wins=stats["wins"],
        losses=stats["losses"],
        total_bet=stats["total_bet"],
        total_won=stats["total_won"],
        ref_count=ref_count,
        avatar_bytes=avatar,
        frame=user.get("active_frame"),
        title=user.get("active_title"),
        xp=user.get("xp", 0) or 0,
    )
    return ("profile.png", card_buf.getvalue())


@router.message(Command("profile"))
async def profile_command(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала нажмите /start")
        return
    stats = db.get_stats(message.from_user.id)
    ref_count = user.get("referral_count", 0) or 0
    filename, photo_bytes = await _make_card(user, stats, ref_count, message.from_user)
    from aiogram.types import FSInputFile
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), filename)
    with open(tmp, "wb") as f:
        f.write(photo_bytes)
    try:
        await message.answer_photo(photo=FSInputFile(tmp), reply_markup=profile_kb())
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


@router.callback_query(F.data == "profile", StateFilter("*"))
async def profile_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Используйте /start")
        return
    stats = db.get_stats(callback.from_user.id)
    ref_count = user.get("referral_count", 0) or 0
    filename, photo_bytes = await _make_card(user, stats, ref_count, callback.from_user)
    from aiogram.types import FSInputFile
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), filename)
    with open(tmp, "wb") as f:
        f.write(photo_bytes)
    try:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(photo=FSInputFile(tmp), reply_markup=profile_kb())
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


@router.callback_query(F.data == "balance", StateFilter("*"))
async def balance_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Используйте /start")
        return
    await callback.message.edit_text(balance_text(user), reply_markup=balance_kb())
