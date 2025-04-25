import os
import re
import fitz  # PyMuPDF
import pytz
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Цвет текста (тёмно-серый)
COLOR = (69 / 255, 69 / 255, 69 / 255)

def текущая_дата_киев():
    return datetime.now(pytz.timezone("Europe/Kiev")).strftime("%d.%m.%Y")

def очистить_имя_файла(text):
    return re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()

def заменить_текст_на_странице(page, старый_текст, новый_текст, is_date=False, только_первые_n=0):
    области = page.search_for(старый_текст)
    if not области:
        return False

    if только_первые_n > 0:
        области = области[:только_первые_n]

    for область in области:
        расширенная_область = fitz.Rect(
            область.x0 - 5, область.y0 - 5,
            область.x1 + 50, область.y1 + 5
        )
        page.add_redact_annot(расширенная_область, fill=(1, 1, 1))
    page.apply_redactions()

    for i, область in enumerate(области):
        смещение_y = 15 if is_date else 0
        if i == 1 and len(области) > 1:
            предыдущая_область = области[i - 1]
            if abs(область.y0 - предыдущая_область.y0) < 10:
                смещение_y += 15
        page.insert_text(
            (область.x0, область.y0 + смещение_y),
            новый_текст,
            fontname="helv",
            fontsize=11,
            color=COLOR
        )
    return True

def generate_pdf(путь_к_шаблону: str, текст: str, custom_date: str = None) -> str:
    дата = custom_date if custom_date else текущая_дата_киев()
    имя_файла = очистить_имя_файла(текст) or "результат"
    путь_к_выходному_файлу = f"{имя_файла}.pdf"

    try:
        doc = fitz.open(путь_к_шаблону)
        for page in doc:
            if "template_imperative.pdf" in путь_к_шаблону:
                if page.number == 0:
                    заменить_текст_на_странице(page, "Client:", f"Client: {текст}")
                if page.number == 12:
                    заменить_текст_на_странице(page, "DATE:", f"DATE: {дата}", is_date=True)
            elif "template_small_world.pdf" in путь_к_шаблону:
                if page.number == 0:
                    заменить_текст_на_странице(page, "Client: ", f"Client: {текст}")
                if page.number == 4:
                    заменить_текст_на_странице(page, "Date: ", f"Date: {дата}", is_date=True, только_первые_n=2)
            else:
                if page.number == 0:
                    заменить_текст_на_странице(page, "Client: ", f"Client: {текст}")
                if page.number == 4:
                    заменить_текст_на_странице(page, "Date: ", f"Date: {дата}", is_date=True)

        doc.save(путь_к_выходному_файлу, garbage=4, deflate=True, clean=True)
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {str(e)}")
        raise
    finally:
        doc.close()

    return путь_к_выходному_файлу

