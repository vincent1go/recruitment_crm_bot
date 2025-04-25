import logging
import asyncio
import os
import random
from datetime import datetime, timezone
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.error import TelegramError
import config
from pdf_generator import generate_pdf
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы для состояний
SELECTING_TEMPLATE = 1
ENTERING_TEXT = 2
EDITING_DATE = 3
MAX_BOOKMARKS = 10

# Глобальный лок для генерации PDF
pdf_lock = asyncio.Lock()

# Вакансии (предполагается, что это данные для шаблонов)
VACANCIES = {
    "УБОРЩИЦА HILTON 3700£": (
        "Уборщица в гостинице Hilton\n"
        "📍 Лондон\n"
        "💷 Зарплата: от 3700£ в месяц\n\n"
        "🧼 Обязанности:\n"
        "🛏 Уборка номеров и замена белья\n"
        "🧽 Поддержка чистоты в общественных зонах\n"
        "🚽 Уборка санузлов и смена расходников\n\n"
        "📅 График:\n"
        "📆 6 рабочих дней в неделю\n"
        "⏰ Смены по 8–10 часов\n"
        "💼 Возможность брать дополнительные часы\n\n"
        "✅ Условия:\n"
        "🏠 Жильё рядом (комната на 2–3 человек)\n"
        "🍽 Бесплатное питание 2 раза в день\n"
        "📝 Полное оформление по визе\n"
        "👕 Рабочая одежда и бытовая химия\n"
        "🌐 Wi-Fi в жилье\n"
        "💵 Еженедельные авансы\n"
        "🗣 Русскоязычный координатор"
    ),
    "УПАКОВЩИК Cadbury 3900£": (
        "Упаковщик на шоколадной фабрике Cadbury\n"
        "📍 Бирмингем\n"
        "💷 Зарплата: от 3900£ в месяц\n\n"
        "🍫 Обязанности:\n"
        "📦 Упаковка и сортировка продукции\n"
        "🔍 Проверка качества\n"
        "🏭 Работа на конвейере\n\n"
        "📅 График: 5/2\n"
        "⏰ Смены по 10–12 часов\n"
        "🌙 Ночные смены — выше ставка\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в квартирах (2–3 чел.)\n"
        "🍲 Бесплатный завтрак, обед и ужин\n"
        "💷 Авансы каждую неделю\n"
        "🎓 Обучение на месте\n"
        "🚌 Бесплатный трансфер\n"
        "🍬 Скидки на продукцию\n"
        "🛂 Полное визовое сопровождение"
    ),
    "СТРОЙКА от 4500£": (
        "Рабочий на строительный объект\n"
        "📍 Манчестер\n"
        "💷 Зарплата: от 4500£ в месяц\n\n"
        "🏗 Обязанности:\n"
        "🧱 Поднос стройматериалов\n"
        "🧹 Уборка территории\n"
        "🔨 Демонтаж/подготовка площадки\n\n"
        "📅 График:\n"
        "📆 5/2\n"
        "⏰ 8–12 часов в день\n"
        "💸 Переработки оплачиваются\n\n"
        "✅ Условия:\n"
        "🏢 Проживание в квартире (по 2-3 человека)\n"
        "💵 Еженедельные авансы\n"
        "👷 Спецодежда и обувь\n"
        "📈 Повышение зарплаты после 2 мес.\n"
        "🛂 Визовая поддержка\n"
        "🩺 Медстраховка"
    ),
    "СОРТИРОВЩИК ZARA 3850£": (
        "Сортировщик на складе Zara\n"
        "📍 Лондон\n"
        "💷 Зарплата: от 3850£ в месяц\n\n"
        "👚 Обязанности:\n"
        "📦 Сортировка и упаковка одежды\n"
        "🧾 Сканирование кодов\n"
        "🚛 Подготовка к отгрузке\n\n"
        "📅 График:\n"
        "📅 5/2\n"
        "⏰ Смены по 8–11 часов\n"
        "🎯 Премии за перевыполнение\n\n"
        "✅ Условия:\n"
        "🏡 Проживание в 10 минутах от места работы\n"
        "🍛 Питание за счёт компании\n"
        "🎓 Бесплатное обучение\n"
        "👕 Спецодежда\n"
        "🩺 Страховка"
    ),
    "ТЕПЛИЦА 3700£": (
        "Работник теплицы (овощи, клубника)\n"
        "📍 Кембридж\n"
        "💷 Зарплата: от 3700£ в месяц\n\n"
        "🌱 Обязанности:\n"
        "🍓 Сбор урожая\n"
        "📦 Упаковка\n"
        "💧 Полив и уход\n"
        "📅 График:\n"
        "📆 5/2, по 9-11 часов\n"
        "⏳ Сезон от 3 месяцев\n\n"
        "✅ Условия:\n"
        "🏕 Проживание в домиках (по 3 чел.)\n"
        "🍽 Завтрак, обед, ужин от работодателя\n"
        "🚿 Комфортный котедж. Душ, кухня, прачечная\n"
        "🚐 Трансфер на работу\n"
        "🛂 Виза + медосмотр за счёт работодателя\n"
        "🎁 Премии за перевыполнение"
    ),
    "ПРАЧЕЧНАЯ 3750£": (
        "Работник прачечной фабрики\n"
        "📍 Ливерпуль\n"
        "💷 Зарплата: от 3750£ в месяц\n\n"
        "🧺 Обязанности:\n"
        "🧼 Стирка и сушка белья\n"
        "📦 Упаковка\n"
        "🔍 Проверка качества\n\n"
        "📅 График:\n"
        "📅 5/2\n"
        "⏰ Смены 9–11 часов\n"
        "🌙 Ночные смены оплачиваются выше\n\n"
        "✅ Условия:\n"
        "🏠 Бесплатное жильё\n"
        "🍛 Завтрак, обед и ужин\n"
        "🌡 Комфортный цех\n"
        "👕 Рабочая одежда"
    ),
    "L'Oréal 4000£": (
        "Упаковщик на складе косметики L'Oréal\n"
        "📍 Лондон\n"
        "💷 Зарплата: от 4000£ в месяц\n\n"
        "💄 Обязанности:\n"
        "📦 Упаковка и маркировка\n"
        "🧴 Работа с косметикой\n"
        "🔍 Контроль качества\n\n"
        "📅 График:\n"
        "📅 5 дней в неделю\n"
        "⏰ Смены по 8–12 часов\n"
        "🎯 Премии за скорость и аккуратность\n\n"
        "✅ Условия:\n"
        "🏡 Жильё оплачивается\n"
        "🍽 Бесплатный обед\n"
        "🛁 Душ, кухня и зона отдыха\n"
        "📈 Повышение ЗП через 2 мес.\n"
        "🛂 Визовое оформление\n"
        "🧼 Чистый и современный склад"
    ),
    "РАБОТНИК НА СКЛАД АВТОЗАПЧАСТЕЙ MERCEDES 3700£": (
        "Работник на склад автозапчастей Mercedes\n"
        "📍 Манчестер\n"
        "💷 Зарплата: от 3700£ в месяц\n\n"
        "🚗 Обязанности:\n"
        "📦 Упаковка и сортировка автозапчастей\n"
        "🔍 Проверка качества\n"
        "🏬 Работа с техникой на складе\n\n"
        "📅 График: 5 рабочих дней в неделю\n"
        "⏰ Смены: от 8 до 12 часов\n"
        "🌙 Ночные смены с повышенной оплатой\n\n"
        "✅ Условия:\n"
        "🛌 Комфортное жилье (2–3 чел. в комнате)\n"
        "🍲 Бесплатные завтраки и обеды\n"
        "💷 Выплаты аванса каждую неделю\n"
        "🎓 Быстрое обучение на месте\n"
        "🚌 Транспорт до работы бесплатно\n"
        "🛠 Скидки на автозапчасти\n"
        "🛂 Полная поддержка с визой"
    ),
    "СОТРУДНИК НА ЛОШАДИНУЮ ФЕРМУ 3800£": (
        "Сотрудник на лошадиную ферму\n"
        "📍 Абердин, Шотландия\n"
        "💷 Зарплата: от 3800£ в месяц\n\n"
        "🐎 Обязанности:\n"
        "🧹 Чистка конюшен\n"
        "🍽 Кормление и уход за лошадьми\n"
        "🏞 Благоустройство территории\n\n"
        "📅 График: пн–пт\n"
        "⏰ Рабочий день: 8–12 часов\n"
        "🌙 Возможны ночные дежурства с бонусами\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в уютных домиках на ферме\n"
        "🍲 Полноценное питание за счет работодателя\n"
        "💷 Еженедельные авансы\n"
        "🎓 Вводное обучение\n"
        "🚌 Бесплатный проезд до города\n"
        "🐴 Скидки на верховую езду\n"
        "🛂 Полное сопровождение визы"
    ),
    "РАБОТНИК НА ФАБРИКУ KIT-KAT 3900£": (
        "Работник на фабрику Kit-Kat\n"
        "📍 Йорк\n"
        "💷 Зарплата: от 3900£ в месяц\n\n"
        "🍫 Обязанности:\n"
        "📦 Фасовка и упаковка шоколада\n"
        "🔍 Контроль качества продукции\n"
        "🏭 Работа на производственной линии\n\n"
        "📅 График: 5/2\n"
        "⏰ Смены: 8–12 часов в день\n"
        "🌙 Ночные смены с дополнительной премией\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в современных квартирах (2–3 чел.)\n"
        "🍲 Бесплатное трехразовое питание\n"
        "💷 Авансы каждую неделю\n"
        "🎓 Обучение на рабочем месте\n"
        "🚌 Бесплатный трансфер\n"
        "🍬 Скидки на сладости\n"
        "🛂 Полная визовая помощь"
    ),
    "СОТРУДНИК НА МЕБЕЛЬНЫЙ ЗАВОД 4000£": (
        "Сотрудник на мебельный завод\n"
        "📍 Кардифф, Уэльс\n"
        "💷 Зарплата: от 4000£ в месяц\n\n"
        "🪑 Обязанности:\n"
        "🛠 Сборка мебельных элементов\n"
        "📦 Упаковка готовой продукции\n"
        "🔍 Проверка качества\n\n"
        "📅 График: 5 дней в неделю\n"
        "⏰ Рабочие смены: 8–12 часов\n"
        "🌙 Ночные смены с повышенной ставкой\n\n"
        "✅ Условия:\n"
        "🛌 Уютное жилье для работников (2–3 чел.)\n"
        "🍲 Бесплатное питание на заводе\n"
        "💷 Еженедельные авансы\n"
        "🎓 Быстрая адаптация на месте\n"
        "🚌 Транспорт до работы\n"
        "🛋 Скидки на мебель\n"
        "🛂 Полная поддержка с визой"
    ),
}

