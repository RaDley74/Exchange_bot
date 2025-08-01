import re
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
(
    ASK_PASSWORD,
    ADMIN_MENU,
    SETTINGS_MENU,
    SET_NEW_PASSWORD,
    SET_EXCHANGE_RATE,
    SET_WALLET,
    SET_SUPPORT
) = range(7)

# /start — вход в админ-панель


async def admin_panel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = config['User'].getint('admin_chat_id', None)
    print(f"Admin ID: {admin_id} | User ID: {update.effective_user.id}")
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
    print(f"Entered Password: {entered_password} | Correct Password: {correct_password}")
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
            # InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')
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
    admin_id = config['User'].getint('admin_chat_id', None)

    if update.effective_user.id != admin_id:
        await query.message.reply_text("🚫 У вас нет доступа к админ-панели.")
        return ConversationHandler.END

    if data == 'admin_info':

        exchange_rate = config['Settings'].get('exchange_rate', '—')
        wallet = config['Settings'].get('wallet_address', '—')
        support = config['Settings'].get('support_contact', '—')
        masked_password = '*' * len(config['Settings'].get('admin_password', ''))

        text = (
            "📊 <b>Информация о боте</b>\n\n"
            f"👤 <b>Admin ID:</b> <code>{admin_id}</code>\n"
            f"🔐 <b>Пароль:</b> <code>{masked_password}</code>\n"
            f"💱 <b>Курс:</b> <code>{exchange_rate}</code>\n"
            f"💼 <b>Кошелёк:</b> <code>{wallet}</code>\n"
            f"📞 <b>Поддержка:</b> <code>{support}</code>"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')

    elif data == 'admin_settings':

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Пароль", callback_data='set_password')],
            [InlineKeyboardButton("💱 Курс", callback_data='set_exchange_rate')],
            [InlineKeyboardButton("💼 Кошелёк", callback_data='set_wallet')],
            [InlineKeyboardButton("📞 Поддержка", callback_data='set_support')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')],
        ])
        await query.edit_message_text("⚙️ Настройки:", reply_markup=keyboard)
        return SETTINGS_MENU

    elif data == 'admin_back_menu':
        await query.message.delete()
        return await admin_panel_menu(query, context)

    elif data == 'set_password':
        await query.edit_message_text("🔐 Введите новый пароль:")
        return SET_NEW_PASSWORD

    elif data == 'set_exchange_rate':
        await query.edit_message_text("💱 Введите новый курс (например, 3.5):")
        return SET_EXCHANGE_RATE

    elif data == 'set_wallet':
        await query.edit_message_text("💼 Введите новый адрес кошелька:")
        return SET_WALLET

    elif data == 'set_support':
        await query.edit_message_text("📞 Введите новый контакт поддержки:")
        return SET_SUPPORT

    else:
        await query.edit_message_text(
            "⚠️ <b>Неизвестная команда админ-панели</b>.\n\n"
            "🛑 <i>Возможно, вы забыли закрыть админ-панель.</i>\n"
            "🔐 Используйте команду: /ac",
            parse_mode='HTML'
        )

        return ADMIN_MENU


async def set_new_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config['Settings']['admin_password'] = update.message.text.strip()
    with open('settings.ini', 'w') as config_file:
        config.write(config_file)
    await update.message.reply_text("✅ Пароль обновлён.")
    return await admin_panel_menu(update, context)


async def set_exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config['Settings']['exchange_rate'] = update.message.text.strip()
    with open('settings.ini', 'w') as config_file:
        config.write(config_file)
    await update.message.reply_text("✅ Курс обновлён.")
    return await admin_panel_menu(update, context)


async def set_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config['Settings']['wallet_address'] = update.message.text.strip()
    with open('settings.ini', 'w') as config_file:
        config.write(config_file)
    await update.message.reply_text("✅ Кошелёк обновлён.")
    return await admin_panel_menu(update, context)


async def set_support_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not re.fullmatch(r"[A-Za-z0-9@._\- ]+", update.message.text.strip()):
        await update.message.reply_text("❌ Недопустимый формат. Используйте только латиницу, цифры и символы @ . _ -")
        return SET_SUPPORT
    else:
        config['Settings']['support_contact'] = update.message.text.strip()

    with open('settings.ini', 'w') as config_file:
        config.write(config_file)
    await update.message.reply_text("✅ Контакт поддержки обновлён.")
    return await admin_panel_menu(update, context)


async def admin_panel_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = config['User'].getint('admin_chat_id', None)

    if update.effective_user.id != admin_id:
        await update.message.reply_text("🚫 У вас нет доступа к админ-панели.")
        return ConversationHandler.END

    await update.message.reply_text("🔒 Админ-панель закрыта.")
    return ConversationHandler.END
