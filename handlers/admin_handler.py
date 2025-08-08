# handlers/admin_handler.py

import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
)

logger = logging.getLogger(__name__)


class AdminPanelHandler:
    """
    Handles all logic related to the admin panel.
    """
    # Conversation states are defined as class attributes for clarity
    (
        ASK_PASSWORD,
        ADMIN_MENU,
        SETTINGS_MENU,
        SET_NEW_PASSWORD,
        SET_EXCHANGE_RATE,
        SET_WALLET,
        SET_SUPPORT,
        AWAIT_USER_FOR_APPS,  # Новое состояние для ожидания ввода пользователя
    ) = range(8)

    def __init__(self, bot_instance):
        """
        The constructor receives the main Bot instance
        to access shared resources like configuration.
        """
        self.bot = bot_instance

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) is trying to access the admin panel.")

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
            logger.info(f"Admin {user.id} ({user.username}) entered the correct password.")
            return await self._show_main_menu(update)
        else:
            logger.warning(f"Admin {user.id} ({user.username}) entered the wrong password.")
            await update.message.reply_text("❌ Неверный пароль. Попробуйте снова:")
            return self.ASK_PASSWORD

    async def _show_main_menu(self, update: Update):
        logger.info(f"Displaying admin main menu for {update.effective_user.id}.")
        keyboard = [
            [
                InlineKeyboardButton("📊 Информация", callback_data='admin_info'),
                InlineKeyboardButton("⚙️ Настройки", callback_data='admin_settings'),
            ],
            [
                InlineKeyboardButton("🔍 Найти заявки", callback_data='find_user_applications'),
            ],
        ]
        text = "⚙️ Админ-панель"
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

        return self.ADMIN_MENU

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        logger.info(f"Admin {user.id} ({user.username}) selected option: {data}")

        if user.id not in self.bot.config.admin_ids:
            await query.message.reply_text("🚫 У вас нет доступа.")
            return ConversationHandler.END

        if data == 'admin_info':
            return await self._show_info(query)
        elif data == 'admin_settings':
            return await self._show_settings_menu(query)
        elif data == 'admin_back_menu':
            return await self._show_main_menu(update)
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

        return self.ADMIN_MENU

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
        user_input = update.message.text.strip().lower()
        admin_user = update.effective_user
        logger.info(f"Admin {admin_user.id} is searching for applications of user: {user_input}")

        # --- Начало симуляции данных ---
        # В реальном приложении здесь будет запрос к вашей базе данных
        # print(f"Mock data for user '{user_input}': {mock_data_dict}")

        # input(f"Press Enter to continue...")  # Для отладки, чтобы увидеть данные в консоли
        # Предполагаем, что у пользователя может быть несколько заявок
        all_applications = self.bot.db.get_request_by_user_id_or_login(user_input)
        logger.info(f"Mock applications for user '{user_input}': {all_applications}")
        # input(f"Press Enter to continue...")  # Для отладки, чтобы увидеть данные в консоли
        # --- Конец симуляции данных ---

        if all_applications:
            await update.message.reply_text(f"✅ Найдены активные заявки ({len(all_applications)} шт.):")
            for app in all_applications:
                response_text = self._format_application_info(app)
                await update.message.reply_text(response_text, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Активных заявок для данного пользователя не найдено.")

        return await self._show_main_menu(update)

    def _format_application_info(self, app) -> str:
        """Форматирует информацию о заявке для вывода."""
        return (
            f"<b>Заявка ID:</b> <code>{app['id']}</code>\n"
            f"<b>Пользователь:</b> @{app['username']} (<code>{app['user_id']}</code>)\n"
            f"<b>Статус:</b> {app['status']}\n"
            f"<b>Валюта:</b> {app['currency']}\n"
            f"<b>Сумма (валюта):</b> {app['amount_currency']}\n"
            f"<b>Сумма (UAH):</b> {app['amount_uah']}\n"
            f"<b>Банк:</b> {app['bank_name']}\n"
            f"<b>Карта:</b> <code>{app['card_info']}</code>\n"
            f"<b>ФИО:</b> {app['fio']}\n"
            f"<b>ИНН:</b> <code>{app['inn']}</code>\n"
            f"<b>TRX адрес:</b> <code>{app['trx_address'] or 'Не указан'}</code>\n"
            f"<b>Нужен TRX?:</b> {'Да' if app['needs_trx'] == '1' else 'Нет'}\n"
            f"<b>Хеш транзакции:</b> <code>{app['transaction_hash'] or 'Нет'}</code>\n"
            f"<b>Создана:</b> {app['created_at']}\n"
            f"<b>Обновлена:</b> {app['updated_at']}"
        )

    async def set_new_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.bot.config.admin_password = update.message.text.strip()
        await self.bot.config.save()
        logger.info(f"Admin {update.effective_user.id} updated the password.")
        await update.message.reply_text("✅ Пароль обновлён.")
        return await self._show_main_menu(update)

    async def set_exchange_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            new_rate = float(update.message.text.strip().replace(',', '.'))
            self.bot.config.exchange_rate = new_rate
            await self.bot.config.save()
            logger.info(
                f"Admin {update.effective_user.id} updated the exchange rate to: {new_rate}")
            await update.message.reply_text("✅ Курс обновлён.")
        except ValueError:
            await update.message.reply_text("❌ Ошибка: введите корректное число.")
        return await self._show_main_menu(update)

    async def set_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.bot.config.wallet_address = update.message.text.strip()
        await self.bot.config.save()
        logger.info(f"Admin {update.effective_user.id} updated the wallet address.")
        await update.message.reply_text("✅ Кошелёк обновлён.")
        return await self._show_main_menu(update)

    async def set_support_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        new_support = update.message.text.strip()
        if not re.fullmatch(r"[A-Za-z0-9@._\- ]+", new_support):
            await update.message.reply_text("❌ Недопустимый формат. Используйте латиницу, цифры, @ . _ -")
            return self.SET_SUPPORT
        else:
            self.bot.config.support_contact = new_support
            await self.bot.config.save()
            logger.info(f"Admin {update.effective_user.id} updated the support contact.")
            await update.message.reply_text("✅ Контакт поддержки обновлён.")
        return await self._show_main_menu(update)

    async def close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id in self.bot.config.admin_ids:
            logger.info(f"Admin {user.id} closed the admin panel.")
            await update.message.reply_text("🔒 Админ-панель закрыта.")
        return ConversationHandler.END

    def setup_handlers(self, application):
        """Creates and registers the handlers for the admin panel."""
        admin_conversation_handler = ConversationHandler(
            entry_points=[CommandHandler('a', self.start)],
            states={
                self.ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_password)],
                self.ADMIN_MENU: [CallbackQueryHandler(self.handle_callback, pattern='^admin_|find_user_applications')],
                self.SETTINGS_MENU: [CallbackQueryHandler(self.handle_callback, pattern='^admin_')],
                self.SET_NEW_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_new_password)],
                self.SET_EXCHANGE_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_exchange_rate)],
                self.SET_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_wallet)],
                self.SET_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_support_contact)],
                self.AWAIT_USER_FOR_APPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.show_user_applications)],
            },
            fallbacks=[CommandHandler('a', self.start), CommandHandler('ac', self.close)]
        )
        application.add_handler(admin_conversation_handler)
