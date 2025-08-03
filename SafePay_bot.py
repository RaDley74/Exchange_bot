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
import logging
import Config
import warnings
import logging

import os
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # handlers=[
    #     # logging.FileHandler("bot.log"),
    #     logging.StreamHandler()
    # ]
)
# Получаем объект логгера для текущего модуля.
logger = logging.getLogger(__name__)

# Подавляем INFO-логи от библиотеки httpx, чтобы не засорять вывод
logging.getLogger("httpx").setLevel(logging.WARNING)


warnings.filterwarnings("ignore", category=UserWarning)


def clear_console():
    # Для Windows
    if os.name == 'nt':
        _ = os.system('cls')
    # Для macOS и Linux
    else:
        _ = os.system('clear')


class SafePayBot:
    def __init__(self):

        self.user_sessions = {}
        (
            self.CHOOSING_CURRENCY,
            self.ENTERING_AMOUNT,
            self.ENTERING_BANK_NAME,
            self.ENTERING_CARD_DETAILS,
            self.ENTERING_FIO_DETAILS,
            self.ENTERING_INN_DETAILS,
            self.CONFIRMING_EXCHANGE,
            self.CONFIRMING_EXCHANGE_TRX,
            self.ENTERING_TRX_ADDRESS,
            self.FINAL_CONFIRMING_EXCHANGE_TRX
        ) = range(10)

        self.config = Config.Config()

        self.token = self.config.get_token()
        self.admin_chat_id = self.config.get_admin_chat_id()
        self.exchange_rate = float(self.config.get_exchange_rate())
        self.admin_password = self.config.get_admin_password()

        # Создаем приложение бота
        self.application = ApplicationBuilder().token(self.token).post_init(self.post_init).build()

        self.SafePay_bot = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.handel_user_menu, pattern='^user_')],
            states={
                self.CHOOSING_CURRENCY: [CallbackQueryHandler(self.choosing_currency, pattern='^user_')],
                self.ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_amount)],
                self.ENTERING_BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_bank_name)],
                # self.ENTERING_CARD_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_card_details)],
                # self.ENTERING_FIO_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_fio_details)],
                # self.ENTERING_INN_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_inn_details)],
                # self.CONFIRMING_EXCHANGE: [CallbackQueryHandler(self.confirming_exchange)],
                # self.CONFIRMING_EXCHANGE_TRX: [CallbackQueryHandler(self.confirming_exchange_trx)],
                # self.ENTERING_TRX_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_trx_address)],
                # self.FINAL_CONFIRMING_EXCHANGE_TRX: [CallbackQueryHandler(self.final_confirming_exchange_trx)],
            },
            fallbacks=[CommandHandler('start', self.start)],
        )

        # Регистрация обработчиков команд
        self.application.add_handler(self.SafePay_bot)
        self.application.add_handler(CommandHandler("start", self.start))

    async def post_init(self, application):
        """Эта функция будет выполнена один раз после запуска бота."""
        await application.bot.set_my_commands([
            ("start", "Запустить бота"),
            ("a", "Панель администратора")
        ])
        logger.info("Bot commands have been set.")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started the bot.")
        context.bot_data['ADMIN_CHAT_ID'] = int(self.config.get_admin_chat_id())

        keyboard = [
            [
                InlineKeyboardButton("➸ Обменять", callback_data='user_exchange'),
                InlineKeyboardButton("📉 Курс", callback_data='user_rate'),
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

    async def handel_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.query = update.callback_query
        await self.query.answer()
        self.data = self.query.data
        self.user = self.query.from_user
        logger.info(
            f"User {self.user.id} ({self.user.username}) selected menu option: {self.data}")

        if self.data == 'user_rate':
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад", callback_data='user_menu_back_to_menu')]
            ]
            await self.query.edit_message_text(
                f"📉 Актуальный курс: 1 USDT = {float(self.config.get_exchange_rate())} UAH",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif self.data == 'user_exchange':
            keyboard = [
                [InlineKeyboardButton("USDT", callback_data='user_currency_usdt')],
                [InlineKeyboardButton("⬅️ Назад", callback_data='user_menu_back_to_menu')]
            ]
            await self.query.edit_message_text(
                "💱 Выберите валюту для обмена:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return self.CHOOSING_CURRENCY

        elif self.data == 'user_help':
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад", callback_data='user_menu_back_to_menu')]
            ]
            await self.query.edit_message_text(
                f"🔧 Помощь: Напиши {self.config.get_support_contact()} по любым вопросам относительно бота.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif self.data == 'user_menu_back_to_menu':
            await self.start(update, context)
            return ConversationHandler.END

        return ConversationHandler.END

    async def choosing_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.info(
            f"User {update.effective_user.id} ({update.effective_user.username}) is choosing currency.")
        self.query = update.callback_query
        await self.query.answer()
        self.data = self.query.data
        self.user = self.query.from_user

        if self.data == 'user_currency_usdt':
            context.user_data['currency'] = 'USDT'
            logger.info(
                f"User {self.user.id} ({self.user.username}) chose currency: {context.user_data['currency']}")
            await self.query.message.chat.send_message(f"💰 Введите сумму для обмена (в {context.user_data['currency']}):")
            return self.ENTERING_AMOUNT

        elif self.data == 'user_menu_back_to_menu':
            logger.info(
                f"User {self.user.id} ({self.user.username}) returned to the main menu from currency selection.")
            await self.start(update, context)
            return ConversationHandler.END

        return ConversationHandler.END

    async def entering_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.text = update.message.text
        self.user = update.effective_user
        try:
            self.amount = float(self.text.replace(',', '.'))
            if self.amount <= 0:
                logger.warning(
                    f"User {self.user.id} ({self.user.username}) entered a non-positive amount: {self.amount}")
                await update.message.reply_text("Введите число больше нуля.")
                return self.ENTERING_AMOUNT
        except ValueError:
            logger.warning(
                f"User {self.user.id} ({self.user.username}) entered an invalid amount: '{self.text}'")
            await update.message.reply_text("Пожалуйста, введите корректное число.")
            return self.ENTERING_AMOUNT

        context.user_data['amount'] = self.amount
        self.currency = context.user_data.get('currency', 'USDT')
        self.sum_uah = self.amount * float(self.config.get_exchange_rate())
        context.user_data['sum_uah'] = self.sum_uah
        logger.info(
            f"User {self.user.id} ({self.user.username}) entered amount: {self.amount} {self.currency}. Calculated sum: {self.sum_uah:.2f} UAH.")

        await update.message.reply_text(
            f"✅ Хорошо! К оплате: {self.sum_uah:.2f} UAH.\n\n🏦 Пожалуйста, укажите название банка, с которого будет производиться обмен (например, 'ПриватБанк', 'Монобанк' и т.д.).\n"
        )
        return self.ENTERING_BANK_NAME

    async def entering_bank_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.bank_name = update.message.text.strip()
        self.user = update.effective_user
        if not self.bank_name:
            logger.warning(
                f"User {self.user.id} ({self.user.username}) entered an empty bank name.")
            await update.message.reply_text("Пожалуйста, введите корректное название банка.")
            return self.ENTERING_BANK_NAME

        context.user_data['bank_name'] = self.bank_name
        logger.info(
            f"User {self.user.id} ({self.user.username}) entered bank name: {self.bank_name}")

        await update.message.reply_text(
            f"🏦 Вы указали банк: {self.bank_name}\n\n"
            "💳 Введите реквизиты вашей банковской карты (номер карты или IBAN):"
        )

        return self.ENTERING_CARD_DETAILS

    async def entering_card_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.card_info = update.message.text.strip()
        self.user = update.effective_user
        if not self.card_info:
            logger.warning(
                f"User {self.user.id} ({self.user.username}) entered empty card details.")
            await update.message.reply_text("Пожалуйста, введите корректные реквизиты.")
            return self.ENTERING_CARD_DETAILS

        context.user_data['card_info'] = self.card_info
        # Не логируем сами реквизиты
        logger.info(f"User {self.user.id} ({self.user.username}) entered card details.")

        await update.message.reply_text(
            f"💳 Вы указали реквизиты: {self.card_info}\n\n"
            f"👤 Укажите ФИО для зачисления средств:"
        )

        return self.ENTERING_FIO_DETAILS

    async def entering_fio_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.fio = update.message.text.strip()
        self.user = update.effective_user
        if not self.fio:
            logger.warning(f"User {self.user.id} ({self.user.username}) entered empty FIO.")
            await update.message.reply_text("Пожалуйста, введите корректные ФИО.")
            return self.ENTERING_FIO_DETAILS

        context.user_data['fio'] = self.fio
        logger.info(f"User {self.user.id} ({self.user.username}) entered FIO.")  # Не логируем ФИО

        await update.message.reply_text(
            f"👤 Вы указали ФИО: {self.fio}\n\n"
            "🆔 Пожалуйста, введите ИНН (ІПН/ЕДРПОУ):"
        )

        return self.ENTERING_INN_DETAILS

    async def entering_inn_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.inn = update.message.text.strip()
        self.user = update.effective_user
        if not self.inn:
            logger.warning(f"User {self.user.id} ({self.user.username}) entered empty INN.")
            await update.message.reply_text("Пожалуйста, введите корректный ИНН.")
            return self.ENTERING_INN_DETAILS

        context.user_data['inn'] = self.inn
        logger.info(f"User {self.user.id} ({self.user.username}) entered INN.")  # Не логируем ИНН

        await update.message.reply_text(
            f"Вы указали ИНН: {self.inn}\n\n"
        )

        self.amount = context.user_data['amount']
        self.currency = context.user_data['currency']
        self.sum_uah = context.user_data['sum_uah']
        self.fio = context.user_data['fio']
        self.bank_name = context.user_data['bank_name']
        self.keyboard = [
            [InlineKeyboardButton("✅ Отправить", callback_data='user_send_exchange')],
            [InlineKeyboardButton("🚀 Получить TRX", callback_data='user_send_exchange_trx')],
            [InlineKeyboardButton("❌ Отмена", callback_data='user_menu_back_to_menu')]
        ]

        await update.message.reply_text(
            f"💰 Вы хотите обменять {self.amount} {self.currency} на {self.sum_uah:.2f} UAH.\n\n"
            f"🏦 Банк: {self.bank_name}\n"
            f"👤 ФИО: {self.fio}\n"
            f"💳 Реквизиты карты: {context.user_data['card_info']}\n"
            f"🆔 ИНН: {self.inn}\n\n"
            "👉 Нажмите 'Отправить' для подтверждения.\n\n"
            "⚡ В случае если вам нужен TRX, нажмите соответствующую кнопку.",
            reply_markup=InlineKeyboardMarkup(self.keyboard),
            parse_mode='Markdown'
        )

        return self.CONFIRMING_EXCHANGE

    async def confirming_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.query = update.callback_query
        await self.query.answer()
        self.data = self.query.data
        self.user = update.effective_user
        logger.info(
            f"User {self.user.id} ({self.user.username}) is at final confirmation step. Action: {self.data}")

        self.amount = context.user_data.get('amount')
        self.currency = context.user_data.get('currency', 'USDT')
        self.sum_uah = context.user_data.get('sum_uah', 0)
        self.fio = context.user_data.get('fio', '')
        self.bank_name = context.user_data.get('bank_name', '')
        self.inn = context.user_data.get('inn', '')
        self.card_info = context.user_data.get('card_info', '')

        self.user_sessions[self.user.id] = context.user_data.copy()

        user_info = (
            f"👤 Пользователь:\n"
            f"🆔 ID: `{self.user.id}`\n"
            f"📛 Имя: `{self.user.first_name or '-'}`\n"
            f"🔗 Юзернейм: @{self.user.username if self.user.username else 'нет'}\n\n"
        )

        transfer_info = (
            f"🏦 Банк: `{self.bank_name}`\n"
            f"📝 ФИО: `{self.fio}`\n"
            f"💳 Реквизиты карты: `{self.card_info}`\n"
            f"📇 ИНН: `{self.inn}`\n\n"
        )

        if self.data == 'user_send_exchange':
            logger.info(
                f"Creating standard exchange request for user {self.user.id}. Amount: {self.amount} {self.currency}")
            await self.query.message.chat.send_message(
                f"🙏 Спасибо за заявку!\n\n"
                f"💵 Сумма: {self.amount} {self.currency} → {self.sum_uah:.2f} UAH\n\n"
                f"🏦 Переведите средства на адрес:\n"
                f"`{self.config.get_wallet_address()}`\n\n",
                parse_mode='Markdown'
            )

            admin_chat_id = self.config.get_admin_chat_id
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Перевод получен",
                                     callback_data=f"confirm_payment_{self.user.id}")
            ]])

            admin_msg = await context.bot.send_message(
                chat_id=admin_chat_id,
                text=(
                    f"📥 Новая заявка на обмен\n\n"
                    f"💱 {self.amount} {self.currency} → {self.sum_uah:.2f} UAH\n\n"
                    f"{user_info}"
                    f"{transfer_info}"
                ),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            self.user_sessions[self.user.id]['admin_message_id'] = admin_msg.message_id
            self.user_sessions[self.user.id]['admin_chat_id'] = admin_msg.chat_id
            logger.info(f"Exchange request for user {self.user.id} sent to admin {admin_chat_id}.")
            return ConversationHandler.END

        elif self.data == 'send_exchange_trx':
            logger.info(f"User {self.user.id} chose to receive TRX for commission.")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Согласен", callback_data='user_send_transfer_trx')],
                [InlineKeyboardButton("❌ Не согласен", callback_data='user_menu_back_to_menu')]
            ])

            await self.query.edit_message_text(
                "⚡ Вам будет предоставлено **15 USDT** в TRX для оплаты комиссии перевода, которые будут отняты из общей суммы обмена.\n\n"
                "💡 Эти средства позволят безопасно и быстро завершить транзакцию.",
                reply_markup=keyboard, parse_mode='Markdown'
            )
            return ConversationHandler.END


if __name__ == "__main__":
    clear_console()
    bot = SafePayBot()
    logger.info("Starting SafePay Bot...")
    logger.info("Bot Token: %s", bot.token)
    bot.application.run_polling()
