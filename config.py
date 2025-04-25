import os

# Токен бота и другие параметры из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "7511704960:AAFKDWgg2-cAzRxywX1gXK47OQRWJi72qGw")
ADMIN_ID = os.getenv("ADMIN_ID", "6587507343")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://telegram-pdf-bot-1f5c.onrender.com/telegram")

# Путь к шаблонам PDF
TEMPLATES = {
    "clean_template": "clean_template_no_text.pdf",
    "small_world": "template_small_world.pdf",
    "imperative": "template_imperative.pdf"
}
