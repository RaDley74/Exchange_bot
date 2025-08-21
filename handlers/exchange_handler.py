import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
)
from telegram.error import TelegramError


logger = logging.getLogger(__name__)


class ExchangeHandler:
    """
    Handles all logic related to the currency exchange process.
    """
    (
        CHOOSING_CURRENCY, ENTERING_AMOUNT, ASK_USE_PROFILE_REQUISITES, ENTERING_BANK_NAME, ENTERING_CARD_DETAILS,
        ENTERING_CARD_NUMBER, ENTERING_FIO_DETAILS, ENTERING_INN_DETAILS, CONFIRMING_EXCHANGE,
        CONFIRMING_EXCHANGE_TRX, ENTERING_TRX_ADDRESS, FINAL_CONFIRMING_EXCHANGE_TRX,
        ENTERING_HASH, SELECTING_CANCELLATION_TYPE, AWAITING_REASON_TEXT,
        ASK_USE_REFERRAL_BALANCE, ASK_PAY_TRX_FROM_REFERRAL, AWAITING_REVIEW_TEXT
    ) = range(18)

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sends or edits a message to show the main menu."""
        user = update.effective_user
        profile_data = self.bot.db.get_user_profile(user.id)
        vip_status = profile_data.get('vip_status') if profile_data else None

        # Format VIP status
        vip_status_text = ""
        if vip_status == 'Gold':
            vip_status_text = "\n\n👑 **Ваш статус:** 💎 Gold"
        elif vip_status == 'Silver':
            vip_status_text = "\n\n👑 **Ваш статус:** ⚪️ Silver"

        keyboard = [
            [
                InlineKeyboardButton("➸ Обменять", callback_data='exchange'),
                InlineKeyboardButton("📉 Курс", callback_data='rate'),
                InlineKeyboardButton("📝 Отзывы", url=self.bot.config.review_channel_url)
            ],
            [
                InlineKeyboardButton("🔐 Личный кабинет", callback_data='user_cabinet'),
                InlineKeyboardButton("🛠 Помощь", callback_data='user_help'),
            ],
            [
                InlineKeyboardButton("🏆 Реферальная программа", callback_data='referral_program')
            ]
        ]
        text = (
            "👋 **Привет!**\n"
            f"Добро пожаловать в **SafePay Bot** 🤝{vip_status_text}\n\n"
            "⚡ _Обмен — быстро, удобно и безопасно_ 🔒\n\n"
            "📂 **Выбери раздел ниже** ⬇️"
        )

        query = update.callback_query
        if query:
            await query.answer()
            if query.message:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        elif update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, called_from_referral: bool = False):
        """
        Handles the /start command. Ensures a user profile exists
        and then shows the main menu or active request status.
        """
        user = update.effective_user

        if context.args and context.args[0].startswith('ref_') and not called_from_referral:
            return await self.bot.referral_handler.handle_referral_start(update, context)

        logger.info(f"[Uid] ({user.id}, {user.username}) - Executed /start command.")

        self.bot.db.create_or_update_user_profile(user.id, {'username': user.username})

        if not self.bot.config.bot_enabled:
            await update.message.reply_text("🔧🤖 Бот на техническом обслуживании. \n\n⏳ Пожалуйста, попробуйте позже.")
            return

        check_request = self.check_if_request_exists(user)
        if check_request:
            logger.info(
                f"[Uid] ({user.id}, {user.username}) - Already has an active request ({check_request['id']}).")
            await update.message.reply_text(f"🚫 У вас уже есть активная заявка #{check_request['id']} в статусе: {self.translate_status(check_request['status'])}. \n\n 🛠️Если столкнулись с проблемой, напишите: {self.bot.config.support_contact}")
            return

        await self.main_menu(update, context)

    def check_if_request_exists(self, user):
        """Checks if a user has an active request."""
        check_request = self.bot.db.get_request_by_user_id(user.id)
        return check_request if check_request is not None else None

    async def cancel_and_return_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Universal function to end any conversation. The /start command handler
        in a lower group will then display the main menu.
        """
        user = update.effective_user
        logger.info(
            f"[Uid] ({user.id}, {user.username}) - Canceled or finished a conversation. Returning ConversationHandler.END to let global /start handler take over.")

        if update.message:
            try:
                await update.message.delete()
            except TelegramError as e:
                logger.warning(
                    f"Could not delete message {update.message.message_id} from chat {update.effective_chat.id}: {e}")

        return ConversationHandler.END

    async def start_exchange_convo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Entry point ONLY for the exchange conversation.
        """
        query = update.callback_query
        await query.answer()
        user = query.from_user
        logger.info(f"[Uid] ({user.id}, {user.username}) - Started exchange conversation.")

        context.user_data.clear()
        keyboard = [
            [InlineKeyboardButton("USDT", callback_data='currency_usdt')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
        ]
        await query.edit_message_text("💱 Выберите валюту для обмена:", reply_markup=InlineKeyboardMarkup(keyboard))
        return self.CHOOSING_CURRENCY

    async def show_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """A simple (non-conversation) handler to show the rate."""
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]
        await query.edit_message_text(f"📉 Актуальный курс: 1 USDT = {self.bot.config.exchange_rate} UAH", reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """A simple (non-conversation) handler to show help info."""
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]
        await query.edit_message_text(
            f"🔧 Помощь: Напиши {self.bot.config.support_contact} по любым вопросам относительно бота.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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

        current_rate = self.bot.config.exchange_rate
        context.user_data['exchange_rate'] = current_rate
        context.user_data['amount'] = amount
        sum_uah = amount * current_rate
        context.user_data['sum_uah'] = sum_uah
        context.user_data['original_sum_uah'] = sum_uah
        logger.info(
            f"[Uid] ({user.id}, {user.username}) - Entered amount: {amount} {context.user_data['currency']}. Calculated sum: {sum_uah:.2f} UAH.")

        profile_data = self.bot.db.get_user_profile(user.id)
        referral_balance = profile_data.get('referral_balance', 0.0) if profile_data else 0.0

        if referral_balance >= self.bot.config.min_referral_payout:
            context.user_data['referral_balance'] = referral_balance
            keyboard = [
                [InlineKeyboardButton("✅ Да, добавить к обмену", callback_data='ref_payout_yes')],
                [InlineKeyboardButton("❌ Нет, оставить на балансе", callback_data='ref_payout_no')]
            ]
            await update.message.reply_text(
                f"💰 На вашем реферальном балансе есть ${referral_balance:.2f}.\n\n"
                "Хотите добавить эти средства к текущему обмену?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return self.ASK_USE_REFERRAL_BALANCE
        else:
            return await self._proceed_to_requisites(update, context, is_callback=False)

    async def ask_use_referral_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        ud = context.user_data

        if query.data == 'ref_payout_yes':
            referral_balance_usd = ud.get('referral_balance', 0.0)
            rate = ud.get('exchange_rate')
            referral_payout_uah = referral_balance_usd * rate

            ud['total_referral_debit'] = referral_balance_usd
            ud['sum_uah'] += referral_payout_uah

            user = update.effective_user
            logger.info(
                f"[Uid] ({user.id}, {user.username}) - User chose to use referral balance of ${referral_balance_usd:.2f}.")

        return await self._proceed_to_requisites(update, context, is_callback=True)

    async def _proceed_to_requisites(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool) -> int:
        user = update.effective_user
        profile_data = self.bot.db.get_user_profile(user.id)
        has_profile = profile_data and any(profile_data.get(key)
                                           for key in ['bank_name', 'fio', 'card_number', 'inn'])

        ud = context.user_data
        message_text = f"✅ Хорошо! К оплате: {ud['sum_uah']:.2f} UAH.\n\n"

        if ud.get('total_referral_debit', 0.0) > 0:
            message_text = (
                f"✅ Отлично! Ваш реферальный баланс будет добавлен к выплате.\n\n"
                f"💰 Итого к получению: **{ud['sum_uah']:.2f} UAH**.\n\n"
            )

        if has_profile:
            keyboard = [
                [InlineKeyboardButton("✅ Да, использовать сохраненные",
                                      callback_data='profile_yes')],
                [InlineKeyboardButton("📝 Нет, ввести новые", callback_data='profile_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message_text += "У вас есть сохраненные реквизиты. Использовать их для этого обмена?"

            if is_callback:
                await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
            return self.ASK_USE_PROFILE_REQUISITES
        else:
            message_text += "🏦 Пожалуйста, укажите название банка."
            if is_callback:
                await update.callback_query.edit_message_text(message_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(message_text, parse_mode='Markdown')

            return self.ENTERING_BANK_NAME

    async def ask_use_profile_requisites(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handles the user's choice to use saved requisites or not."""
        query = update.callback_query
        await query.answer()
        user = query.from_user

        if query.data == 'profile_yes':
            profile_data = self.bot.db.get_user_profile(user.id)
            context.user_data.update(profile_data)
            logger.info(
                f"[Uid] ({user.id}, {user.username}) - Chose to use saved profile requisites.")
            return await self._show_final_confirmation(update, context, is_callback=True)

        elif query.data == 'profile_no':
            logger.info(f"[Uid] ({user.id}, {user.username}) - Chose to enter new requisites.")
            await query.edit_message_text("🏦 Пожалуйста, укажите название вашего банка:")
            return self.ENTERING_BANK_NAME

    async def entering_bank_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        bank_name = update.message.text.strip()
        if not bank_name:
            await update.message.reply_text("Пожалуйста, введите корректное название банка.")
            return self.ENTERING_BANK_NAME

        context.user_data['bank_name'] = bank_name
        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered bank: {bank_name}")
        await update.message.reply_text(f"🏦 Вы указали банк: {bank_name}\n\n💳 Введите IBAN:")
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
        return await self._show_final_confirmation(update, context)

    async def _show_final_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False):
        """Displays the final confirmation message with all details."""
        ud = context.user_data

        main_exchange_text = f"💰 Обмен {ud['amount']} {ud['currency']} на {ud['original_sum_uah']:.2f} UAH."

        referral_text = ""
        if ud.get('total_referral_debit', 0.0) > 0:
            referral_payout_uah = ud['sum_uah'] - ud['original_sum_uah']
            referral_text = f"\n🏆 Реферальный бонус: +{referral_payout_uah:.2f} UAH (списано ${ud['total_referral_debit']:.2f})."

        total_text = f"\n\n💸 **Итого к получению: {ud['sum_uah']:.2f} UAH**"

        details_text = (
            f"\n\n🏦 Банк: `{ud.get('bank_name', 'Не указан')}`\n"
            f"👤 ФИО: `{ud.get('fio', 'Не указано')}`\n"
            f"💳 IBAN: `{ud.get('card_info', 'Не указан')}`\n"
            f"🔢 Номер карты: `{ud.get('card_number', 'Не указан')}`\n"
            f"🆔 ІПН/ЄДРПОУ: `{ud.get('inn', 'Не указано')}`\n\n"
        )

        text = main_exchange_text + referral_text + total_text + details_text + \
            "👉 Нажмите 'Отправить' для подтверждения или 'Получить TRX', если вам нужен TRX для комиссии."

        keyboard = [
            [InlineKeyboardButton("✅ Отправить", callback_data='send_exchange')],
            [InlineKeyboardButton("🚀 Получить TRX", callback_data='send_exchange_trx')],
            [InlineKeyboardButton("❌ Отмена", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if is_callback:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

        return self.CONFIRMING_EXCHANGE

    async def confirming_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        ud = context.user_data

        if data == 'send_exchange':
            ud.pop('trx_address', None)
            request_id = self.bot.db.create_exchange_request(query.from_user, ud)
            if not request_id:
                await query.edit_message_text("❌ Произошла ошибка при создании заявки. Попробуйте снова.")
                return ConversationHandler.END

            await self._process_standard_exchange(query, context, request_id)
            return ConversationHandler.END

        elif data == 'send_exchange_trx':
            trx_cost_usd = self.bot.config.trx_cost_usdt
            referral_balance = ud.get('referral_balance', 0.0)

            if referral_balance >= trx_cost_usd:
                keyboard = [
                    [InlineKeyboardButton(f"✅ Да, оплатить с баланса",
                                          callback_data='trx_from_ref_yes')],
                    [InlineKeyboardButton(f"❌ Нет, вычесть из обмена",
                                          callback_data='trx_from_ref_no')]
                ]
                await query.edit_message_text(
                    f"🚀 Вы можете оплатить комиссию за TRX (${trx_cost_usd}) из вашего реферального баланса (${referral_balance:.2f}).\n\n"
                    "Хотите это сделать?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return self.ASK_PAY_TRX_FROM_REFERRAL
            else:
                keyboard = [
                    [InlineKeyboardButton("✅ Согласен", callback_data='send_transfer_trx')],
                    [InlineKeyboardButton("❌ Не согласен", callback_data='back_to_menu')]
                ]
                await query.edit_message_text(
                    f"⚡ Вам будет предоставлено **{trx_cost_usd} USDT** в TRX для оплаты комиссии, которые будут вычтены из общей суммы обмена.\n\n"
                    "💡 Эти средства позволят безопасно завершить транзакцию.",
                    reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
                )
                return self.CONFIRMING_EXCHANGE_TRX

        elif data == 'back_to_menu':
            await self.main_menu(update, context)
            return ConversationHandler.END
        return ConversationHandler.END

    async def ask_pay_trx_from_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        ud = context.user_data

        if query.data == 'trx_from_ref_yes':
            ud['trx_paid_by_referral'] = True
            logger.info(
                f"[Uid] ({update.effective_user.id}) - User chose to pay TRX fee from referral balance.")
        else:
            ud['trx_paid_by_referral'] = False
            logger.info(
                f"[Uid] ({update.effective_user.id}) - User chose to pay TRX fee from exchange amount.")

        await query.edit_message_text(
            "✅ Ваш выбор учтен.\n\n📬 Пожалуйста, укажите ваш TRX-кошелек:",
            parse_mode='Markdown'
        )
        return self.ENTERING_TRX_ADDRESS

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
        user_text, user_keyboard, new_user_message_id = None, None, None

        if status == 'awaiting trx transfer':
            user_text = f"🙏 Спасибо за заявку #{request_id}!\n\n" \
                "🏦 Ожидайте сообщения об успешном переводе TRX ✅"
        elif status == 'awaiting payment':
            amount_display = request_data['amount_currency']
            message_intro = f"🙏 Спасибо за заявку #{request_id}!\n\n"
            if request_data.get('needs_trx'):
                message_intro = f"✅ Перевод TRX выполнен для заявки #{request_id}.\n\n"

            user_text = message_intro + \
                f"📥 Переведите {amount_display:.2f} {request_data['currency']} на кошелек:\n" \
                f"`{self.bot.config.wallet_address}`\n\n" \
                "После перевода нажмите кнопку ниже для предоставления хэша."
            user_keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("✅ Я совершил(а) перевод",
                                          callback_data=f"user_confirms_sending_{request_id}")],
                    [InlineKeyboardButton("❌ Отменить заявку",
                                          callback_data=f"cancel_by_user_{request_id}")]
                ])
        elif status == 'awaiting confirmation':
            user_text = "✅ Спасибо, ваш хэш получен и отправлен на проверку."
        elif status == 'payment received':
            user_text = f"✅ Средства по заявке #{request_id} получены."
        elif status == 'funds sent':
            user_text = f"⏳ В течение часа средства по заявке #{request_id} будут зачислены на указанные вами реквизиты.\n\n" \
                "⚠️ Пожалуйста, не подтверждайте получение, пока средства фактически не поступят.\n\n" \
                "❗️ В случае, если подтверждение будет отправлено до получения средств, организация не несёт ответственности за возможные последствия."
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
                "✅ Вы подтвердили получение."\
                "\n\n💬 Оставив свой отзыв вы получите $1 на реферальный счет."
            user_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Оставить отзыв",
                                      callback_data=f"leave_review_{request_id}")]
            ])

        if user_text:
            try:
                msg = await self.bot.application.bot.send_message(
                    chat_id=user_id, text=user_text, reply_markup=user_keyboard, parse_mode='Markdown'
                )
                new_user_message_id = msg.message_id
            except Exception as e:
                logger.error(
                    f"[System] - Failed to send restoration message to user {user_id} for request #{request_id}: {e}")

        await self._send_admin_notification(request_id, is_restoration=True)

        if new_user_message_id:
            self.bot.db.update_request_data(request_id, {'user_message_id': new_user_message_id})

    # --- НОВЫЙ МЕТОД ---
    async def regenerate_admin_message(self, request_id: int):
        """
        Regenerates and sends a fresh admin notification message for a given request,
        reflecting its current state.
        """
        logger.info(f"[System] - Regenerating admin message for request #{request_id}.")
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            logger.warning(
                f"[System] - Could not regenerate admin message: Request #{request_id} not found.")
            return

        text, keyboard = self._generate_admin_message_content(request_data)
        await self._update_admin_messages(request_id, text, keyboard)
        logger.info(
            f"[System] - Successfully regenerated admin message for request #{request_id}.")
    # --- КОНЕЦ НОВОГО МЕТОДА ---

    async def confirming_exchange_trx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = query.from_user
        if query.data == 'send_transfer_trx':
            logger.info(
                f"[Uid] ({user.id}, {user.username}) - Confirmed the TRX request (standard flow).")
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
        ud = context.user_data
        trx_cost_usd = self.bot.config.trx_cost_usdt
        rate = ud['exchange_rate']
        info_text_lines = []

        payout_from_ref_usd = ud.get('total_referral_debit', 0.0)

        final_amount_to_send_usdt = ud.get('amount')
        final_sum_uah = ud['original_sum_uah']
        final_total_referral_debit = 0.0

        if ud.get('trx_paid_by_referral'):
            final_total_referral_debit = payout_from_ref_usd

            if payout_from_ref_usd > 0:
                payout_after_trx_usd = payout_from_ref_usd - trx_cost_usd
                final_sum_uah += payout_after_trx_usd * rate
                info_text_lines.append(
                    f"💰 Обмен: {final_amount_to_send_usdt:.2f} {ud['currency']} → {ud['original_sum_uah']:.2f} UAH")
                info_text_lines.append(
                    f"🏆 Реф. бонус (за вычетом TRX): +{payout_after_trx_usd * rate:.2f} UAH")
            else:
                final_total_referral_debit = trx_cost_usd
                info_text_lines.append(
                    f"💰 Обмен: {final_amount_to_send_usdt:.2f} {ud['currency']} → {final_sum_uah:.2f} UAH")

            info_text_lines.append(
                f"⚡ Комиссия TRX (${trx_cost_usd}) **оплачена с реферального баланса**.")

        else:
            final_amount_to_send_usdt -= trx_cost_usd
            final_sum_uah = final_amount_to_send_usdt * rate

            if payout_from_ref_usd > 0:
                final_sum_uah += payout_from_ref_usd * rate
                info_text_lines.append(f"🏆 Реф. бонус: +{payout_from_ref_usd * rate:.2f} UAH")

            final_total_referral_debit = payout_from_ref_usd
            info_text_lines.insert(
                0, f"💰 Обмен (сумма к отправке): {final_amount_to_send_usdt:.2f} {ud['currency']}")
            info_text_lines.append(f"⚡ Вычет за TRX из суммы обмена: -${trx_cost_usd}")

        ud['amount'] = final_amount_to_send_usdt
        ud['sum_uah'] = final_sum_uah
        ud['total_referral_debit'] = final_total_referral_debit

        info_text = "\n".join(info_text_lines)

        details_text = (
            f"\n\n**Ваши реквизиты для получения выплаты:**\n"
            f"🏦 Банк: `{ud.get('bank_name', 'Не указан')}`\n"
            f"👤 ФИО: `{ud.get('fio', 'Не указано')}`\n"
            f"💳 IBAN: `{ud.get('card_info', 'Не указан')}`\n"
            f"🔢 Номер карты: `{ud.get('card_number', 'Не указан')}`\n"
            f"🆔 ІПН/ЄДРПОУ: `{ud.get('inn', 'Не указан')}`"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Отправить", callback_data='send_exchange_with_trx')],
            [InlineKeyboardButton("❌ Отмена", callback_data='back_to_menu')]
        ]

        await update.message.reply_text(
            f"📋 **Проверьте информацию:**\n\n"
            f"{info_text}\n"
            f"💸 **Итого к получению: {final_sum_uah:.2f} UAH**"
            f"{details_text}\n\n"
            f"🔗 Ваш TRX-адрес для получения комиссии: `{trx_address}`\n\n"
            f"👉 Нажмите 'Отправить' для окончательного подтверждения.",
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
            f"\n\n✅2️⃣ Пользователь подтвердил перевод. \n\n 🔒 Hash: `{submitted_hash}`"

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
            f"[Aid] ({admin_user.id}) - Confirmed TRX transfer for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.answer("Заявка не найдена!", show_alert=True)
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я совершил(а) перевод",
                                  callback_data=f"user_confirms_sending_{request_id}")],
            [InlineKeyboardButton("❌ Отменить заявку",
                                  callback_data=f"cancel_by_user_{request_id}")]
        ])

        amount_to_send_usdt = request_data['amount_currency']

        msg = await context.bot.send_message(
            chat_id=request_data['user_id'],
            text=(f"✅ Перевод TRX выполнен для заявки #{request_id}.\n\n"
                  f"📥 Переведите {amount_to_send_usdt:.2f} {request_data['currency']} на кошелек:\n"
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
            f"[Aid] ({admin_user.id}) - Confirmed payment receipt for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            return

        msg = await context.bot.send_message(chat_id=request_data['user_id'], text=f"✅ Средства по заявке #{request_id} получены.")

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
            f"[Aid] ({admin_user.id}) - Confirmed funds transfer to the client for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подтвердить получение средств",
                                  callback_data=f"by_user_confirm_transfer_{request_id}")]
        ])
        msg = await context.bot.send_message(
            chat_id=request_data['user_id'],
            text=f"⏳ В течение часа средства по заявке #{request_id} будут зачислены на указанные вами реквизиты.\n\n"
            "⚠️ Пожалуйста, не подтверждайте получение, пока средства фактически не поступят.\n\n"
            "❗️ В случае, если подтверждение будет отправлено до получения средств, организация не несёт ответственности за возможные последствия.",
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
            'new': 'Новая', 'awaiting payment': 'Ожидание оплаты клиентом',
            'awaiting trx transfer': 'Ожидание перевода TRX клиенту', 'awaiting confirmation': 'Ожидание подтверждения перевода',
            'payment received': 'Платёж от клиента получен', 'funds sent': 'Средства клиенту отправлены',
            'declined': 'Отклонено', 'completed': 'Завершено'
        }
        return translations.get(status.lower(), status)

    async def start_cancellation_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        request_id = int(query.data.split('_')[-1])
        context.chat_data['request_id_for_cancellation'] = request_id

        keyboard = [
            [InlineKeyboardButton("✏️ Указать причину и отменить",
                                  callback_data=f"ask_reason_{request_id}")],
            [InlineKeyboardButton("🚫 Отменить без причины",
                                  callback_data=f"confirm_decline_no_reason_{request_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="cancel_decline_process")]
        ]
        await query.answer()
        await query.edit_message_text(f"Выберите действие для заявки #{request_id}:", reply_markup=InlineKeyboardMarkup(keyboard))
        return self.SELECTING_CANCELLATION_TYPE

    async def ask_for_reason_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        request_id = context.chat_data.get('request_id_for_cancellation')
        await query.answer()
        await query.edit_message_text(f"📝 Введите причину отмены для заявки #{request_id}, которая будет отправлена пользователю:")
        return self.AWAITING_REASON_TEXT

    async def handle_decline_request_no_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        request_id = int(query.data.split('_')[-1])
        admin_user = query.from_user
        await query.answer()
        logger.info(f"[Aid] ({admin_user.id}) - Declined request #{request_id} without reason.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.edit_message_text(f"❌ Заявка #{request_id} больше не найдена.")
            return ConversationHandler.END

        await self.refund_referral_debit_for_request(request_id)

        if request_data['user_message_id']:
            try:
                await context.bot.delete_message(chat_id=request_data['user_id'], message_id=request_data['user_message_id'])
                logger.info(
                    f"[System] - Deleted old status message for user {request_data['user_id']}")
            except TelegramError as e:
                logger.warning(
                    f"[System] - Failed to delete old user message during cancellation for request #{request_id}: {e}")

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

        self.bot.db.update_request_status(request_id, 'declined')

        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += f"\n\n📄 Прежний статус заявки: {self.translate_status(request_data['status'])}\n\n❌🚫 ЗАЯВКА ОТКЛОНЕНА (🛡️ админ @{admin_user.username or admin_user.id})"
        await self._update_admin_messages(request_id, updated_text, None)
        return ConversationHandler.END

    async def handle_cancellation_with_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        admin_user = update.effective_user
        reason = update.message.text
        request_id = context.chat_data.pop('request_id_for_cancellation', None)

        if not request_id:
            await update.message.reply_text("❌ Произошла ошибка сессии. Не удалось найти заявку для отмены.")
            return ConversationHandler.END

        logger.info(
            f"[Aid] ({admin_user.id}) - Cancelling request #{request_id} with reason: {reason}")

        await self.refund_referral_debit_for_request(request_id)

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await update.message.reply_text(f"❌ Заявка #{request_id} не найдена.")
            return ConversationHandler.END

        if request_data['user_message_id']:
            try:
                await context.bot.delete_message(chat_id=request_data['user_id'], message_id=request_data['user_message_id'])
                logger.info(
                    f"[System] - Deleted old status message for user {request_data['user_id']}")
            except TelegramError as e:
                logger.warning(
                    f"[System] - Failed to delete old user message during cancellation for request #{request_id}: {e}")

        support_contact = self.bot.config.support_contact
        user_message = (f"❌ Ваша заявка #{request_id} была отменена.\n\n"
                        f"📄 Причина: {reason}\n\n"
                        f"📞 По вопросам обращайтесь: {support_contact}")

        try:
            msg = await context.bot.send_message(chat_id=request_data['user_id'], text=user_message)
            self.bot.db.update_request_data(request_id, {'user_message_id': msg.message_id})
        except Exception as e:
            logger.error(
                f"[System] - Failed to send cancellation message to user {request_data['user_id']}: {e}")
            await update.message.reply_text(f"⚠️ Не удалось отправить сообщение пользователю {request_data['user_id']}.")

        self.bot.db.update_request_status(request_id, 'declined')

        updated_text, _ = self._prepare_admin_notification(
            self.bot.db.get_request_by_id(request_id))
        updated_text += (f"\n\n📄 Прежний статус заявки: {self.translate_status(request_data['status'])}\n"
                         f"💬 Причина: {reason}\n\n"
                         f"❌🚫 ЗАЯВКА ОТКЛОНЕНА (🛡️ админ @{admin_user.username or admin_user.id})")

        await self._update_admin_messages(request_id, updated_text, None)
        return ConversationHandler.END

    async def _cancel_cancellation_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        admin_user = update.effective_user
        request_id = context.chat_data.pop('request_id_for_cancellation', None)

        if not request_id:
            await query.edit_message_text("❌ Произошла ошибка. Не удалось восстановить заявку.", reply_markup=None)
            return ConversationHandler.END

        logger.info(
            f"[Aid] ({admin_user.id}) - Canceled decline process for request #{request_id}.")
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.edit_message_text(f"❌ Заявка #{request_id} больше не найдена.", reply_markup=None)
            return ConversationHandler.END

        text, keyboard = self._generate_admin_message_content(request_data)
        try:
            await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='Markdown')
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
            await query.edit_message_text("⏳ Сессия истекла. Начните заново: /start", reply_markup=None)
            return

        self.bot.db.update_request_status(request_id, 'completed')

        await self.bot.referral_handler.credit_referrer(user.id)
        updated_text, _ = self._generate_admin_message_content(
            self.bot.db.get_request_by_id(request_id))
        await self._update_admin_messages(request_id, updated_text, None)

        review_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Оставить отзыв", callback_data=f"leave_review_{request_id}")]
        ])

        await query.edit_message_text(
            text=f"✅ Перевод средств по заявке #{request_id} вам выполнен успешно. 💸\n\n"
            "🙏 Спасибо за использование нашего сервиса! 🤝\n\n"
            "✅ Вы подтвердили получение.\n\n"
            "💬 Оставив свой отзыв вы получите $1 на реферальный счет.\n",
            reply_markup=review_keyboard, parse_mode='Markdown'
        )

    async def refund_referral_debit_for_request(self, request_id: int):
        """
        Checks if a cancelled request used referral funds and refunds them.
        Sends a notification to the user about the refund.
        """
        logger.info(
            f"[System] - Checking for referral refund for cancelled request #{request_id}.")
        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            logger.warning(f"[System] - Refund check failed: Request #{request_id} not found.")
            return

        amount_to_refund = request_data.get('referral_payout_amount', 0.0)

        if amount_to_refund > 0:
            user_id = request_data['user_id']
            self.bot.db.update_referral_balance(user_id, amount_to_refund)
            logger.info(
                f"[System] - Refunded ${amount_to_refund:.2f} to user {user_id} for cancelled request #{request_id}.")

            try:
                await self.bot.application.bot.send_message(
                    chat_id=user_id,
                    text=f"💰 Средства в размере ${amount_to_refund:.2f} с вашего реферального баланса, которые были использованы в отмененной заявке #{request_id}, возвращены на ваш счет."
                )
            except Exception as e:
                logger.error(
                    f"[System] - Failed to send refund notification to user {user_id} for request #{request_id}: {e}")

    async def cancel_request_by_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        await self.refund_referral_debit_for_request(request_id)

        self.bot.db.update_request_status(request_id, 'declined')
        await query.edit_message_text(f"✅ Ваша заявка #{request_id} была успешно отменена.", reply_markup=None)

        admin_text, _ = self._prepare_admin_notification(self.bot.db.get_request_by_id(request_id))
        admin_text += f"\n\n❌🚫 ЗАЯВКА ОТМЕНЕНА ПОЛЬЗОВАТЕЛЕМ (@{user.username or user.id})"
        await self._update_admin_messages(request_id, admin_text, None)

    def _prepare_admin_notification(self, request_data):
        username_display = 'none'
        if request_data['username']:
            username_display = request_data['username'].replace('_', '\\_').replace(
                '*', '\\*').replace('`', '\\`').replace('[', '\\[')

        def sanitize(text): return str(text).replace('`', "'") if text else ""

        # Fetch user profile to get VIP status
        user_profile = self.bot.db.get_user_profile(request_data['user_id'])
        vip_status = user_profile.get('vip_status') if user_profile else None

        vip_status_text = ""
        if vip_status == 'Gold':
            vip_status_text = "👑 VIP-статус: 💎 Gold\n"
        elif vip_status == 'Silver':
            vip_status_text = "👑 VIP-статус: ⚪️ Silver\n"

        status_text = self.translate_status(request_data['status'])
        rate_info = f"(Курс: {request_data['exchange_rate']})" if request_data.get(
            'exchange_rate') else ""
        title = f"📥 Заявка #{request_data['id']} {rate_info} (Статус: {status_text})"

        user_info_block = (f"👤 Пользователь:\n"
                           f"🆔 ID: `{request_data['user_id']}`\n"
                           f"📛 Юзернейм: @{username_display}\n"
                           f"{vip_status_text}\n")

        transfer_details_block = (f"```Реквизиты:\n"
                                  f"🏦 Банк: {sanitize(request_data.get('bank_name'))}\n"
                                  f"📝 ФИО: {sanitize(request_data.get('fio'))}\n"
                                  f"💳 Номер карты: {sanitize(request_data.get('card_info'))}\n"
                                  f"🔢 IBAN: {sanitize(request_data.get('card_number'))}\n"
                                  f"📇 ИНН: {sanitize(request_data.get('inn'))}```\n\n")

        referral_payout = request_data.get('referral_payout_amount', 0.0)
        rate = request_data.get('exchange_rate')
        payout_info = f"💱 {request_data['amount_currency']} {request_data['currency']} → {request_data['amount_uah']:.2f} UAH\n\n"

        if referral_payout > 0:
            if rate and rate > 0:
                uah_for_exchange = request_data['amount_currency'] * rate
                usd_for_payout = request_data['amount_uah'] / rate
                payout_info = (
                    f"💱 Обмен: {request_data['amount_currency']} {request_data['currency']} → {uah_for_exchange:.2f} UAH\n"
                    f"🏆 Списано с реф. баланса: ${referral_payout:.2f}\n"
                    f"💸 **Итого к выплате: {request_data['amount_uah']:.2f} UAH → ${usd_for_payout:.2f}**\n\n"
                )
            else:  # Fallback
                payout_info = (
                    f"💱 Обмен: {request_data['amount_currency']} {request_data['currency']}\n"
                    f"🏆 Списано с реф. баланса: ${referral_payout:.2f}\n"
                    f"💸 **Итого к выплате: {request_data['amount_uah']:.2f} UAH**\n\n"
                )

        base_text = (f"{title}\n\n"
                     f"{payout_info}"
                     f"{user_info_block}{transfer_details_block}")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "❌ Отказать", callback_data=f"decline_request_{request_data['id']}")]
        ])

        if request_data.get('needs_trx'):
            trx_cost_usd = self.bot.config.trx_cost_usdt
            title = f"{title} (с TRX)"
            trx_info = f"⚠️ Клиент нуждается в TRX.\n📬 TRX-адрес: `{sanitize(request_data.get('trx_address'))}`"

            base_text = (f"{title}\n\n"
                         f"{payout_info}"
                         f"{user_info_block}{transfer_details_block}"
                         f"{trx_info}")

            if request_data['status'] == 'awaiting trx transfer':
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "✅ TRX переведено", callback_data=f"confirm_trx_transfer_{request_data['id']}")],
                    [InlineKeyboardButton(
                        "❌ Отказать", callback_data=f"decline_request_{request_data['id']}")]
                ])
        return base_text, keyboard

    def _generate_admin_message_content(self, request_data):
        text, keyboard = self._prepare_admin_notification(request_data)
        status, req_id = request_data['status'], request_data['id']
        tx_hash = request_data.get("transaction_hash") or "не указан"

        if status == 'awaiting confirmation':
            text += f"\n\n✅2️⃣ Пользователь подтвердил перевод. Hash: `{tx_hash}`"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Средства получены",
                                      callback_data=f"confirm_payment_{req_id}")],
                [InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{req_id}")]
            ])
        elif status == 'payment received':
            text += f"\n\n✅ Hash: `{tx_hash}`\n\n✅3️⃣ Уведомление о получении средств отправлено."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Перевод клиенту сделан",
                                      callback_data=f"confirm_transfer_{req_id}")],
                [InlineKeyboardButton("❌ Отказать", callback_data=f"decline_request_{req_id}")]
            ])
        elif status == 'funds sent':
            text += f"\n\n✅ Hash: `{tx_hash}`\n\n✅4️⃣ Уведомление об отправке средств клиенту отправлено."
            keyboard = None
        elif status == 'completed':
            text += f"\n\n✅ Hash: `{tx_hash}`\n\n✅🛑 Пользователь подтвердил получение средств. ЗАЯВКА ЗАВЕРШЕНА. 🛑✅"
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
                f"[System] - _update_admin_messages called for a non-existent request #{request_id}")
            return

        if request_data.get('admin_message_ids'):
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
                    f"[System] - Failed to parse admin_message_ids for request #{request_id}: {e}")

        admin_ids = self.bot.config.admin_ids
        new_admin_message_ids = {}
        if not admin_ids:
            logger.warning("[System] - Admin IDs are not configured.")
            self.bot.db.update_request_data(request_id, {'admin_message_ids': json.dumps({})})
            return

        for admin_id in admin_ids:
            try:
                msg = await self.bot.application.bot.send_message(
                    chat_id=admin_id, text=text, reply_markup=reply_markup, parse_mode='Markdown'
                )
                new_admin_message_ids[admin_id] = msg.message_id
            except Exception as e:
                logger.error(f"[System] - Failed to send updated message to admin {admin_id}: {e}")

        self.bot.db.update_request_data(
            request_id, {'admin_message_ids': json.dumps(new_admin_message_ids)})

    async def prompt_for_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Asks the user to enter their review text."""
        query = update.callback_query
        await query.answer()
        user = query.from_user
        logger.info(f"[Uid] ({user.id}, {user.username}) - Chose to leave a review.")
        context.user_data['username_for_review'] = user.username or f"ID: {user.id}"
        await query.edit_message_text("✍️ Пожалуйста, введите текст вашего отзыва:")
        return self.AWAITING_REVIEW_TEXT

    async def process_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Processes the review, sends it to the channel, and thanks the user."""
        user = update.effective_user
        review_text = update.message.text
        username = context.user_data.pop('username_for_review', user.username or f"ID: {user.id}")

        logger.info(f"[Uid] ({user.id}, {username}) - Submitted a review.")

        channel_id = self.bot.config.review_channel_id

        if channel_id:
            channel_message = (
                f"Пользователь: @{username}\n"
                f"Отзыв: {review_text}"
            )

            try:
                await context.bot.send_message(
                    chat_id=channel_id,
                    text=channel_message
                )
                logger.info(
                    f"Successfully sent review from user {username} to channel {channel_id}.")
            except Exception as e:
                logger.error(f"Failed to send review to channel {channel_id}: {e}")
                # Optionally notify admins that sending failed
                for admin_id in self.bot.config.admin_ids:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=f"⚠️ Не удалось отправить отзыв в канал.\n\n{channel_message}"
                        )
                    except Exception as admin_e:
                        logger.error(
                            f"Failed to even notify admin {admin_id} about the review failure: {admin_e}")
        else:
            logger.warning(
                "Review was submitted but REVIEW_CHANNEL_ID is not configured. The review was not sent.")
            # Notify admin that the channel ID is missing
            for admin_id in self.bot.config.admin_ids:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text="⚠️ Пользователь оставил отзыв, но ID канала для отзывов (REVIEW_CHANNEL_ID) не настроен в settings.ini."
                    )
                except Exception:
                    pass

        await update.message.reply_text("Спасибо за оставленный вами отзыв! 🙏\n\nВы получили $1 на реферальный счет 💵")
        self.bot.db.update_referral_balance(user.id, 1.0)  # Credit
        return ConversationHandler.END

    def setup_handlers(self, application):
        exchange_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_exchange_convo, pattern='^exchange$')],
            states={
                self.CHOOSING_CURRENCY: [CallbackQueryHandler(self.choosing_currency, pattern='^(currency_usdt|back_to_menu)$')],
                self.ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_amount)],
                self.ASK_USE_REFERRAL_BALANCE: [CallbackQueryHandler(self.ask_use_referral_balance, pattern='^ref_payout_(yes|no)$')],
                self.ASK_USE_PROFILE_REQUISITES: [CallbackQueryHandler(self.ask_use_profile_requisites, pattern='^profile_(yes|no)$')],
                self.ENTERING_BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_bank_name)],
                self.ENTERING_CARD_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_card_details)],
                self.ENTERING_CARD_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_card_number)],
                self.ENTERING_FIO_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_fio_details)],
                self.ENTERING_INN_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_inn_details)],
                self.CONFIRMING_EXCHANGE: [CallbackQueryHandler(self.confirming_exchange, pattern='^(send_exchange|send_exchange_trx|back_to_menu)$')],
                self.ASK_PAY_TRX_FROM_REFERRAL: [CallbackQueryHandler(self.ask_pay_trx_from_referral, pattern='^trx_from_ref_(yes|no)$')],
                self.CONFIRMING_EXCHANGE_TRX: [CallbackQueryHandler(self.confirming_exchange_trx, pattern='^(send_transfer_trx|back_to_menu)$')],
                self.ENTERING_TRX_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_trx_address)],
                self.FINAL_CONFIRMING_EXCHANGE_TRX: [CallbackQueryHandler(self.final_confirming_exchange_trx, pattern='^(send_exchange_with_trx|back_to_menu)$')],
            },
            fallbacks=[
                CommandHandler('start', self.cancel_and_return_to_menu),
                CallbackQueryHandler(self.main_menu, pattern='^back_to_menu$')
            ],
            per_message=False
        )

        hash_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.ask_for_hash, pattern=r'^user_confirms_sending_')],
            states={self.ENTERING_HASH: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, self.process_hash)]},
            fallbacks=[CommandHandler('start', self.cancel_and_return_to_menu)],
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
                self.AWAITING_REASON_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_cancellation_with_reason)],
            },
            fallbacks=[
                CommandHandler('start', self.cancel_and_return_to_menu),
                CallbackQueryHandler(self._cancel_cancellation_flow,
                                     pattern='^cancel_decline_process$')
            ],
            conversation_timeout=300
        )

        review_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.prompt_for_review, pattern=r'^leave_review_')],
            states={
                self.AWAITING_REVIEW_TEXT: [MessageHandler(
                    filters.TEXT & ~filters.COMMAND, self.process_review)]
            },
            fallbacks=[CommandHandler('start', self.cancel_and_return_to_menu)],
            conversation_timeout=300
        )

        application.add_handler(exchange_conv_handler)
        application.add_handler(hash_conv_handler)
        application.add_handler(cancellation_conv_handler)
        application.add_handler(review_conv_handler)

        application.add_handler(CallbackQueryHandler(self.show_rate, pattern='^rate$'))
        application.add_handler(CallbackQueryHandler(self.show_help, pattern='^user_help$'))
        application.add_handler(CallbackQueryHandler(self.main_menu, pattern='^back_to_menu$'))

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

        application.add_handler(CommandHandler('start', self.start_command), group=1)
