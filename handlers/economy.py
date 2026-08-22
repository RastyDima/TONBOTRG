from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from keyboards.common import back_button
from utils.helpers import (
    balance_text,
    format_number,
    get_daily_bonus,
    get_weekly_bonus,
    history_text,
    quick_command,
)
from utils.notify import send as notify_send

router = Router()

TRANSFER_COMMANDS = ("п", "перевод", "перевести", "transfer")
BALANCE_COMMANDS = ("б", "баланс", "balance", "balance")
TRANSFER_MAX = 10 ** 15


def is_balance(message: Message) -> bool:
    return quick_command(message.text, BALANCE_COMMANDS) is not None


def is_transfer(message: Message) -> bool:
    return quick_command(message.text, TRANSFER_COMMANDS, max_bet=TRANSFER_MAX) is not None


def back_kb():
    kb = InlineKeyboardBuilder()
    kb.row(back_button("menu"))
    return kb.as_markup()


@router.message(Command("daily"))
async def daily_command(message: Message):
    ok = db.claim_daily(message.from_user.id, get_daily_bonus())
    if ok:
        await message.answer(
            f"🎁 <b>Ежедневный бонус</b>\n\nВы получили {format_number(get_daily_bonus())} TON!",
            reply_markup=back_kb(),
        )
    else:
        await message.answer(
            "⏳ Вы уже получали бонус сегодня. Возвращайтесь завтра!", reply_markup=back_kb()
        )


@router.callback_query(F.data == "daily", StateFilter("*"))
async def daily_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    ok = db.claim_daily(callback.from_user.id, get_daily_bonus())
    if ok:
        await callback.message.edit_text(
            f"🎁 <b>Ежедневный бонус</b>\n\nВы получили {format_number(get_daily_bonus())} TON!",
            reply_markup=back_kb(),
        )
    else:
        await callback.message.edit_text(
            "⏳ Вы уже получали бонус сегодня. Возвращайтесь завтра!", reply_markup=back_kb()
        )


@router.message(Command("weekly"))
async def weekly_command(message: Message):
    ok = db.claim_weekly(message.from_user.id, get_weekly_bonus())
    if ok:
        await message.answer(
            f"🗓 <b>Еженедельный бонус</b>\n\nВы получили {format_number(get_weekly_bonus())} TON!",
            reply_markup=back_kb(),
        )
    else:
        await message.answer(
            "⏳ Вы уже получали еженедельный бонус. Возвращайтесь на следующей неделе!",
            reply_markup=back_kb(),
        )


@router.callback_query(F.data == "weekly", StateFilter("*"))
async def weekly_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    ok = db.claim_weekly(callback.from_user.id, get_weekly_bonus())
    if ok:
        await callback.message.edit_text(
            f"🗓 <b>Еженедельный бонус</b>\n\nВы получили {format_number(get_weekly_bonus())} TON!",
            reply_markup=back_kb(),
        )
    else:
        await callback.message.edit_text(
            "⏳ Вы уже получали еженедельный бонус. Возвращайтесь на следующей неделе!",
            reply_markup=back_kb(),
        )


@router.message(Command("history"))
async def history_command(message: Message):
    tx = db.get_transactions(message.from_user.id)
    await message.answer(history_text(tx), reply_markup=back_kb())


@router.callback_query(F.data == "history", StateFilter("*"))
async def history_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    tx = db.get_transactions(callback.from_user.id)
    await callback.message.edit_text(history_text(tx), reply_markup=back_kb())


@router.message(F.text, is_balance)
async def balance_quick(message: Message, state: FSMContext):
    await state.clear()
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала нажмите /start")
        return
    await message.answer(balance_text(user))


@router.message(F.text, is_transfer)
async def transfer_money(message: Message, state: FSMContext):
    info = quick_command(message.text, TRANSFER_COMMANDS, max_bet=TRANSFER_MAX)
    amount = info["bet"]
    if amount is None:
        await message.answer(
            "💸 <b>Перевод</b>\nОтветьте на сообщение игрока: <code>п 12000</code>\n"
            "Например: <code>п 5к</code>, <code>п 1.5м</code>"
        )
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer(
            "💸 <b>Перевод</b>\nОтветьте на сообщение игрока, которому хотите перевести:\n"
            "<code>п 12000</code>"
        )
        return
    sender = message.from_user
    receiver = message.reply_to_message.from_user
    if receiver.id == sender.id:
        await message.answer("❌ Нельзя переводить самому себе.")
        return
    rec = db.get_user(receiver.id)
    if not rec:
        await message.answer("❌ Получатель не найден. Игрок должен нажать /start.")
        return
    sender_db = db.get_user(sender.id)
    if not sender_db:
        await message.answer("Сначала нажмите /start")
        return
    if amount > sender_db["balance"]:
        await message.answer(
            f"❌ Недостаточно средств. Баланс: {format_number(sender_db['balance'])}"
        )
        return
    await state.clear()
    db.add_balance(sender.id, -amount, "transfer_out", f"Перевод игроку {receiver.full_name}")
    db.add_balance(receiver.id, amount, "transfer_in", f"Перевод от игрока {sender.full_name}")
    latest = db.get_user(receiver.id)
    await notify_send(
        receiver.id,
        f"💸 <b>Перевод получен</b>\n\n"
        f"Игрок {sender.full_name} перевёл вам <b>{format_number(amount)}</b> TON.\n"
        f"💳 Баланс: {format_number(latest['balance'])}",
    )
    await message.answer(
        f"✅ Переведено <b>{format_number(amount)}</b> TON игроку {receiver.full_name}.\n"
        f"💰 Ваш баланс: {format_number(sender_db['balance'] - amount)}"
    )