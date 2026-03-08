import os
import shutil
import random

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import API_ID, API_HASH, BOT_TOKEN, TEMP_DIR

from database import SessionLocal
from models import Photo

from processor import unpack_archive, walk_files, crc32_file
from excel_report import create_excel

from sqlalchemy import select


os.makedirs(TEMP_DIR, exist_ok=True)


app = Client(
    "dedupe_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


users_passed_test = set()
users_passed_survey = {}


# ========================
# START + TEST
# ========================

@app.on_message(filters.command("start"))
async def start(client, message: Message):

    emojis = ["😀","😎","🤖","🐱","🔥","🍕","🚀","🎧","⭐"]

    correct = random.choice(emojis)

    random.shuffle(emojis)

    keyboard = []

    for i in range(0, 9, 3):

        row = []

        for e in emojis[i:i+3]:

            row.append(
                InlineKeyboardButton(
                    e,
                    callback_data=f"emoji_{e}_{correct}"
                )
            )

        keyboard.append(row)

    await message.reply(

        f"🤖 Проверка на бота\n\n"
        f"Нажмите на смайлик {correct}",

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ========================
# CHECK TEST
# ========================

@app.on_callback_query(filters.regex("emoji_"))
async def emoji_check(client, callback):

    data = callback.data.split("_")

    chosen = data[1]
    correct = data[2]

    user_id = callback.from_user.id

    if chosen == correct:

        users_passed_test.add(user_id)

        await callback.message.edit_text(
            "✅ Проверка пройдена!\n\n"
            "Теперь ответьте на несколько вопросов."
        )

        await ask_question1(callback.message)

    else:

        await callback.answer("❌ Неправильно", show_alert=True)


# ========================
# QUESTION 1
# ========================

async def ask_question1(message):

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Telegram", callback_data="src_tg")],
        [InlineKeyboardButton("TikTok", callback_data="src_tt")],
        [InlineKeyboardButton("Друзья", callback_data="src_friends")],
        [InlineKeyboardButton("Другое", callback_data="src_other")]
    ])

    await message.reply(
        "❓ Откуда вы узнали о тиме?",
        reply_markup=keyboard
    )


# ========================
# ANSWER 1
# ========================

@app.on_callback_query(filters.regex("src_"))
async def answer1(client, callback):

    user_id = callback.from_user.id

    users_passed_survey[user_id] = {
        "source": callback.data
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="team_yes")],
        [InlineKeyboardButton("Нет", callback_data="team_no")]
    ])

    await callback.message.edit_text(
        "❓ Были ли вы в подобных тимах?",
        reply_markup=keyboard
    )


# ========================
# ANSWER 2
# ========================

@app.on_callback_query(filters.regex("team_"))
async def answer2(client, callback):

    user_id = callback.from_user.id

    users_passed_survey[user_id]["team"] = callback.data

    await callback.message.edit_text(
        "✅ Спасибо за ответы!\n\n"
        "Теперь вы можете пользоваться ботом.\n"
        "Отправьте архив с фотографиями."
    )


# ========================
# ARCHIVE HANDLER
# ========================

@app.on_message(filters.document)
async def handle_archive(client, message: Message):

    user_id = message.from_user.id

    if user_id not in users_passed_survey:

        await message.reply(
            "❌ Сначала пройдите проверку.\n"
            "Напишите /start"
        )
        return


    doc = message.document

    if not doc.file_name.endswith((".zip", ".rar")):

        await message.reply("Нужен архив .zip или .rar")
        return


    user_dir = os.path.join(TEMP_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    archive_path = os.path.join(user_dir, doc.file_name)


    await message.reply("⬇️ Скачиваю архив...")

    await message.download(file_name=archive_path)


    extract_dir = os.path.join(user_dir, "extract")
    os.makedirs(extract_dir, exist_ok=True)

    await message.reply("📦 Распаковываю...")

    unpack_archive(archive_path, extract_dir)


    files = walk_files(extract_dir)

    total = len(files)
    new = 0
    dup = 0

    rows = []


    async with SessionLocal() as session:

        for f in files:

            crc = crc32_file(f)

            res = await session.execute(
                select(Photo).where(Photo.crc32_hash == crc)
            )

            exists = res.scalar_one_or_none()

            if exists:

                status = "Duplicate"
                dup += 1

            else:

                status = "New"
                new += 1

                photo = Photo(
                    crc32_hash=crc,
                    file_name=os.path.basename(f),
                    user_id=user_id
                )

                session.add(photo)

            rows.append([
                os.path.basename(f),
                status,
                crc,
                ""
            ])

        await session.commit()


    report_path = os.path.join(user_dir, "report.xlsx")

    create_excel(rows, report_path)


    await message.reply(
        f"📊 Результат\n\n"
        f"Всего: {total}\n"
        f"Новых: {new}\n"
        f"Повторов: {dup}"
    )


    await message.reply_document(report_path)


    shutil.rmtree(user_dir, ignore_errors=True)


app.run()