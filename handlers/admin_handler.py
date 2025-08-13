# handlers/admin_handler.py

import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
)
from telegram.error import TelegramError
import json
logger = logging.getLogger(__name__)


class AdminPanelHandler:
    """
    Handles all logic related to the admin panel.
    """
    # Conversation states
    (
        ASK_PASSWORD,
        ADMIN_MENU,
        SETTINGS_MENU,
        SET_NEW_PASSWORD,
        SET_EXCHANGE_RATE,
        SET_WALLET,
        SET_SUPPORT,
        AWAIT_USER_FOR_APPS,
        AWAIT_REQUEST_ID_FOR_RESTORE,
        AWAIT_REQUEST_ID_FOR_STATUS_CHANGE,
        SELECT_NEW_STATUS,
        # --- START OF CHANGE ---
        REFERRAL_MENU,
        AWAIT_USER_FOR_REF_ACTION,
        AWAIT_AMOUNT_FOR_REF_ACTION,
        AWAIT_USER_FOR_REF_CHECK
        # --- END OF CHANGE ---
    ) = range(15)

    # Ordered list of statuses defining the main workflow
    WORKFLOW_STATUSES = [
        'new',
        'awaiting trx transfer',
        'awaiting payment',
        'awaiting confirmation',
        'payment received',
        'funds sent',
        'completed'
    ]
    # Terminal statuses from which the state cannot be changed
    TERMINAL_STATUSES = ['completed', 'declined']

    def __init__(self, bot_instance):
        """
        The constructor receives the main Bot instance
        to access shared resources like configuration.
        """
        self.bot = bot_instance

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"[Uid] ({user.id}, {user.username}) - Trying to access the admin panel.")

        if not self.bot.config.admin_ids:
            await update.message.reply_text("❌ Бот не активирован. Нет ID администратора.")
            return ConversationHandler.END

        if user.id not in self.bot.config.admin_ids:
            await update.message.reply_text("🚫 У вас нет доступа к админ-панели.")
            return ConversationHandler.END

        await update.message.reply_text("Введите пароль для доступа к админ-панели:")
        return self.ASK_PASSWORD

    async def check_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        entered_password = update.message.text.strip()
        user = update.effective_user

        if entered_password == self.bot.config.admin_password:
            logger.info(f"[Aid] ({user.id}, {user.username}) - Entered the correct password.")
            return await self._show_main_menu(update, context)
        else:
            logger.warning(f"[Aid] ({user.id}, {user.username}) - Entered the wrong password.")
            await update.message.reply_text("❌ Неверный пароль. Попробуйте снова:")
            return self.ASK_PASSWORD

    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"[Aid] ({user.id}, {user.username}) - Displaying the admin panel main menu.")
        
        # Clear any previous conversation data
        context.user_data.clear()

        is_enabled = self.bot.config.bot_enabled
        toggle_button_text = "🔴 Выключить бота" if is_enabled else "🟢 Включить бота"
        toggle_button = InlineKeyboardButton(toggle_button_text, callback_data='toggle_bot_status')

        keyboard = [
            [
                InlineKeyboardButton("📊 Информация", callback_data='admin_info'),
                InlineKeyboardButton("⚙️ Настройки", callback_data='admin_settings'),
            ],
            [
                InlineKeyboardButton("🔍 Найти заявки", callback_data='find_user_applications'),
                InlineKeyboardButton("🔄 Восстановить", callback_data='restore_application'),
            ],
            [
                InlineKeyboardButton("🔧 Изменить статус", callback_data='change_status'),
                InlineKeyboardButton("🏆 Рефералка", callback_data='admin_referral_menu') # --- NEW BUTTON ---
            ],
            [toggle_button],
        ]
        text = "⚙️ Админ-панель"
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            except TelegramError as e:
                logger.warning(
                    f"[Aid] ({user.id}, {user.username}) - Failed to edit the menu message, sending a new one. Error: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=reply_markup
                )
        else:
            if update.message:
                await update.message.delete()
            await update.message.reply_text(text, reply_markup=reply_markup)

        return self.ADMIN_MENU

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        logger.info(f"[Aid] ({user.id}, {user.username}) - Selected option: {data}")

        if user.id not in self.bot.config.admin_ids:
            await query.message.reply_text("🚫 У вас нет доступа.")
            return ConversationHandler.END

        if data == 'admin_info':
            return await self._show_info(query)
        elif data == 'admin_settings':
            return await self._show_settings_menu(query)
        # --- START OF CHANGE ---
        elif data == 'admin_referral_menu':
            return await self._show_referral_menu(query)
        # --- END OF CHANGE ---
        elif data == 'admin_back_menu':
            return await self._show_main_menu(update, context)
        elif data == 'admin_set_password':
            await query.edit_message_text("🔐 Введите новый пароль:")
            return self.SET_NEW_PASSWORD
        elif data == 'admin_set_exchange_rate':
            await query.edit_message_text(f"💱 Введите новый курс (текущий: {self.bot.config.exchange_rate}):")
            return self.SET_EXCHANGE_RATE
        elif data == 'admin_set_wallet':
            await query.edit_message_text("💼 Введите новый адрес кошелька:")
            return self.SET_WALLET
        elif data == 'admin_set_support':
            await query.edit_message_text("📞 Введите новый контакт поддержки:")
            return self.SET_SUPPORT
        elif data == 'find_user_applications':
            await query.edit_message_text("Введите ID аккаунта или login телеграм для поиска активных заявок:")
            return self.AWAIT_USER_FOR_APPS
        elif data == 'restore_application':
            await query.edit_message_text("Введите ID заявки, которую нужно восстановить:")
            return self.AWAIT_REQUEST_ID_FOR_RESTORE
        elif data == 'change_status':
            await query.edit_message_text("Введите ID заявки для изменения статуса:")
            return self.AWAIT_REQUEST_ID_FOR_STATUS_CHANGE
        elif data == 'toggle_bot_status':
            return await self.toggle_bot_status(update, context)

        return self.ADMIN_MENU
        
    # --- START: NEW REFERRAL MANAGEMENT METHODS ---
    async def _show_referral_menu(self, query: Update.callback_query): # type: ignore
        """Displays the referral balance management menu."""
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data='ref_add_balance')],
            [InlineKeyboardButton("➖ Отнять", callback_data='ref_subtract_balance')],
            [InlineKeyboardButton("🔍 Проверить баланс", callback_data='ref_check_balance')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')]
        ]
        await query.edit_message_text("🏆 Управление реферальным балансом:", reply_markup=InlineKeyboardMarkup(keyboard))
        return self.REFERRAL_MENU

    async def _ask_for_user_to_modify(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Asks for a user ID/login to perform a balance action on."""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        context.user_data['ref_action'] = action # 'ref_add_balance' or 'ref_subtract_balance'
        
        action_text = "добавить средства" if action == 'ref_add_balance' else "списать средства"

        await query.edit_message_text(f"Введите ID или юзернейм пользователя, которому вы хотите {action_text}:")
        return self.AWAIT_USER_FOR_REF_ACTION

    async def _ask_for_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Finds the user and asks for the amount to add/subtract."""
        user_input = update.message.text.strip()
        admin_user = update.effective_user

        # Find the target user's profile
        target_profile = self.bot.db.get_profile_by_id_or_login(user_input)

        if not target_profile:
            await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова или вернитесь в меню /a.")
            return self.AWAIT_USER_FOR_REF_ACTION

        target_user_id = target_profile['user_id']
        target_username = target_profile.get('username', 'N/A')
        current_balance = target_profile.get('referral_balance', 0.0)

        context.user_data['target_user_id'] = target_user_id
        context.user_data['target_username'] = target_username

        action = context.user_data['ref_action']
        action_text = "добавить" if action == 'ref_add_balance' else "списать"

        await update.message.reply_text(
            f"✅ Пользователь @{target_username} (ID: `{target_user_id}`) найден.\n"
            f"💰 Текущий баланс: ${current_balance:.2f}\n\n"
            f"Введите сумму в USD для списания/добавления (например, 10.5):",
            parse_mode='Markdown'
        )
        return self.AWAIT_AMOUNT_FOR_REF_ACTION

    async def _process_balance_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Processes the balance change, updates DB, and notifies parties."""
        admin_user = update.effective_user
        try:
            amount_str = update.message.text.strip().replace(',', '.')
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Введите корректное положительное число. Попробуйте снова.")
            return self.AWAIT_AMOUNT_FOR_REF_ACTION

        target_user_id = context.user_data['target_user_id']
        target_username = context.user_data['target_username']
        action = context.user_data['ref_action']
        
        # Make amount negative for subtraction
        if action == 'ref_subtract_balance':
            amount *= -1
            
        # Update balance in DB
        self.bot.db.update_referral_balance(target_user_id, amount)
        
        # Get new balance for confirmation message
        new_profile = self.bot.db.get_user_profile(target_user_id)
        new_balance = new_profile.get('referral_balance', 0.0)
        
        action_text = "Добавлено" if amount > 0 else "Списано"
        
        # Notify admin
        logger.info(f"[Aid] ({admin_user.id}) manually changed ref balance for user {target_user_id} by {amount}. New balance: {new_balance}")
        await update.message.reply_text(
            f"✅ Успешно!\n\n"
            f"👤 Пользователь: @{target_username}\n"
            f"⚙️ Действие: {action_text} ${abs(amount):.2f}\n"
            f"💰 Новый баланс: ${new_balance:.2f}"
        )

        # Notify user
        try:
            await self.bot.application.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"🔔 Уведомление об изменении баланса!\n\n"
                    f"🛡️ Администратор изменил ваш реферальный баланс.\n"
                    f"⚙️ Действие: **{action_text} ${abs(amount):.2f}**\n"
                    f"💰 Ваш новый реферальный баланс: **${new_balance:.2f}**"
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send balance change notification to user {target_user_id}: {e}")
            await update.message.reply_text(f"⚠️ Не удалось отправить уведомление пользователю @{target_username}.")

        return await self._show_main_menu(update, context)

    async def _ask_for_user_to_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Asks for a user ID/login to check their balance."""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Введите ID или юзернейм пользователя для проверки баланса:")
        return self.AWAIT_USER_FOR_REF_CHECK

    async def _check_user_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Finds the user and shows their balance to the admin."""
        user_input = update.message.text.strip()
        
        target_profile = self.bot.db.get_profile_by_id_or_login(user_input)
        
        if not target_profile:
            await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова или вернитесь в меню /a.")
            return self.AWAIT_USER_FOR_REF_CHECK
            
        target_user_id = target_profile['user_id']
        target_username = target_profile.get('username', 'N/A')
        current_balance = target_profile.get('referral_balance', 0.0)

        await update.message.reply_text(
            f"✅ Пользователь @{target_username} (ID: `{target_user_id}`)\n"
            f"💰 Реферальный баланс: **${current_balance:.2f}**",
            parse_mode='Markdown'
        )
        return await self._show_main_menu(update, context)

    # --- END: NEW REFERRAL MANAGEMENT METHODS ---

    async def show_status_selection_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_user = update.effective_user
        try:
            request_id = int(update.message.text.strip())
        except (ValueError, TypeError):
            await update.message.reply_text("❌ ID заявки должен быть числом. Попробуйте снова.")
            return self.AWAIT_REQUEST_ID_FOR_STATUS_CHANGE

        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Wants to change status for request #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await update.message.reply_text(f"❌ Заявка с ID #{request_id} не найдена.")
            return await self._show_main_menu(update, context)

        current_status = request_data['status']
        if current_status in self.TERMINAL_STATUSES:
            await update.message.reply_text(f"❌ Заявка #{request_id} уже завершена или отклонена и ее статус изменить нельзя.")
            return await self._show_main_menu(update, context)

        context.user_data['request_id_for_status_change'] = request_id

        keyboard = []
        statuses_to_show = []

        try:
            current_index = self.WORKFLOW_STATUSES.index(current_status)
            statuses_to_show.extend(self.WORKFLOW_STATUSES[current_index + 1:])
        except ValueError:
            logger.warning(
                f"[System] - Status '{current_status}' for request #{request_id} not found in WORKFLOW_STATUSES. Offering fallback options.")
            statuses_to_show.extend(
                [s for s in self.WORKFLOW_STATUSES if s not in self.TERMINAL_STATUSES])

        statuses_to_show.append('declined')

        for status in statuses_to_show:
            translated_status = self.bot.exchange_handler.translate_status(status)
            keyboard.append([InlineKeyboardButton(
                f"» {translated_status}", callback_data=f"set_status_{status}")])

        keyboard.append([InlineKeyboardButton("⬅️ Назад в меню", callback_data='admin_back_menu')])

        current_translated_status = self.bot.exchange_handler.translate_status(current_status)
        await update.message.reply_text(
            f"Выберите новый статус для заявки #{request_id} (текущий: {current_translated_status}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return self.SELECT_NEW_STATUS

    async def process_status_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        admin_user = query.from_user

        if data == 'admin_back_menu':
            await query.delete_message()
            return await self._show_main_menu(update, context)

        request_id = context.user_data.get('request_id_for_status_change')
        if not request_id:
            await query.edit_message_text("❌ Произошла ошибка сессии. Пожалуйста, начните сначала.")
            return await self._show_main_menu(update, context)

        new_status = data.replace('set_status_', '')
        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Changing status of request #{request_id} to '{new_status}'.")
            
        # --- START OF CHANGE ---
        # If the admin manually declines the request, trigger the refund logic.
        if new_status == 'declined':
            await self.bot.exchange_handler.refund_referral_debit_for_request(request_id)
        # --- END OF CHANGE ---

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await query.edit_message_text(f"❌ Заявка с ID #{request_id} больше не найдена.")
            return await self._show_main_menu(update, context)

        self.bot.db.update_request_status(request_id, new_status)
        translated_new_status = self.bot.exchange_handler.translate_status(new_status)
        await query.edit_message_text(f"✅ Статус для заявки #{request_id} обновлен на '{translated_new_status}'.\n\nПересоздаю сообщения для пользователя и админов...")

        try:
            await self._delete_old_messages(request_data, context)
            await self.bot.exchange_handler.resend_messages_for_request(request_id)
            await query.message.reply_text(f"✅ Сообщения для заявки #{request_id} успешно обновлены.")
            logger.info(
                f"[Aid] ({admin_user.id}, {admin_user.username}) - Successfully updated messages for request #{request_id} after manual status change.")
        except Exception as e:
            await query.message.reply_text(f"🚫 Произошла ошибка при обновлении сообщений: {e}")
            logger.error(
                f"[Aid] ({admin_user.id}, {admin_user.username}) - Failed to update messages for request #{request_id} after manual status change: {e}", exc_info=True)

        return await self._show_main_menu(update, context)

    async def restore_application(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_user = update.effective_user
        try:
            request_id = int(update.message.text.strip())
        except (ValueError, TypeError):
            await update.message.reply_text("❌ ID заявки должен быть числом. Попробуйте снова.")
            return self.AWAIT_REQUEST_ID_FOR_RESTORE

        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Trying to restore application #{request_id}.")

        request_data = self.bot.db.get_request_by_id(request_id)
        if not request_data:
            await update.message.reply_text(f"❌ Заявка с ID #{request_id} не найдена.")
            return await self._show_main_menu(update, context)

        if request_data['status'] in self.TERMINAL_STATUSES:
            await update.message.reply_text(f"❌ Заявка #{request_id} уже завершена или отклонена и не может быть восстановлена.")
            return await self._show_main_menu(update, context)

        await self._delete_old_messages(request_data, context)

        try:
            await self.bot.exchange_handler.resend_messages_for_request(request_id)
            await update.message.reply_text(f"✅ Сообщения для заявки #{request_id} были успешно пересозданы для пользователя и администраторов.")
            logger.info(
                f"[Aid] ({admin_user.id}, {admin_user.username}) - Successfully restored messages for application #{request_id}.")
        except Exception as e:
            await update.message.reply_text(f"🚫 Произошла ошибка при восстановлении заявки: {e}")
            logger.error(
                f"[Aid] ({admin_user.id}, {admin_user.username}) - Failed to restore application #{request_id}: {e}", exc_info=True)

        return await self._show_main_menu(update, context)

    async def _delete_old_messages(self, request_data: dict, context: ContextTypes.DEFAULT_TYPE):
        logger.info(
            f"[System] - Attempting to delete old messages for request #{request_data['id']}.")

        if request_data['user_message_id']:
            try:
                await context.bot.delete_message(
                    chat_id=request_data['user_id'],
                    message_id=request_data['user_message_id']
                )
                logger.info(
                    f"[System] - Deleted old message {request_data['user_message_id']} for user {request_data['user_id']}.")
            except TelegramError as e:
                logger.warning(
                    f"[System] - Failed to delete message for user {request_data['user_id']}: {e}")

        if request_data['admin_message_ids']:
            try:
                admin_message_ids = json.loads(request_data['admin_message_ids'])
                for admin_id, message_id in admin_message_ids.items():
                    try:
                        await context.bot.delete_message(chat_id=admin_id, message_id=message_id)
                        logger.info(
                            f"[System] - Deleted old message {message_id} for admin {admin_id}.")
                    except TelegramError as e:
                        logger.warning(
                            f"[System] - Failed to delete message for admin {admin_id}: {e}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(
                    f"[System] - Failed to parse admin_message_ids for request #{request_data['id']}: {e}")

    async def _show_info(self, query):
        masked_password = '*' * len(self.bot.config.admin_password)
        admin_ids_str = ', '.join(map(str, self.bot.config.admin_ids))
        text = (
            "📊 <b>Информация о боте</b>\n\n"
            f"👤 <b>Admin IDs:</b> <code>{admin_ids_str}</code>\n"
            f"🔐 <b>Пароль:</b> <code>{masked_password}</code>\n"
            f"💱 <b>Курс:</b> <code>{self.bot.config.exchange_rate}</code>\n"
            f"💼 <b>Кошелёк:</b> <code>{self.bot.config.wallet_address}</code>\n"
            f"📞 <b>Поддержка:</b> <code>{self.bot.config.support_contact}</code>"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')]])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        return self.ADMIN_MENU

    async def _show_settings_menu(self, query):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Пароль", callback_data='admin_set_password')],
            [InlineKeyboardButton("💱 Курс", callback_data='admin_set_exchange_rate')],
            [InlineKeyboardButton("💼 Кошелёк", callback_data='admin_set_wallet')],
            [InlineKeyboardButton("📞 Поддержка", callback_data='admin_set_support')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')],
        ])
        await query.edit_message_text("⚙️ Настройки:", reply_markup=keyboard)
        return self.SETTINGS_MENU

    async def show_user_applications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_input = update.message.text.strip()
        admin_user = update.effective_user
        logger.info(
            f"[Aid] ({admin_user.id}, {admin_user.username}) - Searching for user applications: {user_input}")

        all_applications = self.bot.db.get_request_by_user_id_or_login(user_input)
        logger.info(f"[System] - Found applications for '{user_input}': {len(all_applications)}.")

        if all_applications:
            await update.message.reply_text(f"✅ Найдены активные заявки ({len(all_applications)} шт.):")
            for app in all_applications:
                response_text = self._format_application_info(app)
                await update.message.reply_text(response_text, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Активных заявок для данного пользователя не найдено.")

        return await self._show_main_menu(update, context)

    def _format_application_info(self, app) -> str:
        referral_payout = app.get('referral_payout_amount', 0.0)
        payout_info = ""
        
        payout_info = f"<b>Сумма (UAH):</b> {app['amount_uah']:.2f}\n"
        if referral_payout > 0:
            payout_info = (
                f"<b>Сумма обмена (валюта):</b> {app['amount_currency']}\n"
                f"<b>Списано с реф. баланса ($):</b> {referral_payout:.2f}\n"
                f"<b>ИТОГО к выплате (UAH):</b> {app['amount_uah']:.2f}\n"
            )
        else:
             payout_info = (
                f"<b>Сумма (валюта):</b> {app['amount_currency']}\n"
                f"<b>Сумма (UAH):</b> {app['amount_uah']:.2f}\n"
            )

        return (
            f"<b>Заявка ID:</b> <code>{app['id']}</code>\n"
            f"<b>Пользователь:</b> @{app['username']} (<code>{app['user_id']}</code>)\n"
            f"<b>Статус:</b> {self.bot.exchange_handler.translate_status(app['status'])}\n"
            f"<b>Валюта:</b> {app['currency']}\n"
            f"{payout_info}"
            f"<b>Банк:</b> {app['bank_name']}\n"
            f"<b>IBAN:</b> <code>{app['card_info']}</code>\n"
            f"<b>Номер карты:</b> <code>{app['card_number'] or 'Не указан'}</code>\n"
            f"<b>ФИО:</b> {app['fio']}\n"
            f"<b>ИНН:</b> <code>{app['inn']}</code>\n"
            f"<b>TRX адрес:</b> <code>{app['trx_address'] or 'Не указан'}</code>\n"
            f"<b>Нужен TRX?:</b> {'Да' if app['needs_trx'] else 'Нет'}\n"
            f"<b>Хеш транзакции:</b> <code>{app['transaction_hash'] or 'Нет'}</code>\n"
            f"<b>Создана:</b> {app['created_at']}\n"
            f"<b>Обновлена:</b> {app['updated_at']}"
        )

    async def set_new_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.bot.config.admin_password = update.message.text.strip()
        await self.bot.config.save()
        logger.info(f"[Aid] ({user.id}, {user.username}) - Updated the password.")
        await update.message.reply_text("✅ Пароль обновлён.")
        return await self._show_main_menu(update, context)

    async def toggle_bot_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user = update.effective_user
        current_status = self.bot.config.bot_enabled
        new_status = not current_status

        self.bot.config.bot_enabled = new_status
        await self.bot.config.save()

        logger.info(
            f"[Aid] ({user.id}, {user.username}) - Changed bot status to: {'ENABLED' if new_status else 'DISABLED'}")

        await query.answer(f"Бот теперь {'включен' if new_status else 'выключен'}.")

        return await self._show_main_menu(update, context)

    async def set_exchange_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        try:
            new_rate = float(update.message.text.strip().replace(',', '.'))
            self.bot.config.exchange_rate = new_rate
            await self.bot.config.save()
            logger.info(
                f"[Aid] ({user.id}, {user.username}) - Updated the exchange rate to: {new_rate}")
            await update.message.reply_text("✅ Курс обновлён.")
        except ValueError:
            await update.message.reply_text("❌ Ошибка: введите корректное число.")
        return await self._show_main_menu(update, context)

    async def set_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.bot.config.wallet_address = update.message.text.strip()
        await self.bot.config.save()
        logger.info(f"[Aid] ({user.id}, {user.username}) - Updated the wallet address.")
        await update.message.reply_text("✅ Кошелёк обновлён.")
        return await self._show_main_menu(update, context)

    async def set_support_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        new_support = update.message.text.strip()
        if not re.fullmatch(r"[A-Za-z0-9@._\- ]+", new_support):
            await update.message.reply_text("❌ Недопустимый формат. Используйте латиницу, цифры, @ . _ -")
            return self.SET_SUPPORT
        else:
            self.bot.config.support_contact = new_support
            await self.bot.config.save()
            logger.info(f"[Aid] ({user.id}, {user.username}) - Updated the support contact.")
            await update.message.reply_text("✅ Контакт поддержки обновлён.")
        return await self._show_main_menu(update, context)

    async def close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id in self.bot.config.admin_ids:
            logger.info(f"[Aid] ({user.id}, {user.username}) - Closed the admin panel.")
            await update.message.reply_text("🔒 Админ-панель закрыта.")
        return ConversationHandler.END

    def setup_handlers(self, application):
        admin_conversation_handler = ConversationHandler(
            entry_points=[CommandHandler('a', self.start)],
            states={
                self.ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_password)],
                self.ADMIN_MENU: [CallbackQueryHandler(self.handle_callback, pattern='^admin_|find_user_applications|restore_application|change_status|toggle_bot_status')],
                self.SETTINGS_MENU: [CallbackQueryHandler(self.handle_callback, pattern='^admin_')],
                self.SET_NEW_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_new_password)],
                self.SET_EXCHANGE_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_exchange_rate)],
                self.SET_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_wallet)],
                self.SET_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_support_contact)],
                self.AWAIT_USER_FOR_APPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.show_user_applications)],
                self.AWAIT_REQUEST_ID_FOR_RESTORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.restore_application)],
                self.AWAIT_REQUEST_ID_FOR_STATUS_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.show_status_selection_menu)],
                self.SELECT_NEW_STATUS: [CallbackQueryHandler(self.process_status_change, pattern='^set_status_|admin_back_menu$')],
                
                # --- START OF CHANGE: Add new states for referral management ---
                self.REFERRAL_MENU: [
                    CallbackQueryHandler(self._ask_for_user_to_modify, pattern='^ref_(add|subtract)_balance$'),
                    CallbackQueryHandler(self._ask_for_user_to_check, pattern='^ref_check_balance$'),
                    CallbackQueryHandler(self._show_main_menu, pattern='^admin_back_menu$')
                ],
                self.AWAIT_USER_FOR_REF_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._ask_for_amount)],
                self.AWAIT_AMOUNT_FOR_REF_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._process_balance_change)],
                self.AWAIT_USER_FOR_REF_CHECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._check_user_balance)],
                # --- END OF CHANGE ---
            },
            fallbacks=[CommandHandler('a', self.start), CommandHandler('ac', self.close)]
        )
        application.add_handler(admin_conversation_handler)