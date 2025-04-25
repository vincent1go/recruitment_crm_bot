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

def заменить_текст_на_странице(page, старый_текст, новый_текст, только_первые_n=0, offset_y=0):
    # Ищем области, где находится старый текст
    области = page.search_for(старый_текст)
    if not области:
        logger.warning(f"Текст '{старый_текст}' не найден на странице {page.number + 1}")
        return False

    if только_первые_n > 0:
        области = области[:только_первые_n]

    # Удаляем старый текст, перекрывая его пустым текстом
    for область in области:
        page.insert_text(
            (область.x0, область.y0),
            "",  # Пустой текст для "удаления" старого
            fontname="helv",
            fontsize=11,
            color=COLOR
        )

    # Вставляем новый текст в те же позиции с учетом смещения
    for i, область in enumerate(области):
        y_position = область.y0 + offset_y
        page.insert_text(
            (область.x0, y_position),
            новый_текст,
            fontname="helv",
            fontsize=11,
            color=COLOR
        )
        logger.info(f"Заменен текст '{старый_текст}' на '{новый_текст}' на странице {page.number + 1}, позиция: ({область.x0}, {y_position})")
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
        # Замена Client: только на первой странице
        if page.number == 0:
            if "template_imperative.pdf" in путь_к_шаблону:
                заменить_текст_на_странице(page, "Client:", f"Client: {текст}")
            else:
                заменить_текст_на_странице(page, "Client: ", f"Client: {текст}")

        # Замена даты на соответствующих страницах
        if "template_imperative.pdf" in путь_к_шаблону:
            if page.number == 12:  # Страница с подписями и датой
                заменить_текст_на_странице(page, "DATE:", f"DATE: {дата}")
        elif "template_small_world.pdf" in путь_к_шаблону:
            if page.number == 4:
                заменить_текст_на_странице(page, "Date: ", f"Date: {дата}", только_первые_n=2)
        elif "clean_template_no_text.pdf" in путь_к_шаблону:
            if page.number == 4:
                # Смещаем надпись "Signatures:" вниз
                заменить_текст_на_странице(page, "Signatures:", "Signatures:", offset_y=30)
                # Вставляем дату без смещения
                заменить_текст_на_странице(page, "Date: ", f"Date: {дата}")
        else:
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
