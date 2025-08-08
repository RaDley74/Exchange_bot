# main.py

import os
import sys
import logging
import warnings

from telegram.ext import ApplicationBuilder

# Import our new classes
from config_manager import ConfigManager
# --- Import the new DatabaseManager ---
from database_manager import DatabaseManager
from handlers.admin_handler import AdminPanelHandler
from handlers.exchange_handler import ExchangeHandler

# --- Logging Setup ---

os.makedirs("log", exist_ok=True)
os.makedirs("database", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
        logger.info("Initializing the bot...")

        # 1. Create and load the configuration
        self.config = ConfigManager()
        self.config.load()

        # 2. --- Initialize the Database ---
        # Instead of an in-memory dictionary, we now use our persistent database.
        self.db = DatabaseManager()
        self.db.connect()
        self.db.setup_database()  # Creates tables if they don't exist

        # 3. Create the PTB application
        self.application = ApplicationBuilder().token(self.config.token).build()

        # 4. Create instances of our handlers, passing them `self` (the Bot instance)
        #    to provide access to config and now the database.
        self.admin_handler = AdminPanelHandler(self)
        self.exchange_handler = ExchangeHandler(self)

    def setup_handlers(self):
        """
        Delegates handler setup to the respective classes.
        """
        self.admin_handler.setup_handlers(self.application)
        self.exchange_handler.setup_handlers(self.application)
        logger.info("Handlers have been set up successfully.")

    def run(self):
        """
        Starts the bot.
        """
        try:
            self.setup_handlers()
            logger.info("Bot is running and ready to work...")
            self.application.run_polling()
        finally:
            # --- Ensure the database connection is closed gracefully ---
            self.db.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    bot = Bot()
    bot.run()
