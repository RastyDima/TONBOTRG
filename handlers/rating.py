from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from keyboards.common import back_button
from utils.helpers import rating_text

router = Router()


def rating_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 По максимуму", callback_data="rating_balance")
    kb.button(text="🎯 По победам", callback_data="rating_wins")
    kb.adjust(2)
    kb.row(back_button("menu"))
    return kb.as_markup()


@router.message(Command("rating"))
async def rating_command(message: Message):
    top = db.top_max_balance(10)
    await message.answer(rating_text(top, "balance"), reply_markup=rating_kb())


@router.callback_query(F.data == "rating", StateFilter("*"))
async def rating_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    top = db.top_max_balance(10)
    await callback.message.edit_text(rating_text(top, "balance"), reply_markup=rating_kb())


@router.callback_query(F.data.in_({"rating_balance", "rating_wins"}), StateFilter("*"))
async def rating_switch(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    if callback.data == "rating_balance":
        top = db.top_max_balance(10)
        mode = "balance"
    else:
        top = db.top_wins(10)
        mode = "wins"
    await callback.message.edit_text(rating_text(top, mode), reply_markup=rating_kb())