# Функция для загрузки стикеров с обработкой ошибок
async def init_stickers(app: Application) -> None:
    try:
        sticker_set = await app.bot.get_sticker_set("monke2004")
        if sticker_set.stickers:
            app.bot_data["stickers"] = [sticker.file_id for sticker in sticker_set.stickers]
            logger.info(f"Loaded {len(app.bot_data['stickers'])} stickers from monke2004")
        else:
            logger.warning("Sticker set monke2004 is empty")
            app.bot_data["stickers"] = []
    except TelegramError as e:
        logger.error(f"Failed to load stickers from monke2004: {e}")
        app.bot_data["stickers"] = []

# Функция для проверки webhook
async def check_webhook(context: ContextTypes.DEFAULT_TYPE) -> None:
    webhook_info = await context.bot.get_webhook_info()
    if not webhook_info.url:
        logger.warning("Webhook not set, resetting...")
        await context.bot.set_webhook(f"{config.WEBHOOK_URL}/telegram")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    context.user_data.clear()
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот для создания договоров.\n"
        "Выберите шаблон или введите имя клиента для генерации договора:"
    )
    await show_templates(update, context)

# Отображение главного меню
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("📌 В закладки", callback_data="add_bookmark"),
            InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date"),
        ],
        [
            InlineKeyboardButton("📄 К шаблонам", callback_data="select_template"),
            InlineKeyboardButton("💾 Сохраненные", callback_data="show_bookmarks"),
        ],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(
        "✅ Документ создан!\nВведите имя клиента для генерации следующего договора, либо выберите другое действие:",
        reply_markup=reply_markup
    )

