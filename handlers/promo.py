"""Промокоды: игрок вводит #КОД в чат любым сообщением (без меню)."""
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from keyboards.common import back_button
from utils.helpers import format_number

router = Router()


@router.message(F.text.regexp(r"^#\s*\S+"), StateFilter("*"))
async def promo_redeem(message: Message, state: FSMContext):
    await state.clear()
    code = (message.text or "").lstrip("#").strip().split()[0]
    status, amount = db.redeem_promo(message.from_user.id, code)
    texts = {
        "ok": (
            f"🎟 <b>Промокод активирован!</b>\n\n"
            f"Вы получили {format_number(amount)} TON!"
        ),
        "not_found": "❌ Промокод не найден.",
        "inactive": "❌ Этот промокод неактивен.",
        "used_up": "❌ Промокод исчерпал лимит активаций.",
        "already": "❌ Вы уже активировали этот промокод.",
    }
    text = texts.get(status, "❌ Не удалось активировать промокод.")
    if status == "ok":
        user = db.get_user(message.from_user.id)
        if user:
            text += f"\n💳 Баланс: {format_number(user['balance'])}"
    kb = InlineKeyboardBuilder()
    kb.row(back_button("menu"))
    await message.answer(text, reply_markup=kb.as_markup())