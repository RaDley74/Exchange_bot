from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, MenuButtonCommands
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import configparser
import os
import admin_panel
import warnings
import logging

# --- Настройка логирования ---
# Устанавливаем базовую конфигурацию для логирования.
# Логи будут записываться в файл 'bot.log' и выводиться в консоль.
# Уровень логирования INFO означает, что будут записываться все информационные сообщения и выше (WARNING, ERROR, CRITICAL).
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
# Получаем объект логгера для текущего модуля.
logger = logging.getLogger(__name__)

# Подавляем INFO-логи от библиотеки httpx, чтобы не засорять вывод
logging.getLogger("httpx").setLevel(logging.WARNING)


warnings.filterwarnings("ignore", category=UserWarning)


(
    CHOOSING_CURRENCY,
    ENTERING_AMOUNT,
    ENTERING_BANK_NAME,
    ENTERING_CARD_DETAILS,
    ENTERING_FIO_DETAILS,
    ENTERING_INN_DETAILS,
    CONFIRMING_EXCHANGE,
    CONFIRMING_EXCHANGE_TRX,
    ENTERING_TRX_ADDRESS,
    FINAL_CONFIRMING_EXCHANGE_TRX
) = range(10)

config_file_name = 'settings.ini'
config = configparser.ConfigParser()
user_sessions = {}

if not os.path.exists(config_file_name):
    logger.warning(f"Configuration file '{config_file_name}' not found. Creating a new one.")
    config['User'] = {
        'TOKEN': 'your_token_here',
        'ADMIN_CHAT_ID': 'your_admin_chat_id_here',
    }
    config['Settings'] = {
        'EXCHANGE_RATE': '41.2',
        'ADMIN_PASSWORD': 'your_admin_id_here',
        'WALLET_ADDRESS': 'your_wallet_address_here',
        'SUPPORT_CONTACT': 'your_support_contact_here'
    }

    with open(config_file_name, 'w') as config_file:
        config.write(config_file)

    logger.info(f"Configuration file '{config_file_name}' created. Please edit it and restart.")
    print(
        f"Configuration file '{config_file_name}' created. Please edit it with your token and admin chat ID, then restart the script.")
    input("Press Enter to exit...")
    exit(0)

