import logging
import asyncio
import os
import random
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.error import BadRequest
import config
from pdf_generator import generate_pdf
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SELECTING_TEMPLATE = 1
ENTERING_TEXT = 2
EDITING_DATE = 3
MAX_BOOKMARKS = 10
pdf_lock = asyncio.Lock()

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
    "СОТРУДНИК НА МЕБЕЛЬНЫЙ ЗАВОД трудом4000£": (
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
    "СОТРУДНИК НА ФЕРМУ (КОРОВЫ И ОВЦЫ) 3750£": (
        "Сотрудник на ферму, работа с коровами и овцами\n"
        "📍 Белфаст, Северная Ирландия\n"
        "💷 Зарплата: от 3750£ в месяц\n\n"
        "🐄 Обязанности:\n"
        "🍽 Кормление животных\n"
        "🧹 Уборка помещений\n"
        "🌾 Уход за пастбищами\n\n"
        "📅 График: пн–пт\n"
        "⏰ Рабочий день: от 8 до 12 часов\n"
        "🌙 Ночные дежурства с бонусами\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в домиках на ферме\n"
        "🍲 Бесплатное питание три раза в день\n"
        "💷 Авансы каждую неделю\n"
        "🎓 Обучение на месте\n"
        "🚌 Проезд до ближайшего города\n"
        "🥛 Скидки на фермерские продукты\n"
        "🛂 Полная визовая поддержка"
    ),
    "РАБОТНИК НА ЗАВОД БЫТОВОЙ ХИМИИ ECOVER 4100£": (
        "Работник на завод бытовой химии Ecover\n"
        "📍 Лондон\n"
        "💷 Зарплата: от 4100£ в месяц\n\n"
        "🧼 Обязанности:\n"
        "📦 Упаковка моющих средств\n"
        "🔍 Контроль качества\n"
        "🏭 Работа на линии розлива\n\n"
        "📅 График: 5 рабочих дней\n"
        "⏰ Смены: 8–12 часов\n"
        "🌙 Ночные смены с доплатой\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в комфортабельных квартирах\n"
        "🍲 Бесплатное питание на заводе\n"
        "💷 Выплаты аванса еженедельно\n"
        "🎓 Быстрое обучение\n"
        "🚌 Бесплатный транспорт\n"
        "🧴 Скидки на продукцию\n"
        "🛂 Полное сопровождение визы"
    ),
    "СОТРУДНИК НА ДРЕВООБРАБАТЫВАЮЩИЙ ЗАВОД 3950£": (
        "Сотрудник на деревообрабатывающий завод\n"
        "📍 Эдинбург, Шотландия\n"
        "💷 Зарплата: от 3950£ в месяц\n\n"
        "🪵 Обязанности:\n"
        "🛠 Обработка древесины\n"
        "📦 Упаковка изделий\n"
        "🔍 Проверка качества\n\n"
        "📅 График: 5/2\n"
        "⏰ Смены: от 8 до 12 часов\n"
        "🌙 Ночные смены с бонусами\n\n"
        "✅ Условия:\n"
        "🛌 Жилье в квартирах (2–3 чел.)\n"
        "🍲 Бесплатные обеды и ужины\n"
        "💷 Авансы раз в неделю\n"
        "🎓 Обучение на производстве\n"
        "🚌 Трансфер до завода\n"
        "🪚 Скидки на деревянные изделия\n"
        "🛂 Полная визовая помощь"
    ),
    "РАБОТНИК НА СКЛАД ADIDAS 3850£": (
        "Работник на склад спортивной одежды Adidas\n"
        "📍 Ливерпуль\n"
        "💷 Зарплата: от 3850£ в месяц\n\n"
        "👟 Обязанности:\n"
        "📦 Сортировка спортивной одежды\n"
        "🔍 Проверка заказов\n"
        "🏬 Работа со сканером\n\n"
        "📅 График: пн–пт\n"
        "⏰ Рабочий день: 8–12 часов\n"
        "🌙 Ночные смены с премией\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в современных квартирах\n"
        "🍲 Бесплатное питание на складе\n"
        "💷 Еженедельные авансы\n"
        "🎓 Быстрая адаптация\n"
        "🚌 Бесплатный трансфер\n"
        "👕 Скидки на одежду Adidas\n"
        "🛂 Полное сопровождение визы"
    ),
    "РАБОТНИК СОРТИРОВОЧНОГО СКЛАДА ОВОЩЕЙ И ФРУКТОВ 3700£": (
        "Работник сортировочного склада овощей и фруктов\n"
        "📍 Бристоль\n"
        "💷 Зарплата: от 3700£ в месяц\n\n"
        "🥕 Обязанности:\n"
        "📦 Сортировка овощей и фруктов\n"
        "🔍 Контроль свежести\n"
        "📦 Упаковка продукции\n\n"
        "📅 График: 5 рабочих дней\n"
        "⏰ Смены: 8–12 часов\n"
        "🌙 Ночные смены с доплатой\n\n"
        "✅ Условия:\n"
        "🛌 Комфортное жилье для работников\n"
        "🍲 Бесплатное питание\n"
        "💷 Авансы каждую неделю\n"
        "🎓 Обучение на месте\n"
        "🚌 Транспорт до склада\n"
        "🍎 Скидки на свежие продукты\n"
        "🛂 Полная визовая поддержка"
    ),
    "РАБОТНИК СКЛАДА APPLE 4200£": (
        "Работник на склад Apple\n"
        "📍 Лондон\n"
        "💷 Зарплата: от 4200£ в месяц\n\n"
        "📱 Обязанности:\n"
        "📦 Упаковка электроники\n"
        "🔍 Проверка комплектации\n"
        "🏬 Работа со сканером\n\n"
        "📅 График: 5/2\n"
        "⏰ Смены: 8–12 часов в день\n"
        "🌙 Ночные смены с бонусами\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в стильных квартирах\n"
        "🍲 Бесплатное трехразовое питание\n"
        "💷 Еженедельные авансы\n"
        "🎓 Быстрое обучение\n"
        "🚌 Бесплатный транспорт\n"
        "📱 Скидки на продукцию Apple\n"
        "🛂 Полная визовая помощь"
    ),
    "РАБОТНИК НА ПРОИЗВОДСТВО ЧАЯ LIPTON 3900£": (
        "Работник на производство чая Lipton\n"
        "📍 Норидж\n"
        "💷 Зарплата: от 3900£ в месяц\n\n"
        "☕ Обязанности:\n"
        "📦 Фасовка чая\n"
        "🔍 Контроль качества\n"
        "🏭 Работа на линии упаковки\n\n"
        "📅 График: пн–пт\n"
        "⏰ Рабочий день: от 8 до 12 часов\n"
        "🌙 Ночные смены с доплатой\n\n"
        "✅ Условия:\n"
        "🛌 Уютное жилье (2–3 чел.)\n"
        "🍲 Бесплатное питание на производстве\n"
        "💷 Авансы раз в неделю\n"
        "🎓 Обучение на месте\n"
        "🚌 Трансфер до завода\n"
        "🍵 Скидки на чай\n"
        "🛂 Полное сопровождение визы"
    ),
    "ВОДИТЕЛЬ-КУРЬЕР DHL 4100£": (
        "Водитель-курьер DHL\n"
        "📍 Глазго, Шотландия\n"
        "💷 Зарплата: от 4100£ в месяц\n\n"
        "🚚 Обязанности:\n"
        "📦 Доставка посылок\n"
        "🚗 Управление фургоном\n"
        "📲 Работа с маршрутами\n\n"
        "📅 График: 5 рабочих дней\n"
        "⏰ Смены: 8–12 часов\n"
        "🌙 Ночные маршруты с премией\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в комфортабельных квартирах\n"
        "🍲 Бесплатное питание\n"
        "💷 Еженедельные авансы\n"
        "🎓 Обучение на месте\n"
        "🚗 Предоставляется автомобиль\n"
        "📦 Скидки на услуги DHL\n"
        "🛂 Полная визовая поддержка"
    ),
    "РАБОТНИК НА СКЛАД JYSK 3800£": (
        "Работник на склад Jysk\n"
        "📍 Бирмингем\n"
        "💷 Зарплата: от 3800£ в месяц\n\n"
        "🛏 Обязанности:\n"
        "📦 Упаковка товаров для дома\n"
        "🔍 Проверка заказов\n"
        "🏬 Работа с погрузочной техникой\n\n"
        "📅 График: 5/2\n"
        "⏰ Смены: от 8 до 12 часов\n"
        "🌙 Ночные смены с бонусами\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в современных квартирах\n"
        "🍲 Бесплатное питание на складе\n"
        "💷 Авансы каждую неделю\n"
        "🎓 Быстрая адаптация\n"
        "🚌 Бесплатный трансфер\n"
        "🛋 Скидки на товары Jysk\n"
        "🛂 Полное сопровождение визы"
    ),
    "РАБОТНИК НА СКЛАД COCA-COLA 4000£": (
        "Работник на склад Coca-Cola\n"
        "📍 Белфаст, Северная Ирландия\n"
        "💷 Зарплата: от 4000£ в месяц\n\n"
        "🥤 Обязанности:\n"
        "📦 Упаковка напитков\n"
        "🔍 Контроль качества\n"
        "🏬 Работа со сканером\n\n"
        "📅 График: пн–пт\n"
        "⏰ Рабочий день: 8–12 часов\n"
        "🌙 Ночные смены с доплатой\n\n"
        "✅ Условия:\n"
        "🛌 Комфортное жилье для работников\n"
        "🍲 Бесплатное питание\n"
        "💷 Еженедельные авансы\n"
        "🎓 Обучение на месте\n"
        "🚌 Трансфер до склада\n"
        "🥤 Скидки на напитки\n"
        "🛂 Полная визовая поддержка"
    ),
    "РАБОТНИК ПОЧТОВОГО СКЛАДА UPS 3950£": (
        "Работник почтового склада UPS\n"
        "📍 Кардифф, Уэльс\n"
        "💷 Зарплата: от 3950£ в месяц\n\n"
        "📬 Обязанности:\n"
        "📦 Сортировка посылок\n"
        "🔍 Проверка адресов\n"
        "🏬 Работа с техникой\n\n"
        "📅 График: 5 рабочих дней\n"
        "⏰ Смены: 8–12 часов\n"
        "🌙 Ночные смены с премией\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в уютных квартирах\n"
        "🍲 Бесплатное питание на складе\n"
        "💷 Авансы раз в неделю\n"
        "🎓 Быстрое обучение\n"
        "🚌 Бесплатный транспорт\n"
        "📦 Скидки на услуги UPS\n"
        "🛂 Полная визовая помощь"
    ),
    "РАЗНОРАБОЧИЙ В СТУДИЮ ЛАНДШАФТНОГО ДИЗАЙНА 3750£": (
        "Разнорабочий в студию ландшафтного дизайна\n"
        "📍 Брайтон\n"
        "💷 Зарплата: от 3750£ в месяц\n\n"
        "🌳 Обязанности:\n"
        "🌱 Посадка деревьев и кустарников\n"
        "🧹 Уборка территории\n"
        "🛠 Помощь в создании дизайна\n\n"
        "📅 График: 5/2\n"
        "⏰ Рабочий день: 8–12 часов\n"
        "🌙 Вечерние смены с доплатой\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в стильных квартирах\n"
        "🍲 Бесплатное питание\n"
        "💷 Еженедельные авансы\n"
        "🎓 Обучение на месте\n"
        "🚌 Трансфер до объектов\n"
        "🌸 Скидки на услуги студии\n"
        "🛂 Полная визовая поддержка"
    ),
    "РАБОТНИК НА ПРОИЗВОДСТВО ПЕЧЕНЬЯ MCVITIE’S 3900£": (
        "Работник на производство печенья McVitie’s\n"
        "📍 Манчестер\n"
        "💷 Зарплата: от 3900£ в месяц\n\n"
        "🍪 Обязанности:\n"
        "📦 Упаковка печенья\n"
        "🔍 Проверка качества\n"
        "🏭 Работа на линии фасовки\n\n"
        "📅 График: пн–пт\n"
        "⏰ Смены: 8–12 часов\n"
        "🌙 Ночные смены с бонусами\n\n"
        "✅ Условия:\n"
        "🛌 Комфортное жилье (2–3 чел.)\n"
        "🍲 Бесплатное питание на заводе\n"
        "💷 Авансы каждую неделю\n"
        "🎓 Быстрая адаптация\n"
        "🚌 Бесплатный трансфер\n"
        "🍪 Скидки на печенье\n"
        "🛂 Полная визовая помощь"
    ),
    "СОТРУДНИК НА СКЛАД КОСМЕТИКИ L’ORÉAL 4000£": (
        "Сотрудник на склад косметики L’Oréal\n"
        "📍 Лондон\n"
        "💷 Зарплата: от 4000£ в месяц\n\n"
        "💄 Обязанности:\n"
        "📦 Упаковка косметической продукции\n"
        "🔍 Проверка заказов\n"
        "🏬 Работа со сканером\n\n"
        "📅 График: 5 рабочих дней\n"
        "⏰ Смены: от 8 до 12 часов\n"
        "🌙 Ночные смены с доплатой\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в современных квартирах\n"
        "🍲 Бесплатное питание\n"
        "💷 Еженедельные авансы\n"
        "🎓 Обучение на месте\n"
        "🚌 Трансфер до склада\n"
        "💅 Скидки на косметику\n"
        "🛂 Полная визовая поддержка"
    ),
    "РАБОТНИК НА СКЛАД КНИГ WATERSTONES 3800£": (
        "Работник на склад книг Waterstones\n"
        "📍 Эдинбург, Шотландия\n"
        "💷 Зарплата: от 3800£ в месяц\n\n"
        "📚 Обязанности:\n"
        "📦 Сортировка и упаковка книг\n"
        "🔍 Проверка заказов\n"
        "🏬 Работа с техникой\n\n"
        "📅 График: 5/2\n"
        "⏰ Рабочий день: 8–12 часов\n"
        "🌙 Ночные смены с премией\n\n"
        "✅ Условия:\n"
        "🛌 Уютное жилье для работников\n"
        "🍲 Бесплатное питание\n"
        "💷 Авансы раз в неделю\n"
        "🎓 Быстрое обучение\n"
        "🚌 Бесплатный транспорт\n"
        "📖 Скидки на книги\n"
        "🛂 Полная визовая помощь"
    ),
    "СОТРУДНИК В ЦЕХ УПАКОВКИ МОРЕПРОДУКТОВ 3850£": (
        "Сотрудник в цех упаковки морепродуктов\n"
        "📍 Абердин, Шотландия\n"
        "💷 Зарплата: от 3850£ в месяц\n\n"
        "🦞 Обязанности:\n"
        "📦 Упаковка рыбы и морепродуктов\n"
        "🔍 Контроль свежести\n"
        "🏭 Работа в холодильных цехах\n\n"
        "📅 График: пн–пт\n"
        "⏰ Смены: 8–12 часов\n"
        "🌙 Ночные смены с бонусами\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в комфортабельных квартирах\n"
        "🍲 Бесплатное питание\n"
        "💷 Еженедельные авансы\n"
        "🎓 Обучение на месте\n"
        "🚌 Трансфер до цеха\n"
        "🦑 Скидки на морепродукты\n"
        "🛂 Полная визовая поддержка"
    ),
    "РАБОТНИК НА ПРОИЗВОДСТВО КЕРАМИЧЕСКОЙ ПЛИТКИ 3950£": (
        "Работник на производство керамической плитки\n"
        "📍 Бристоль\n"
        "💷 Зарплата: от 3950£ в месяц\n\n"
        "🪨 Обязанности:\n"
        "📦 Упаковка плитки\n"
        "🔍 Проверка качества\n"
        "🏭 Работа на производственной линии\n\n"
        "📅 График: 5 рабочих дней\n"
        "⏰ Смены: от 8 до 12 часов\n"
        "🌙 Ночные смены с доплатой\n\n"
        "✅ Условия:\n"
        "🛌 Проживание в стильных квартирах\n"
        "🍲 Бесплатное питание на заводе\n"
        "💷 Авансы каждую неделю\n"
        "🎓 Быстрая адаптация\n"
        "🚌 Бесплатный трансфер\n"
        "🪨 Скидки на плитку\n"
        "🛂 Полная визовая помощь"
    ),
}

