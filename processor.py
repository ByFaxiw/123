import os
import zlib
import zipfile
import patoolib

IGNORE = {".ds_store", "thumbs.db"}

ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}


def crc32_file(path):

    crc = 0

    with open(path, "rb") as f:
        while chunk := f.read(65536):
            crc = zlib.crc32(chunk, crc)

    return format(crc & 0xFFFFFFFF, "08x")


def unpack_archive(archive, dest):

    if archive.endswith(".zip"):

        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)

    elif archive.endswith(".rar"):

        patoolib.extract_archive(archive, outdir=dest)


def walk_files(folder):

    files = []

    for root, _, fs in os.walk(folder):

        for f in fs:

            if f.lower() in IGNORE:
                continue

            ext = os.path.splitext(f)[1].lower()

            if ext not in ALLOWED:
                continue

            files.append(os.path.join(root, f))

    return files