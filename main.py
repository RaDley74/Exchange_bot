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
    config['User'] = {
        'TOKEN': 'your_token_here',
        'ADMIN_CHAT_ID': 'your_admin_chat_id_here',
    }
    config['Settings'] = {
        'EXCHANGE_RATE': '41.2',
    }

    with open(config_file_name, 'w') as config_file:
        config.write(config_file)

    print(
        f"Configuration file '{config_file_name}' created. Please edit it with your token and admin chat ID, then restart the script.")
    exit(0)

else:
    config.read(config_file_name)

EXCHANGE_RATE = float(config['Settings']['EXCHANGE_RATE'])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("➸ Обменять", callback_data='exchange'),
            # InlineKeyboardButton("💰 Получить TRX", callback_data='get_trx'),
            InlineKeyboardButton("📉 Курс", callback_data='rate'),

        ],
        # [
        #     InlineKeyboardButton("📦 Статус заявки", callback_data='status'),
        #     InlineKeyboardButton("🏰 Рефералка", callback_data='referral'),
        #     InlineKeyboardButton("🛠 Помощь", callback_data='help'),
        # ]
    ]
    text = (
        "👋 Привет! Добро пожаловать в Crypto-Exchange Bot 💱\n\n"
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

    if data == 'rate':
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
        ]
        await query.edit_message_text(f"📉 Актуальный курс: 1 USDT = {EXCHANGE_RATE} UAH", reply_markup=InlineKeyboardMarkup(keyboard))

    # elif data == 'get_trx':
    #     await query.edit_message_text("💰 Пожалуйста, введите сумму TRX для получения:")
    #     return ENTERING_TRX_AMOUNT

    elif data == 'exchange':
        keyboard = [
            [InlineKeyboardButton("USDT", callback_data='currency_usdt')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
        ]
        await query.edit_message_text("💱 Выберите валюту для обмена:",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return CHOOSING_CURRENCY

    # elif data == 'status':
    #     await query.edit_message_text("Введите номер вашей заявки (в разработке)")

    # elif data == 'referral':
    #     await query.edit_message_text(
    #         "🌟 Приглашай друзей и получай бонусы! Твоя ссылка: https://t.me/ТвойБот?start=ref")

    # elif data == 'help':
    #     await query.edit_message_text("🔧 Помощь: Напиши @admin по любым вопросам")

    elif data == 'back_to_menu':
        await start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


async def choosing_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'currency_usdt':
        context.user_data['currency'] = 'USDT'
        await query.message.chat.send_message(f"💰 Введите сумму для обмена (в {context.user_data['currency']}):")
        return ENTERING_AMOUNT

    elif data == 'back_to_menu':
        await start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


async def entering_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        amount = float(text.replace(',', '.'))
        if amount <= 0:
            await update.message.reply_text("Введите число больше нуля.")
            return ENTERING_AMOUNT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число.")
        return ENTERING_AMOUNT

    context.user_data['amount'] = amount
    currency = context.user_data.get('currency', 'USDT')
    sum_uah = amount * EXCHANGE_RATE
    context.user_data['sum_uah'] = sum_uah
    # keyboard = [
    #     [InlineKeyboardButton("Отправить", callback_data='send_exchange')],
    #     [InlineKeyboardButton("Отмена", callback_data='back_to_menu')]
    # ]

    # await update.message.reply_text(
    #     f"Вы хотите обменять {amount} {currency} по курсу {EXCHANGE_RATE}.\n"
    #     f"Итого к оплате: {sum_uah:.2f} UAH.\n\nНажмите 'Отправить' для подтверждения.",
    #     reply_markup=InlineKeyboardMarkup(keyboard)
    # )
    # return CONFIRMING_EXCHANGE
    await update.message.reply_text(
        f"✅ Хорошо! К оплате: {sum_uah:.2f} UAH.\n\n🏦 Пожалуйста, укажите название банка, с которого будет производиться обмен (например, 'ПриватБанк', 'Монобанк' и т.д.).\n"
    )
    return ENTERING_BANK_NAME  # ← переходим в следующее состояние


async def entering_bank_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bank_name = update.message.text.strip()
    if not bank_name:
        await update.message.reply_text("Пожалуйста, введите корректное название банка.")
        return ENTERING_BANK_NAME

    context.user_data['bank_name'] = bank_name

    await update.message.reply_text(
        f"🏦 Вы указали банк: {bank_name}\n\n"
        "💳 Введите реквизиты вашей банковской карты (номер карты или IBAN):"
    )

    return ENTERING_CARD_DETAILS


async def entering_card_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card_info = update.message.text.strip()
    if not card_info:
        await update.message.reply_text("Пожалуйста, введите корректные реквизиты.")
        return ENTERING_CARD_DETAILS

    context.user_data['card_info'] = card_info

    await update.message.reply_text(
        f"💳 Вы указали реквизиты: {card_info}\n\n"
        f"👤 Укажите ФИО для зачисления средств:"
    )

    return ENTERING_FIO_DETAILS


async def entering_fio_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fio = update.message.text.strip()
    if not fio:
        await update.message.reply_text("Пожалуйста, введите корректные ФИО.")
        return ENTERING_FIO_DETAILS

    context.user_data['fio'] = fio

    await update.message.reply_text(
        f"👤 Вы указали ФИО: {fio}\n\n"
        "🆔 Пожалуйста, введите ИНН (ІПН/ЕДРПОУ):"
    )

    return ENTERING_INN_DETAILS


async def entering_inn_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inn = update.message.text.strip()
    if not inn:
        await update.message.reply_text("Пожалуйста, введите корректный ИНН.")
        return ENTERING_INN_DETAILS

    await update.message.reply_text(
        f"Вы указали ИНН: {inn}\n\n"
    )

    context.user_data['inn'] = inn
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

    # Данные из user_data
    amount = context.user_data.get('amount')
    currency = context.user_data.get('currency', 'USDT')
    sum_uah = context.user_data.get('sum_uah', 0)
    fio = context.user_data.get('fio', '')
    bank_name = context.user_data.get('bank_name', '')
    inn = context.user_data.get('inn', '')
    card_info = context.user_data.get('card_info', '')

    user = update.effective_user

    user_sessions[update.effective_user.id] = context.user_data.copy()

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
        # Отправляем пользователю инструкцию и администратору заявку
        await query.message.chat.send_message(
            f"🙏 Спасибо за заявку!\n\n"
            f"💵 Сумма: {amount} {currency} → {sum_uah:.2f} UAH\n"
            f"🏦 Переведите средства на адрес:\n"
            f"`TMHDhHp3qdT4EuEuFQGWxuZ14EvzDZseac`",
            parse_mode='Markdown'
        )

        admin_chat_id = config['User']['ADMIN_CHAT_ID']

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Перевод получен", callback_data=f"confirm_payment_{user.id}")
        ]])

        await context.bot.send_message(
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

        await start(update, context)
        return ConversationHandler.END

    elif data == 'send_exchange_trx':
        # Предложение получить 15 USDT в TRX для оплаты комиссии
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
        await start(update, context)
        return ConversationHandler.END

    else:
        # На случай непредвиденных callback_data
        await query.message.reply_text("Неизвестная команда. Возвращаю в меню.")
        await start(update, context)
        return ConversationHandler.END


async def confirming_exchange_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'send_transfer_trx':
        await query.edit_message_text(
            "✅ Вы подтвердили перевод **15 USDT** в TRX.\n\n"
            "📬 Пожалуйста, укажите номер вашего TRX-кошелька:",
            parse_mode='Markdown'
        )

        return ENTERING_TRX_ADDRESS

    elif data == 'back_to_menu':
        await start(update, context)
        return ConversationHandler.END


# async def entering_trx_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     text = update.message.text
#     try:
#         amount = float(text.replace(',', '.'))
#         if amount <= 0:
#             await update.message.reply_text("Введите число больше нуля.")
#             return ENTERING_TRX_AMOUNT
#     except ValueError:
#         await update.message.reply_text("Пожалуйста, введите корректное число.")
#         return ENTERING_TRX_AMOUNT

#     context.user_data['trx_amount'] = amount
#     await update.message.reply_text("Введите адрес TRX для отправки:")
#     return ENTERING_TRX_ADDRESS


async def entering_trx_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx_address = update.message.text.strip()
    if not trx_address:
        await update.message.reply_text("Пожалуйста, введите корректный адрес.")
        return ENTERING_TRX_ADDRESS

    amount = context.user_data['amount']
    currency = context.user_data['currency']
    sum_uah = context.user_data['sum_uah']
    fio = context.user_data['fio']
    bank_name = context.user_data['bank_name']
    inn = context.user_data['inn']
    context.user_data['trx_address'] = trx_address

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
        f"💱 Сумма обмена с учетом TRX: {amount - 15} {currency} → {(amount - 15) * EXCHANGE_RATE:.2f} UAH\n\n"
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

    # Данные из user_data
    amount = context.user_data['amount']
    currency = context.user_data['currency']
    sum_uah = context.user_data['sum_uah']
    fio = context.user_data['fio']
    bank_name = context.user_data['bank_name']
    inn = context.user_data['inn']
    trx_address = context.user_data.get('trx_address', '')
    card_info = context.user_data['card_info']

    user = update.effective_user
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
        # Отправляем пользователю инструкцию и администратору заявку
        await query.message.chat.send_message(
            f"🙏 Спасибо за заявку!\n\n"
            f"💰 Из общей суммы {amount:.2f} {currency}, вам будет отправлено **15 USDT** в TRX для оплаты комиссии.\n\n"
            f"💵 Конечная сумма обмена: {amount-15} {currency} = {(amount-15) * EXCHANGE_RATE:.2f} UAH\n\n"
            f"🏦 Ожидайте, сообщения от бота о успешном переводе TRX ✅\n",
            parse_mode='Markdown'
        )

        admin_chat_id = config['User']['ADMIN_CHAT_ID']

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ TRX переведено",
                                 callback_data=f"confirm_trx_transfer_{user.id}")
        ]])

        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"📥 Новая заявка на обмен\n\n"
                f"💱 {amount} {currency} = {sum_uah:.2f} UAH\n\n"
                f"💵 После вычета TRX: {amount-15} {currency} → {((amount-15) * EXCHANGE_RATE):.2f} UAH\n\n"
                f"{user_info}"
                f"{transfer_info}"
            ),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        await start(update, context)
        return ConversationHandler.END

    elif data == 'back_to_menu':
        await start(update, context)
        return ConversationHandler.END

    else:
        # На случай непредвиденных callback_data
        await query.message.reply_text("Неизвестная команда. Возвращаю в меню.")
        await start(update, context)
        return ConversationHandler.END