VACANCY_EMOJIS = {
    "УБОРЩИЦА HILTON 3700£": "🧹",
    "УПАКОВЩИК Cadbury 3900£": "🍫",
    "СТРОЙКА от 4500£": "🏗️",
    "СОРТИРОВЩИК ZARA 3850£": "👗",
    "ТЕПЛИЦА 3700£": "🌱",
    "ПРАЧЕЧНАЯ 3750£": "🧺",
    "L'Oréal 4000£": "💄",
    "РАБОТНИК НА СКЛАД АВТОЗАПЧАСТЕЙ MERCEDES 3700£": "🚗",
    "СОТРУДНИК НА ЛОШАДИНУЮ ФЕРМУ 3800£": "🐎",
    "РАБОТНИК НА ФАБРИКУ KIT-KAT 3900£": "🍬",
    "СОТРУДНИК НА МЕБЕЛЬНЫЙ ЗАВОД 4000£": "🪑",
    "СОТРУДНИК НА ФЕРМУ (КОРОВЫ И ОВЦЫ) 3750£": "🐄",
    "РАБОТНИК НА ЗАВОД БЫТОВОЙ ХИМИИ ECOVER 4100£": "🧼",
    "СОТРУДНИК НА ДРЕВООБРАБАТЫВАЮЩИЙ ЗАВОД 3950£": "🪵",
    "РАБОТНИК НА СКЛАД ADIDAS 3850£": "👟",
    "РАБОТНИК СОРТИРОВОЧНОГО СКЛАДА ОВОЩЕЙ И ФРУКТОВ 3700£": "🥕",
    "РАБОТНИК СКЛАДА APPLE 4200£": "📱",
    "РАБОТНИК НА ПРОИЗВОДСТВО ЧАЯ LIPTON 3900£": "☕",
    "ВОДИТЕЛЬ-КУРЬЕР DHL 4100£": "🚚",
    "РАБОТНИК НА СКЛАД JYSK 3800£": "🛏️",
    "РАБОТНИК НА СКЛАД COCA-COLA 4000£": "🥤",
    "РАБОТНИК ПОЧТОВОГО СКЛАДА UPS 3950£": "📬",
    "РАЗНОРАБОЧИЙ В СТУДИЮ ЛАНДШАФТНОГО ДИЗАЙНА 3750£": "🌳",
    "РАБОТНИК НА ПРОИЗВОДСТВО ПЕЧЕНЬЯ MCVITIE’S 3900£": "🍪",
    "СОТРУДНИК НА СКЛАД КОСМЕТИКИ L’ORÉAL 4000£": "💅",
    "РАБОТНИК НА СКЛАД КНИГ WATERSTONES 3800£": "📚",
    "СОТРУДНИК В ЦЕХ УПАКОВКИ МОРЕПРОДУКТОВ 3850£": "🦞",
    "РАБОТНИК НА ПРОИЗВОДСТВО КЕРАМИЧЕСКОЙ ПЛИТКИ 3950£": "🪨",
}

