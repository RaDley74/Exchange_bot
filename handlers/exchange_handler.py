# handlers/exchange_handler.py

import logging
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
        shared resources like configuration and sessions.
        """
        self.bot = bot_instance

    # --- Main Menu and its handling ---

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
        logger.info(f"User {user.id} ({user.username}) started the bot.")
        await self.main_menu(update, context)

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

    # --- ConversationHandler methods for the exchange process ---

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

    async def confirming_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == 'send_exchange':
            return await self._process_standard_exchange(query, context)
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

    async def _process_standard_exchange(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
        user = query.from_user
        logger.info(f"Creating a standard exchange request for user {user.id}.")

        self.bot.user_sessions[user.id] = context.user_data.copy()

        user_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Я совершил(а) перевод",
                                 callback_data=f"user_confirms_sending_{user.id}")
        ]])

        await query.edit_message_text(
            f"🙏 Спасибо за заявку!\n\n"
            f"💵 Сумма: {context.user_data['amount']} {context.user_data['currency']} → {context.user_data['sum_uah']:.2f} UAH\n\n"
            f"🏦 Переведите средства на адрес:\n`{self.bot.config.wallet_address}`\n\n"
            "После перевода нажмите кнопку ниже для предоставления хэша.",
            parse_mode='Markdown', reply_markup=user_keyboard
        )

        text_for_admin, admin_keyboard = self._prepare_admin_notification(user, context.user_data)
        await self._send_admin_notification(user.id, text_for_admin, admin_keyboard)

        return ConversationHandler.END

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
        user = query.from_user

        if query.data == 'send_exchange_with_trx':
            self.bot.user_sessions[user.id] = context.user_data.copy()

            await query.message.chat.send_message(
                "🙏 Спасибо за заявку!\n\n"
                "🏦 Ожидайте сообщения от бота об успешном переводе TRX ✅",
                parse_mode='Markdown'
            )

            text_for_admin, admin_keyboard = self._prepare_admin_notification(
                user, context.user_data, needs_trx=True)
            await self._send_admin_notification(user.id, text_for_admin, admin_keyboard)

            return ConversationHandler.END
        elif query.data == 'back_to_menu':
            await self.main_menu(update, context)
            return ConversationHandler.END
        return ConversationHandler.END

    async def ask_for_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = int(query.data.split('_')[-1])
        context.user_data['session_user_id'] = user_id
        await query.edit_message_text(text="✍️ Пожалуйста, отправьте хэш вашей транзакции:")
        return self.ENTERING_HASH

    async def process_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        submitted_hash = update.message.text
        session_user_id = context.user_data.get('session_user_id')

        session = self.bot.user_sessions.get(session_user_id)
        if not session:
            await update.message.reply_text("Произошла ошибка сессии. Начните сначала: /start")
            return ConversationHandler.END

        base_admin_text = session.get('admin_text_after_trx') or session.get('admin_text')
        final_admin_text = base_admin_text + \
            f"\n\n✅2️⃣ Пользователь подтвердил перевод. Hash: `{submitted_hash}`"
        session['admin_text'] = final_admin_text

        admin_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Средства получены",
                                 callback_data=f"confirm_payment_{session_user_id}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{session_user_id}")
        ]])

        await self._update_admin_messages(session, final_admin_text, admin_keyboard)
        await update.message.reply_text("✅ Спасибо, ваш хэш получен и отправлен на проверку.")
        return ConversationHandler.END

    # --- Admin Callback Handlers ---

    async def handle_transfer_confirmation_trx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = int(query.data.split('_')[-1])
        session = self.bot.user_sessions.get(user_id)
        if not session:
            return

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Я совершил(а) перевод",
                                 callback_data=f"user_confirms_sending_{user_id}")
        ]])
        await context.bot.send_message(
            chat_id=user_id,
            text=(f"✅ Перевод TRX выполнен.\n\n"
                  f"📥 Переведите {(session['amount'] - 15):.2f} {session['currency']} на кошелек:\n"
                  f"`{self.bot.config.wallet_address}`\n\n"
                  "После перевода нажмите кнопку ниже."),
            reply_markup=keyboard, parse_mode='Markdown'
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{user_id}")
        ]])
        updated_text = session.get('admin_text', '') + \
            "\n\n✅1️⃣ Уведомление о переводе TRX отправлено"
        session['admin_text_after_trx'] = updated_text
        await self._update_admin_messages(session, updated_text, keyboard)

    async def handle_payment_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = int(query.data.split('_')[-1])
        await context.bot.send_message(chat_id=user_id, text="✅ Средства получены.\n\n⏳ Ожидайте перевода.")

        session = self.bot.user_sessions.get(user_id, {})
        updated_text = session.get('admin_text', '') + \
            f"\n\n✅3️⃣ Уведомление о получении средств отправлено."
        session['admin_text'] = updated_text
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Перевод клиенту сделан",
                                 callback_data=f"confirm_transfer_{user_id}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{user_id}")
        ]])
        await self._update_admin_messages(session, updated_text, keyboard)

    async def handle_transfer_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = int(query.data.split('_')[-1])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подтвердить получение средств",
                                  callback_data=f"by_user_confirm_transfer_{user_id}")]
        ])
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Перевод средств вам выполнен успешно. 💸\n\n"
                 "🙏 Спасибо за использование нашего сервиса! 🤝\n\n"
                 "Пожалуйста, подтвердите получение средств.",
            reply_markup=keyboard, parse_mode='Markdown'
        )

        session = self.bot.user_sessions.get(user_id, {})
        updated_text = session.get('admin_text', '') + \
            "\n\n✅4️⃣ Уведомление об отправке средств клиенту отправлено."
        session['admin_text'] = updated_text
        await self._update_admin_messages(session, updated_text, None)

    async def handle_decline_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = int(query.data.split('_')[-1])
        admin_user = query.from_user

        support_contact = self.bot.config.support_contact
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Ваша заявка была отклонена.\n\nПо вопросам обращайтесь: {support_contact}"
        )

        session = self.bot.user_sessions.get(user_id)
        if session:
            updated_text = session.get(
                'admin_text', '') + f"\n\n❌ ЗАЯВКА ОТКЛОНЕНА (админ @{admin_user.username or admin_user.id})"
            await self._update_admin_messages(session, updated_text, None)
            del self.bot.user_sessions[user_id]
        else:
            await query.edit_message_text(
                query.message.text + f"\n\n❌ ЗАЯВКА ОТКЛОНЕНА", reply_markup=None
            )

    async def handle_by_user_transfer_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = int(query.data.split('_')[-1])
        session = self.bot.user_sessions.get(user_id)
        if not session:
            await query.edit_message_text("⏳ Сессия истекла. \n🔄 Пожалуйста, начните заново. \n🚀 /start", reply_markup=None)
            return

        # Update the admin message
        updated_text = session.get('admin_text', '') + \
            "\n\n✅🛑 Пользователь подтвердил получение средств. 🛑✅"
        session['admin_text'] = updated_text
        await self._update_admin_messages(session, updated_text, None)

        # Remove the button for the user
        await query.edit_message_text(
            text="✅ Перевод средств вам выполнен успешно. 💸\n\n"
                 "🙏 Спасибо за использование нашего сервиса! 🤝\n\n"
                 "✅ Вы подтвердили получение.",
            reply_markup=None,
            parse_mode='Markdown'
        )

        # Delete the session after full completion
        if user_id in self.bot.user_sessions:
            del self.bot.user_sessions[user_id]

    # --- Helper Methods ---

    def _prepare_admin_notification(self, user, user_data, needs_trx=False):
        """Prepares the text and keyboard for the administrator notification."""
        user_info_block = (f"👤 Пользователь:\n"
                           f"🆔 ID: `{user.id}`\n"
                           f"📛 Имя: `{user.first_name or '-'}`\n"
                           f"🔗 Юзернейм: @{user.username if user.username else 'нет'}\n\n")
        transfer_details_block = (f"🏦 Банк: `{user_data['bank_name']}`\n"
                                  f"📝 ФИО: `{user_data['fio']}`\n"
                                  f"💳 Реквизиты: `{user_data['card_info']}`\n"
                                  f"📇 ИНН: `{user_data['inn']}`\n\n")
        if needs_trx:
            amount, sum_uah = user_data['amount'], user_data['sum_uah']
            final_amount = amount - 15
            final_sum_uah = final_amount * self.bot.config.exchange_rate
            text = (f"📥 Новая заявка (с TRX)\n\n"
                    f"💱 {amount} {user_data['currency']} → {sum_uah:.2f} UAH\n"
                    f"💵 После вычета TRX: {final_amount} {user_data['currency']} → {final_sum_uah:.2f} UAH\n\n"
                    f"{user_info_block}{transfer_details_block}"
                    f"⚠️ Клиент нуждается в TRX.\n📬 TRX-адрес: `{user_data['trx_address']}`")
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ TRX переведено",
                                     callback_data=f"confirm_trx_transfer_{user.id}"),
                InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{user.id}")
            ]])
        else:
            text = (f"📥 Новая заявка на обмен\n\n"
                    f"💱 {user_data['amount']} {user_data['currency']} → {user_data['sum_uah']:.2f} UAH\n\n"
                    f"{user_info_block}{transfer_details_block}")
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{user.id}")
            ]])
        return text, keyboard

    async def _send_admin_notification(self, user_id, text, keyboard):
        """Sends notifications to all administrators."""
        admin_ids = self.bot.config.admin_ids
        if not admin_ids:
            return

        session = self.bot.user_sessions.get(user_id)
        if not session:
            return

        admin_message_ids = {}
        for admin_id in admin_ids:
            try:
                msg = await self.bot.application.bot.send_message(
                    chat_id=admin_id, text=text, parse_mode='Markdown', reply_markup=keyboard
                )
                admin_message_ids[admin_id] = msg.message_id
            except Exception as e:
                logger.error(f"Failed to send message to admin {admin_id}: {e}")

        session['admin_message_ids'] = admin_message_ids
        session['admin_text'] = text

    async def _update_admin_messages(self, session, text, reply_markup):
        """Updates messages for all administrators."""
        admin_message_ids = session.get('admin_message_ids', {})
        for admin_id, message_id in admin_message_ids.items():
            try:
                await self.bot.application.bot.edit_message_text(
                    chat_id=admin_id, message_id=message_id, text=text,
                    reply_markup=reply_markup, parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to update message for admin {admin_id}: {e}")

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

        application.add_handler(CallbackQueryHandler(
            self.handle_decline_request, pattern=r'^decline_request_'))
        application.add_handler(CallbackQueryHandler(
            self.handle_payment_confirmation, pattern=r'^confirm_payment_'))
        application.add_handler(CallbackQueryHandler(
            self.handle_transfer_confirmation, pattern=r'^confirm_transfer_'))
        application.add_handler(CallbackQueryHandler(
            self.handle_transfer_confirmation_trx, pattern=r'^confirm_trx_transfer_'))
        application.add_handler(CallbackQueryHandler(
            self.handle_by_user_transfer_confirmation, pattern=r'^by_user_confirm_transfer_'))

        application.add_handler(CommandHandler('start', self.start_command))