async def handle_transfer_confirmation_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Извлекаем user_id из callback_data
    data = query.data  # confirm_payment_12345678
    user_id = int(data.split('_')[-1])

    session = user_sessions.get(user_id)

    if session:
        amount = session.get('amount', 0)
        currency = session.get('currency', 'USDT')
    else:
        amount = 0
        currency = 'USDT'

    # Отправляем пользователю уведомление
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Перевод TRX выполнен. \n\n"
                f"📥 Переведите {(amount - 15):.2f} {currency} на кошелек и ожидайте сообщение о получении средств:\n"
                f"`TMHDhHp3qdT4EuEuFQGWxuZ14EvzDZseac`"),
            parse_mode='Markdown'
        )
        original_text = query.message.text
        updated_text = original_text + "\n\n✅ Сообщение о успешном переводе TRX отправлено"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Средства от клиента получены",
                                  callback_data=f"confirm_payment_{user_id}")]
        ])
        await query.edit_message_text(updated_text, reply_markup=keyboard)

    except Exception as e:
        await query.edit_message_text(
            query.message.text + f"\n\n❌ Ошибка при отправке пользователю: {e}"
        )


async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Извлекаем user_id из callback_data
    data = query.data  # confirm_payment_12345678
    user_id = int(data.split('_')[-1])

    # Отправляем пользователю уведомление
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Средства получены. \n\n⏳ Ожидайте перевода."
        )
        original_text = query.message.text
        updated_text = original_text + "\n\n✅ Пользователю отправлено подтверждение получения средств."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Перевод клиенту сделан",
                                  callback_data=f"confirm_transfer_{user_id}")]
        ])
        await query.edit_message_text(updated_text, reply_markup=keyboard)

    except Exception as e:
        await query.edit_message_text(
            query.message.text + f"\n\n❌ Ошибка при отправке пользователю: {e}"
        )


async def handle_transfer_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = int(data.split('_')[-1])

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Перевод средств вам выполнен успешно. 💸\n\n🙏 Спасибо за использование нашего сервиса! 🤝"
        )
        original_text = query.message.text
        updated_text = original_text + "\n\n✅ Пользователю отправлено подтверждение осуществления перевода."
        await query.edit_message_text(updated_text)

    except Exception as e:
        await query.edit_message_text(
            query.message.text + f"\n\n❌ Ошибка при отправке пользователю: {e}"
        )


def main():
    print("Starting the bot...")

    application = ApplicationBuilder().token(config['User']['TOKEN']).build()
    bot = Bot(token=config['User']['TOKEN'])

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
    application.add_handler(CallbackQueryHandler(
        handle_payment_confirmation, pattern=r'^confirm_payment_'))
    application.add_handler(CallbackQueryHandler(
        handle_transfer_confirmation, pattern=r'^confirm_transfer_'))
    application.add_handler(CallbackQueryHandler(
        handle_transfer_confirmation_trx, pattern=r'^confirm_trx_transfer_'))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
