import logging
import asyncio
import os
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import config
from pdf_generator import generate_pdf
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SELECTING_TEMPLATE = 1
ENTERING_TEXT = 2
EDITING_DATE = 3
MAX_BOOKMARKS = 10  # Ограничение на количество закладок на пользователя

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "👋 *Добро пожаловать в PDF-бот!*\n\n"
        "Выберите шаблон, введите имя клиента — и получите PDF-файл 📄\n"
        "⚠️ Закладки сохраняются до перезапуска бота."
    )
    keyboard = [
        [
            InlineKeyboardButton("📄 Выбрать шаблон", callback_data="select_template"),
            InlineKeyboardButton("ℹ️ О боте", callback_data="about"),
        ],
        [InlineKeyboardButton("📑 Сохраненные договоры", callback_data="show_bookmarks")]
    ]
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    message = (
        "ℹ️ *О боте*\n\n"
        "Бот генерирует PDF-документы на основе шаблонов.\n"
        "Автор: @vincent1go\n"
        "[GitHub](https://github.com/vincent1go/telegram-pdf-bot)"
    )
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="main_menu")]]
    await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    message = "🏠 *Главное меню*\n\nВыберите действие:"
    keyboard = [
        [
            InlineKeyboardButton("📄 Выбрать шаблон", callback_data="select_template"),
            InlineKeyboardButton("ℹ️ О боте", callback_data="about"),
        ],
        [InlineKeyboardButton("📑 Сохраненные договоры", callback_data="show_bookmarks")]
    ]
    await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def select_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    message = "📄 *Выберите шаблон*:"
    keyboard = []
    for name in config.TEMPLATES.keys():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"template_{name}")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["state"] = SELECTING_TEMPLATE

