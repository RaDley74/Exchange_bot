
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
import logging
import Config
from SafePay_bot import SafePayBot, logger


class RequestForExchange:
    def __init__(self, bot: SafePayBot, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.config = bot.config
        self.token = self.config.get_token()
        self.admin_chat_id = self.config.get_admin_chat_id
        self.exchange_rate = self.config.get_exchange_rate
        self.admin_password = self.config.get_exchange_rate
        self.amount = context.user_data.get('amount')
        self.currency = context.user_data.get('currency', 'USDT')
        self.sum_uah = context.user_data.get('sum_uah', 0)
        self.fio = context.user_data.get('fio', '')
        self.bank_name = context.user_data.get('bank_name', '')
        self.inn = context.user_data.get('inn', '')
        self.card_info = context.user_data.get('card_info', '')
        self.user_id = bot.user.id
        self.user_first_name = bot.user.username or 'нету'
        self.user_username = bot.user.username if bot.user.username else 'нету'

    def form_admin_msg(self):

        user_info = (
            f"👤 Пользователь:\n"
            f"🆔 ID: `{self.user_id}`\n"
            f"📛 Имя: `{self.user_first_name or '-'}`\n"
            f"🔗 Юзернейм: @{self.user_username if self.user_username else 'нет'}\n\n"
        )

        transfer_info = (
            f"🏦 Банк: `{self.bank_name}`\n"
            f"📝 ФИО: `{self.fio}`\n"
            f"💳 Реквизиты карты: `{self.card_info}`\n"
            f"📇 ИНН: `{self.inn}`\n\n"
        )

        return user_info + transfer_info

    async def send_admin_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query):
        self.data = query.data
        self.user = update.effective_user
        admin_msg = self.form_admin_msg()

        logger.info(
            f"Creating standard exchange request for user {self.user.id}. Amount: {self.amount} {self.currency}"
        )

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                f"🙏 Спасибо за заявку!\n\n"
                f"💵 Сумма: {self.amount} {self.currency} → {self.sum_uah:.2f} UAH\n\n"
                f"🏦 Переведите средства на адрес:\n"
                f"`{self.config.get_wallet_address()}`\n\n"
            ),
            parse_mode='Markdown'
        )

        admin_chat_id = self.config.get_admin_chat_id()
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
            "✅ Перевод получен",
            callback_data=f"confirm_payment_{self.user.id}"
        )]])

        admin_msg_info = await context.bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"📥 Новая заявка на обмен\n\n"
                f"💱 {self.amount} {self.currency} → {self.sum_uah:.2f} UAH\n\n"
                f"{admin_msg}"
            ),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        if self.user.id not in self.user_sessions:
            self.user_sessions[self.user.id] = {}

        self.user_sessions[self.user.id]['admin_message_id'] = admin_msg_info.message_id
        self.user_sessions[self.user.id]['admin_chat_id'] = admin_msg_info.chat_id

        logger.info(f"Exchange request for user {self.user.id} sent to admin {admin_chat_id}.")
        return ConversationHandler.END
