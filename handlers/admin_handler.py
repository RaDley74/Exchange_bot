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
    Обрабатывает всю логику, связанную с админ-панелью.
    """
    # Этапы разговора вынесены как атрибуты класса для ясности
    (
        ASK_PASSWORD,
        ADMIN_MENU,
        SETTINGS_MENU,
        SET_NEW_PASSWORD,
        SET_EXCHANGE_RATE,
        SET_WALLET,
        SET_SUPPORT
    ) = range(7)

    def __init__(self, bot_instance):
        """
        Конструктор получает экземпляр главного класса Bot,
        чтобы иметь доступ к общим ресурсам, таким как конфигурация.
        """
        self.bot = bot_instance

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) пытается войти в админ-панель.")

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
            logger.info(f"Admin {user.id} ({user.username}) ввел верный пароль.")
            return await self._show_main_menu(update)
        else:
            logger.warning(f"Admin {user.id} ({user.username}) ввел неверный пароль.")
            await update.message.reply_text("❌ Неверный пароль. Попробуйте снова:")
            return self.ASK_PASSWORD

    async def _show_main_menu(self, update: Update):
        logger.info(f"Отображение главного меню админки для {update.effective_user.id}.")
        keyboard = [
            [
                InlineKeyboardButton("📊 Информация", callback_data='admin_info'),
                InlineKeyboardButton("⚙️ Настройки", callback_data='admin_settings'),
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
        logger.info(f"Admin {user.id} ({user.username}) выбрал опцию: {data}")

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
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data='admin_back_menu')]])
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

    async def set_new_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.bot.config.admin_password = update.message.text.strip()
        await self.bot.config.save()
        logger.info(f"Admin {update.effective_user.id} обновил пароль.")
        await update.message.reply_text("✅ Пароль обновлён.")
        return await self._show_main_menu(update)

    async def set_exchange_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            new_rate = float(update.message.text.strip().replace(',', '.'))
            self.bot.config.exchange_rate = new_rate
            await self.bot.config.save()
            logger.info(f"Admin {update.effective_user.id} обновил курс на: {new_rate}")
            await update.message.reply_text("✅ Курс обновлён.")
        except ValueError:
            await update.message.reply_text("❌ Ошибка: введите корректное число.")
        return await self._show_main_menu(update)

    async def set_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.bot.config.wallet_address = update.message.text.strip()
        await self.bot.config.save()
        logger.info(f"Admin {update.effective_user.id} обновил кошелёк.")
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
            logger.info(f"Admin {update.effective_user.id} обновил контакт поддержки.")
            await update.message.reply_text("✅ Контакт поддержки обновлён.")
        return await self._show_main_menu(update)
    
    async def close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id in self.bot.config.admin_ids:
            logger.info(f"Admin {user.id} закрыл админ-панель.")
            await update.message.reply_text("🔒 Админ-панель закрыта.")
        return ConversationHandler.END

    def setup_handlers(self, application):
        """Создает и регистрирует обработчики для админ-панели."""
        admin_handler = ConversationHandler(
            entry_points=[CommandHandler('a', self.start)],
            states={
                self.ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_password)],
                self.ADMIN_MENU: [CallbackQueryHandler(self.handle_callback, pattern='^admin_')],
                self.SETTINGS_MENU: [CallbackQueryHandler(self.handle_callback, pattern='^admin_')],
                self.SET_NEW_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_new_password)],
                self.SET_EXCHANGE_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_exchange_rate)],
                self.SET_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_wallet)],
                self.SET_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_support_contact)],
            },
            fallbacks=[CommandHandler('a', self.start), CommandHandler('ac', self.close)]
        )
        application.add_handler(admin_handler)