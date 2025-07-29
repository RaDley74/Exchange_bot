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
    CONFIRMING_EXCHANGE,
    ENTERING_TRX_AMOUNT,
    ENTERING_TRX_ADDRESS,
) = range(5)

config_file_name = 'settings.ini'
config = configparser.ConfigParser()

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
        await query.edit_message_text("Выберите валюту для обмена:",
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
        await query.edit_message_text("Введите сумму для обмена (в USDT):")
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
    keyboard = [
        [InlineKeyboardButton("Отправить", callback_data='send_exchange')],
        [InlineKeyboardButton("Отмена", callback_data='back_to_menu')]
    ]

    await update.message.reply_text(
        f"Вы хотите обменять {amount} {currency} по курсу {EXCHANGE_RATE}.\n"
        f"Итого к оплате: {sum_uah:.2f} UAH.\n\nНажмите 'Отправить' для подтверждения.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMING_EXCHANGE


async def confirming_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    user = update.effective_user
    user_info = f"👤 Пользователь:\n" \
        f"ID: {user.id}\n" \
        f"Имя: {user.first_name or '-'}\n" \
        f"Юзернейм: @{user.username if user.username else 'нет'}"

    if data == 'send_exchange':

        amount = context.user_data.get('amount')
        currency = context.user_data.get('currency', 'USDT')
        sum_uah = amount * EXCHANGE_RATE if amount else 0

        await query.message.chat.send_message(
            f"Спасибо за заявку!\n\n"
            f"Сумма: {amount} {currency} = {sum_uah:.2f} UAH\n"
            f"Переведите средства на адрес:\n"
            f"`TMHDhHp3qdT4EuEuFQGWxuZ14EvzDZseac`",
            parse_mode='Markdown'
        )

        admin_chat_id = config['User']['ADMIN_CHAT_ID']

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Деньги получены", callback_data=f"confirm_payment_{user.id}")]
        ])

        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"📥 Новая заявка на обмен\n\n"
                f"💱 {amount} {currency} = {sum_uah:.2f} UAH\n\n"
                f"{user_info}"
            ), reply_markup=keyboard
        )

        await start(update, context)
        return ConversationHandler.END

    elif data == 'back_to_menu':
        await start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


async def entering_trx_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        amount = float(text.replace(',', '.'))
        if amount <= 0:
            await update.message.reply_text("Введите число больше нуля.")
            return ENTERING_TRX_AMOUNT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число.")
        return ENTERING_TRX_AMOUNT

    context.user_data['trx_amount'] = amount
    await update.message.reply_text("Введите адрес TRX для отправки:")
    return ENTERING_TRX_ADDRESS


async def entering_trx_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx_address = update.message.text.strip()
    if not trx_address:
        await update.message.reply_text("Пожалуйста, введите корректный адрес.")
        return ENTERING_TRX_ADDRESS

    amount = context.user_data.get('trx_amount')
    await update.message.reply_text(
        f"Заявка на получение {amount} TRX принята.\n"
        f"Адрес для отправки: {trx_address}\n\n"
        "Ожидайте обработки заявки."
    )
    return ConversationHandler.END


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
            text="✅ Средства получены. Ожидайте перевода. Спасибо за использование нашего сервиса!"
        )
        original_text = query.message.text
        updated_text = original_text + "\n\n✅ Пользователю отправлено подтверждение получения средств."
        await query.edit_message_text(updated_text)
    except Exception as e:
        await query.edit_message_text(
            query.message.text + f"\n\n❌ Ошибка при отправке пользователю: {e}"
        )


def main():
    print("Starting the bot...")

    application = ApplicationBuilder().token(config['User']['TOKEN']).build()
    bot = Bot(token=config['User']['TOKEN'])
    bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_menu)],
        states={
            CHOOSING_CURRENCY: [CallbackQueryHandler(choosing_currency)],
            ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_amount)],
            CONFIRMING_EXCHANGE: [CallbackQueryHandler(confirming_exchange)],

            ENTERING_TRX_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_trx_amount)],
            ENTERING_TRX_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_trx_address)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    application.add_handler(CallbackQueryHandler(
        handle_payment_confirmation, pattern=r'^confirm_payment_'))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
