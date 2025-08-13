# handlers/user_cabinet_handler.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)

logger = logging.getLogger(__name__)


class UserCabinetHandler:
    """
    Handles all logic related to the user's personal cabinet,
    allowing them to view and manage their payment requisites.
    """
    (
        CABINET_MENU,
        EDIT_BANK,
        EDIT_IBAN,
        EDIT_CARD_NUMBER,
        EDIT_FIO,
        EDIT_INN
    ) = range(20, 26)

    def __init__(self, bot_instance):
        self.bot = bot_instance

    def _format_profile_info(self, profile_data: dict, user_id, username) -> str:
        """Formats user profile data for display in a message."""
        referral_balance = profile_data.get('referral_balance', 0.0) if profile_data else 0.0
        header = (
            f"<b>👤 Профиль:</b> @{username or 'N/A'}\n"
            f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
            f"<b>💰 Реферальный баланс:</b> ${referral_balance:.2f}\n\n"
        )

        if not profile_data or not any([profile_data.get(key) for key in ['bank_name', 'card_info', 'card_number', 'fio', 'inn']]):
            return header + "📭 Ваши реквизиты еще не сохранены."

        body = (
            "<b>🗂️ Ваши сохраненные реквизиты:</b>\n\n"
            f"<b>👤 ФИО:</b> {profile_data.get('fio') or 'Не указано'}\n"
            f"<b>🏦 Банк:</b> {profile_data.get('bank_name') or 'Не указан'}\n"
            f"<b>💳 IBAN:</b> <code>{profile_data.get('card_info') or 'Не указан'}</code>\n"
            f"<b>🔢 Номер карты:</b> <code>{profile_data.get('card_number') or 'Не указан'}</code>\n"
            f"<b>🆔 ІПН/ЄДРПОУ:</b> <code>{profile_data.get('inn') or 'Не указан'}</code>"
        )
        return header + body

    async def start_cabinet(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Entry point for the user cabinet. Fetches user profile
        and displays it with action buttons.
        """
        user = update.effective_user
        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered user cabinet.")

        profile_data = self.bot.db.get_user_profile(user.id)
        text = self._format_profile_info(profile_data, user.id, user.username)

        keyboard = [
            [InlineKeyboardButton("📝 Изменить мои реквизиты", callback_data='edit_profile')],
            [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data='back_to_main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

        return self.CABINET_MENU

    async def handle_cabinet_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handles button presses within the cabinet menu."""
        query = update.callback_query
        await query.answer()

        if query.data == 'edit_profile':
            context.user_data['profile'] = {}
            await query.edit_message_text("🏦 Пожалуйста, укажите название вашего банка:")
            return self.EDIT_BANK
        elif query.data == 'back_to_main_menu':
            await self.bot.exchange_handler.main_menu(update, context)
            return ConversationHandler.END

    async def edit_bank(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        bank_name = update.message.text.strip()
        context.user_data['profile']['bank_name'] = bank_name
        logger.info(
            f"[Uid] ({update.effective_user.id}) - Cabinet Update: Set bank to {bank_name}")
        await update.message.reply_text("💳 Введите ваш IBAN:")
        return self.EDIT_IBAN

    async def edit_iban(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        card_info = update.message.text.strip()
        context.user_data['profile']['card_info'] = card_info
        logger.info(f"[Uid] ({update.effective_user.id}) - Cabinet Update: Set IBAN.")
        await update.message.reply_text("🔢 Теперь введите номер вашей карты:")
        return self.EDIT_CARD_NUMBER

    async def edit_card_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        card_number = update.message.text.strip()
        context.user_data['profile']['card_number'] = card_number
        logger.info(f"[Uid] ({update.effective_user.id}) - Cabinet Update: Set card number.")
        await update.message.reply_text("👤 Укажите ваши ФИО:")
        return self.EDIT_FIO

    async def edit_fio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        fio = update.message.text.strip()
        context.user_data['profile']['fio'] = fio
        logger.info(f"[Uid] ({update.effective_user.id}) - Cabinet Update: Set FIO.")
        await update.message.reply_text("🆔 Пожалуйста, введите ваш ІПН/ЄДРПОУ:")
        return self.EDIT_INN

    async def edit_inn_and_save(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Saves the INN, writes all collected data to the database, and returns to the cabinet menu."""
        user = update.effective_user
        inn = update.message.text.strip()
        context.user_data['profile']['inn'] = inn
        logger.info(f"[Uid] ({user.id}) - Cabinet Update: Set INN. Saving complete profile.")

        profile_data = context.user_data.pop('profile', {})
        self.bot.db.create_or_update_user_profile(user.id, profile_data)

        await update.message.reply_text("✅ Ваши реквизиты успешно сохранены!")

        return await self.start_cabinet(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Cancels the current conversation and returns ConversationHandler.END.
        The global /start handler will then show the main menu.
        """
        user = update.effective_user
        logger.info(f"[Uid] ({user.id}) - Canceled cabinet operation.")
        if update.message:
            try:
                await update.message.delete()
            except Exception as e:
                logger.warning(f"Failed to delete message during cabinet cancellation: {e}")

        if 'profile' in context.user_data:
            del context.user_data['profile']
        return ConversationHandler.END

    def setup_handlers(self, application):
        """Sets up the ConversationHandler for the user cabinet."""
        cabinet_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('cabinet', self.start_cabinet),
                CallbackQueryHandler(self.start_cabinet, pattern='^user_cabinet$')
            ],
            states={
                self.CABINET_MENU: [
                    CallbackQueryHandler(self.handle_cabinet_menu,
                                         pattern='^(edit_profile|back_to_main_menu)$')
                ],
                self.EDIT_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_bank)],
                self.EDIT_IBAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_iban)],
                self.EDIT_CARD_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_card_number)],
                self.EDIT_FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_fio)],
                self.EDIT_INN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_inn_and_save)],
            },
            fallbacks=[
                CommandHandler('start', self.cancel),
                CallbackQueryHandler(self.handle_cabinet_menu, pattern='^back_to_main_menu$')
            ],
            per_message=False
        )
        application.add_handler(cabinet_conv_handler)
