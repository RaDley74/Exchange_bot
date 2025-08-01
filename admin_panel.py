from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
import configparser

# Читаем конфиг
config = configparser.ConfigParser()
config.read('settings.ini')

# Этапы разговора
[ASK_PASSWORD, ADMIN_MENU] = range(2)

# /start — вход в админ-панель


async def admin_panel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = context.bot_data.get('ADMIN_CHAT_ID')
    if admin_id is None:
        await update.message.reply_text("❌ Бот не активирован.\n\n⚠️ Пропишите /start ▶️")
        return ConversationHandler.END
    elif update.effective_user.id != admin_id:
        await update.message.reply_text("🚫 У вас нет доступа к админ-панели.")
        return ConversationHandler.END

    await update.message.reply_text("Введите пароль для доступа к админ-панели:")
    return ASK_PASSWORD


# Этап — проверка пароля
async def admin_panel_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entered_password = update.message.text.strip()
    correct_password = config['Settings']['admin_password']

    if entered_password == correct_password:
        return await admin_panel_menu(update, context)
    else:
        await update.message.reply_text("❌ Неверный пароль. Попробуйте снова:")
        return ASK_PASSWORD


# Этап — меню
async def admin_panel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📊 Информация", callback_data='admin_info'),
            InlineKeyboardButton("⚙️ Настройки", callback_data='admin_settings'),
            InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')
        ],
    ]
    await update.message.reply_text(
        "⚙️ Админ-панель",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_MENU


# Обработка кнопок
async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    admin_id = context.bot_data.get('ADMIN_CHAT_ID')

    if update.effective_user.id != admin_id:
        await query.message.reply_text("🚫 У вас нет доступа к админ-панели.")
        return ConversationHandler.END

    if data == 'admin_info':
        exchange_rate = float(config['Settings']['exchange_rate'])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Назад", callback_data='admin_back_menu')]
        ])
        await query.edit_message_text(
            f"📊 Информация о боте:\n\n 🆔 ADMIN_ID: {admin_id}\n\n Курс: {exchange_rate}",
            reply_markup=keyboard
        )

    elif data == 'admin_settings':
        await query.edit_message_text("⚙️ Настройки пока не реализованы.")

    elif data == 'admin_back_menu':
        await query.edit_message_text("Возвращаемся в меню.")
        # повторно показать меню
        return await admin_panel_menu(query, context)

    else:
        await query.edit_message_text("Неизвестная команда админ-панели.")

    return ADMIN_MENU


# Отмена / выход
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚪 Выход из админ-панели.")
    return ConversationHandler.END
