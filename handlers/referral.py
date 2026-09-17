"""Реферальная система: /ref — ссылка, % от ставок рефералов."""
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import PUBLIC_BASE_URL
from database import db
from keyboards.common import back_button
from utils.helpers import format_number

router = Router()

REFERRAL_PERCENT = 0.05  # 5% от ставки реферала


def get_ref_link(user_id: int) -> str:
    if PUBLIC_BASE_URL:
        return f"https://t.me/{__import__('config', fromlist=['BOT_TOKEN']).BOT_TOKEN.split(':')[0].lower()}bot?start=ref{user_id}"
    return f"/start ref{user_id}"


def process_referral_bet(user_id: int, bet: int) -> None:
    """Начисляет реферальный бонус приговоре реферала."""
    user = db.get_user(user_id)
    if not user or not user.get("referrer_id"):
        return
    referrer_id = user["referrer_id"]
    bonus = int(bet * REFERRAL_PERCENT)
    if bonus < 1:
        return
    db.add_balance(referrer_id, bonus, "referral", f"Реферальный бонус от игрока {user_id}")
    db.add_referral_earning(referrer_id, bonus)


@router.message(Command("ref"))
async def ref_command(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала нажмите /start")
        return
    ref_link = get_ref_link(message.from_user.id)
    ref_count = user.get("referral_count", 0) or 0
    ref_earned = user.get("referral_earned", 0) or 0
    await message.answer(
        f"👥 <b>Реферальная система</b>\n\n"
        f"Приглашайте друзей и получайте <b>5%</b> от каждой их ставки!\n\n"
        f"📊 Приглашено: <b>{ref_count}</b>\n"
        f"💰 Заработано: <b>{format_number(ref_earned)}</b> TON\n\n"
        f"🔗 Ваша ссылка:\n<code>{ref_link}</code>\n\n"
        f"Отправьте её другу — он должен нажать на неё и написать /start",
        reply_markup=back_kb(),
    )


@router.callback_query(F.data == "ref", StateFilter("*"))
async def ref_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Используйте /start")
        return
    ref_link = get_ref_link(callback.from_user.id)
    ref_count = user.get("referral_count", 0) or 0
    ref_earned = user.get("referral_earned", 0) or 0
    await callback.message.edit_text(
        f"👥 <b>Реферальная система</b>\n\n"
        f"Приглашайте друзей и получайте <b>5%</b> от каждой их ставки!\n\n"
        f"📊 Приглашено: <b>{ref_count}</b>\n"
        f"💰 Заработано: <b>{format_number(ref_earned)}</b> TON\n\n"
        f"🔗 Ваша ссылка:\n<code>{ref_link}</code>\n\n"
        f"Отправьте её другу — он должен нажать на неё и написать /start",
        reply_markup=back_kb(),
    )


def back_kb():
    kb = InlineKeyboardBuilder()
    kb.row(back_button("menu"))
    return kb.as_markup()
