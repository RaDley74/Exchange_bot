from SafePay_bot import bot
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

class RequestForExchange:
    def __init__(self, config_file="settings.ini"):
        self.config = bot.config
        self.token = self.config.get_token()
        self.admin_chat_id = self.config.get_admin_chat_id()
        self.exchange_rate = float(self.config.get_exchange_rate())
        self.admin_password = self.config.get_admin_password()
        
        
        
    async def start_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        context.user_data['user'] = user
        await update.message.reply_text(
            "💱 Выберите тип обмена:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Обмен USDT на UAH", callback_data='send_exchange')],
                [InlineKeyboardButton("Обмен USDT на TRX", callback_data='send_exchange_trx')]
            ])
        )