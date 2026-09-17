from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from keyboards.common import back_button
from utils.helpers import balance_text
from utils.profile_card import generate_profile_card

router = Router()


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


def _make_card(user, stats, ref_count):
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
    filename, photo_bytes = _make_card(user, stats, ref_count)
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
    filename, photo_bytes = _make_card(user, stats, ref_count)
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