else:
    config.read(config_file_name)
    logger.info(f"Configuration file '{config_file_name}' loaded successfully.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot.")
    config.read(config_file_name)
    context.bot_data['ADMIN_CHAT_ID'] = int(config['User']['admin_chat_id'])

    keyboard = [
        [
            InlineKeyboardButton("➸ Обменять", callback_data='exchange'),
            InlineKeyboardButton("📉 Курс", callback_data='rate'),
            InlineKeyboardButton("🛠 Помощь", callback_data='user_help'),
        ],
    ]
    text = (
        "👋 Привет! Добро пожаловать в SafePay Bot 💱\n\n"
        "🧲 Обмен быстрый и удобный.\n\n"
        "🌟 Выбери раздел:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    logger.info(f"User {user.id} ({user.username}) selected menu option: {data}")

    config.read(config_file_name)

    if data == 'rate':
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
        ]
        await query.edit_message_text(f"📉 Актуальный курс: 1 USDT = {float(config['Settings']['exchange_rate'])} UAH", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'exchange':
        keyboard = [
            [InlineKeyboardButton("USDT", callback_data='currency_usdt')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
        ]
        await query.edit_message_text("💱 Выберите валюту для обмена:",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return CHOOSING_CURRENCY

    elif data == 'user_help':
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
        ]
        await query.edit_message_text(
            f"🔧 Помощь: Напиши {config['Settings']['SUPPORT_CONTACT']} по любым вопросам относительно бота.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == 'back_to_menu':
        await start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


async def choosing_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == 'currency_usdt':
        context.user_data['currency'] = 'USDT'
        logger.info(
            f"User {user.id} ({user.username}) chose currency: {context.user_data['currency']}")
        await query.message.chat.send_message(f"💰 Введите сумму для обмена (в {context.user_data['currency']}):")
        return ENTERING_AMOUNT

    elif data == 'back_to_menu':
        logger.info(
            f"User {user.id} ({user.username}) returned to the main menu from currency selection.")
        await start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


async def entering_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    try:
        amount = float(text.replace(',', '.'))
        if amount <= 0:
            logger.warning(
                f"User {user.id} ({user.username}) entered a non-positive amount: {amount}")
            await update.message.reply_text("Введите число больше нуля.")
            return ENTERING_AMOUNT
    except ValueError:
        logger.warning(f"User {user.id} ({user.username}) entered an invalid amount: '{text}'")
        await update.message.reply_text("Пожалуйста, введите корректное число.")
        return ENTERING_AMOUNT

    context.user_data['amount'] = amount
    currency = context.user_data.get('currency', 'USDT')
    sum_uah = amount * float(config['Settings']['exchange_rate'])
    context.user_data['sum_uah'] = sum_uah
    logger.info(
        f"User {user.id} ({user.username}) entered amount: {amount} {currency}. Calculated sum: {sum_uah:.2f} UAH.")

    await update.message.reply_text(
        f"✅ Хорошо! К оплате: {sum_uah:.2f} UAH.\n\n🏦 Пожалуйста, укажите название банка, с которого будет производиться обмен (например, 'ПриватБанк', 'Монобанк' и т.д.).\n"
    )
    return ENTERING_BANK_NAME


async def entering_bank_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bank_name = update.message.text.strip()
    user = update.effective_user
    if not bank_name:
        logger.warning(f"User {user.id} ({user.username}) entered an empty bank name.")
        await update.message.reply_text("Пожалуйста, введите корректное название банка.")
        return ENTERING_BANK_NAME

    context.user_data['bank_name'] = bank_name
    logger.info(f"User {user.id} ({user.username}) entered bank name: {bank_name}")

    await update.message.reply_text(
        f"🏦 Вы указали банк: {bank_name}\n\n"
        "💳 Введите реквизиты вашей банковской карты (номер карты или IBAN):"
    )

    return ENTERING_CARD_DETAILS


async def entering_card_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card_info = update.message.text.strip()
    user = update.effective_user
    if not card_info:
        logger.warning(f"User {user.id} ({user.username}) entered empty card details.")
        await update.message.reply_text("Пожалуйста, введите корректные реквизиты.")
        return ENTERING_CARD_DETAILS

    context.user_data['card_info'] = card_info
    # Не логируем сами реквизиты
    logger.info(f"User {user.id} ({user.username}) entered card details.")

    await update.message.reply_text(
        f"💳 Вы указали реквизиты: {card_info}\n\n"
        f"👤 Укажите ФИО для зачисления средств:"
    )

    return ENTERING_FIO_DETAILS


async def entering_fio_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fio = update.message.text.strip()
    user = update.effective_user
    if not fio:
        logger.warning(f"User {user.id} ({user.username}) entered empty FIO.")
        await update.message.reply_text("Пожалуйста, введите корректные ФИО.")
        return ENTERING_FIO_DETAILS

    context.user_data['fio'] = fio
    logger.info(f"User {user.id} ({user.username}) entered FIO.")  # Не логируем ФИО

    await update.message.reply_text(
        f"👤 Вы указали ФИО: {fio}\n\n"
        "🆔 Пожалуйста, введите ИНН (ІПН/ЕДРПОУ):"
    )

    return ENTERING_INN_DETAILS


async def entering_inn_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inn = update.message.text.strip()
    user = update.effective_user
    if not inn:
        logger.warning(f"User {user.id} ({user.username}) entered empty INN.")
        await update.message.reply_text("Пожалуйста, введите корректный ИНН.")
        return ENTERING_INN_DETAILS

    context.user_data['inn'] = inn
    logger.info(f"User {user.id} ({user.username}) entered INN.")  # Не логируем ИНН

    await update.message.reply_text(
        f"Вы указали ИНН: {inn}\n\n"
    )

    amount = context.user_data['amount']
    currency = context.user_data['currency']
    sum_uah = context.user_data['sum_uah']
    fio = context.user_data['fio']
    bank_name = context.user_data['bank_name']
    keyboard = [
        [InlineKeyboardButton("✅ Отправить", callback_data='send_exchange')],
        [InlineKeyboardButton("🚀 Получить TRX", callback_data='send_exchange_trx')],
        [InlineKeyboardButton("❌ Отмена", callback_data='back_to_menu')]
    ]

    await update.message.reply_text(
        f"💰 Вы хотите обменять {amount} {currency} на {sum_uah:.2f} UAH.\n\n"
        f"🏦 Банк: {bank_name}\n"
        f"👤 ФИО: {fio}\n"
        f"💳 Реквизиты карты: {context.user_data['card_info']}\n"
        f"🆔 ИНН: {inn}\n\n"
        "👉 Нажмите 'Отправить' для подтверждения.\n\n"
        "⚡ В случае если вам нужен TRX, нажмите соответствующую кнопку.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    return CONFIRMING_EXCHANGE


async def confirming_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) is at final confirmation step. Action: {data}")

    amount = context.user_data.get('amount')
    currency = context.user_data.get('currency', 'USDT')
    sum_uah = context.user_data.get('sum_uah', 0)
    fio = context.user_data.get('fio', '')
    bank_name = context.user_data.get('bank_name', '')
    inn = context.user_data.get('inn', '')
    card_info = context.user_data.get('card_info', '')

    user_sessions[user.id] = context.user_data.copy()

    user_info = (
        f"👤 Пользователь:\n"
        f"🆔 ID: `{user.id}`\n"
        f"📛 Имя: `{user.first_name or '-'}`\n"
        f"🔗 Юзернейм: @{user.username if user.username else 'нет'}\n\n"
    )

    transfer_info = (
        f"🏦 Банк: `{bank_name}`\n"
        f"📝 ФИО: `{fio}`\n"
        f"💳 Реквизиты карты: `{card_info}`\n"
        f"📇 ИНН: `{inn}`\n\n"
    )

    if data == 'send_exchange':
        logger.info(
            f"Creating standard exchange request for user {user.id}. Amount: {amount} {currency}")
        await query.message.chat.send_message(
            f"🙏 Спасибо за заявку!\n\n"
            f"💵 Сумма: {amount} {currency} → {sum_uah:.2f} UAH\n\n"
            f"🏦 Переведите средства на адрес:\n"
            f"`{config['Settings']['wallet_address']}`",
            parse_mode='Markdown'
        )

        admin_chat_id = config['User']['ADMIN_CHAT_ID']
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Перевод получен", callback_data=f"confirm_payment_{user.id}")
        ]])

        admin_msg = await context.bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"📥 Новая заявка на обмен\n\n"
                f"💱 {amount} {currency} → {sum_uah:.2f} UAH\n\n"
                f"{user_info}"
                f"{transfer_info}"
            ),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        user_sessions[user.id]['admin_message_id'] = admin_msg.message_id
        user_sessions[user.id]['admin_chat_id'] = admin_msg.chat_id
        logger.info(f"Exchange request for user {user.id} sent to admin {admin_chat_id}.")
        return ConversationHandler.END

    elif data == 'send_exchange_trx':
        logger.info(f"User {user.id} chose to receive TRX for commission.")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Согласен", callback_data='send_transfer_trx')],
            [InlineKeyboardButton("❌ Не согласен", callback_data='back_to_menu')]
        ])

        await query.edit_message_text(
            "⚡ Вам будет предоставлено **15 USDT** в TRX для оплаты комиссии перевода, которые будут отняты из общей суммы обмена.\n\n"
            "💡 Эти средства позволят безопасно и быстро завершить транзакцию.",
            reply_markup=keyboard, parse_mode='Markdown'
        )
        return CONFIRMING_EXCHANGE_TRX

    elif data == 'back_to_menu':
        logger.info(f"User {user.id} cancelled the exchange.")
        await start(update, context)
        return ConversationHandler.END

    else:
        logger.warning(f"User {user.id} triggered an unknown callback: {data}")
        await query.message.reply_text("Неизвестная команда. Возвращаю в меню.")
        await start(update, context)
        return ConversationHandler.END