async def template_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    name = query.data.replace("template_", "")
    if name not in config.TEMPLATES:
        await query.message.edit_text("⚠️ Ошибка: Шаблон не найден.")
        return
    context.user_data["template"] = name
    context.user_data["state"] = ENTERING_TEXT
    await query.message.edit_text(
        f"✅ Шаблон выбран: *{name}*\n\nВведите имя клиента:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Сменить шаблон", callback_data="select_template")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
        ])
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.message.edit_text("❌ Отменено. Выберите действие:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Выбрать шаблон", callback_data="select_template")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton("📑 Сохраненные договоры", callback_data="show_bookmarks")]
    ]))

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "template" not in context.user_data:
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        await update.message.reply_text(
            "⚠️ Сначала выберите шаблон через меню.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if context.user_data.get("state") == EDITING_DATE:
        await edit_date(update, context)
        return

    client_name = update.message.text.strip()
    template_name = context.user_data["template"]
    try:
        template_path = config.TEMPLATES[template_name]
        pdf_path = generate_pdf(template_path, client_name)
        filename = f"{client_name}.pdf"
        with open(pdf_path, "rb") as f:
            await update.message.reply_document(document=f, filename=filename)

        # Сохраняем параметры последнего документа
        context.user_data["last_document"] = {
            "client_name": client_name,
            "template": template_name,
            "date": datetime.now().strftime("%d.%m.%Y")
        }

        keyboard = [
            [InlineKeyboardButton("📌 В закладки", callback_data="add_bookmark")],
            [InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date")],
            [InlineKeyboardButton("📄 Новый шаблон", callback_data="select_template")],
        ]
        await update.message.reply_text(
            "✅ Документ создан!\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Удаляем временный PDF-файл для экономии места
        try:
            os.remove(pdf_path)
        except OSError:
            logger.warning(f"Не удалось удалить временный файл {pdf_path}")
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {e}")
        await update.message.reply_text("❌ Ошибка при создании PDF.")

async def add_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if "last_document" not in context.user_data:
        await query.message.edit_text("⚠️ Нет документа для добавления в закладки.")
        return

    if "bookmarks" not in context.user_data:
        context.user_data["bookmarks"] = []

    if len(context.user_data["bookmarks"]) >= MAX_BOOKMARKS:
        await query.message.edit_text(
            f"⚠️ Достигнут лимит закладок ({MAX_BOOKMARKS}). Удалите старые или перезапустите бота.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
        return

    document = context.user_data["last_document"]
    context.user_data["bookmarks"].append(document)
    await query.message.edit_text(
        f"📌 Документ для *{document['client_name']}* добавлен в закладки!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📑 Сохраненные договоры", callback_data="show_bookmarks")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ])
    )

async def show_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if "bookmarks" not in context.user_data or not context.user_data["bookmarks"]:
        await query.message.edit_text(
            "📑 У вас нет сохраненных договоров.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
        return

    message = "📑 *Сохраненные договоры*:\n\n"
    keyboard = []
    for i, doc in enumerate(context.user_data["bookmarks"]):
        message += f"{i + 1}. {doc['client_name']} ({doc['template']}, {doc['date']})\n"
        keyboard.append([InlineKeyboardButton(
            f"{doc['client_name']} ({doc['date']})",
            callback_data=f"generate_bookmark_{i}"
        )])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])

    await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def generate_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    index = int(query.data.replace("generate_bookmark_", ""))
    if "bookmarks" not in context.user_data or index >= len(context.user_data["bookmarks"]):
        await query.message.edit_text("⚠️ Документ не найден.")
        return

    doc = context.user_data["bookmarks"][index]
    client_name = doc["client_name"]
    template_name = doc["template"]
    date = doc["date"]

    try:
        template_path = config.TEMPLATES[template_name]
        pdf_path = generate_pdf(template_path, client_name, custom_date=date)
        filename = f"{client_name}.pdf"
        with open(pdf_path, "rb") as f:
            await query.message.reply_document(document=f, filename=filename)

        context.user_data["last_document"] = doc  # Обновляем последний документ
        keyboard = [
            [InlineKeyboardButton("📌 В закладки", callback_data="add_bookmark")],
            [InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date")],
            [InlineKeyboardButton("📑 Сохраненные договоры", callback_data="show_bookmarks")],
        ]
        await query.message.edit_text(
            f"✅ Документ для *{client_name}* сгенерирован!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Удаляем временный PDF-файл
        try:
            os.remove(pdf_path)
        except OSError:
            logger.warning(f"Не удалось удалить временный файл {pdf_path}")
    except Exception as e:
        logger.error(f"Ошибка генерации PDF из закладки: {e}")
        await query.message.edit_text("❌ Ошибка при создании PDF.")

async def edit_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if "last_document" not in context.user_data:
        await query.message.edit_text("⚠️ Нет документа для редактирования даты.")
        return

    context.user_data["state"] = EDITING_DATE
    await query.message.edit_text(
        "📅 Введите новую дату в формате DD.MM.YYYY (например, 24.04.2025):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ])
    )

async def validate_date(date_str: str) -> bool:
    pattern = r"^\d{2}\.\d{2}\.\d{4}$"
    if not re.match(pattern, date_str):
        return False
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

async def edit_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    new_date = update.message.text.strip()
    if not validate_date(new_date):
        await update.message.reply_text(
            "⚠️ Неверный формат даты. Введите дату в формате DD.MM.YYYY (например, 24.04.2025):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]])
        )
        return

    document = context.user_data["last_document"]
    client_name = document["client_name"]
    template_name = document["template"]

    try:
        template_path = config.TEMPLATES[template_name]
        pdf_path = generate_pdf(template_path, client_name, custom_date=new_date)
        filename = f"{client_name}.pdf"
        with open(pdf_path, "rb") as f:
            await update.message.reply_document(document=f, filename=filename)

        context.user_data["last_document"]["date"] = new_date
        keyboard = [
            [InlineKeyboardButton("📌 В закладки", callback_data="add_bookmark")],
            [InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date")],
            [InlineKeyboardButton("📄 Новый шаблон", callback_data="select_template")],
        ]
        await update.message.reply_text(
            f"✅ Документ с датой {new_date} создан!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["state"] = ENTERING_TEXT

        # Удаляем временный PDF-файл
        try:
            os.remove(pdf_path)
        except OSError:
            logger.warning(f"Не удалось удалить временный файл {pdf_path}")
    except Exception as e:
        logger.error(f"Ошибка генерации PDF с новой датой: {e}")
        await update.message.reply_text("❌ Ошибка при создании PDF.")

# === Webhook ===

async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(text="ok")
    except Exception as e:
        logger.exception("Ошибка вебхука:")
        return web.Response(status=500, text="error")

async def home(request):
    return web.Response(text="Бот работает!")

# === Запуск ===

async def main():
    global application
    application = Application.builder().token(config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(select_template, pattern="select_template"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    application.add_handler(CallbackQueryHandler(about, pattern="about"))
    application.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    application.add_handler(CallbackQueryHandler(template_selected, pattern="template_.*"))
    application.add_handler(CallbackQueryHandler(add_bookmark, pattern="add_bookmark"))
    application.add_handler(CallbackQueryHandler(show_bookmarks, pattern="show_bookmarks"))
    application.add_handler(CallbackQueryHandler(generate_bookmark, pattern="generate_bookmark_.*"))
    application.add_handler(CallbackQueryHandler(edit_date, pattern="edit_date"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))

    await application.initialize()
    await application.bot.set_webhook(url=config.WEBHOOK_URL)
    await application.start()

    app = web.Application()
    app.router.add_post("/telegram", handle_webhook)
    app.router.add_get("/", home)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port=8080)
    await site.start()

    logger.info("Бот успешно запущен на порту 8080")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