# Отображение списка шаблонов
async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"template_{name}")]
        for name in VACANCIES.keys()
    ]
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.edit_text(
            "Выберите шаблон:", reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Выберите шаблон:", reply_markup=reply_markup)

# Добавление в закладки
async def add_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if "current_template" not in context.user_data:
        await update.callback_query.message.reply_text("Сначала выберите шаблон!")
        return

    template_name = context.user_data["current_template"]
    if "bookmarks" not in context.user_data:
        context.user_data["bookmarks"] = []
    
    if len(context.user_data["bookmarks"]) >= MAX_BOOKMARKS:
        await update.callback_query.message.reply_text("Достигнут лимит закладок!")
        return
    
    if template_name not in context.user_data["bookmarks"]:
        context.user_data["bookmarks"].append(template_name)
        await update.callback_query.message.reply_text(f"Шаблон '{template_name}' добавлен в закладки!")
    else:
        await update.callback_query.message.reply_text(f"Шаблон '{template_name}' уже в закладках!")

# Показ сохраненных закладок
async def show_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bookmarks = context.user_data.get("bookmarks", [])
    if not bookmarks:
        await update.callback_query.message.edit_text("У вас нет сохраненных шаблонов!")
        return

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"template_{name}")]
        for name in bookmarks
    ]
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(
        "Ваши сохраненные шаблоны:", reply_markup=reply_markup
    )

