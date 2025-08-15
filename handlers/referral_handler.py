# handlers/referral_handler.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler
)

logger = logging.getLogger(__name__)


class ReferralHandler:
    """
    Manages all logic related to the referral system, including pagination.
    """
    REFERRAL_MENU = 30
    REFERRALS_PER_PAGE = 10
    REFERRAL_BONUS = 15.0

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def _display_referral_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
        """
        Displays the referral program menu for the specified page.
        This function is the core of pagination.
        """
        user = update.effective_user

        referrals, total_pages = self.bot.db.get_referrals_by_referrer_id(
            user.id, page=page, page_size=self.REFERRALS_PER_PAGE
        )

        profile = self.bot.db.get_user_profile(user.id)
        referral_balance = profile.get('referral_balance', 0.0) if profile else 0.0

        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"

        text = (
            f"🏆 **Ваша реферальная программа**\n\n"
            f"Приглашайте друзей и получайте **${self.REFERRAL_BONUS}** за каждого, кто совершит свой первый успешный обмен!\n\n"
            f"Если вы пришли от конкурента, напишите в поддержку и предоставьте доказательства. Вам будет зачислено $5\n\n"
            f"🔗 **Ваша реферальная ссылка:**\n`{referral_link}`\n\n"
            f"💰 **Ваш реферальный баланс:** ${referral_balance:.2f}\n\n"
        )

        if referrals:
            text += "👥 **Приглашенные вами пользователи:**\n"
            for ref in referrals:
                status = "✅ (бонус начислен)" if ref['is_credited'] else "⏳ (ожидает обмена)"
                text += f"- @{ref.get('referred_username') or 'Пользователь'} {status}\n"
        else:
            text += "Вы еще никого не пригласили. Поделитесь ссылкой с друзьями!"

        pagination_buttons = []
        if total_pages > 1:
            if page > 1:
                pagination_buttons.append(InlineKeyboardButton(
                    "⬅️ Назад", callback_data=f'ref_page_{page - 1}'))

            pagination_buttons.append(InlineKeyboardButton(
                f"📄 {page}/{total_pages}", callback_data='ref_page_ignore'))

            if page < total_pages:
                pagination_buttons.append(InlineKeyboardButton(
                    "Вперед ➡️", callback_data=f'ref_page_{page + 1}'))

        keyboard = []
        if pagination_buttons:
            keyboard.append(pagination_buttons)

        keyboard.append([InlineKeyboardButton(
            "⬅️ В главное меню", callback_data='back_to_main_menu')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def start_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Entry point for the referral program conversation. Displays the first page."""
        user = update.effective_user
        logger.info(f"[Uid] ({user.id}, {user.username}) - Entered referral menu.")
        await self._display_referral_menu(update, context, page=1)
        return self.REFERRAL_MENU

    async def handle_page_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handles clicks on pagination buttons."""
        query = update.callback_query

        if query.data == 'ref_page_ignore':
            await query.answer()
            return self.REFERRAL_MENU

        page = int(query.data.split('_')[-1])
        await self._display_referral_menu(update, context, page=page)
        return self.REFERRAL_MENU

    async def handle_referral_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles following a referral link."""
        user = update.effective_user
        referrer_id_str = context.args[0].split('_')[1]

        if not referrer_id_str.isdigit():
            return await self.bot.exchange_handler.start_command(update, context, called_from_referral=True)

        referrer_id = int(referrer_id_str)

        if user.id == referrer_id:
            await update.message.reply_text("Вы не можете использовать свою собственную реферальную ссылку.")
            return await self.bot.exchange_handler.start_command(update, context, called_from_referral=True)

        if not self.bot.db.get_referral_by_referred_id(user.id):
            if self.bot.db.get_user_profile(user.id) is not None:
                logger.info(
                    f"[Uid] ({user.id}) clicked referral link from {referrer_id} but is already a registered user. Ignoring referral.")
            else:
                self.bot.db.create_referral(referrer_id, user.id, user.username)
                logger.info(
                    f"[Uid] ({user.id}, {user.username}) registered as a referral of {referrer_id}.")
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 У вас новый реферал: @{user.username or user.id}! Вы получите бонус после его первой успешной сделки."
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to referrer {referrer_id}: {e}")

        await self.bot.exchange_handler.start_command(update, context, called_from_referral=True)

    async def credit_referrer(self, referred_user_id: int):
        """Credits the referrer after the referral's first successful exchange."""
        referral = self.bot.db.get_referral_by_referred_id(referred_user_id)
        if not referral or referral['is_credited']:
            return

        if self.bot.db.get_user_completed_request_count(referred_user_id) != 1:
            return

        referrer_id = referral['referrer_id']
        self.bot.db.update_referral_balance(referrer_id, self.REFERRAL_BONUS)
        self.bot.db.update_referral_as_credited(referred_user_id)
        logger.info(
            f"Credited ${self.REFERRAL_BONUS} to {referrer_id} for referral {referred_user_id}.")

        referred_username = referral.get('referred_username')
        referred_user_display = f"@{referred_username}" if referred_username else f"пользователь (ID: {referred_user_id})"

        try:
            await self.bot.application.bot.send_message(
                chat_id=referrer_id,
                text=f"✅ Поздравляем! Ваш реферал {referred_user_display} совершил первую сделку. Вам начислено **${self.REFERRAL_BONUS}**.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send bonus notification to referrer {referrer_id}: {e}")

        # Notify admin about the credited bonus
        try:
            admin_ids = self.bot.config.admin_ids
            if not admin_ids:
                return

            referrer_profile = self.bot.db.get_user_profile(referrer_id)
            referrer_username = referrer_profile.get(
                'username') if referrer_profile else f"ID: {referrer_id}"
            referrer_display = f"@{referrer_username}" if referrer_username != f"ID: {referrer_id}" else f"пользователь (ID: {referrer_id})"

            admin_message = f"💰 Пользователь {referrer_display} получил ${self.REFERRAL_BONUS:.2f}, так как его реферал {referred_user_display} выполнил первую сделку."

            for admin_id in admin_ids:
                try:
                    await self.bot.application.bot.send_message(
                        chat_id=admin_id,
                        text=admin_message
                    )
                except Exception as e_inner:
                    logger.error(
                        f"Failed to send referral bonus notification to admin {admin_id}: {e_inner}")
        except Exception as e:
            logger.error(
                f"An error occurred while trying to notify admins about a referral bonus: {e}")

    async def back_to_main_menu_from_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Returns the user to the main menu and ends the conversation."""
        await self.bot.exchange_handler.main_menu(update, context)
        return ConversationHandler.END

    def setup_handlers(self, application):
        """Sets up the handlers for the referral conversation."""
        referral_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('referral', self.start_referral),
                CallbackQueryHandler(self.start_referral, pattern='^referral_program$')
            ],
            states={
                self.REFERRAL_MENU: [
                    CallbackQueryHandler(self.back_to_main_menu_from_referral,
                                         pattern='^back_to_main_menu$'),
                    CallbackQueryHandler(self.handle_page_navigation, pattern=r'^ref_page_')
                ]
            },
            fallbacks=[
                CommandHandler('start', self.bot.exchange_handler.cancel_and_return_to_menu)
            ],
            per_message=False
        )
        application.add_handler(referral_conv_handler)
