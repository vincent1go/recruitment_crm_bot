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

def удалить_текст_на_странице(page, старый_текст, только_первые_n=0):
    # Ищем области с текстом
    области = page.search_for(старый_текст)
    if not области:
        logger.warning(f"Текст '{старый_текст}' не найден на странице {page.number + 1}")
        return False

    if только_первые_n > 0:
        области = области[:только_первые_n]

    # Удаляем старый текст через редактирование
    for область in области:
        page.add_redact_annot(область, fill=(0, 0, 0, 0))  # Прозрачная заливка, чтобы не использовать белый цвет
        page.apply_redactions()  # Применяем удаление
        logger.info(f"Удален текст '{старый_текст}' на странице {page.number + 1}, область: {область}")
    return True

def вставить_текст_на_странице(page, текст, позиция):
    # Вставляем новый текст в указанную позицию
    page.insert_text(
        позиция,
        текст,
        fontname="helv",
        fontsize=11,
        color=COLOR
    )
    logger.info(f"Вставлен текст '{текст}' на странице {page.number + 1}, позиция: {позиция}")

def generate_pdf(путь_к_шаблону: str, текст: str, custom_date: datetime = None, output_dir: str = ".") -> str:
    logger.info(f"Генерация PDF с шаблоном '{путь_к_шаблону}' и текстом '{текст}'")
    дата = custom_date.strftime("%d.%m.%Y") if custom_date else текущая_дата_киев()
    имя_файла = очистить_имя_файла(текст) or "результат"
    путь_к_выходному_файлу = os.path.join(output_dir, f"{имя_файла}.pdf")

    try:
        doc = fitz.open(путь_к_шаблону)
    except Exception as e:
        logger.error(f"Ошибка открытия файла '{путь_к_шаблону}': {str(e)}")
        raise

    for page in doc:
        logger.info(f"Обработка страницы {page.number + 1}")
        # Удаляем старый текст Client:
        if page.number == 0:
            if "template_imperative.pdf" in путь_к_шаблону:
                удалить_текст_на_странице(page, "Client:")
            else:
                удалить_текст_на_странице(page, "Client: ")

        # Удаляем старый текст Date:
        if "template_imperative.pdf" in путь_к_шаблону:
            if page.number == 12:
                удалить_текст_на_странице(page, "DATE:")
        elif "template_small_world.pdf" in путь_к_шаблону:
            if page.number == 4:
                удалить_текст_на_странице(page, "Date: ", только_первые_n=2)
        else:
            if page.number == 4:
                удалить_текст_на_странице(page, "Date: ")

    # Вставляем новый текст
    for page in doc:
        if page.number == 0:
            # Определяем позицию для Client:
            области_client = page.search_for("Client:") if "template_imperative.pdf" in путь_к_шаблону else page.search_for("Client: ")
            if области_client:
                позиция_client = (области_client[0].x0, области_client[0].y0)
                вставить_текст_на_странице(page, f"Client: {текст}", позиция_client)

        if "template_imperative.pdf" in путь_к_шаблону:
            if page.number == 12:
                области_date = page.search_for("DATE:")
                if области_date:
                    позиция_date = (области_date[0].x0, области_date[0].y0)
                    вставить_текст_на_странице(page, f"DATE: {дата}", позиция_date)
        elif "template_small_world.pdf" in путь_к_шаблону:
            if page.number == 4:
                области_date = page.search_for("Date: ", только_первые_n=2)
                for область in области_date:
                    позиция_date = (область.x0, область.y0)
                    вставить_текст_на_странице(page, f"Date: {дата}", позиция_date)
        else:
            if page.number == 4:
                области_date = page.search_for("Date: ")
                if области_date:
                    позиция_date = (области_date[0].x0, области_date[0].y0)
                    вставить_текст_на_странице(page, f"Date: {дата}", позиция_date)

    try:
        doc.save(путь_к_выходному_файлу, garbage=4, deflate=True, clean=True)
        logger.info(f"PDF сохранен как '{путь_к_выходному_файлу}'")
    except Exception as e:
        logger.error(f"Ошибка сохранения PDF: {str(e)}")
        raise
    finally:
        doc.close()

    return путь_к_выходному_файлу
