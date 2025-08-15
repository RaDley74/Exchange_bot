import os
import sys
import logging
import warnings

from telegram.ext import ApplicationBuilder

from config_manager import ConfigManager
from database_manager import DatabaseManager
from handlers.admin_handler import AdminPanelHandler
from handlers.exchange_handler import ExchangeHandler
from handlers.user_cabinet_handler import UserCabinetHandler
from handlers.referral_handler import ReferralHandler

os.makedirs("log", exist_ok=True)
os.makedirs("database", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)-29s - %(levelname)-8s - %(message)s',
    handlers=[
        logging.FileHandler("log/bot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning)


class Bot:
    """
    The main bot class.
    Responsible for initializing all components and launching the bot.
    """

    def __init__(self):
        logger.info("[System] - Initializing the bot...")

        self.config = ConfigManager()
        self.config.load()

        self.db = DatabaseManager()
        self.db.connect()
        self.db.setup_database()

        self.application = ApplicationBuilder().token(self.config.token).build()

        self.admin_handler = AdminPanelHandler(self)
        self.exchange_handler = ExchangeHandler(self)
        self.user_cabinet_handler = UserCabinetHandler(self)
        self.referral_handler = ReferralHandler(self)

    def setup_handlers(self):
        """
        Delegates handler setup to the respective classes.
        """
        self.admin_handler.setup_handlers(self.application)
        self.exchange_handler.setup_handlers(self.application)
        self.user_cabinet_handler.setup_handlers(self.application)
        self.referral_handler.setup_handlers(self.application)
        logger.info("[System] - Handlers have been successfully set up.")

    def run(self):
        """
        Starts the bot.
        """
        try:
            self.setup_handlers()
            logger.info("[System] - Bot is running and ready to work...")
            self.application.run_polling()
        finally:
            self.db.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    bot = Bot()
    bot.run()
