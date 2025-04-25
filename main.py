import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from pdf_generator import generate_pdf

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения")

# Определяем доступные шаблоны
TEMPLATES = {
    "clean_template": "clean_template_no_text.pdf",
    "small_world": "template_small_world.pdf",
    "imperative": "template_imperative.pdf"
}

# Приветственное сообщение
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Выбрать шаблон 📄", callback_data="select_template")],
        [InlineKeyboardButton("О боте ℹ️", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Я бот для генерации PDF-документов.\n"
        "Выбери действие ниже ⬇️",
        reply_markup=reply_markup
    )

# Обработка кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "select_template":
        keyboard = [
            [InlineKeyboardButton("Clean Template", callback_data="template_clean_template")],
            [InlineKeyboardButton("Small World", callback_data="template_small_world")],
            [InlineKeyboardButton("Imperative", callback_data="template_imperative")],
            [InlineKeyboardButton("Начать заново 🔄", callback_data="start_over")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📄 Выбери шаблон для генерации PDF:",
            reply_markup=reply_markup
        )
    elif query.data == "about":
        keyboard = [
            [InlineKeyboardButton("Назад 🔙", callback_data="start_over")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "ℹ️ Я бот, который помогает генерировать PDF-документы на основе шаблонов.\n"
            "Выбери шаблон, укажи данные, и я создам документ для тебя! 🚀",
            reply_markup=reply_markup
        )
    elif query.data == "start_over":
        keyboard = [
            [InlineKeyboardButton("Выбрать шаблон 📄", callback_data="select_template")],
            [InlineKeyboardButton("О боте ℹ️", callback_data="about")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👋 Привет! Я бот для генерации PDF-документов.\n"
            "Выбери действие ниже ⬇️",
            reply_markup=reply_markup
        )
    elif query.data.startswith("template_"):
        template_key = query.data.split("template_")[1]
        context.user_data["selected_template"] = template_key
        keyboard = [
            [InlineKeyboardButton("Назад 🔙", callback_data="select_template")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📄 Вы выбрали шаблон: {template_key.replace('_', ' ').title()}.\n"
            "Теперь отправьте имя клиента (например, John Doe):",
            reply_markup=reply_markup
        )

# Обработка текстового ввода (имя клиента)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "selected_template" not in context.user_data:
        await update.message.reply_text("❌ Сначала выберите шаблон! Используйте /start.")
        return

    template_key = context.user_data["selected_template"]
    client_name = update.message.text.strip()
    
    try:
        template_path = TEMPLATES[template_key]
        pdf_path = generate_pdf(template_path, client_name)
        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(document=pdf_file, filename=f"{client_name}.pdf")
        os.remove(pdf_path)  # Удаляем временный файл
        await update.message.reply_text("✅ PDF успешно создан и отправлен!")
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {str(e)}")
        await update.message.reply_text(f"❌ Произошла ошибка при создании PDF: {str(e)}")

# Обработчик вебхука для проверки
async def webhook_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return "Bot is running"

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.Text & ~filters.Command, handle_text))

    # Настройка вебхука
    port = int(os.getenv("PORT", 8080))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="/telegram",
        webhook_url=f"https://telegram-pdf-bot-zu70.onrender.com/telegram"
    )
    logger.info(f"Запускаем сервер на порту {port}")
    logger.info("Бот успешно запущен")

if __name__ == "__main__":
    main()
