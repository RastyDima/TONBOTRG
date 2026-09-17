from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import aiohttp
import logging

from config import BOT_TOKEN
from database import db
from keyboards.common import back_button
from utils.helpers import balance_text
from utils.profile_card import generate_profile_card

router = Router()
log = logging.getLogger(__name__)


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


async def _get_avatar(user_id: int) -> bytes | None:
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos"
            async with session.get(url, params={"user_id": user_id, "limit": 1}) as resp:
                data = await resp.json()
                log.info("getUserProfilePhotos for %s: ok=%s, count=%s", user_id, data.get("ok"), len(data.get("result", {}).get("photos", [])) if data.get("ok") else "N/A")
                if not data.get("ok") or not data["result"]["photos"]:
                    return None
                photo = data["result"]["photos"][0][-1]
                file_id = photo["file_id"]
            url2 = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
            async with session.get(url2, params={"file_id": file_id}) as resp2:
                data2 = await resp2.json()
                log.info("getFile for %s: ok=%s", file_id[:20], data2.get("ok"))
                if not data2.get("ok"):
                    return None
                file_path = data2["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            async with session.get(file_url) as resp3:
                log.info("download %s: status=%s", file_path, resp3.status)
                if resp3.status == 200:
                    avatar = await resp3.read()
                    log.info("avatar downloaded: %d bytes", len(avatar))
                    return avatar
                return None
    except Exception as e:
        log.warning("Failed to get avatar for %s: %s", user_id, e)
        return None


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
