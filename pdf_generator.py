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
    name = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    return re.sub(r"\s+", "_", name)


def вставить_текст_на_странице(
    page: fitz.Page,
    шаблон: str,
    поиск: str,
    новый_текст: str,
    is_date: bool = False,
    первые_n: int = 0
) -> bool:
    """
    Находит все вхождения `поиск` на странице и вставляет поверх `новый_текст`.
    Если is_date=True, текст сдвигается влево на 10 пунктов без вертикального смещения.
    """
    области = page.search_for(поиск)
    if not области:
        return False
    if первые_n > 0:
        области = области[:первые_n]

    for область in области:
        # смещение по X: сдвиг влево для даты
        смещение_x = -10 if is_date else 0
        # вертикального смещения нет
        смещение_y = 0
        page.insert_text(
            (область.x0 + смещение_x, область.y0 + смещение_y),
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
    - Без фонового затирания, текст накладывается поверх штампа/подписи.
    """
    дата = custom_date or текущая_дата_киев()
    base = очистить_имя_файла(имя_клиента) or "rezultat"
    имя_выходного = f"{base}.pdf"

    try:
        doc = fitz.open(путь_к_шаблону)
        for page in doc:
            # Вставка клиента
            вставить_текст_на_странице(
                page,
                путь_к_шаблону,
                "Client:",
                f"Client: {имя_клиента}",
                is_date=False,
                первые_n=1
            )
            # Вставка даты
            вставить_текст_на_странице(
                page,
                путь_к_шаблону,
                "Date:",
                f"Date: {дата}",
                is_date=True,
                первые_n=2
            )
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
        description="Генерация PDF на основе шаблона с подстановкой клиента и даты без фонового затирания."
    )
    parser.add_argument('template', help='Путь к PDF-шаблону')
    parser.add_argument('client', help='Имя клиента для вставки')
    parser.add_argument('--date', help='Дата в формате DD.MM.YYYY (по умолчанию киевская)', default=None)
    args = parser.parse_args()

    output = generate_pdf(args.template, args.client, args.date)
    print(f"Сгенерирован файл: {output}")
