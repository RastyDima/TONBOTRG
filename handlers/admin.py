from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from database import db
from keyboards.admin import admin_menu
from keyboards.common import back_button, cancel_kb
from utils.helpers import format_number
from utils.notify import send as notify_send

router = Router()


class AdminStates(StatesGroup):
    give_user = State()
    give_amount = State()
    block_user = State()
    unblock_user = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def resolve_user(text):
    text = (text or "").strip().lstrip("@")
    if not text:
        return None
    if text.isdigit():
        return db.get_user(int(text))
    return db.get_user_by_username(text)


def user_label(user: dict) -> str:
    return user["first_name"] or user["username"] or f"ID {user['id']}"


@router.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён.")
        return
    await message.answer("⚙️ <b>Админ-панель</b>", reply_markup=admin_menu())


@router.callback_query(F.data == "admin", StateFilter("*"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    await callback.message.edit_text("⚙️ <b>Админ-панель</b>", reply_markup=admin_menu())


@router.callback_query(F.data == "admin_give", StateFilter("*"))
async def admin_give_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.give_user)
    await callback.answer()
    await callback.message.edit_text(
        "💰 <b>Выдача валюты</b>\n\nОтправьте ID или @username игрока:",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.give_user)
async def admin_give_user(message: Message, state: FSMContext):
    user = resolve_user(message.text)
    if not user:
        await message.answer("❌ Пользователь не найден. Попробуйте ещё раз:")
        return
    await state.update_data(target_id=user["id"])
    await state.set_state(AdminStates.give_amount)
    await message.answer(
        f"Игрок: <b>{user_label(user)}</b> (ID: <code>{user['id']}</code>)\n\nВведите сумму:"
    )


@router.message(AdminStates.give_amount)
async def admin_give_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("target_id")
    text = (message.text or "").strip().replace(" ", "").replace(",", "")
    try:
        amount = int(text)
    except ValueError:
        await message.answer("❌ Некорректная сумма. Введите целое число:")
        return
    if amount < 0 or amount > 10_000_000_000:
        await message.answer("❌ Некорректная сумма.")
        return
    target = db.get_user(target_id)
    if not target:
        await state.clear()
        await message.answer("❌ Пользователь не найден.")
        return
    db.add_balance(target_id, amount, "admin", f"Выдача администратором {message.from_user.full_name}")
    await state.clear()
    latest = db.get_user(target_id)
    await notify_send(
        target_id,
        f"💰 <b>Вам начислено {format_number(amount)} монет</b>\n\n"
        f"💳 Баланс: {format_number(latest['balance'])}",
    )
    await message.answer(f"✅ Игроку <b>{user_label(target)}</b> начислено {format_number(amount)} монет.")


@router.callback_query(F.data == "admin_block", StateFilter("*"))
async def admin_block_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.block_user)
    await callback.answer()
    await callback.message.edit_text(
        "🚫 <b>Блокировка</b>\n\nОтправьте ID или @username игрока:", reply_markup=cancel_kb()
    )


@router.message(AdminStates.block_user)
async def admin_block_user(message: Message, state: FSMContext):
    user = resolve_user(message.text)
    if not user:
        await message.answer("❌ Пользователь не найден. Попробуйте ещё раз:")
        return
    db.set_blocked(user["id"], True)
    await state.clear()
    await message.answer(f"🚫 Пользователь <b>{user_label(user)}</b> заблокирован.")


@router.callback_query(F.data == "admin_unblock", StateFilter("*"))
async def admin_unblock_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.unblock_user)
    await callback.answer()
    await callback.message.edit_text(
        "✅ <b>Разблокировка</b>\n\nОтправьте ID или @username игрока:", reply_markup=cancel_kb()
    )


@router.message(AdminStates.unblock_user)
async def admin_unblock_user(message: Message, state: FSMContext):
    user = resolve_user(message.text)
    if not user:
        await message.answer("❌ Пользователь не найден. Попробуйте ещё раз:")
        return
    db.set_blocked(user["id"], False)
    await state.clear()
    await message.answer(f"✅ Пользователь <b>{user_label(user)}</b> разблокирован.")


@router.callback_query(F.data == "admin_stats", StateFilter("*"))
async def admin_stats(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    data = db.admin_overview()
    kb = InlineKeyboardBuilder()
    kb.row(back_button("menu"))
    await callback.message.edit_text(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: {data['users']}\n"
        f"💰 Суммарный баланс: {format_number(data['balance'])}\n"
        f"🎮 Всего игр: {data['games']}\n"
        f"✅ Побед: {data['wins']}\n"
        f"📜 Транзакций: {data['tx_count']}\n"
        f"💸 Оборот: {format_number(data['tx_volume'])}",
        reply_markup=kb.as_markup(),
    )