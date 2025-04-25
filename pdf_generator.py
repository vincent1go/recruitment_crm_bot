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
    """Возвращает текущую дату в формате ДД.ММ.ГГГГ по киевскому времени."""
    return datetime.now(pytz.timezone("Europe/Kiev")).strftime("%d.%m.%Y")

def очистить_имя_файла(текст):
    """Удаляет специальные символы из текста для создания безопасного имени файла."""
    return re.sub(r"[^\w\s-]", "", текст, flags=re.UNICODE).strip()

def найти_и_заменить_текст(страница, старый_текст, новый_текст, только_первые_n=0):
    """Находит и заменяет текст на странице PDF."""
    области = страница.search_for(старый_текст)
    if not области:
        logger.warning(f"Текст '{старый_текст}' не найден на странице {страница.number + 1}")
        return False

    if только_первые_n > 0:
        области = области[:только_первые_n]

    # Удаляем старый текст
    for область in области:
        страница.add_redact_annot(область, fill=(0, 0, 0, 0))  # Прозрачная заливка
    страница.apply_redactions()

    # Вставляем новый текст
    for область in области:
        # Смещаем текст вправо, чтобы он не наложился на метку
        x_offset = область.x0 + len(старый_текст) * 5  # Примерное смещение
        y_offset = область.y0
        страница.insert_text(
            (x_offset, y_offset),
            новый_текст,
            fontname="helv",
            fontsize=11,
            color=COLOR
        )
        logger.info(f"Вставлен текст '{новый_текст}' на странице {страница.number + 1}, позиция: ({x_offset}, {y_offset})")
    return True

def generate_pdf(путь_к_шаблону: str, текст: str, пользовательская_дата: datetime = None, выходная_папка: str = ".") -> str:
    """Генерирует PDF, заменяя текст в шаблоне."""
    logger.info(f"Генерация PDF с шаблоном '{путь_к_шаблону}' и текстом '{текст}'")
    дата = пользовательская_дата.strftime("%d.%m.%Y") if пользовательская_дата else текущая_дата_киев()
    имя_файла = очистить_имя_файла(текст) or "результат"
    путь_к_выходному_файлу = os.path.join(выходная_папка, f"{имя_файла}.pdf")

    try:
        документ = fitz.open(путь_к_шаблону)
    except Exception as e:
        logger.error(f"Ошибка открытия файла '{путь_к_шаблону}': {str(e)}")
        raise

    for страница in документ:
        logger.info(f"Обработка страницы {страница.number + 1}")
        
        # Определяем, является ли шаблон template_imperative.pdf
        это_imperative = "template_imperative.pdf" in путь_к_шаблону.lower()

        # Замена Client:
        if это_imperative:
            # Для template_imperative.pdf заменяем Client: только на первой странице
            if страница.number == 0:
                найти_и_заменить_текст(страница, "Client:", f"{текст}")
                найти_и_заменить_текст(страница, "Client: ", f"{текст}")
        else:
            # Для других шаблонов заменяем Client: на всех страницах
            найти_и_заменить_текст(страница, "Client:", f"{текст}")
            найти_и_заменить_текст(страница, "Client: ", f"{текст}")

        # Замена даты
        if это_imperative:
            # Для template_imperative.pdf заменяем DATE:
            найти_и_заменить_текст(страница, "DATE:", f"DATE: {дата}")
            найти_и_заменить_текст(страница, "DATE: ", f"DATE: {дата}")
        else:
            # Для других шаблонов заменяем Date:
            найти_и_заменить_текст(страница, "Date:", f"Date: {дата}", только_первые_n=2)  # Ограничиваем замену, чтобы избежать дублирования
            найти_и_заменить_текст(страница, "Date: ", f"Date: {дата}", только_первые_n=2)

    try:
        документ.save(путь_к_выходному_файлу, garbage=4, deflate=True, clean=True)
        logger.info(f"PDF сохранен как '{путь_к_выходному_файлу}'")
    except Exception as e:
        logger.error(f"Ошибка сохранения PDF: {str(e)}")
        raise
    finally:
        документ.close()

    return путь_к_выходному_файлу