async def confirming_exchange_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    logger.info(f"User {user.id} ({user.username}) is confirming TRX commission. Action: {data}")

    if data == 'send_transfer_trx':
        await query.edit_message_text(
            "✅ Вы подтвердили перевод **15 USDT** в TRX.\n\n"
            "📬 Пожалуйста, укажите номер вашего TRX-кошелька:",
            parse_mode='Markdown'
        )
        return ENTERING_TRX_ADDRESS

    elif data == 'back_to_menu':
        logger.info(
            f"User {user.id} ({user.username}) declined TRX commission and returned to menu.")
        await start(update, context)
        return ConversationHandler.END


async def entering_trx_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx_address = update.message.text.strip()
    user = update.effective_user
    if not trx_address:
        logger.warning(f"User {user.id} ({user.username}) entered an empty TRX address.")
        await update.message.reply_text("Пожалуйста, введите корректный адрес.")
        return ENTERING_TRX_ADDRESS

    logger.info(f"User {user.id} ({user.username}) entered TRX address.")  # Не логируем адрес

    context.user_data['trx_address'] = trx_address
    amount = context.user_data['amount']
    currency = context.user_data['currency']
    sum_uah = context.user_data['sum_uah']
    fio = context.user_data['fio']
    bank_name = context.user_data['bank_name']
    inn = context.user_data['inn']

    keyboard = [
        [InlineKeyboardButton("✅ Отправить", callback_data='send_exchange')],
        [InlineKeyboardButton("❌ Отмена", callback_data='back_to_menu')]
    ]

    await update.message.reply_text(
        f"📋 Ваша информация:\n\n"
        f"💰 Обмен: {amount} {currency} → {sum_uah:.2f} UAH\n\n"
        f"🏦 Банк: {bank_name}\n"
        f"👤 ФИО: {fio}\n"
        f"💳 Реквизиты карты: {context.user_data['card_info']}\n"
        f"🆔 ИНН: {inn}\n\n"
        f"⚡ Вам будет отправлено **15 USDT** в TRX для оплаты комиссии.\n\n"
        f"💱 Сумма обмена с учетом TRX: {amount - 15} {currency} → {(amount - 15) * float(config['Settings']['exchange_rate']):.2f} UAH\n\n"
        f"🔗 TRX-адрес: {trx_address}\n\n"
        "👉 Нажмите 'Отправить' для подтверждения.\n\n",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    return FINAL_CONFIRMING_EXCHANGE_TRX


async def final_confirming_exchange_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) is at final TRX confirmation. Action: {data}")

    amount = context.user_data['amount']
    currency = context.user_data['currency']
    sum_uah = context.user_data['sum_uah']
    fio = context.user_data['fio']
    bank_name = context.user_data['bank_name']
    inn = context.user_data['inn']
    trx_address = context.user_data.get('trx_address', '')
    card_info = context.user_data['card_info']

    user_info = (
        f"👤 Пользователь:\n"
        f"🆔 ID: `{user.id}`\n"
        f"📛 Имя: `{user.first_name or '-'}`\n"
        f"🔗 Юзернейм: @{user.username if user.username else 'нет'}\n\n"
    )

    transfer_info = (
        f"🏦 Банк: `{bank_name}`\n"
        f"📝 ФИО: `{fio}`\n"
        f"💳 Реквизиты карты: `{card_info}`\n"
        f"📇 ИНН: `{inn}`\n\n"
        f"⚠️ Клиент нуждается в TRX для оплаты комиссии.\n"
        f"📬 TRX-адрес: `{trx_address}`\n"
    )

    if data == 'send_exchange':
        logger.info(
            f"Creating TRX exchange request for user {user.id}. Amount: {amount} {currency}")
        await query.message.chat.send_message(
            f"🙏 Спасибо за заявку!\n\n"
            f"💰 Из общей суммы {amount:.2f} {currency}, вам будет отправлено **15 USDT** в TRX для оплаты комиссии.\n\n"
            f"💵 Конечная сумма обмена: {amount-15} {currency} = {(amount-15) * float(config['Settings']['exchange_rate']):.2f} UAH\n\n"
            f"🏦 Ожидайте, сообщения от бота о успешном переводе TRX ✅\n",
            parse_mode='Markdown'
        )

        admin_chat_id = config['User']['ADMIN_CHAT_ID']
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ TRX переведено",
                                 callback_data=f"confirm_trx_transfer_{user.id}")
        ]])

        admin_msg = await context.bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"📥 Новая заявка на обмен\n\n"
                f"💱 {amount} {currency} = {sum_uah:.2f} UAH\n\n"
                f"💵 После вычета TRX: {amount-15} {currency} → {((amount-15) * float(config['Settings']['exchange_rate'])):.2f} UAH\n\n"
                f"{user_info}"
                f"{transfer_info}"
            ),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        user_sessions[user.id]['admin_message_id'] = admin_msg.message_id
        user_sessions[user.id]['admin_chat_id'] = admin_msg.chat_id
        logger.info(f"TRX exchange request for user {user.id} sent to admin {admin_chat_id}.")
        return ConversationHandler.END

    elif data == 'back_to_menu':
        logger.info(f"User {user.id} cancelled the TRX exchange.")
        await start(update, context)
        return ConversationHandler.END

    else:
        logger.warning(
            f"User {user.id} triggered an unknown callback in final TRX confirmation: {data}")
        await query.message.reply_text("Неизвестная команда. Возвращаю в меню.")
        await start(update, context)
        return ConversationHandler.END


