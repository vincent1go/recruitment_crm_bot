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

def заменить_текст_на_странице(page, старый_текст, новый_текст, только_первые_n=0):
    области = page.search_for(старый_текст)
    if not области:
        logger.warning(f"Текст '{старый_текст}' не найден на странице {page.number + 1}")
        return False

    if только_первые_n > 0:
        области = области[:только_первые_n]

    for область in области:
        # Создаем аннотацию для удаления текста без белой заливки
        page.add_redact_annot(область, fill=None)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_GRAPHICS_NONE)

    for i, область in enumerate(области):
        # Вставляем новый текст точно в координаты старого текста
        page.insert_text(
            (область.x0, область.y0),
            новый_текст,
            fontname="helv",
            fontsize=11,
            color=COLOR
        )
    return True

def generate_pdf(путь_к_шаблону: str, текст: str) -> str:
    logger.info(f"Генерация PDF с шаблоном '{путь_к_шаблону}' и текстом '{текст}'")
    дата = текущая_дата_киев()
    имя_файла = очистить_имя_файла(текст) or "результат"
    путь_к_выходному_файлу = f"{имя_файла}.pdf"

    try:
        doc = fitz.open(путь_к_шаблону)
    except Exception as e:
        logger.error(f"Ошибка открытия файла '{путь_к_шаблону}': {str(e)}")
        raise

    for page in doc:
        logger.info(f"Обработка страницы {page.number + 1}")
        if "template_imperative.pdf" in путь_к_шаблону:
            if page.number == 0:  # Первая страница
                заменить_текст_на_странице(page, "Client:", f"Client: {текст}")
            if page.number == 12:  # Страница с датой
                заменить_текст_на_странице(page, "DATE:", f"DATE: {дата}")
        elif "template_small_world.pdf" in путь_к_шаблону:
            if page.number == 0:
                заменить_текст_на_странице(page, "Client: ", f"Client: {текст}")
            if page.number == 4:
                заменить_текст_на_странице(page, "Date: ", f"Date: {дата}", только_первые_n=2)
        else:
            if page.number == 0:
                заменить_текст_на_странице(page, "Client: ", f"Client: {текст}")
            if page.number == 4:
                заменить_текст_на_странице(page, "Date: ", f"Date: {дата}")

    try:
        doc.save(путь_к_выходному_файлу, garbage=4, deflate=True, clean=True)
        logger.info(f"PDF сохранен как '{путь_к_выходному_файлу}'")
    except Exception as e:
        logger.error(f"Ошибка сохранения PDF: {str(e)}")
        raise
    finally:
        doc.close()

    return путь_к_выходному_файлу
