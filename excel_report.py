from openpyxl import Workbook


def create_excel(rows, path):

    wb = Workbook()
    ws = wb.active

    ws.append(["File Name", "Status", "CRC32", "Date"])

    for r in rows:
        ws.append(r)

    wb.save(path)