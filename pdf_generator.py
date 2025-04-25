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


def текущая_дата_киев() -> str:
    """Возвращает текущую дату в формате DD.MM.YYYY по часовому поясу Киева."""
    tz = pytz.timezone("Europe/Kiev")
    return datetime.now(tz).strftime("%d.%m.%Y")


def очистить_имя_файла(text: str) -> str:
    """Очищает строку для использования в имени файла."""
    # удаляем недопустимые символы
    name = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    # заменяем пробелы на подчеркивания
    return re.sub(r"[\s]+", "_", name)


def вставить_текст_на_странице(
    page: fitz.Page,
    шаблон: str,
    поиск: str,
    новый_текст: str,
    is_date: bool = False,
    первые_n: int = 0
) -> bool:
    """
    Находит на странице все вхождения текста `поиск` и накладывает сверху `новый_текст`.
    - is_date: смещает текст вниз, чтобы было "под" линией подписи.
    - первые_n: если >0, обрабатывает только первые N вхождений.
    """
    области = page.search_for(поиск)
    if not области:
        return False
    if первые_n > 0:
        области = области[:первые_n]

    for область in области:
        # смещение по Y: для даты чуть ниже линии
        смещение_y = 15 if is_date else 0
        # особое правило: если шаблон clean_template_no_text.pdf, можно подвинуть вверх,
        # чтобы не закрывать подпись
        if is_date and "clean_template_no_text.pdf" in os.path.basename(шаблон):
            смещение_y = -5
        page.insert_text(
            (область.x0, область.y0 + смещение_y),
            новый_текст,
            fontname="helv",
            fontsize=11,
            color=COLOR
        )
    return True


def generate_pdf(
    путь_к_шаблону: str,
    имя_клиента: str,
    custom_date: str = None
) -> str:
    """
    Генерирует PDF на основе шаблона:
    - Вставляет имя клиента вместо поля Client.
    - Вставляет дату (текущую или custom_date) вместо поля Date.
    - Не затирает фон и не скрывает подписи/штампы.
    """
    дата = custom_date or текущая_дата_киев()
    base = очистить_имя_файла(имя_клиента) or "результат"
    имя_выходного = f"{base}.pdf"

    try:
        doc = fitz.open(путь_к_шаблону)
        for page in doc:
            # поле Client
            вставить_текст_на_странице(
                page,
                путь_к_шаблону,
                "Client:",
                f"Client: {имя_клиента}",
                is_date=False,
                первые_n=1
            )
            # поле Date
            вставить_текст_на_странице(
                page,
                путь_к_шаблону,
                "Date:",
                f"Date: {дата}",
                is_date=True,
                первые_n=2
            )
        # сохраняем без дополнительных redactions
        doc.save(
            имя_выходного,
            garbage=4,
            deflate=True,
            clean=True
        )
        logger.info(f"PDF сохранён: {имя_выходного}")
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {e}")
        raise
    finally:
        doc.close()

    return имя_выходного


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Генерация PDF на основе шаблона с подстановкой клиента и даты без затирания подписей."
    )
    parser.add_argument('template', help='Путь к PDF-шаблону')
    parser.add_argument('client', help='Имя клиента для вставки')
    parser.add_argument('--date', help='Дата в формате DD.MM.YYYY (по умолчанию киевская)', default=None)
    args = parser.parse_args()

    output = generate_pdf(args.template, args.client, args.date)
    print(f"Сгенерирован файл: {output}")