async def handle_transfer_confirmation_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split('_')[-1])
    logger.info(f"Admin confirmed TRX transfer to user {user_id}.")

    session = user_sessions.get(user_id)
    if session:
        amount = session.get('amount', 0)
        currency = session.get('currency', 'USDT')
    else:
        logger.warning(f"No session found for user {user_id} during TRX transfer confirmation.")
        amount = 0
        currency = 'USDT'

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Перевод TRX выполнен. \n\n"
                f"📥 Переведите {(amount - 15):.2f} {currency} на кошелек и ожидайте сообщение о получении средств:\n"
                f"`{config['Settings']['wallet_address']}`"
            ),
            parse_mode='Markdown'
        )
        logger.info(f"Sent TRX transfer confirmation message to user {user_id}.")

        original_text = query.message.text
        updated_text = original_text + "\n\n✅ Сообщение о успешном переводе TRX отправлено"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Средства от клиента получены",
                                  callback_data=f"confirm_payment_{user_id}")]
        ])
        await query.edit_message_text(updated_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Failed to send TRX confirmation to user {user_id}: {e}", exc_info=True)
        await query.edit_message_text(
            query.message.text + f"\n\n❌ Ошибка при отправке пользователю: {e}"
        )


async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split('_')[-1])
    logger.info(f"Admin confirmed payment received from user {user_id}.")

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Средства получены. \n\n⏳ Ожидайте перевода."
        )
        logger.info(f"Sent payment received confirmation to user {user_id}.")

        original_text = query.message.text
        updated_text = original_text + "\n\n✅ Пользователю отправлено подтверждение получения средств."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Перевод клиенту сделан",
                                  callback_data=f"confirm_transfer_{user_id}")]
        ])
        await query.edit_message_text(updated_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Failed to send payment confirmation to user {user_id}: {e}", exc_info=True)
        await query.edit_message_text(
            query.message.text + f"\n\n❌ Ошибка при отправке пользователю: {e}"
        )


async def handle_transfer_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split('_')[-1])
    logger.info(f"Admin confirmed final transfer to user {user_id}.")

    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подтвердить платёж",
                                  callback_data=f"user_confirm_transfer_{user_id}")]
        ])

        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Перевод средств вам выполнен успешно. 💸\n\n🙏 Спасибо за использование нашего сервиса! 🤝",
            reply_markup=keyboard
        )
        logger.info(f"Sent final transfer confirmation to user {user_id}.")

        original_text = query.message.text
        updated_text = original_text + "\n\n✅ Пользователю отправлено подтверждение осуществления перевода."
        await query.edit_message_text(updated_text)
        if user_id in user_sessions:
            user_sessions[user_id]['admin_text'] = updated_text

    except Exception as e:
        logger.error(
            f"Failed to send final transfer confirmation to user {user_id}: {e}", exc_info=True)
        await query.edit_message_text(
            query.message.text + f"\n\n❌ Ошибка при отправке пользователю: {e}"
        )