# Кэш для стикеров
STICKER_SET_NAME = "monke2004"
STICKERS = []

# Инициализация стикеров из стикерпака
async def init_stickers(application: Application) -> None:
    global STICKERS
    try:
        sticker_set = await application.bot.get_sticker_set(STICKER_SET_NAME)
        STICKERS = [sticker.file_id for sticker in sticker_set.stickers]
        logger.info(f"Loaded {len(STICKERS)} stickers from {STICKER_SET_NAME}")
    except Exception as e:
        logger.error(f"Failed to load stickers from {STICKER_SET_NAME}: {e}")

# Глобальный обработчик ошибок с отправкой случайного стикера
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    
    # Отправляем случайный стикер, если список стикеров не пуст
    if STICKERS:
        try:
            random_sticker = random.choice(STICKERS)
            if update.callback_query:
                await update.callback_query.message.reply_sticker(sticker=random_sticker)
            elif update.message:
                await update.message.reply_sticker(sticker=random_sticker)
        except Exception as e:
            logger.error(f"Failed to send sticker: {e}")
    
    # Отправляем текстовое сообщение об ошибке
    error_message = "Произошла ошибка. Пожалуйста, попробуйте снова."
    if update.callback_query:
        await update.callback_query.message.reply_text(error_message)
    elif update.message:
        await update.message.reply_text(error_message)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "bookmarks" in context.user_data and len(context.user_data["bookmarks"]) > MAX_BOOKMARKS:
        context.user_data["bookmarks"] = context.user_data["bookmarks"][-MAX_BOOKMARKS:]
    message = (
        "👋 *Добро пожаловать в PDF-бот!*\n\n"
        "Выберите шаблон, введите имя клиента — и получите PDF-файл 📄\n"
        "⚠️ Закладки сохраняются до перезапуска бота."
    )
    keyboard = [
        [
            InlineKeyboardButton("📄 Шаблоны", callback_data="select_template"),
            InlineKeyboardButton("ℹ️ О боте", callback_data="about"),
        ],
        [
            InlineKeyboardButton("💾 Сохраненные", callback_data="show_bookmarks"),
            InlineKeyboardButton("👷 Вакансии", callback_data="show_vacancies"),
        ],
    ]
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    message = (
        "ℹ️ *О боте*\n\n"
        "Этот бот помогает в работе с документами и вакансиями:\n"
        "- 📄 Генерирует PDF-договоры на основе шаблонов.\n"
        "- 📌 Сохраняет до 10 договоров в закладки с возможностью удаления.\n"
        "- 👷 Предоставляет список вакансий с подробным описанием.\n"
        "Автор: @sennudeswithboobs"
    )
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="main_menu")]]
    try:
        await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest as e:
        logger.error(f"Failed to edit message in about: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    message = "🏠 *Главное меню*\n\nВыберите действие:"
    keyboard = [
        [
            InlineKeyboardButton("📄 Шаблоны", callback_data="select_template"),
            InlineKeyboardButton("ℹ️ О боте", callback_data="about"),
        ],
        [
            InlineKeyboardButton("💾 Сохраненные", callback_data="show_bookmarks"),
            InlineKeyboardButton("👷 Вакансии", callback_data="show_vacancies"),
        ],
    ]
    try:
        await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest as e:
        logger.error(f"Failed to edit message in main_menu: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

async def select_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    message = "📄 *Выберите шаблон*:"
    keyboard = []
    for name in config.TEMPLATES.keys():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"template_{name}")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    try:
        await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data["state"] = SELECTING_TEMPLATE
    except BadRequest as e:
        logger.error(f"Failed to edit message in select_template: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

async def template_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    name = query.data.replace("template_", "")
    if name not in config.TEMPLATES:
        await query.message.edit_text("⚠️ Ошибка: Шаблон не найден.")
        return
    context.user_data["template"] = name
    context.user_data["state"] = ENTERING_TEXT
    try:
        await query.message.edit_text(
            f"✅ Шаблон выбран: *{name}*\n\nВведите имя клиента:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Сменить шаблон", callback_data="select_template")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
            ])
        )
    except BadRequest as e:
        logger.error(f"Failed to edit message in template_selected: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    try:
        await query.message.edit_text(
            "❌ Отменено. Выберите действие:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Шаблоны", callback_data="select_template")],
                [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
                [InlineKeyboardButton("💾 Сохраненные", callback_data="show_bookmarks")],
                [InlineKeyboardButton("👷 Вакансии", callback_data="show_vacancies")],
            ])
        )
    except BadRequest as e:
        logger.error(f"Failed to edit message in cancel: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "template" not in context.user_data:
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        await update.message.reply_text(
            "⚠️ Сначала выберите шаблон через меню.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if context.user_data.get("state") == EDITING_DATE:
        await receive_new_date(update, context)
        return

    client_name = update.message.text.strip()
    if len(client_name) > 50:
        await update.message.reply_text("⚠️ Имя клиента слишком длинное (макс. 50 символов).")
        return

    template_name = context.user_data["template"]
    async with pdf_lock:
        try:
            template_path = config.TEMPLATES[template_name]
            pdf_path = generate_pdf(template_path, client_name)
            filename = f"{client_name}.pdf"
            with open(pdf_path, "rb") as f:
                await update.message.reply_document(document=f, filename=filename)

            context.user_data["last_document"] = {
                "client_name": client_name,
                "template": template_name,
                "date": datetime.now().strftime("%d.%m.%Y")
            }

            keyboard = [
                [
                    InlineKeyboardButton("📌 В закладки", callback_data="add_bookmark"),
                    InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date"),
                ],
                [
                    InlineKeyboardButton("📄 К шаблонам", callback_data="select_template"),
                    InlineKeyboardButton("💾 Сохраненные", callback_data="show_bookmarks"),
                ],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            await update.message.reply_text(
                "✅ Документ создан!\nВведите имя клиента для генерации следующего договора, либо выберите другое действие:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

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
            f"⚠️ Достигнут лимит закладок ({MAX_BOOKMARKS}).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
        return

    document = context.user_data["last_document"]
    context.user_data["bookmarks"].append(document)
    bookmarks_count = len(context.user_data["bookmarks"])
    try:
        await query.message.edit_text(
            f"📌 Документ для *{document['client_name']}* добавлен в закладки!\n"
            f"У вас {bookmarks_count} сохраненных документов из {MAX_BOOKMARKS}.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Сохраненные", callback_data="show_bookmarks")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ])
        )
    except BadRequest as e:
        logger.error(f"Failed to edit message in add_bookmark: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

async def delete_all_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if "bookmarks" not in context.user_data or not context.user_data["bookmarks"]:
        await query.message.edit_text(
            "💾 У вас нет сохраненных документов.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Удалить все", callback_data="delete_all_bookmarks")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        return

    context.user_data["bookmarks"] = []
    try:
        await query.message.edit_text(
            f"🗑️ Все сохраненные документы удалены.\n"
            f"У вас 0 сохраненных документов из {MAX_BOOKMARKS}.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
    except BadRequest as e:
        logger.error(f"Failed to edit message in delete_all_bookmarks: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

async def show_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if "bookmarks" not in context.user_data or not context.user_data["bookmarks"]:
        await query.message.edit_text(
            f"💾 У вас нет сохраненных документов.\n"
            f"У вас 0 сохраненных документов из {MAX_BOOKMARKS}.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Удалить все", callback_data="delete_all_bookmarks")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        return

    message = "💾 *Сохраненные документы*:\n\n"
    keyboard = []
    for i, doc in enumerate(context.user_data["bookmarks"]):
        message += f"{i + 1}. {doc['client_name']} ({doc['template']}, {doc['date']})\n"
        keyboard.append([InlineKeyboardButton(
            f"{doc['client_name']} ({doc['date']})",
            callback_data=f"generate_bookmark_{i}"
        )])
    bookmarks_count = len(context.user_data["bookmarks"])
    message += f"\nУ вас {bookmarks_count} сохраненных документов из {MAX_BOOKMARKS}."
    keyboard.append([InlineKeyboardButton("🗑️ Удалить все", callback_data="delete_all_bookmarks")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])

    try:
        await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest as e:
        logger.error(f"Failed to edit message in show_bookmarks: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

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

    async with pdf_lock:
        try:
            template_path = config.TEMPLATES[template_name]
            pdf_path = generate_pdf(template_path, client_name, custom_date=date)
            filename = f"{client_name}.pdf"
            with open(pdf_path, "rb") as f:
                await query.message.reply_document(document=f, filename=filename)

            context.user_data["last_document"] = doc
            keyboard = [
                [
                    InlineKeyboardButton("📌 В закладки", callback_data="add_bookmark"),
                    InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date"),
                ],
                [
                    InlineKeyboardButton("📄 К шаблонам", callback_data="select_template"),
                    InlineKeyboardButton("💾 Сохраненные", callback_data="show_bookmarks"),
                ],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            await query.message.reply_text(
                "✅ Документ создан!\nВведите имя клиента для генерации следующего договора, либо выберите другое действие:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            try:
                os.remove(pdf_path)
            except OSError:
                logger.warning(f"Не удалось удалить временный файл {pdf_path}")
        except Exception as e:
            logger.error(f"Ошибка генерации PDF из закладки: {e}")
            await query.message.edit_text("❌ Ошибка при создании PDF.")

async def show_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    message = "👷 *Вакансии*:\n\nВыберите вакансию:"
    keyboard = []
    vacancy_list = list(VACANCIES.keys())
    
    for i, vacancy_name in enumerate(vacancy_list):
        emoji = VACANCY_EMOJIS.get(vacancy_name, "")
        callback_data = f"vacancy_{i}"
        logger.info(f"Creating button for {vacancy_name} with callback_data: {callback_data}")
        if len(callback_data.encode("utf-8")) > 64:
            logger.error(f"Callback data too long for {vacancy_name}: {callback_data}")
            await query.message.reply_text("Ошибка: данные кнопки слишком длинные.")
            return
        keyboard.append([InlineKeyboardButton(f"{emoji} {vacancy_name}", callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    try:
        await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest as e:
        logger.error(f"Failed to edit message in show_vacancies: {e}")
        await query.message.reply_text("Ошибка при отображении вакансий. Попробуйте снова.")

async def show_vacancy_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        index = int(query.data.replace("vacancy_", ""))
        vacancy_list = list(VACANCIES.keys())
        if index < 0 or index >= len(vacancy_list):
            await query.message.edit_text("⚠️ Вакансия не найдена.")
            return
        vacancy_name = vacancy_list[index]
        vacancy_text = VACANCIES[vacancy_name]
        # Форматируем текст как моноширинный с цитированием
        quoted_text = "\n".join(f"> {line}" for line in vacancy_text.split("\n"))
        message = f"*{vacancy_name}*\n\n```\n{quoted_text}\n```"
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к вакансиям", callback_data="show_vacancies")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        await query.message.edit_text(message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except ValueError:
        logger.error(f"Invalid vacancy index in callback_data: {query.data}")
        await query.message.edit_text("⚠️ Ошибка: некорректные данные вакансии.")
    except BadRequest as e:
        logger.error(f"Failed to edit message in show_vacancy_details: {e}")
        await query.message.reply_text("Ошибка при отображении деталей вакансии.")

async def request_new_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    logger.info("Нажата кнопка 'Изменить дату'")
    if "last_document" not in context.user_data:
        await query.message.edit_text("⚠️ Нет документа для редактирования даты.")
        return

    context.user_data["state"] = EDITING_DATE
    try:
        await query.message.edit_text(
            "📅 Введите новую дату в формате DD.MM.YYYY (например, 24.04.2025):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
            ])
        )
    except BadRequest as e:
        logger.error(f"Failed to edit message in request_new_date: {e}")
        await query.message.reply_text("Ошибка при обновлении сообщения.")

async def validate_date(date_str: str) -> bool:
    pattern = r"^\d{2}\.\d{2}\.\d{4}$"
    if not re.match(pattern, date_str):
        logger.warning(f"Invalid date format: {date_str}")
        return False
    try:
        day, month, year = map(int, date_str.split("."))
        if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
            logger.warning(f"Invalid date values: {date_str}")
            return False
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        logger.warning(f"Date parsing error: {date_str}")
        return False

async def receive_new_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        logger.warning("Получено обновление без текста сообщения")
        await update.message.reply_text("⚠️ Пожалуйста, введите дату.")
        return

    new_date = update.message.text.strip()
    logger.info(f"Получена дата: {new_date}")
    if not await validate_date(new_date):
        await update.message.reply_text(
            "⚠️ Неверный формат даты. Введите дату в формате DD.MM.YYYY (например, 24.04.2025):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]])
        )
        return

    document = context.user_data["last_document"]
    client_name = document["client_name"]
    template_name = document["template"]

    async with pdf_lock:
        try:
            template_path = config.TEMPLATES[template_name]
            pdf_path = generate_pdf(template_path, client_name, custom_date=new_date)
            filename = f"{client_name}.pdf"
            with open(pdf_path, "rb") as f:
                await update.message.reply_document(document=f, filename=filename)

            context.user_data["last_document"]["date"] = new_date
            keyboard = [
                [
                    InlineKeyboardButton("📌 В закладки", callback_data="add_bookmark"),
                    InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date"),
                ],
                [
                    InlineKeyboardButton("📄 К шаблонам", callback_data="select_template"),
                    InlineKeyboardButton("💾 Сохраненные", callback_data="show_bookmarks"),
                ],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            await update.message.reply_text(
                "✅ Документ создан!\nВведите имя клиента для генерации следующего договора, либо выберите другое действие:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data["state"] = ENTERING_TEXT

            try:
                os.remove(pdf_path)
            except OSError:
                logger.warning(f"Не удалось удалить временный файл {pdf_path}")
        except Exception as e:
            logger.error(f"Ошибка генерации PDF с новой датой: {e}")
            await update.message.reply_text("❌ Ошибка при создании PDF.")

async def check_webhook(context: ContextTypes.DEFAULT_TYPE):
    try:
        webhook_info = await context.bot.get_webhook_info()
        if webhook_info.url != config.WEBHOOK_URL:
            logger.warning("Вебхук сброшен, восстанавливаем...")
            await context.bot.set_webhook(url=config.WEBHOOK_URL)
    except Exception as e:
        logger.error(f"Ошибка проверки вебхука: {e}")

async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        if not update:
            logger.error("Невалидное обновление от Telegram")
            return web.Response(status=400, text="invalid update")
        await application.process_update(update)
        return web.Response(text="ok")
    except Exception as e:
        logger.error(f"Ошибка вебхука: {str(e)}")
        return web.Response(status=500, text="error")

async def home(request):
    return web.Response(text="Бот работает!")

async def main():
    global application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Инициализация стикеров
    await init_stickers(application)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(select_template, pattern="select_template"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    application.add_handler(CallbackQueryHandler(about, pattern="about"))
    application.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    application.add_handler(CallbackQueryHandler(template_selected, pattern="template_.*"))
    application.add_handler(CallbackQueryHandler(add_bookmark, pattern="add_bookmark"))
    application.add_handler(CallbackQueryHandler(show_bookmarks, pattern="show_bookmarks"))
    application.add_handler(CallbackQueryHandler(generate_bookmark, pattern="generate_bookmark_.*"))
    application.add_handler(CallbackQueryHandler(request_new_date, pattern="edit_date"))
    application.add_handler(CallbackQueryHandler(show_vacancies, pattern="show_vacancies"))
    application.add_handler(CallbackQueryHandler(show_vacancy_details, pattern="vacancy_.*"))
    application.add_handler(CallbackQueryHandler(delete_all_bookmarks, pattern="delete_all_bookmarks"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    application.add_error_handler(error_handler)

    await application.initialize()
    await application.bot.set_webhook(url=config.WEBHOOK_URL)
    await application.start()
    application.job_queue.run_repeating(check_webhook, interval=600)

    app = web.Application()
    app.router.add_post("/telegram", handle_webhook)
    app.router.add_get("/", home)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port=port)
    logger.info(f"Запускаем сервер на порту {port}")
    await site.start()

    logger.info("Бот успешно запущен")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
