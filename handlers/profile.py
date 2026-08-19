from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from keyboards.common import back_button
from utils.helpers import profile_text

router = Router()


def profile_kb():
    kb = InlineKeyboardBuilder()
    kb.row(back_button("menu"))
    return kb.as_markup()


@router.message(Command("profile"))
async def profile_command(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала нажмите /start")
        return
    stats = db.get_stats(message.from_user.id)
    await message.answer(profile_text(user, stats), reply_markup=profile_kb())


@router.callback_query(F.data.in_({"profile", "balance"}), StateFilter("*"))
async def profile_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Используйте /start")
        return
    stats = db.get_stats(callback.from_user.id)
    await callback.message.edit_text(profile_text(user, stats), reply_markup=profile_kb())