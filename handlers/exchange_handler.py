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
        ENTERING_CARD_NUMBER, ENTERING_FIO_DETAILS, ENTERING_INN_DETAILS, CONFIRMING_EXCHANGE,
        CONFIRMING_EXCHANGE_TRX, ENTERING_TRX_ADDRESS, FINAL_CONFIRMING_EXCHANGE_TRX,
        ENTERING_HASH, SELECTING_CANCELLATION_TYPE, AWAITING_REASON_TEXT,
    ) = range(14)

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
        if not self.bot.config.bot_enabled:
            await update.message.reply_text("🔧🤖 Бот на техническом обслуживании. \n\n⏳ Пожалуйста, попробуйте позже.")
            return
        user = update.effective_user

        check_request = self.check_if_request_exists(update, context)
        if check_request:
            logger.info(
                f"[Uid] ({user.id}, {user.username}) - Already has an active request ({check_request['id']}).")
            await update.message.reply_text(f"🚫 У вас уже есть активная заявка #{check_request['id']} в статусе: {self.translate_status(check_request['status'])}. \n\n 🛠️Если столкнулись с проблемой, напишите: {self.bot.config.support_contact}")
            return
        logger.info(f"[Uid] ({user.id}, {user.username}) - Started the bot.")
        await self.main_menu(update, context)

    def check_if_request_exists(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        check_request = self.bot.db.get_request_by_user_id(user.id)
        return check_request if check_request is not None else None

    async def cancel_and_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Ends the current conversation and shows the main menu."""
        user = update.effective_user
        if not self.bot.config.bot_enabled:
            await update.message.reply_text("🔧🤖 Бот на техническом обслуживании. \n\n⏳ Пожалуйста, попробуйте позже.")
            return
        logger.info(
            f"[Uid] ({user.id}, {user.username}) - Used /start to cancel or restart the dialog.")
        await self.main_menu(update, context)
        return ConversationHandler.END

    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles main menu button presses, starting a conversation."""
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        logger.info(f"[Uid] ({user.id}, {user.username}) - Selected menu option: {data}")

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

    async def choosing_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user

        if data == 'currency_usdt':
            context.user_data['currency'] = 'USDT'
            logger.info(
                f"[Uid] ({user.id}, {user.username}) - Chose currency: {context.user_data['currency']}")
            await query.edit_message_text(f"💰 Введите сумму для обмена (в {context.user_data['currency']}):")
            return self.ENTERING_AMOUNT
        elif data == 'back_to_menu':
            logger.info(f"[Uid] ({user.id}, {user.username}) - Returned to the main menu.")
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
            f"[Uid] ({user.id}, {user.username}) - Entered amount: {amount} {currency}. Calculated sum: {sum_uah:.2f} UAH.")

        await update.message.reply_text(
            f"✅ Хорошо! К оплате: {sum_uah:.2f} UAH.\n\n🏦 Пожалуйста, укажите название банка."
        )
        return self.ENTERING_BANK_NAME

    async def entering_bank_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        bank_name = update.message.text.strip()
        if not bank_name:
            await update.message.reply_text("Пожалуйста, введите корректное название банка.")
            return self.ENTERING_BANK_NAME

        context.user_data['bank_name'] = bank_name
        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered bank: {bank_name}")
        await update.message.reply_text(
            f"🏦 Вы указали банк: {bank_name}\n\n💳 Введите IBAN:"
        )
        return self.ENTERING_CARD_DETAILS

    async def entering_card_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        card_info = update.message.text.strip()
        if not card_info:
            await update.message.reply_text("Пожалуйста, введите корректный IBAN.")
            return self.ENTERING_CARD_DETAILS

        context.user_data['card_info'] = card_info
        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered IBAN: {card_info}")
        await update.message.reply_text(f"💳 Вы указали IBAN: {card_info}\n\n🔢 Теперь введите номер карты:")
        return self.ENTERING_CARD_NUMBER

    async def entering_card_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        card_number = update.message.text.strip()
        if not card_number:
            await update.message.reply_text("Пожалуйста, введите корректный номер карты.")
            return self.ENTERING_CARD_NUMBER

        context.user_data['card_number'] = card_number
        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered card number: {card_number}")
        await update.message.reply_text(f"🔢 Вы указали номер карты: {card_number}\n\n👤 Укажите ФИО:")
        return self.ENTERING_FIO_DETAILS

    async def entering_fio_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        fio = update.message.text.strip()
        if not fio:
            await update.message.reply_text("Пожалуйста, введите корректные ФИО.")
            return self.ENTERING_FIO_DETAILS

        context.user_data['fio'] = fio
        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered full name: {fio}")
        await update.message.reply_text(f"👤 Вы указали ФИО: {fio}\n\n🆔 Пожалуйста, введите ІПН/ЄДРПОУ:")
        return self.ENTERING_INN_DETAILS

    async def entering_inn_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        inn = update.message.text.strip()
        if not inn:
            await update.message.reply_text("Пожалуйста, введите корректный ИНН.")
            return self.ENTERING_INN_DETAILS

        context.user_data['inn'] = inn
        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered INN: {inn}")
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
            f"💳 IBAN: `{context.user_data['card_info']}`\n"
            f"🔢 Номер карты: `{context.user_data['card_number']}`\n"
            f"🆔 ІПН/ЄДРПОУ: `{inn}`\n\n"
            "👉 Нажмите 'Отправить' для подтверждения или 'Получить TRX', если вам нужен TRX для комиссии.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
        return self.CONFIRMING_EXCHANGE

    async def confirming_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == 'send_exchange':
            request_id = self.bot.db.create_exchange_request(query.from_user, context.user_data)
            if not request_id:
                await query.edit_message_text("❌ Произошла ошибка при создании заявки. Попробуйте снова.")
                return ConversationHandler.END

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
        logger.info(
            f"[Uid] ({user.id}, {user.username}) - Creating a standard exchange request (#{request_id}).")

        user_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я совершил(а) перевод",
                                  callback_data=f"user_confirms_sending_{request_id}")],
            [InlineKeyboardButton("❌ Отменить заявку",
                                  callback_data=f"cancel_by_user_{request_id}")]
        ])

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
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            raise ValueError(f"Request with ID {request_id} not found in the database.")

        status = request_data['status']
        user_id = request_data['user_id']
        user_text = None
        user_keyboard = None
        new_user_message_id = None

        if status == 'awaiting trx transfer':
            user_text = f"🙏 Спасибо за заявку #{request_id}!\n\n" \
                "🏦 Ожидайте сообщения об успешном переводе TRX ✅"
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
            user_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Я совершил(а) перевод",
                                      callback_data=f"user_confirms_sending_{request_id}")],
                [InlineKeyboardButton("❌ Отменить заявку",
                                      callback_data=f"cancel_by_user_{request_id}")]
            ])
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
            user_text = (
                f"❌ Ваша заявка #{request_id} была отклонена.\n\n"
                f"📞 По вопросам обращайтесь: {self.bot.config.support_contact}\n"
                f"⚠️ Не забудьте указать номер заявки."
            )
        elif status == 'completed':
            user_text = f"✅ Перевод средств по заявке #{request_id} вам выполнен успешно. 💸\n\n" \
                "🙏 Спасибо за использование нашего сервиса! 🤝\n\n" \
                "✅ Вы подтвердили получение."

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
                    f"[System] - Failed to send restoration message to user {user_id} for request #{request_id}: {e}")

        await self._send_admin_notification(request_id, is_restoration=True)

        if new_user_message_id:
            self.bot.db.update_request_data(request_id, {'user_message_id': new_user_message_id})

    async def confirming_exchange_trx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = query.from_user
        if query.data == 'send_transfer_trx':
            logger.info(f"[Uid] ({user.id}, {user.username}) - Confirmed the TRX request.")
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
        user = update.effective_user
        trx_address = update.message.text.strip()
        if not trx_address:
            await update.message.reply_text("Пожалуйста, введите корректный адрес.")
            return self.ENTERING_TRX_ADDRESS

        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered TRX address.")
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
            f"💱 Сумма которую вы получите на карту с учетом вычета TRX: {final_amount} {context.user_data['currency']} → {final_sum_uah:.2f} UAH\n\n"
            f"⚡ Вам будет отправлено **15 USDT** в TRX.\n\n"
            f"🔗 TRX-адрес: {trx_address}\n\n👉 Нажмите 'Отправить' для подтверждения.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
        return self.FINAL_CONFIRMING_EXCHANGE_TRX

    async def final_confirming_exchange_trx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = query.from_user

        if query.data == 'send_exchange_with_trx':
            request_id = self.bot.db.create_exchange_request(user, context.user_data)
            if not request_id:
                await query.edit_message_text("❌ Произошла ошибка при создании заявки. Попробуйте снова.")
                return ConversationHandler.END

            logger.info(
                f"[Uid] ({user.id}, {user.username}) - Creating an exchange request with TRX (#{request_id}).")
            msg = await query.edit_message_text(
                f"🙏 Спасибо за заявку #{request_id}!\n\n"
                "🏦 Ожидайте сообщения об успешном переводе TRX ✅",
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
        user = query.from_user
        logger.info(
            f"[Uid] ({user.id}, {user.username}) - Confirmed the transfer for request #{request_id}, requesting hash.")
        context.user_data['request_id'] = request_id
        await query.edit_message_text(text="✍️ Пожалуйста, отправьте хэш вашей транзакции:")
        return self.ENTERING_HASH

    async def process_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        submitted_hash = update.message.text
        request_id = context.user_data.get('request_id')
        user = update.effective_user

        logger.info(
            f"[Uid] ({user.id}, {user.username}) - Provided hash for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await update.message.reply_text("Произошла ошибка сессии. Начните сначала: /start")
            return ConversationHandler.END

        self.bot.db.update_request_data(request_id, {'transaction_hash': submitted_hash})
        self.bot.db.update_request_status(request_id, 'awaiting confirmation')

        request_data = self.bot.db.get_request_by_id(request_id)

        base_admin_text, _ = self._prepare_admin_notification(request_data)
        final_admin_text = base_admin_text + \
            f"\n\n✅2️⃣ Пользователь подтвердил перевод {request_data['amount_currency']} {request_data['currency']}. \n\n 🔒 Hash: `{submitted_hash}`"

        admin_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Средства получены",
                                 callback_data=f"confirm_payment_{request_id}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{request_id}")
        ]])

        await self._update_admin_messages(request_id, final_admin_text, admin_keyboard)
        await update.message.reply_text("✅ Спасибо, ваш хэш получен и отправлен на проверку.")
        return ConversationHandler.END

    async def handle_transfer_confirmation_trx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        admin_user = query.from_user
        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Confirmed TRX transfer for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.answer("Заявка не найдена!", show_alert=True)
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я совершил(а) перевод",
                                  callback_data=f"user_confirms_sending_{request_id}")],
        ])
        msg = await context.bot.send_message(
            chat_id=request_data['user_id'],
            text=(f"✅ Перевод TRX выполнен для заявки #{request_id}.\n\n"
                  f"📥 Переведите {(request_data['amount_currency']):.2f} {request_data['currency']} на кошелек:\n"
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
        admin_user = query.from_user
        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Confirmed payment receipt for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            return

        msg = await context.bot.send_message(chat_id=request_data['user_id'], text=f"✅ Средства по заявке #{request_id} получены.\n\n⏳ Ожидайте перевода.")

        self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
        self.bot.db.update_request_status(request_id, 'payment received')

        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += f"\n\n✅ Hash:`{request_data['transaction_hash']}`"
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
        admin_user = query.from_user
        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Confirmed funds transfer to the client for request #{request_id}.")

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
        updated_text += f"\n\n✅ Hash: `{request_data['transaction_hash']}`"
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

    async def start_cancellation_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Starts the cancellation process by offering choices."""
        query = update.callback_query
        request_id = int(query.data.split('_')[-1])
        context.chat_data['request_id_for_cancellation'] = request_id

        keyboard = [
            [InlineKeyboardButton("✏️ Указать причину и отменить",
                      callback_data=f"ask_reason_{request_id}")],
            [InlineKeyboardButton("🚫 Отменить без причины",
                                callback_data=f"confirm_decline_no_reason_{request_id}")],
            [InlineKeyboardButton("⬅️ Назад", 
                                callback_data="cancel_decline_process")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.answer()
        await query.edit_message_text(f"Выберите действие для заявки #{request_id}:", reply_markup=reply_markup)

        return self.SELECTING_CANCELLATION_TYPE

    async def ask_for_reason_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Edits the message to ask for the cancellation reason."""
        query = update.callback_query
        request_id = context.chat_data.get('request_id_for_cancellation')
        await query.answer()
        await query.edit_message_text(f"📝 Введите причину отмены для заявки #{request_id}, которая будет отправлена пользователю:")
        return self.AWAITING_REASON_TEXT

    async def handle_decline_request_no_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Declines a request without a specified reason."""
        query = update.callback_query
        request_id = int(query.data.split('_')[-1])
        admin_user = query.from_user

        await query.answer()
        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Declined request #{request_id} without reason.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.edit_message_text(f"❌ Заявка #{request_id} больше не найдена.")
            return ConversationHandler.END

        # 1. Immediately edit the message to give the admin feedback.
        await query.edit_message_text(f"✅ Заявка #{request_id} успешно отменена. Обновляю информацию...")

        # 2. Notify the user
        support_contact = self.bot.config.support_contact
        try:
            msg = await context.bot.send_message(
                chat_id=request_data['user_id'],
                text=f"❌ Ваша заявка #{request_id} была отменена.\n\n📞 По вопросам обращайтесь: {support_contact}"
            )
            self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
        except Exception as e:
            logger.error(
                f"[System] - Failed to send cancellation message to user {request_data['user_id']}: {e}")

        # 3. Update DB status
        self.bot.db.update_request_status(request_id, 'declined')

        # 4. Prepare and send the final updated notification to all admins.
        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += f"\n\n📄 Прежний статус заявки: {self.translate_status(request_data['status'])}\n\n❌🚫 ЗАЯВКА ОТКЛОНЕНА (🛡️ админ @{admin_user.username or admin_user.id})"

        await self._update_admin_messages(request_id, updated_text, None)

        return ConversationHandler.END

    async def handle_cancellation_with_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handles the cancellation reason provided by the admin, notifies the user, and updates the status."""
        admin_user = update.effective_user
        reason = update.message.text
        request_id = context.chat_data.pop('request_id_for_cancellation', None)

        if not request_id:
            await update.message.reply_text("❌ Произошла ошибка сессии. Не удалось найти заявку для отмены.")
            return ConversationHandler.END

        await update.message.reply_text(f"Отменяю заявку #{request_id}...")
        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Cancelling request #{request_id} with reason: {reason}")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await update.message.reply_text(f"❌ Заявка #{request_id} не найдена.")
            return ConversationHandler.END

        # Send a message with the reason to the user
        support_contact = self.bot.config.support_contact
        user_message = (f"❌ Ваша заявка #{request_id} была отменена.\n\n"
                        f"📄 Причина: {reason}\n\n"
                        f"📞 По вопросам обращайтесь: {support_contact}")

        try:
            msg = await context.bot.send_message(
                chat_id=request_data['user_id'],
                text=user_message
            )
            self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
        except Exception as e:
            logger.error(
                f"[System] - Failed to send cancellation message to user {request_data['user_id']}: {e}")
            await update.message.reply_text(f"⚠️ Не удалось отправить сообщение пользователю {request_data['user_id']}. Проверьте, не заблокировал ли он бота.")

        # Update the request status in the database
        self.bot.db.update_request_status(request_id, 'declined')

        # Prepare and send the updated notification to all admins
        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += (f"\n\n📄 Прежний статус заявки: {self.translate_status(request_data['status'])}\n"
                         f"💬 Причина: {reason}\n\n"
                         f"❌🚫 ЗАЯВКА ОТКЛОНЕНА (🛡️ админ @{admin_user.username or admin_user.id})")

        await self._update_admin_messages(request_id, updated_text, None)
        await update.message.reply_text(f"✅ Заявка #{request_id} успешно отменена. Пользователь уведомлен.")

        return ConversationHandler.END

    async def _cancel_cancellation_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancels the decline process and restores the original application message."""
        query = update.callback_query
        await query.answer()
        admin_user = update.effective_user
        request_id = context.chat_data.pop('request_id_for_cancellation', None)

        if not request_id:
            await query.edit_message_text("❌ Произошла ошибка. Не удалось восстановить заявку. Пожалуйста, попробуйте снова.", reply_markup=None)
            logger.warning(
                f"[Aid] ({admin_user.id}) - _cancel_cancellation_flow called without a request_id in chat_data.")
            return ConversationHandler.END

        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Canceled the decline process for request #{request_id}. Restoring message.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.edit_message_text(f"❌ Заявка #{request_id} больше не найдена.", reply_markup=None)
            return ConversationHandler.END

        # Re-generate the original message content using the helper function.
        text, keyboard = self._generate_admin_message_content(request_data)

        try:
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error restoring admin message for request #{request_id}: {e}")
            await query.message.reply_text("Не удалось отредактировать сообщение. Действие отменено.")

        return ConversationHandler.END

    async def handle_by_user_transfer_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        user = query.from_user
        logger.info(
            f"[Uid] ({user.id}, {user.username}) - Confirmed receipt of funds for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.edit_message_text("⏳ Сессия истекла. \n🔄 Пожалуйста, начните заново. \n🚀 /start", reply_markup=None)
            return

        self.bot.db.update_request_status(request_id, 'completed')

        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += "\n\n✅🛑 Пользователь подтвердил получение средств. ЗАЯВКА ЗАВЕРШЕНА. 🛑✅"
        await self._update_admin_messages(request_id, updated_text, None)

        await query.edit_message_text(
            text=f"✅ Перевод средств по заявке #{request_id} вам выполнен успешно. 💸\n\n"
            "🙏 Спасибо за использование нашего сервиса! 🤝\n\n"
            "✅ Вы подтвердили получение.",
            reply_markup=None,
            parse_mode='Markdown'
        )

    async def cancel_request_by_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles the user's request to cancel an application."""
        query = update.callback_query
        await query.answer()
        request_id = int(query.data.split('_')[-1])
        user = query.from_user

        logger.info(
            f"[Uid] ({user.id}, {user.username}) - User initiated cancellation for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data or request_data['status'] in ['completed', 'declined']:
            await query.edit_message_text("❌ Эту заявку уже нельзя отменить.", reply_markup=None)
            return

        self.bot.db.update_request_status(request_id, 'declined')

        await query.edit_message_text(
            f"✅ Ваша заявка #{request_id} была успешно отменена.",
            reply_markup=None
        )

        admin_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id)
        )
        admin_text += f"\n\n❌🚫 ЗАЯВКА ОТМЕНЕНА ПОЛЬЗОВАТЕЛЕМ (@{user.username or user.id})"
        await self._update_admin_messages(request_id, admin_text, None)

    def _prepare_admin_notification(self, request_data):
        username_display = 'none'
        if request_data['username']:
            username_display = request_data['username'].replace('_', '\\_').replace(
                '*', '\\*').replace('`', '\\`').replace('[', '\\[')

        def sanitize_for_code_block(text):
            # Simple sanitization for Markdown code blocks.
            return str(text).replace('`', "'") if text else ""

        bank_name_safe = sanitize_for_code_block(request_data['bank_name'])
        fio_safe = sanitize_for_code_block(request_data['fio'])
        card_info_safe = sanitize_for_code_block(request_data['card_info'])
        card_number_safe = sanitize_for_code_block(request_data['card_number'])
        inn_safe = sanitize_for_code_block(request_data['inn'])
        trx_address_safe = sanitize_for_code_block(request_data['trx_address'])

        status_text = self.translate_status(request_data['status'])
        title = f"📥 Заявка #{request_data['id']} (Статус: {status_text})"

        user_info_block = (f"👤 Пользователь:\n"
                           f"🆔 ID: `{request_data['user_id']}`\n"
                           f"📛 Юзернейм: @{username_display}\n\n")

        transfer_details_block = (f"🏦 Банк: `{bank_name_safe}`\n"
                                  f"📝 ФИО: `{fio_safe}`\n"
                                  f"💳 IBAN: `{card_info_safe}`\n"
                                  f"🔢 Номер карты: `{card_number_safe}`\n"
                                  f"📇 ИНН: `{inn_safe}`\n\n")

        base_text = (f"{title}\n\n"
                     f"💱 {request_data['amount_currency']} {request_data['currency']} → {request_data['amount_uah']:.2f} UAH\n\n"
                     f"{user_info_block}{transfer_details_block}")

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

    def _generate_admin_message_content(self, request_data):
        """Generates the text and keyboard for an admin notification based on request status."""
        text, keyboard = self._prepare_admin_notification(request_data)
        status = request_data['status']
        request_id = request_data['id']
        tx_hash = request_data["transaction_hash"] or "не указан"

        if status == 'awaiting confirmation':
            text += f"\n\n✅2️⃣ Пользователь подтвердил перевод. Hash: `{tx_hash}`"
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Средства получены",
                                     callback_data=f"confirm_payment_{request_id}"),
                InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{request_id}")
            ]])

        elif status == 'payment received':
            text += f"\n\n✅ Hash: `{tx_hash}`"
            text += f"\n\n✅3️⃣ Уведомление о получении средств отправлено."
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Перевод клиенту сделан",
                                     callback_data=f"confirm_transfer_{request_id}"),
                InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{request_id}")
            ]])
        elif status == 'funds sent':
            text += f"\n\n✅ Hash: `{tx_hash}`"
            text += "\n\n✅4️⃣ Уведомление об отправке средств клиенту отправлено."
            keyboard = None
        elif status == 'completed':
            text += f"\n\n✅ Hash: `{tx_hash}`"
            text += "\n\n✅🛑 Пользователь подтвердил получение средств. ЗАЯВКА ЗАВЕРШЕНА. 🛑✅"
            keyboard = None
        elif status == 'declined':
            text += f"\n\n❌ ЗАЯВКА ОТКЛОНЕНА"
            keyboard = None

        return text, keyboard

    async def _send_admin_notification(self, request_id, is_restoration=False):
        admin_ids = self.bot.config.admin_ids
        if not admin_ids:
            return

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            return

        text, keyboard = self._generate_admin_message_content(request_data)
        admin_message_ids = {}

        for admin_id in admin_ids:
            try:
                msg = await self.bot.application.bot.send_message(
                    chat_id=admin_id, text=text, parse_mode='Markdown', reply_markup=keyboard
                )
                admin_message_ids[admin_id] = msg.message_id
            except Exception as e:
                logger.error(f"[System] - Failed to send message to admin {admin_id}: {e}")

        self.bot.db.update_request_data(
            request_id, {'admin_message_ids': json.dumps(admin_message_ids)})

    async def _update_admin_messages(self, request_id: int, text: str, reply_markup: InlineKeyboardMarkup):
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            logger.warning(
                f"[System] - _update_admin_messages was called for a non-existent request #{request_id}")
            return

        if request_data['admin_message_ids']:
            try:
                old_admin_message_ids = json.loads(request_data['admin_message_ids'])
                for admin_id, message_id in old_admin_message_ids.items():
                    try:
                        await self.bot.application.bot.delete_message(chat_id=admin_id, message_id=message_id)
                    except Exception as e:
                        logger.warning(
                            f"[System] - Failed to delete old message {message_id} for admin {admin_id}: {e}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(
                    f"[System] - Failed to parse or process admin_message_ids for request #{request_id}: {e}")

        admin_ids = self.bot.config.admin_ids
        new_admin_message_ids = {}
        if not admin_ids:
            logger.warning(
                "[System] - Admin IDs are not configured, cannot send/update admin messages.")
            self.bot.db.update_request_data(request_id, {'admin_message_ids': json.dumps({})})
            return

        for admin_id in admin_ids:
            try:
                msg = await self.bot.application.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                new_admin_message_ids[admin_id] = msg.message_id
            except Exception as e:
                logger.error(
                    f"[System] - Failed to send updated message to admin {admin_id} for request #{request_id}: {e}")

        self.bot.db.update_request_data(
            request_id, {'admin_message_ids': json.dumps(new_admin_message_ids)}
        )

    def setup_handlers(self, application):
        exchange_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.handle_menu_callback, pattern='^(exchange|rate|user_help|back_to_menu)$')],
            states={
                self.CHOOSING_CURRENCY: [CallbackQueryHandler(self.choosing_currency, pattern='^(currency_usdt|back_to_menu)$')],
                self.ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_amount)],
                self.ENTERING_BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_bank_name)],
                self.ENTERING_CARD_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_card_details)],
                self.ENTERING_CARD_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_card_number)],
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

        cancellation_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.start_cancellation_flow, pattern=r'^decline_request_\d+')],
            states={
                self.SELECTING_CANCELLATION_TYPE: [
                    CallbackQueryHandler(self.ask_for_reason_text, pattern=r'^ask_reason_'),
                    CallbackQueryHandler(self.handle_decline_request_no_reason,
                                         pattern=r'^confirm_decline_no_reason_'),
                ],
                self.AWAITING_REASON_TEXT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   self.handle_cancellation_with_reason)
                ],
            },
            fallbacks=[CallbackQueryHandler(
                self._cancel_cancellation_flow, pattern='^cancel_decline_process$')],
            conversation_timeout=300
        )

        application.add_handler(exchange_conv_handler)
        application.add_handler(hash_conv_handler)
        application.add_handler(cancellation_conv_handler)

        application.add_handler(CallbackQueryHandler(
            self.handle_payment_confirmation, pattern=r'^confirm_payment_\d+'))
        application.add_handler(CallbackQueryHandler(
            self.handle_transfer_confirmation, pattern=r'^confirm_transfer_\d+'))
        application.add_handler(CallbackQueryHandler(
            self.handle_transfer_confirmation_trx, pattern=r'^confirm_trx_transfer_\d+'))
        application.add_handler(CallbackQueryHandler(
            self.handle_by_user_transfer_confirmation, pattern=r'^by_user_confirm_transfer_\d+'))
        application.add_handler(CallbackQueryHandler(
            self.cancel_request_by_user, pattern=r'^cancel_by_user_\d+'))

        application.add_handler(CommandHandler('start', self.start_command))
