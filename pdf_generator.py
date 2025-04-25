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

def заменить_текст_на_странице(page, старый_текст, новый_текст, is_date=False, только_первые_n=0, date_offset_y=15):
    области = page.search_for(старый_текст)
    if not области:
        logger.warning(f"Текст '{старый_текст}' не найден на странице {page.number}")
        return False

    if только_первые_n > 0:
        области = области[:только_первые_n]

    for область in области:
        logger.info(f"Найдена область для '{старый_текст}': {область}")
        # Увеличиваем область редактирования, чтобы избежать наложения
        расширенная_область = fitz.Rect(
            область.x0 - 10, область.y0 - 10,
            область.x1 + 70, область.y1 + 10
        )
        page.add_redact_annot(расширенная_область, fill=(1, 1, 1))
    page.apply_redactions()

    for i, область in enumerate(области):
        смещение_y = date_offset_y if is_date else 0
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
        logger.info(f"Вставлен текст '{новый_текст}' на координаты: ({область.x0}, {область.y0 + смещение_y})")
    return True

def generate_pdf(путь_к_шаблону: str, текст: str, custom_date: datetime = None, output_dir: str = ".") -> str:
    дата = custom_date.strftime("%d.%m.%Y") if custom_date else текущая_дата_киев()
    имя_файла = очистить_имя_файла(текст) or "результат"
    путь_к_выходному_файлу = os.path.join(output_dir, f"{имя_файла}.pdf")

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
            elif "clean_template_no_text.pdf" in путь_к_шаблону:
                if page.number == 0:
                    заменить_текст_на_странице(page, "Client: ", f"Client: {текст}")
                if page.number == 4:
                    # Увеличиваем смещение для даты, чтобы избежать перекрытия с подписью
                    заменить_текст_на_странице(page, "Date: ", f"Date: {дата}", is_date=True, date_offset_y=30)
            else:
                if page.number == 0:
                    заменить_текст_на_странице(page, "Client: ", f"Client: {текст}")
                if page.number == 4:
                    заменить_текст_на_странице(page, "Date: ", f"Date: {дата}", is_date=True)

        doc.save(путь_к_выходному_файлу, garbage=4, deflate=True, clean=True)
        logger.info(f"PDF успешно сохранен: {путь_к_выходному_файлу}")
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {str(e)}")
        raise
    finally:
        doc.close()

    return путь_к_выходному_файлу
