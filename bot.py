import os
import random
import re

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from sqlalchemy import select

from config import *
from database import SessionLocal
from models import User


app = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


bot_tests = {}
survey_state = {}


# ================= START =================

@app.on_message(filters.command("start"))
async def start(client, message):

    async with SessionLocal() as session:

        res = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )

        user = res.scalar_one_or_none()

        if user:

            if user.status == "banned":
                await message.reply("Вы заблокированы.")
                return

            if user.status == "approved":
                await show_menu(message)
                return

    emojis = ["😀","😎","🤖","🐱","🔥","🍕","🚀","🎧","⭐"]

    correct = random.choice(emojis)

    bot_tests[message.from_user.id] = correct

    random.shuffle(emojis)

    keyboard = []

    for i in range(0,9,3):

        row=[]

        for e in emojis[i:i+3]:
            row.append(
                InlineKeyboardButton(e,callback_data=f"test_{e}")
            )

        keyboard.append(row)

    await message.reply(

        "Привет. Это бот тимы zippaoffer.\n\n"
        f"Нажмите на смайлик {correct}",

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= TEST =================

@app.on_callback_query(filters.regex("test_"))
async def test(client, callback):

    emoji = callback.data.split("_")[1]

    correct = bot_tests.get(callback.from_user.id)

    if emoji != correct:

        await callback.answer("Неверно",show_alert=True)
        return

    await callback.message.edit_text("Проверка пройдена")

    survey_state[callback.from_user.id] = "source"

    await callback.message.reply(
        "1️⃣ Откуда вы узнали о тиме?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("TikTok",callback_data="src_tt")],
            [InlineKeyboardButton("Telegram",callback_data="src_tg")],
            [InlineKeyboardButton("От друга",callback_data="src_friend")],
            [InlineKeyboardButton("Другое",callback_data="src_other")]
        ])
    )


# ================= SOURCE =================

@app.on_callback_query(filters.regex("src_"))
async def source(client, callback):

    survey_state[callback.from_user.id] = callback.data

    if callback.data == "src_tt":

        survey_state[callback.from_user.id] = "teams"

        await callback.message.reply("2️⃣ Были ли в похожих тимах?")
        return

    if callback.data == "src_tg":

        survey_state[callback.from_user.id] = "tg_detail"

        await callback.message.reply("Напишите где именно в Telegram")
        return

    if callback.data == "src_friend":

        survey_state[callback.from_user.id] = "friend_detail"

        await callback.message.reply("Напишите username друга")
        return

    if callback.data == "src_other":

        survey_state[callback.from_user.id] = "other_detail"

        await callback.message.reply("Напишите источник")
        return


# ================= TEXT ANSWERS =================

@app.on_message(filters.text & ~filters.command)
async def survey_text(client,message):

    uid = message.from_user.id

    state = survey_state.get(uid)

    if not state:
        return

    async with SessionLocal() as session:

        res = await session.execute(select(User).where(User.tg_id == uid))

        user = res.scalar_one_or_none()

        if not user:

            user = User(
                tg_id=uid,
                username=message.from_user.username
            )

            session.add(user)

        if state == "tg_detail":
            user.source="telegram"
            user.source_detail=message.text
            survey_state[uid]="teams"
            await message.reply("2️⃣ Были ли в похожих тимах?")
            return

        if state == "friend_detail":
            user.source="friend"
            user.source_detail=message.text
            survey_state[uid]="teams"
            await message.reply("2️⃣ Были ли в похожих тимах?")
            return

        if state == "other_detail":
            user.source="other"
            user.source_detail=message.text
            survey_state[uid]="teams"
            await message.reply("2️⃣ Были ли в похожих тимах?")
            return

        if state == "teams":
            user.teams = message.text
            survey_state[uid]="reason"
            await message.reply("3️⃣ Почему хотите вступить к нам?")
            return

        if state == "reason":

            user.reason = message.text

            await session.commit()

            text=f"""
Новая заявка

ID: {uid}
Username: @{message.from_user.username}

Источник: {user.source}
Детали: {user.source_detail}

Был в тимах: {user.teams}

Причина: {user.reason}
"""

            await app.send_message(
                1077122199,
                text,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Принять",callback_data=f"approve_{uid}"),
                        InlineKeyboardButton("Отклонить",callback_data=f"deny_{uid}")
                    ]
                ])
            )

            await message.reply("Заявка отправлена админу")

            survey_state.pop(uid)

            await session.commit()


# ================= ADMIN =================

@app.on_callback_query(filters.regex("approve_"))
async def approve(client,callback):

    uid=int(callback.data.split("_")[1])

    async with SessionLocal() as session:

        res=await session.execute(select(User).where(User.tg_id==uid))
        user=res.scalar_one()

        user.status="approved"

        await session.commit()

    await app.send_message(uid,"Ваша заявка одобрена")



@app.on_callback_query(filters.regex("deny_"))
async def deny(client,callback):

    uid=int(callback.data.split("_")[1])

    async with SessionLocal() as session:

        res=await session.execute(select(User).where(User.tg_id==uid))
        user=res.scalar_one()

        user.status="banned"

        await session.commit()

    await app.send_message(uid,"Ваша заявка отклонена")


# ================= MENU =================

async def show_menu(message):

    kb=ReplyKeyboardMarkup(
        [
            [KeyboardButton("Сдать архив")],
            [KeyboardButton("Поддержка"),KeyboardButton("Ссылка на чат")],
            [KeyboardButton("Профиль")]
        ],
        resize_keyboard=True
    )

    await message.reply("Меню",reply_markup=kb)


# ================= PROFILE =================

@app.on_message(filters.regex("Профиль"))
async def profile(client,message):

    async with SessionLocal() as session:

        res=await session.execute(select(User).where(User.tg_id==message.from_user.id))
        user=res.scalar_one()

        text=f"""
Профиль

Username: @{user.username}
ID: {user.tg_id}

Архивов сдано: {user.archives}

Всего выплат: {user.payouts}
"""

        await message.reply(text)


# ================= ARCHIVE =================

@app.on_message(filters.regex("Сдать архив"))
async def ask_archive(client,message):

    await message.reply("Отправьте архив")


@app.on_message(filters.document)
async def archive(client,message):

    name=message.document.file_name

    if not (name.endswith(".zip") or name.endswith(".rar")):

        await message.reply("Только zip или rar")
        return

    if not re.match(r"\d+_\d{2}-\d{2}",name):

        await message.reply("Название должно быть: количествоскринов_день-месяц")
        return

    await message.reply("Архив принят")


app.run()