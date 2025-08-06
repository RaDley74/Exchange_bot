import logging
from telegram.ext import (
    ConversationHandler, ContextTypes
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import re

# Импортируем общие объекты и функции из config_manager
from config_manager import config, save_config, get_admin_ids

# --- Настройка логирования ---
logger = logging.getLogger(__name__)

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

async def admin_panel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) trying to access admin panel.")

    admin_ids = get_admin_ids()

    if not admin_ids:
        logger.warning("Admin panel access denied: Bot not activated (no admin_chat_id).")
        await update.message.reply_text("❌ Бот не активирован.\n\n⚠️ Пропишите /start ▶️")
        return ConversationHandler.END

    if user.id not in admin_ids:
        logger.warning(f"User {user.id} ({user.username}) denied access to admin panel.")
        await update.message.reply_text("🚫 У вас нет доступа к админ-панели.")
        return ConversationHandler.END

    logger.info(f"Admin {user.id} ({user.username}) is being asked for password.")
    await update.message.reply_text("Введите пароль для доступа к админ-панели:")
    return ASK_PASSWORD


async def admin_panel_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entered_password = update.message.text.strip()
    correct_password = config['Settings']['admin_password']
    user = update.effective_user

    if entered_password == correct_password:
        logger.info(f"Admin {user.id} ({user.username}) entered correct password.")
        return await admin_panel_menu(update, context)
    else:
        logger.warning(f"Admin {user.id} ({user.username}) entered incorrect password.")
        await update.message.reply_text("❌ Неверный пароль. Попробуйте снова:")
        return ASK_PASSWORD


async def admin_panel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Displaying main admin menu for {update.effective_user.id}.")
    keyboard = [
        [
            InlineKeyboardButton("📊 Информация", callback_data='admin_info'),
            InlineKeyboardButton("⚙️ Настройки", callback_data='admin_settings'),
        ],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "⚙️ Админ-панель",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            "⚙️ Админ-панель",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return ADMIN_MENU


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    logger.info(f"Admin {user.id} ({user.username}) selected admin panel option: {data}")

    admin_ids = get_admin_ids()

    if user.id not in admin_ids:
        logger.warning(f"Non-admin user {user.id} tried to use admin panel via callback.")
        await query.message.reply_text("🚫 У вас нет доступа к админ-панели.")
        return ConversationHandler.END

    if data == 'admin_info':
        exchange_rate = config['Settings'].get('exchange_rate', '—')
        wallet = config['Settings'].get('wallet_address', '—')
        support = config['Settings'].get('support_contact', '—')
        masked_password = '*' * len(config['Settings'].get('admin_password', ''))
        admin_ids_str = ', '.join(map(str, admin_ids))

        text = (
            "📊 <b>Информация о боте</b>\n\n"
            f"👤 <b>Admin IDs:</b> <code>{admin_ids_str}</code>\n"
            f"🔐 <b>Пароль:</b> <code>{masked_password}</code>\n"
            f"💱 <b>Курс:</b> <code>{exchange_rate}</code>\n"
            f"💼 <b>Кошелёк:</b> <code>{wallet}</code>\n"
            f"📞 <b>Поддержка:</b> <code>{support}</code>"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        return ADMIN_MENU

    elif data == 'admin_settings':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Пароль", callback_data='admin_set_password')],
            [InlineKeyboardButton("💱 Курс", callback_data='admin_set_exchange_rate')],
            [InlineKeyboardButton("💼 Кошелёк", callback_data='admin_set_wallet')],
            [InlineKeyboardButton("📞 Поддержка", callback_data='admin_set_support')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')],
        ])
        await query.edit_message_text("⚙️ Настройки:", reply_markup=keyboard)
        return SETTINGS_MENU

    elif data == 'admin_back_menu':
        return await admin_panel_menu(update, context)

    elif data == 'admin_set_password':
        await query.edit_message_text("🔐 Введите новый пароль:")
        return SET_NEW_PASSWORD

    elif data == 'admin_set_exchange_rate':
        await query.edit_message_text("💱 Введите новый курс (например, 41.5):")
        return SET_EXCHANGE_RATE

    elif data == 'admin_set_wallet':
        await query.edit_message_text("💼 Введите новый адрес кошелька:")
        return SET_WALLET

    elif data == 'admin_set_support':
        await query.edit_message_text("📞 Введите новый контакт поддержки:")
        return SET_SUPPORT

    else:
        logger.warning(f"Admin {user.id} triggered an unknown admin command: {data}")
        await query.edit_message_text(
            "⚠️ <b>Неизвестная команда админ-панели</b>.",
            parse_mode='HTML'
        )
        return ADMIN_MENU


async def set_new_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_password = update.message.text.strip()
    user = update.effective_user
    config['Settings']['admin_password'] = new_password
    await save_config()  # Асинхронное сохранение
    logger.info(f"Admin {user.id} updated the password.")
    await update.message.reply_text("✅ Пароль обновлён.")
    return await admin_panel_menu(update, context)


async def set_exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_rate = update.message.text.strip()
    user = update.effective_user
    try:
        float(new_rate)
        config['Settings']['exchange_rate'] = new_rate
        await save_config()  # Асинхронное сохранение
        logger.info(f"Admin {user.id} updated exchange rate to: {new_rate}")
        await update.message.reply_text("✅ Курс обновлён.")
    except ValueError:
        logger.warning(f"Admin {user.id} entered invalid exchange rate: {new_rate}")
        await update.message.reply_text("❌ Ошибка: введите корректное число.")
    return await admin_panel_menu(update, context)


async def set_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_wallet = update.message.text.strip()
    user = update.effective_user
    config['Settings']['wallet_address'] = new_wallet
    await save_config()  # Асинхронное сохранение
    logger.info(f"Admin {user.id} updated wallet address.")
    await update.message.reply_text("✅ Кошелёк обновлён.")
    return await admin_panel_menu(update, context)


async def set_support_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_support = update.message.text.strip()
    user = update.effective_user
    if not re.fullmatch(r"[A-Za-z0-9@._\- ]+", new_support):
        logger.warning(f"Admin {user.id} entered invalid support contact: {new_support}")
        await update.message.reply_text("❌ Недопустимый формат. Используйте только латиницу, цифры и символы @ . _ -")
        return SET_SUPPORT
    else:
        config['Settings']['support_contact'] = new_support
        await save_config()  # Асинхронное сохранение
        logger.info(f"Admin {user.id} updated support contact.")
        await update.message.reply_text("✅ Контакт поддержки обновлён.")
    return await admin_panel_menu(update, context)


async def admin_panel_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_ids = get_admin_ids()

    if user.id not in admin_ids:
        logger.warning(f"Non-admin user {user.id} tried to close admin panel.")
        await update.message.reply_text("🚫 У вас нет доступа к этой команде.")
        return ConversationHandler.END

    logger.info(f"Admin {user.id} closed the admin panel.")
    await update.message.reply_text("🔒 Админ-панель закрыта.")
    return ConversationHandler.END