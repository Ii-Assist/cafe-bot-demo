"""
Telegram-бот для кафе/ресторана
================================
Демо-проект для портфолио.

Функции:
- Просмотр меню по категориям
- Бронирование столика
- Информация о заведении (адрес, часы работы, контакты)
- Отзывы / обратная связь
- Акции и спецпредложения

Для запуска:
1. pip install python-telegram-bot
2. Получить токен у @BotFather в Telegram
3. Вставить токен в config.py
4. python bot.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, CAFE_INFO, MENU, PROMOS, ADMIN_CHAT_ID

# --- Логирование ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Состояния для бронирования ---
BOOKING_NAME, BOOKING_DATE, BOOKING_TIME, BOOKING_GUESTS = range(4)


# ==============================
#  ГЛАВНОЕ МЕНЮ
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и главное меню."""
    keyboard = [
        [InlineKeyboardButton("Меню", callback_data="menu")],
        [InlineKeyboardButton("Забронировать столик", callback_data="booking")],
        [InlineKeyboardButton("Акции", callback_data="promos")],
        [InlineKeyboardButton("О нас", callback_data="about")],
        [InlineKeyboardButton("Оставить отзыв", callback_data="feedback")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = (
        f"Добро пожаловать в {CAFE_INFO['name']}!\n\n"
        "Выберите, что вас интересует:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(welcome, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome, reply_markup=reply_markup)


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка 'Назад' — возврат в главное меню."""
    await start(update, context)


# ==============================
#  МЕНЮ ЗАВЕДЕНИЯ
# ==============================

async def show_menu_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать категории меню."""
    query = update.callback_query
    await query.answer()

    keyboard = []
    for category in MENU:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    keyboard.append([InlineKeyboardButton("< Назад", callback_data="main")])

    await query.edit_message_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_category_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать блюда из выбранной категории с фотографиями."""
    query = update.callback_query
    await query.answer()

    category = query.data.replace("cat_", "")
    items = MENU.get(category, [])

    # Удаляем старое сообщение (текстовое нельзя заменить на фото)
    try:
        await query.message.delete()
    except Exception:
        pass

    # Отправляем каждое блюдо с фотографией
    for item in items:
        caption = f"{item['name']} — {item['price']} руб."
        if item.get("desc"):
            caption += f"\n{item['desc']}"

        photo_url = item.get("photo")
        if photo_url:
            try:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=photo_url,
                    caption=caption,
                )
            except Exception:
                # Если фото не загрузилось, отправим текстом
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=caption,
                )
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=caption,
            )

    # Кнопки навигации в отдельном сообщении
    keyboard = [
        [InlineKeyboardButton("< К категориям", callback_data="menu")],
        [InlineKeyboardButton("<< Главное меню", callback_data="main")],
    ]
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"{category} — выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ==============================
#  БРОНИРОВАНИЕ
# ==============================

async def booking_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало бронирования — запрос имени."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Давайте забронируем столик!\n\n"
        "Введите ваше имя:"
    )
    return BOOKING_NAME


async def booking_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили имя, запрашиваем дату."""
    context.user_data["booking_name"] = update.message.text
    await update.message.reply_text(
        f"Отлично, {update.message.text}!\n\n"
        "На какую дату бронируем? (например: 20.02.2026)"
    )
    return BOOKING_DATE


async def booking_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили дату, запрашиваем время."""
    context.user_data["booking_date"] = update.message.text
    await update.message.reply_text("На какое время? (например: 19:00)")
    return BOOKING_TIME


async def booking_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили время, запрашиваем количество гостей."""
    context.user_data["booking_time"] = update.message.text
    await update.message.reply_text("Сколько гостей будет?")
    return BOOKING_GUESTS


async def booking_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили всё — подтверждаем бронь."""
    context.user_data["booking_guests"] = update.message.text
    data = context.user_data

    confirmation = (
        "Ваша бронь:\n\n"
        f"  Имя: {data['booking_name']}\n"
        f"  Дата: {data['booking_date']}\n"
        f"  Время: {data['booking_time']}\n"
        f"  Гостей: {data['booking_guests']}\n\n"
        "Мы свяжемся с вами для подтверждения.\n"
        f"Или позвоните нам: {CAFE_INFO['phone']}\n\n"
        "Спасибо!"
    )

    keyboard = [[InlineKeyboardButton("На главную", callback_data="main")]]
    await update.message.reply_text(confirmation, reply_markup=InlineKeyboardMarkup(keyboard))

    # Отправляем уведомление администратору
    user = update.effective_user
    admin_msg = (
        "🔔 Новая бронь!\n\n"
        f"Имя: {data['booking_name']}\n"
        f"Дата: {data['booking_date']}\n"
        f"Время: {data['booking_time']}\n"
        f"Гостей: {data['booking_guests']}\n\n"
        f"Клиент: {user.full_name}"
    )
    if user.username:
        admin_msg += f" (@{user.username})"
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)

    return ConversationHandler.END


async def booking_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена бронирования."""
    await update.message.reply_text("Бронирование отменено.")
    return ConversationHandler.END


# ==============================
#  АКЦИИ
# ==============================

async def show_promos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущие акции."""
    query = update.callback_query
    await query.answer()

    if not PROMOS:
        text = "Сейчас акций нет, но скоро появятся!"
    else:
        text = "Наши акции:\n\n"
        for promo in PROMOS:
            text += f"  *{promo['title']}*\n  {promo['desc']}\n\n"

    keyboard = [[InlineKeyboardButton("< Назад", callback_data="main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==============================
#  О НАС
# ==============================

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о заведении."""
    query = update.callback_query
    await query.answer()

    info = CAFE_INFO
    text = (
        f"*{info['name']}*\n\n"
        f"  Адрес: {info['address']}\n"
        f"  Телефон: {info['phone']}\n"
        f"  Часы работы: {info['hours']}\n\n"
        f"{info['description']}"
    )

    keyboard = [[InlineKeyboardButton("< Назад", callback_data="main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==============================
#  ОТЗЫВЫ
# ==============================

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало сбора отзыва."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Будем рады вашему отзыву!\n\n"
        "Напишите сообщение, и мы обязательно его прочитаем.\n"
        "(Для отмены введите /cancel)"
    )
    return 0


async def feedback_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили отзыв."""
    feedback_text = update.message.text
    user = update.effective_user

    logger.info("Отзыв от %s (@%s): %s", user.full_name, user.username, feedback_text)

    # Отправляем отзыв администратору
    admin_msg = (
        "💬 Новый отзыв!\n\n"
        f"От: {user.full_name}"
    )
    if user.username:
        admin_msg += f" (@{user.username})"
    admin_msg += f"\n\nТекст: {feedback_text}"
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)

    keyboard = [[InlineKeyboardButton("На главную", callback_data="main")]]
    await update.message.reply_text(
        "Спасибо за ваш отзыв! Мы ценим каждое мнение.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END


# ==============================
#  ЗАПУСК
# ==============================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Обработчик бронирования (ConversationHandler)
    booking_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(booking_start, pattern="^booking$")],
        states={
            BOOKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_name)],
            BOOKING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_date)],
            BOOKING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_time)],
            BOOKING_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_guests)],
        },
        fallbacks=[CommandHandler("cancel", booking_cancel)],
        per_message=False,
    )

    # Обработчик отзывов (ConversationHandler)
    feedback_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(feedback_start, pattern="^feedback$")],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_receive)],
        },
        fallbacks=[CommandHandler("cancel", booking_cancel)],
        per_message=False,
    )

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(booking_handler)
    app.add_handler(feedback_handler)
    app.add_handler(CallbackQueryHandler(show_menu_categories, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(show_category_items, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(show_promos, pattern="^promos$"))
    app.add_handler(CallbackQueryHandler(show_about, pattern="^about$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^main$"))

    logger.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
