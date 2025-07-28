from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

TOKEN = '7864230893:AAGffXDMbx6RAiGPoAbdn9RBnUnWgn8SEv8'
ADMIN_CHAT_ID = 7802237334
EXCHANGE_RATE = 41.2  # float с точкой

# Состояния для ConversationHandler
(
    CHOOSING_CURRENCY,
    ENTERING_AMOUNT,
    CONFIRMING_EXCHANGE,
    ENTERING_TRX_AMOUNT,
    ENTERING_TRX_ADDRESS,
) = range(5)


def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("➸ Обменять", callback_data='exchange'),
            InlineKeyboardButton("💰 Получить TRX", callback_data='get_trx'),
            InlineKeyboardButton("📉 Курс", callback_data='rate'),
        ],
        [
            InlineKeyboardButton("📦 Статус заявки", callback_data='status'),
            InlineKeyboardButton("🏰 Рефералка", callback_data='referral'),
            InlineKeyboardButton("🛠 Помощь", callback_data='help'),
        ]
    ]
    text = (
        "👋 Привет! Добро пожаловать в Crypto-Exchange Bot 💱\n\n"
        "🧲 Обмен быстрый и удобный.\n\n"
        "🌟 Выбери раздел:"
    )

    if update.message:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


def handle_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'rate':
        query.edit_message_text(f"📉 Актуальный курс: 1 USDT = {EXCHANGE_RATE} UAH")

    elif data == 'get_trx':
        query.edit_message_text("💰 Пожалуйста, введите сумму TRX для получения:")
        return ENTERING_TRX_AMOUNT

    elif data == 'exchange':
        keyboard = [
            [InlineKeyboardButton("USDT", callback_data='currency_usdt')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
        ]
        query.edit_message_text("Выберите валюту для обмена:",
                                reply_markup=InlineKeyboardMarkup(keyboard))
        return CHOOSING_CURRENCY

    elif data == 'status':
        query.edit_message_text("Введите номер вашей заявки (в разработке)")

    elif data == 'referral':
        query.edit_message_text(
            "🌟 Приглашай друзей и получай бонусы! Твоя ссылка: https://t.me/ТвойБот?start=ref")

    elif data == 'help':
        query.edit_message_text("🔧 Помощь: Напиши @admin по любым вопросам")

    elif data == 'back_to_menu':
        start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


def choosing_currency(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'currency_usdt':
        context.user_data['currency'] = 'USDT'
        query.edit_message_text("Введите сумму для обмена (в USDT):")
        return ENTERING_AMOUNT

    elif data == 'back_to_menu':
        start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


def entering_amount(update: Update, context: CallbackContext):
    text = update.message.text
    try:
        amount = float(text.replace(',', '.'))
        if amount <= 0:
            update.message.reply_text("Введите число больше нуля.")
            return ENTERING_AMOUNT
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректное число.")
        return ENTERING_AMOUNT

    context.user_data['amount'] = amount
    currency = context.user_data.get('currency', 'USDT')
    sum_uah = amount * EXCHANGE_RATE

    keyboard = [
        [InlineKeyboardButton("Отправить", callback_data='send_exchange')],
        [InlineKeyboardButton("Отмена", callback_data='back_to_menu')]
    ]

    update.message.reply_text(
        f"Вы хотите обменять {amount} {currency} по курсу {EXCHANGE_RATE}.\n"
        f"Итого к оплате: {sum_uah:.2f} UAH.\n\nНажмите 'Отправить' для подтверждения.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMING_EXCHANGE


def confirming_exchange(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'send_exchange':
        query.edit_message_text(
            "Спасибо за заявку!\n\n"
            "Переведите средства на адрес:\n`TMHDhHp3qdT4EuEuFQGWxuZ14EvzDZseac`",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    elif data == 'back_to_menu':
        start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


def entering_trx_amount(update: Update, context: CallbackContext):
    text = update.message.text
    try:
        amount = float(text.replace(',', '.'))
        if amount <= 0:
            update.message.reply_text("Введите число больше нуля.")
            return ENTERING_TRX_AMOUNT
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректное число.")
        return ENTERING_TRX_AMOUNT

    context.user_data['trx_amount'] = amount
    update.message.reply_text("Введите адрес TRX для отправки:")
    return ENTERING_TRX_ADDRESS


def entering_trx_address(update: Update, context: CallbackContext):
    trx_address = update.message.text.strip()
    if not trx_address:
        update.message.reply_text("Пожалуйста, введите корректный адрес.")
        return ENTERING_TRX_ADDRESS

    amount = context.user_data.get('trx_amount')
    update.message.reply_text(
        f"Заявка на получение {amount} TRX принята.\n"
        f"Адрес для отправки: {trx_address}\n\n"
        "Ожидайте обработки заявки."
    )
    return ConversationHandler.END


def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_menu)],
        states={
            CHOOSING_CURRENCY: [CallbackQueryHandler(choosing_currency)],
            ENTERING_AMOUNT: [MessageHandler(filters.text & ~filters.command, entering_amount)],
            CONFIRMING_EXCHANGE: [CallbackQueryHandler(confirming_exchange)],

            ENTERING_TRX_AMOUNT: [MessageHandler(filters.text & ~filters.command, entering_trx_amount)],
            ENTERING_TRX_ADDRESS: [MessageHandler(filters.text & ~filters.command, entering_trx_address)],
        },
        fallbacks=[CommandHandler('start', start)],
        # per_message не указываем — оставляем по умолчанию False
    )

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
