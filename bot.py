import os
import shutil
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message

from config import API_ID, API_HASH, BOT_TOKEN, TEMP_DIR

from database import SessionLocal
from models import Photo

from processor import unpack_archive, walk_files, crc32_file
from excel_report import create_excel

from sqlalchemy import select


app = Client(
    "dedupe_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


@app.on_message(filters.command("start"))
async def start(client, message: Message):

    await message.reply(
        "Привет 👋\n\n"
        "Отправь архив .zip или .rar с фотографиями.\n"
        "Я проверю дубликаты."
    )


@app.on_message(filters.document)
async def handle_archive(client, message: Message):

    doc = message.document

    if not doc.file_name.endswith((".zip", ".rar")):

        await message.reply("Нужен архив .zip или .rar")
        return

    user_id = message.from_user.id

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