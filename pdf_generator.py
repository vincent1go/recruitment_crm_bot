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

def найти_и_заменить_текст(page, старый_текст, новый_текст, только_первые_n=0):
    # Ищем текст, игнорируя регистр и пробелы
    области = page.search_for(старый_текст, flags=fitz.TEXTFLAGS_SEARCH | fitz.TEXTFLAGS_IGNORE_CASE)
    if not области:
        logger.warning(f"Текст '{старый_текст}' не найден на странице {page.number + 1}")
        return False

    if только_первые_n > 0:
        области = области[:только_первые_n]

    for область in области:
        # Удаляем старый текст
        page.add_redact_annot(область, fill=(0, 0, 0, 0))  # Прозрачная заливка
    page.apply_redactions()

    # Вставляем новый текст в те же позиции
    for область in области:
        page.insert_text(
            (область.x0, область.y0),
            новый_текст,
            fontname="helv",
            fontsize=11,
            color=COLOR
        )
        logger.info(f"Вставлен текст '{новый_текст}' на странице {page.number + 1}, позиция: ({область.x0}, {область.y0})")
    return True

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
        # Замена Client: на первой странице или где найдено
        найти_и_заменить_текст(page, "Client:", f"Client: {текст}")
        найти_и_заменить_текст(page, "Client: ", f"Client: {текст}")  # Проверка с пробелом

        # Замена даты на соответствующих страницах
        найти_и_заменить_текст(page, "Date:", f"Date: {дата}")
        найти_и_заменить_текст(page, "Date: ", f"Date: {дата}")  # Проверка с пробелом

    try:
        doc.save(путь_к_выходному_файлу, garbage=4, deflate=True, clean=True)
        logger.info(f"PDF сохранен как '{путь_к_выходному_файлу}'")
    except Exception as e:
        logger.error(f"Ошибка сохранения PDF: {str(e)}")
        raise
    finally:
        doc.close()

    return путь_к_выходному_файлу