async def handle_user_confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split('_')[-1])
    logger.info(f"User {user_id} confirmed receiving the transfer.")

    try:
        session = user_sessions.get(user_id)
        if not session:
            logger.warning(f"No session found for user {user_id} during their final confirmation.")
            await query.edit_message_text(query.message.text + "\n\n✅ Спасибо! Подтверждение перевода получено.")
            return

        admin_message_id = session.get('admin_message_id')
        admin_chat_id = int(config['User']['ADMIN_CHAT_ID'])

        # Обновляем сообщение пользователя
        original_text = query.message.text
        updated_text = original_text + "\n\n✅ Спасибо! Подтверждение перевода получено."
        await query.edit_message_text(updated_text)

        # Уведомляем админа
        if admin_message_id:
            await context.bot.edit_message_text(
                chat_id=admin_chat_id,
                message_id=admin_message_id,
                text=session.get('admin_text', '') + "\n\n✅🛑 Пользователь подтвердил перевод. 🛑✅ ",
                parse_mode='Markdown'
            )
            logger.info(
                f"Admin message {admin_message_id} updated with user's final confirmation.")
        else:
            logger.warning(
                f"Could not find admin_message_id for user {user_id} to update with final confirmation.")

    except Exception as e:
        logger.error(
            f"Error during user's final confirmation for user {user_id}: {e}", exc_info=True)
        await query.edit_message_text(query.message.text + f"\n\n❌ Ошибка: {e} \n\n Свяжитесь с контактным лицом: {config['Settings']['SUPPORT_CONTACT']}")


