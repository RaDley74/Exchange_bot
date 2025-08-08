# handlers/exchange_handler.py

import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
)

logger = logging.getLogger(__name__)


class ExchangeHandler:
    """
    Handles all logic related to the currency exchange process:
    - User dialog (ConversationHandler)
    - Notifications to administrators
    - Handling administrator actions (confirmation, denial)
    """
    # Conversation states are defined as class attributes for clarity
    (
        CHOOSING_CURRENCY, ENTERING_AMOUNT, ENTERING_BANK_NAME, ENTERING_CARD_DETAILS,
        ENTERING_FIO_DETAILS, ENTERING_INN_DETAILS, CONFIRMING_EXCHANGE,
        CONFIRMING_EXCHANGE_TRX, ENTERING_TRX_ADDRESS, FINAL_CONFIRMING_EXCHANGE_TRX,
        ENTERING_HASH,
    ) = range(11)

    def __init__(self, bot_instance):
        """
        The constructor receives the main Bot instance to access
        shared resources like configuration and the database.
        """
        self.bot = bot_instance

    # --- Main Menu and its handling (no changes here) ---

    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sends or edits a message to show the main menu."""
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

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        elif update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles the /start command when there is no active conversation."""
        user = update.effective_user

        check_request = self.check_if_request_exists(update, context)
        if check_request:
            logger.info(
                f"User {user.id} ({user.username}) has already an active request({check_request['id']}).")
            await update.message.reply_text(f"🚫 У вас уже есть активная заявка #{check_request['id']} в статусе: {self.translate_status(check_request['status'])}. \n\n 🛠️Если столкнулись с проблемой, напишите: {self.bot.config.support_contact}")
            return
        logger.info(f"User {user.id} ({user.username}) started the bot.")
        await self.main_menu(update, context)

    def check_if_request_exists(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        check_request = self.bot.db.get_request_by_user_id(user.id)
        return check_request if check_request is not None else None

    async def cancel_and_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Ends the current conversation and shows the main menu."""
        user = update.effective_user
        logger.info(
            f"User {user.id} ({user.username}) used /start to cancel or restart the conversation.")
        await self.main_menu(update, context)
        return ConversationHandler.END

    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles main menu button presses, starting a conversation."""
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        logger.info(f"User {user.id} ({user.username}) selected menu option: {data}")

        if data == 'rate':
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]
            await query.edit_message_text(f"📉 Актуальный курс: 1 USDT = {self.bot.config.exchange_rate} UAH", reply_markup=InlineKeyboardMarkup(keyboard))
            return ConversationHandler.END

        elif data == 'exchange':
            keyboard = [
                [InlineKeyboardButton("USDT", callback_data='currency_usdt')],
                [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
            ]
            await query.edit_message_text("💱 Выберите валюту для обмена:", reply_markup=InlineKeyboardMarkup(keyboard))
            return self.CHOOSING_CURRENCY

        elif data == 'user_help':
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]
            await query.edit_message_text(
                f"🔧 Помощь: Напиши {self.bot.config.support_contact} по любым вопросам относительно бота.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END

        elif data == 'back_to_menu':
            await self.main_menu(update, context)
            return ConversationHandler.END

        return ConversationHandler.END

    # --- ConversationHandler methods for the exchange process (All methods from here are changed) ---

    async def choosing_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user

        if data == 'currency_usdt':
            context.user_data['currency'] = 'USDT'
            logger.info(
                f"User {user.id} ({user.username}) chose currency: {context.user_data['currency']}")
            await query.edit_message_text(f"💰 Введите сумму для обмена (в {context.user_data['currency']}):")
            return self.ENTERING_AMOUNT
        elif data == 'back_to_menu':
            logger.info(f"User {user.id} ({user.username}) returned to the main menu.")
            await self.main_menu(update, context)
            return ConversationHandler.END
        return ConversationHandler.END

    async def entering_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        user = update.effective_user
        try:
            amount = float(text.replace(',', '.'))
            if amount <= 0:
                await update.message.reply_text("Введите число больше нуля.")
                return self.ENTERING_AMOUNT
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректное число.")
            return self.ENTERING_AMOUNT

        context.user_data['amount'] = amount
        currency = context.user_data.get('currency', 'USDT')
        sum_uah = amount * self.bot.config.exchange_rate
        context.user_data['sum_uah'] = sum_uah
        logger.info(
            f"User {user.id} entered amount: {amount} {currency}. Calculated sum: {sum_uah:.2f} UAH.")

        await update.message.reply_text(
            f"✅ Хорошо! К оплате: {sum_uah:.2f} UAH.\n\n🏦 Пожалуйста, укажите название банка."
        )
        return self.ENTERING_BANK_NAME

    async def entering_bank_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bank_name = update.message.text.strip()
        if not bank_name:
            await update.message.reply_text("Пожалуйста, введите корректное название банка.")
            return self.ENTERING_BANK_NAME

        context.user_data['bank_name'] = bank_name
        logger.info(f"User {update.effective_user.id} entered bank: {bank_name}")
        await update.message.reply_text(
            f"🏦 Вы указали банк: {bank_name}\n\n💳 Введите реквизиты вашей банковской карты:"
        )
        return self.ENTERING_CARD_DETAILS

    async def entering_card_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        card_info = update.message.text.strip()
        if not card_info:
            await update.message.reply_text("Пожалуйста, введите корректные реквизиты.")
            return self.ENTERING_CARD_DETAILS

        context.user_data['card_info'] = card_info
        await update.message.reply_text(f"💳 Вы указали реквизиты: {card_info}\n\n👤 Укажите ФИО:")
        return self.ENTERING_FIO_DETAILS

    async def entering_fio_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        fio = update.message.text.strip()
        if not fio:
            await update.message.reply_text("Пожалуйста, введите корректные ФИО.")
            return self.ENTERING_FIO_DETAILS

        context.user_data['fio'] = fio
        await update.message.reply_text(f"👤 Вы указали ФИО: {fio}\n\n🆔 Пожалуйста, введите ИНН:")
        return self.ENTERING_INN_DETAILS

    async def entering_inn_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        inn = update.message.text.strip()
        if not inn:
            await update.message.reply_text("Пожалуйста, введите корректный ИНН.")
            return self.ENTERING_INN_DETAILS

        context.user_data['inn'] = inn
        amount = context.user_data['amount']
        currency = context.user_data['currency']
        sum_uah = context.user_data['sum_uah']

        keyboard = [
            [InlineKeyboardButton("✅ Отправить", callback_data='send_exchange')],
            [InlineKeyboardButton("🚀 Получить TRX", callback_data='send_exchange_trx')],
            [InlineKeyboardButton("❌ Отмена", callback_data='back_to_menu')]
        ]
        await update.message.reply_text(
            f"💰 Обмен {amount} {currency} на {sum_uah:.2f} UAH.\n\n"
            f"🏦 Банк: `{context.user_data['bank_name']}`\n"
            f"👤 ФИО: `{context.user_data['fio']}`\n"
            f"💳 Реквизиты: `{context.user_data['card_info']}`\n"
            f"🆔 ИНН: `{inn}`\n\n"
            "👉 Нажмите 'Отправить' для подтверждения или 'Получить TRX', если вам нужен TRX для комиссии.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
        return self.CONFIRMING_EXCHANGE

    # --- The logic below is now heavily reliant on the database ---

    async def confirming_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == 'send_exchange':
            # Create the request in the database and get its ID
            request_id = self.bot.db.create_exchange_request(query.from_user, context.user_data)
            if not request_id:
                await query.edit_message_text("❌ Произошла ошибка при создании заявки. Попробуйте снова.")
                return ConversationHandler.END

            # Now we pass the request_id to all related functions
            await self._process_standard_exchange(query, context, request_id)
            return ConversationHandler.END

        elif data == 'send_exchange_trx':
            keyboard = [
                [InlineKeyboardButton("✅ Согласен", callback_data='send_transfer_trx')],
                [InlineKeyboardButton("❌ Не согласен", callback_data='back_to_menu')]
            ]
            await query.edit_message_text(
                "⚡ Вам будет предоставлено **15 USDT** в TRX для оплаты комиссии, которые будут вычтены из общей суммы обмена.\n\n"
                "💡 Эти средства позволят безопасно завершить транзакцию.",
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
            )
            return self.CONFIRMING_EXCHANGE_TRX
        elif data == 'back_to_menu':
            await self.main_menu(update, context)
            return ConversationHandler.END
        return ConversationHandler.END

    async def _process_standard_exchange(self, query: Update, context: ContextTypes.DEFAULT_TYPE, request_id: int):
        user = query.from_user
        request_data = self.bot.db.get_request_by_id(request_id)
        logger.info(f"Creating a standard exchange request ({request_id}) for user {user.id}.")

        user_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Я совершил(а) перевод",
                                 callback_data=f"user_confirms_sending_{request_id}")
        ]])

        wallet_address = self.bot.config.wallet_address

        msg = await query.edit_message_text(
            f"🙏 Спасибо за заявку #{request_id}!\n\n"
            f"💵 Сумма: {request_data['amount_currency']} {request_data['currency']} → {request_data['amount_uah']:.2f} UAH\n\n"
            f"🏦 Переведите средства на адрес:\n`{wallet_address}`\n\n"
            "После перевода нажмите кнопку ниже для предоставления хэша.",
            parse_mode='Markdown', reply_markup=user_keyboard
        )

        self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
        self.bot.db.update_request_status(request_id, 'awaiting payment')
        await self._send_admin_notification(request_id)

    async def resend_messages_for_request(self, request_id: int):
        """
        Re-sends all relevant messages for a specific request to both the user and admins.
        This is used to restore or update messages after a manual status change.
        """
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            raise ValueError(f"Request with ID {request_id} not found in database.")

        status = request_data['status']
        user_id = request_data['user_id']
        user_text = None
        user_keyboard = None
        new_user_message_id = None

        # Determine the user message based on the current status
        if status == 'awaiting trx transfer':
            user_text = f"🙏 Спасибо за заявку #{request_id}!\n\n" \
                "🏦 Ожидайте сообщения от бота об успешном переводе TRX ✅"
        elif status == 'awaiting payment':
            amount_display = request_data['amount_currency']
            message_intro = f"🙏 Спасибо за заявку #{request_id}!\n\n"
            if request_data['needs_trx']:
                amount_display -= 15
                message_intro = f"✅ Перевод TRX выполнен для заявки #{request_id}.\n\n"

            user_text = message_intro + \
                f"📥 Переведите {amount_display:.2f} {request_data['currency']} на кошелек:\n" \
                f"`{self.bot.config.wallet_address}`\n\n" \
                "После перевода нажмите кнопку ниже для предоставления хэша."
            user_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Я совершил(а) перевод",
                                     callback_data=f"user_confirms_sending_{request_id}")
            ]])
        elif status == 'awaiting confirmation':
            user_text = "✅ Спасибо, ваш хэш получен и отправлен на проверку."
        elif status == 'payment received':
            user_text = f"✅ Средства по заявке #{request_id} получены.\n\n⏳ Ожидайте перевода."
        elif status == 'funds sent':
            user_text = f"✅ Перевод средств по заявке #{request_id} вам выполнен успешно. 💸\n\n" \
                "🙏 Спасибо за использование нашего сервиса! 🤝\n\n" \
                "Пожалуйста, подтвердите получение средств."
            user_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Подтвердить получение средств",
                                     callback_data=f"by_user_confirm_transfer_{request_id}")
            ]])
        elif status == 'declined':
            user_text = f"❌ Ваша заявка #{request_id} была отклонена.\n\nПо вопросам обращайтесь: {self.bot.config.support_contact}"
        elif status == 'completed':
            user_text = f"✅ Перевод средств по заявке #{request_id} вам выполнен успешно. 💸\n\n" \
                "🙏 Спасибо за использование нашего сервиса! 🤝\n\n" \
                "✅ Вы подтвердили получение."

        # Send the message to the user if it was formed
        if user_text:
            try:
                msg = await self.bot.application.bot.send_message(
                    chat_id=user_id,
                    text=user_text,
                    reply_markup=user_keyboard,
                    parse_mode='Markdown'
                )
                new_user_message_id = msg.message_id
            except Exception as e:
                logger.error(
                    f"Could not send restoration message to user {user_id} for request #{request_id}: {e}")

        # Regenerate the admin message
        await self._send_admin_notification(request_id, is_restoration=True)

        # Update the user message ID in the database if it was sent
        if new_user_message_id:
            self.bot.db.update_request_data(request_id, {'user_message_id': new_user_message_id})

    async def confirming_exchange_trx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == 'send_transfer_trx':
            await query.edit_message_text(
                "✅ Вы подтвердили запрос на TRX.\n\n📬 Пожалуйста, укажите ваш TRX-кошелек:",
                parse_mode='Markdown'
            )
            return self.ENTERING_TRX_ADDRESS
        elif query.data == 'back_to_menu':
            await self.main_menu(update, context)
            return ConversationHandler.END
        return ConversationHandler.END

    async def entering_trx_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        trx_address = update.message.text.strip()
        if not trx_address:
            await update.message.reply_text("Пожалуйста, введите корректный адрес.")
            return self.ENTERING_TRX_ADDRESS

        context.user_data['trx_address'] = trx_address
        amount = context.user_data['amount']
        final_amount = amount - 15
        final_sum_uah = final_amount * self.bot.config.exchange_rate

        keyboard = [
            [InlineKeyboardButton("✅ Отправить", callback_data='send_exchange_with_trx')],
            [InlineKeyboardButton("❌ Отмена", callback_data='back_to_menu')]
        ]
        await update.message.reply_text(
            f"📋 Ваша информация:\n\n"
            f"💰 Обмен: {amount} {context.user_data['currency']} → {context.user_data['sum_uah']:.2f} UAH\n"
            f"⚡ Вам будет отправлено **15 USDT** в TRX.\n\n"
            f"💱 Итоговая сумма обмена: {final_amount} {context.user_data['currency']} → {final_sum_uah:.2f} UAH\n\n"
            f"🔗 TRX-адрес: {trx_address}\n\n👉 Нажмите 'Отправить' для подтверждения.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
        return self.FINAL_CONFIRMING_EXCHANGE_TRX

    async def final_confirming_exchange_trx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == 'send_exchange_with_trx':
            request_id = self.bot.db.create_exchange_request(query.from_user, context.user_data)
            if not request_id:
                await query.edit_message_text("❌ Произошла ошибка при создании заявки. Попробуйте снова.")
                return ConversationHandler.END

            msg = await query.message.chat.send_message(
                f"🙏 Спасибо за заявку #{request_id}!\n\n"
                "🏦 Ожидайте сообщения от бота об успешном переводе TRX ✅",
                parse_mode='Markdown'
            )

            self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
            self.bot.db.update_request_status(request_id, 'awaiting trx transfer')
            await self._send_admin_notification(request_id)

            return ConversationHandler.END
        elif query.data == 'back_to_menu':
            await self.main_menu(update, context)
            return ConversationHandler.END
        return ConversationHandler.END

    async def ask_for_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        context.user_data['request_id'] = request_id
        await query.edit_message_text(text="✍️ Пожалуйста, отправьте хэш вашей транзакции:")
        return self.ENTERING_HASH

    async def process_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        submitted_hash = update.message.text
        request_id = context.user_data.get('request_id')

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await update.message.reply_text("Произошла ошибка сессии. Начните сначала: /start")
            return ConversationHandler.END

        # Update hash in DB
        self.bot.db.update_request_data(request_id, {'transaction_hash': submitted_hash})
        self.bot.db.update_request_status(request_id, 'awaiting confirmation')

        # Re-fetch data to get the latest state
        request_data = self.bot.db.get_request_by_id(request_id)

        base_admin_text, _ = self._prepare_admin_notification(request_data)
        final_admin_text = base_admin_text + \
            f"\n\n✅2️⃣ Пользователь подтвердил перевод {request_data['amount_currency']} {request_data['currency']}. Hash: `{submitted_hash}`"

        admin_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Средства получены",
                                 callback_data=f"confirm_payment_{request_id}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{request_id}")
        ]])

        await self._update_admin_messages(request_id, final_admin_text, admin_keyboard)
        await update.message.reply_text("✅ Спасибо, ваш хэш получен и отправлен на проверку.")
        return ConversationHandler.END

    # --- Admin Callback Handlers (all updated to use request_id) ---

    async def handle_transfer_confirmation_trx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.answer("Заявка не найдена!", show_alert=True)
            return

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Я совершил(а) перевод",
                                 callback_data=f"user_confirms_sending_{request_id}")
        ]])
        msg = await context.bot.send_message(
            chat_id=request_data['user_id'],
            text=(f"✅ Перевод TRX выполнен для заявки #{request_id}.\n\n"
                  f"📥 Переведите {(request_data['amount_currency'] - 15):.2f} {request_data['currency']} на кошелек:\n"
                  f"`{self.bot.config.wallet_address}`\n\n"
                  "После перевода нажмите кнопку ниже."),
            reply_markup=keyboard, parse_mode='Markdown'
        )
        self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
        self.bot.db.update_request_status(request_id, 'awaiting payment')

        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += "\n\n✅1️⃣ Уведомление о переводе TRX отправлено"

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{request_id}")
        ]])
        await self._update_admin_messages(request_id, updated_text, keyboard)

    async def handle_payment_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            return

        msg = await context.bot.send_message(chat_id=request_data['user_id'], text=f"✅ Средства по заявке #{request_id} получены.\n\n⏳ Ожидайте перевода.")

        self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
        self.bot.db.update_request_status(request_id, 'payment received')

        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += f"\n\n✅ Хэш: `{request_data['transaction_hash']}`"
        updated_text += f"\n\n✅3️⃣ Уведомление о получении средств отправлено."

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Перевод клиенту сделан",
                                 callback_data=f"confirm_transfer_{request_id}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{request_id}")
        ]])
        await self._update_admin_messages(request_id, updated_text, keyboard)

    async def handle_transfer_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подтвердить получение средств",
                                  callback_data=f"by_user_confirm_transfer_{request_id}")]
        ])
        msg = await context.bot.send_message(
            chat_id=request_data['user_id'],
            text=f"✅ Перевод средств по заявке #{request_id} вам выполнен успешно. 💸\n\n"
            "🙏 Спасибо за использование нашего сервиса! 🤝\n\n"
            "Пожалуйста, подтвердите получение средств.",
            reply_markup=keyboard, parse_mode='Markdown'
        )

        self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
        self.bot.db.update_request_status(request_id, 'funds sent')

        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += f"\n\n✅ Хэш: `{request_data['transaction_hash']}`"
        updated_text += "\n\n✅4️⃣ Уведомление об отправке средств клиенту отправлено."
        await self._update_admin_messages(request_id, updated_text, None)

    def translate_status(self, status: str) -> str:
        translations = {
            'new': 'Новая',
            'awaiting payment': 'Ожидание оплаты клиентом',
            'awaiting trx transfer': 'Ожидание перевода TRX клиенту',
            'awaiting confirmation': 'Ожидание подтверждения перевода',
            'payment received': 'Платёж от клиента получен',
            'funds sent': 'Средства клиенту отправлены',
            'declined': 'Отклонено',
            'completed': 'Завершено'
        }
        return translations.get(status.lower(), status)

    async def handle_decline_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        admin_user = query.from_user

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            return

        support_contact = self.bot.config.support_contact
        await context.bot.send_message(
            chat_id=request_data['user_id'],
            text=f"❌ Ваша заявка #{request_id} была отклонена.\n\nПо вопросам обращайтесь: {support_contact}"
        )

        self.bot.db.update_request_status(request_id, 'declined')

        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += f"\n\n❌ ЗАЯВКА ОТКЛОНЕНА (админ @{admin_user.username or admin_user.id})"
        await self._update_admin_messages(request_id, updated_text, None)

    async def handle_by_user_transfer_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.edit_message_text("⏳ Сессия истекла. \n🔄 Пожалуйста, начните заново. \n🚀 /start", reply_markup=None)
            return

        self.bot.db.update_request_status(request_id, 'completed')

        # Update the admin message
        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += "\n\n✅🛑 Пользователь подтвердил получение средств. ЗАЯВКА ЗАВЕРШЕНА. 🛑✅"
        await self._update_admin_messages(request_id, updated_text, None)

        # Remove the button for the user
        await query.edit_message_text(
            text=f"✅ Перевод средств по заявке #{request_id} вам выполнен успешно. 💸\n\n"
            "🙏 Спасибо за использование нашего сервиса! 🤝\n\n"
            "✅ Вы подтвердили получение.",
            reply_markup=None,
            parse_mode='Markdown'
        )

    # --- Helper Methods ---

    def _prepare_admin_notification(self, request_data):
        """Prepares the text and keyboard for the administrator notification."""
        username_display = 'нет'
        if request_data['username']:
            username_display = request_data['username'].replace('_', '\\_').replace(
                '*', '\\*').replace('`', '\\`').replace('[', '\\[')

        def sanitize_for_code_block(text):
            return str(text).replace('`', "'") if text else ""

        bank_name_safe = sanitize_for_code_block(request_data['bank_name'])
        fio_safe = sanitize_for_code_block(request_data['fio'])
        card_info_safe = sanitize_for_code_block(request_data['card_info'])
        inn_safe = sanitize_for_code_block(request_data['inn'])
        trx_address_safe = sanitize_for_code_block(request_data['trx_address'])

        status_text = self.translate_status(request_data['status'])
        title = f"📥 Заявка #{request_data['id']} (Статус: {status_text})"

        user_info_block = (f"👤 Пользователь:\n"
                           f"🆔 ID: `{request_data['user_id']}`\n"
                           f"📛 Юзернейм: @{username_display}\n\n")

        transfer_details_block = (f"🏦 Банк: `{bank_name_safe}`\n"
                                  f"📝 ФИО: `{fio_safe}`\n"
                                  f"💳 Реквизиты: `{card_info_safe}`\n"
                                  f"📇 ИНН: `{inn_safe}`\n\n")

        base_text = (f"{title}\n\n"
                     f"💱 {request_data['amount_currency']} {request_data['currency']} → {request_data['amount_uah']:.2f} UAH\n\n"
                     f"{user_info_block}{transfer_details_block}")

        # Default keyboard
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "❌ Отказать", callback_data=f"decline_request_{request_data['id']}")
        ]])

        if request_data['needs_trx']:
            amount, sum_uah = request_data['amount_currency'], request_data['amount_uah']
            final_amount = amount - 15
            final_sum_uah = final_amount * self.bot.config.exchange_rate
            base_text = (f"{title} (с TRX)\n\n"
                         f"💱 {amount} {request_data['currency']} → {sum_uah:.2f} UAH\n"
                         f"💵 После вычета TRX: {final_amount} {request_data['currency']} → {final_sum_uah:.2f} UAH\n\n"
                         f"{user_info_block}{transfer_details_block}"
                         f"⚠️ Клиент нуждается в TRX.\n📬 TRX-адрес: `{trx_address_safe}`")
            if request_data['status'] == 'awaiting trx transfer':
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ TRX переведено",
                                         callback_data=f"confirm_trx_transfer_{request_data['id']}"),
                    InlineKeyboardButton(
                        "❌ Отказать", callback_data=f"decline_request_{request_data['id']}")
                ]])

        return base_text, keyboard

    async def _send_admin_notification(self, request_id, is_restoration=False):
        """
        Sends notifications to all administrators.
        If is_restoration is True, it regenerates messages based on the current state.
        """
        admin_ids = self.bot.config.admin_ids
        if not admin_ids:
            return

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            return

        text, keyboard = self._prepare_admin_notification(request_data)
        status = request_data['status']

        # Add stage-specific text and buttons
        if status == 'awaiting confirmation':
            text += f"\n\n✅2️⃣ Пользователь подтвердил перевод. Hash: `{request_data['transaction_hash']}`"
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Средства получены",
                                     callback_data=f"confirm_payment_{request_id}"),
                InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{request_id}")
            ]])
        elif status == 'payment received':
            text += f"\n\n✅ Хэш: `{request_data.get('transaction_hash', 'Нет')}`"
            text += f"\n\n✅3️⃣ Уведомление о получении средств отправлено."
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Перевод клиенту сделан",
                                     callback_data=f"confirm_transfer_{request_id}"),
                InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{request_id}")
            ]])
        elif status == 'funds sent':
            text += f"\n\n✅ Хэш: `{request_data.get('transaction_hash', 'Нет')}`"
            text += "\n\n✅4️⃣ Уведомление об отправке средств клиенту отправлено."
            keyboard = None
        elif status == 'completed':
            text += f"\n\n✅ Хэш: `{request_data.get('transaction_hash', 'Нет')}`"
            text += "\n\n✅🛑 Пользователь подтвердил получение средств. ЗАЯВКА ЗАВЕРШЕНА. 🛑✅"
            keyboard = None
        elif status == 'declined':
            text += f"\n\n❌ ЗАЯВКА ОТКЛОНЕНА"
            keyboard = None

        admin_message_ids = {}

        for admin_id in admin_ids:
            try:
                msg = await self.bot.application.bot.send_message(
                    chat_id=admin_id, text=text, parse_mode='Markdown', reply_markup=keyboard
                )
                admin_message_ids[admin_id] = msg.message_id
            except Exception as e:
                logger.error(f"Failed to send message to admin {admin_id}: {e}")

        # Store message IDs as a JSON string in the database
        self.bot.db.update_request_data(
            request_id, {'admin_message_ids': json.dumps(admin_message_ids)})

    async def _update_admin_messages(self, request_id, text, reply_markup):
        """Updates messages for all administrators."""
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data or not request_data['admin_message_ids']:
            return

        admin_message_ids = json.loads(request_data['admin_message_ids'])
        for admin_id, message_id in admin_message_ids.items():
            try:
                await self.bot.application.bot.edit_message_text(
                    chat_id=admin_id, message_id=message_id, text=text,
                    reply_markup=reply_markup, parse_mode='Markdown'
                )
            except Exception as e:
                # The message might have been deleted or the bot blocked.
                logger.warning(f"Failed to update message for admin {admin_id}: {e}")

    def setup_handlers(self, application):
        """Creates and registers all handlers related to the exchange process."""

        exchange_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.handle_menu_callback, pattern='^(exchange|rate|user_help|back_to_menu)$')],
            states={
                self.CHOOSING_CURRENCY: [CallbackQueryHandler(self.choosing_currency, pattern='^(currency_usdt|back_to_menu)$')],
                self.ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_amount)],
                self.ENTERING_BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_bank_name)],
                self.ENTERING_CARD_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_card_details)],
                self.ENTERING_FIO_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_fio_details)],
                self.ENTERING_INN_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_inn_details)],
                self.CONFIRMING_EXCHANGE: [CallbackQueryHandler(self.confirming_exchange, pattern='^(send_exchange|send_exchange_trx|back_to_menu)$')],
                self.CONFIRMING_EXCHANGE_TRX: [CallbackQueryHandler(self.confirming_exchange_trx, pattern='^(send_transfer_trx|back_to_menu)$')],
                self.ENTERING_TRX_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_trx_address)],
                self.FINAL_CONFIRMING_EXCHANGE_TRX: [CallbackQueryHandler(self.final_confirming_exchange_trx, pattern='^(send_exchange_with_trx|back_to_menu)$')],
            },
            fallbacks=[CommandHandler('start', self.cancel_and_restart)],
            per_message=False
        )

        hash_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.ask_for_hash, pattern=r'^user_confirms_sending_')],
            states={
                self.ENTERING_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_hash)],
            },
            fallbacks=[CommandHandler('start', self.cancel_and_restart)],
        )

        application.add_handler(exchange_conv_handler)
        application.add_handler(hash_conv_handler)

        # Regex patterns now match any number of digits for the request_id
        application.add_handler(CallbackQueryHandler(
            self.handle_decline_request, pattern=r'^decline_request_\d+'))
        application.add_handler(CallbackQueryHandler(
            self.handle_payment_confirmation, pattern=r'^confirm_payment_\d+'))
        application.add_handler(CallbackQueryHandler(
            self.handle_transfer_confirmation, pattern=r'^confirm_transfer_\d+'))
        application.add_handler(CallbackQueryHandler(
            self.handle_transfer_confirmation_trx, pattern=r'^confirm_trx_transfer_\d+'))
        application.add_handler(CallbackQueryHandler(
            self.handle_by_user_transfer_confirmation, pattern=r'^by_user_confirm_transfer_\d+'))

        application.add_handler(CommandHandler('start', self.start_command))
