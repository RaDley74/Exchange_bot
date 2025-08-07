# main.py

import os
import sys
import logging
import warnings

from telegram.ext import ApplicationBuilder

# Импортируем наши новые классы
from config_manager import ConfigManager
from handlers.admin_handler import AdminPanelHandler
from handlers.exchange_handler import ExchangeHandler

# --- Настройка логирования ---

os.makedirs("log", exist_ok=True)

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
    Главный класс бота.
    Отвечает за инициализацию всех компонентов и запуск.
    """

    def __init__(self):
        logger.info("Инициализация бота...")

        # 1. Создаем и загружаем конфигурацию
        self.config = ConfigManager()
        self.config.load()

        # 2. Инициализируем хранилище сессий
        self.user_sessions = {}

        # 3. Создаем приложение PTB
        self.application = ApplicationBuilder().token(self.config.token).build()

        # 4. Создаем экземпляры наших обработчиков, передавая им self (Bot instance)
        #    для доступа к config и user_sessions.
        self.admin_handler = AdminPanelHandler(self)
        self.exchange_handler = ExchangeHandler(self)

    def setup_handlers(self):
        """
        Делегирует настройку обработчиков соответствующим классам.
        """
        self.admin_handler.setup_handlers(self.application)
        self.exchange_handler.setup_handlers(self.application)
        logger.info("Обработчики успешно настроены.")

    def run(self):
        """
        Запускает бота.
        """
        self.setup_handlers()
        logger.info("Бот запущен и готов к работе...")
        self.application.run_polling()


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    bot = Bot()
    bot.run()