def main():
    logger.info("Starting the bot...")

    application = ApplicationBuilder().token(config['User']['TOKEN']).build()

    # Рекомендуется также добавить логирование в admin_panel.py
    # Например, передать logger в функции admin_panel или настроить его там.

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_menu)],
        states={
            CHOOSING_CURRENCY: [CallbackQueryHandler(choosing_currency)],
            ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_amount)],
            ENTERING_BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_bank_name)],
            ENTERING_CARD_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_card_details)],
            ENTERING_FIO_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_fio_details)],
            ENTERING_INN_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_inn_details)],
            CONFIRMING_EXCHANGE: [CallbackQueryHandler(confirming_exchange)],
            CONFIRMING_EXCHANGE_TRX: [CallbackQueryHandler(confirming_exchange_trx)],
            ENTERING_TRX_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_trx_address)],
            FINAL_CONFIRMING_EXCHANGE_TRX: [CallbackQueryHandler(final_confirming_exchange_trx)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    admin_handler = ConversationHandler(
        entry_points=[CommandHandler('a', admin_panel.admin_panel_start)],
        states={
            admin_panel.ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.admin_panel_password)],
            admin_panel.ADMIN_MENU: [CallbackQueryHandler(admin_panel.admin_panel_handler, pattern='^admin_')],
            admin_panel.SETTINGS_MENU: [CallbackQueryHandler(admin_panel.admin_panel_handler, pattern='^admin_')],
            admin_panel.SET_NEW_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_new_password)],
            admin_panel.SET_EXCHANGE_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_exchange_rate)],
            admin_panel.SET_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_wallet)],
            admin_panel.SET_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_support_contact)],
        },
        fallbacks=[CommandHandler('a', admin_panel.admin_panel_start),
                   CommandHandler('ac', admin_panel.admin_panel_close)]
    )

    application.add_handler(admin_handler)
    application.add_handler(CallbackQueryHandler(
        handle_payment_confirmation, pattern=r'^confirm_payment_'))
    application.add_handler(CallbackQueryHandler(
        handle_transfer_confirmation, pattern=r'^confirm_transfer_'))
    application.add_handler(CallbackQueryHandler(
        handle_transfer_confirmation_trx, pattern=r'^confirm_trx_transfer_'))
    application.add_handler(CallbackQueryHandler(
        handle_user_confirm_transfer, pattern=r'^user_confirm_transfer_'))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('a', admin_panel.admin_panel_start))
    application.add_handler(conv_handler)

    logger.info("Bot started successfully! Polling for updates...")
    application.run_polling()


if __name__ == "__main__":
    main()