# Обработка нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Подтверждаем callback сразу

    # Проверяем возраст сообщения
    message_date = query.message.date
    current_time = datetime.now(timezone.utc)
    time_diff = (current_time - message_date).total_seconds()

    if time_diff > 30:  # Если запрос старше 30 секунд
        logger.warning(f"Ignoring old callback query: {query.data}, age: {time_diff} seconds")
        return

    try:
        if query.data == "select_template":
            await show_templates(update, context)
        elif query.data == "add_bookmark":
            await add_bookmark(update, context)
        elif query.data == "show_bookmarks":
            await show_bookmarks(update, context)
        elif query.data == "edit_date":
            logger.info("Нажата кнопка 'Изменить дату'")
            context.user_data["state"] = EDITING_DATE
            await query.message.edit_text(
                "Введите новую дату в формате ДД.ММ.ГГГГ (например, 25.04.2025):"
            )
        elif query.data == "main_menu":
            await start(update, context)
        elif query.data.startswith("template_"):
            template_name = query.data[len("template_"):]
            context.user_data["current_template"] = template_name
            context.user_data["state"] = ENTERING_TEXT
            await query.message.edit_text(
                f"Вы выбрали шаблон: {template_name}\nВведите имя клиента:"
            )
    except TelegramError as e:
        logger.error(f"Error handling callback query {query.data}: {e}")

# Обработка текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    state = context.user_data.get("state")

    if state == ENTERING_TEXT:
        context.user_data["client_name"] = update.message.text
        context.user_data["state"] = None
        await generate_and_send_pdf(update, context)

    elif state == EDITING_DATE:
        date_str = update.message.text
        logger.info(f"Получена дата: {date_str}")
        try:
            # Проверяем формат даты
            new_date = datetime.strptime(date_str, "%d.%m.%Y")
            context.user_data["custom_date"] = new_date
            await update.message.reply_text(f"Дата обновлена: {date_str}")
            await show_main_menu(update, context)
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            await update.message.reply_text(
                "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 25.04.2025):"
            )

# Генерация и отправка PDF
async def generate_and_send_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    template_name = context.user_data.get("current_template")
    client_name = context.user_data.get("client_name")
    custom_date = context.user_data.get("custom_date", datetime.now())

    if not template_name or not client_name:
        await update.effective_message.reply_text("Ошибка: выберите шаблон и введите имя клиента!")
        return

    template_text = VACANCIES.get(template_name, "Шаблон не найден")
    async with pdf_lock:
        pdf_path = await generate_pdf(template_text, client_name, custom_date)
    
    with open(pdf_path, "rb") as pdf_file:
        await update.effective_message.reply_document(pdf_file, filename=f"contract_{client_name}.pdf")
    
    os.remove(pdf_path)  # Удаляем временный файл
    await show_main_menu(update, context)

    # Отправка случайного стикера, если они загружены
    stickers = context.bot_data.get("stickers", [])
    if stickers:
        await update.effective_message.reply_sticker(random.choice(stickers))

# Webhook обработчик
async def webhook(request: web.Request) -> web.Response:
    app = request.app["bot"]
    update = Update.de_json(await request.json(), app.bot)
    await app.process_update(update)
    return web.Response(status=200)

# Основная функция
async def main() -> None:
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Загружаем стикеры
    await init_stickers(app)

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Настраиваем webhook
    await app.bot.set_webhook(f"{config.WEBHOOK_URL}/telegram")
    app.job_queue.run_repeating(check_webhook, interval=3600, first=10)

    # Запускаем сервер
    web_app = web.Application()
    web_app["bot"] = app
    web_app.router.add_post("/telegram", webhook)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Запускаем сервер на порту 8080")

    # Запускаем бота
    await app.initialize()
    await app.start()
    logger.info("Бот успешно запущен")

    # Держим приложение запущенным
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
