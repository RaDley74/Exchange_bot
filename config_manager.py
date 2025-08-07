# config_manager.py

import configparser
import logging
import asyncio
import os

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Класс для управления конфигурацией бота из файла settings.ini.
    Инкапсулирует чтение, запись и доступ к настройкам.
    """

    def __init__(self, file_path='settings.ini'):
        self.file_path = file_path
        self._config = configparser.ConfigParser()
        # Приватная переменная _loop для асинхронного сохранения
        self._loop = None

    def load(self):
        """
        Синхронно загружает конфигурацию. Если файл не найден,
        создает его со значениями по умолчанию.
        """
        if not os.path.exists(self.file_path):
            logger.warning(
                f"Файл конфигурации '{self.file_path}' не найден. Создание нового файла.")
            self._create_default_config()
            try:
                with open(self.file_path, 'w', encoding='utf-8') as config_file:
                    self._config.write(config_file)
                logger.info(
                    f"Файл конфигурации '{self.file_path}' создан. Отредактируйте его и перезапустите бота.")
                print(
                    f"Файл конфигурации '{self.file_path}' создан. Укажите токен и ID, затем перезапустите скрипт.")
                input("Нажмите Enter для выхода...")
                exit(0)
            except IOError as e:
                logger.error(f"Не удалось создать файл конфигурации: {e}")
                exit(1)
        else:
            self._config.read(self.file_path, encoding='utf-8')
            logger.info(f"Файл конфигурации '{self.file_path}' успешно загружен.")

    def _create_default_config(self):
        """Создает структуру конфигурации по умолчанию."""
        self._config['User'] = {
            'TOKEN': 'your_token_here',
            'ADMIN_CHAT_ID': 'your_admin_chat_id_here',
        }
        self._config['Settings'] = {
            'EXCHANGE_RATE': 'your_exchange_rate_here',
            'ADMIN_PASSWORD': 'your_admin_password_here',
            'WALLET_ADDRESS': 'your_wallet_address_here',
            'SUPPORT_CONTACT': 'your_support_contact_here'
        }

    def _save_sync(self):
        """Синхронная функция для записи конфигурации в файл."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as config_file:
                self._config.write(config_file)
            logger.info("Конфигурация успешно сохранена.")
        except IOError as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")

    async def save(self):
        """
        Асинхронно сохраняет текущую конфигурацию, не блокируя event loop.
        """
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        await self._loop.run_in_executor(None, self._save_sync)

    def get(self, section, option, fallback=None):
        """Универсальный метод для получения значения из конфигурации."""
        return self._config.get(section, option, fallback=fallback)

    def set(self, section, option, value):
        """Универсальный метод для установки значения в конфигурации."""
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, option, str(value))

    # --- Свойства для удобного доступа к настройкам ---
    # Это позволяет писать bot.config.token вместо bot.config.get('User', 'TOKEN')

    @property
    def token(self) -> str:
        return self.get('User', 'TOKEN')

    @property
    def admin_ids(self) -> list[int]:
        admin_ids_str = self.get('User', 'ADMIN_CHAT_ID', '')
        if not admin_ids_str:
            return []
        try:
            return [int(admin_id.strip()) for admin_id in admin_ids_str.split(',')]
        except ValueError:
            logger.error("Ошибка в формате ADMIN_CHAT_ID. Убедитесь, что это числа через запятую.")
            return []

    @property
    def admin_password(self) -> str:
        return self.get('Settings', 'ADMIN_PASSWORD')

    @admin_password.setter
    def admin_password(self, value: str):
        self.set('Settings', 'admin_password', value)

    @property
    def exchange_rate(self) -> float:
        return float(self.get('Settings', 'EXCHANGE_RATE', '0'))

    @exchange_rate.setter
    def exchange_rate(self, value: float):
        self.set('Settings', 'exchange_rate', value)

    @property
    def wallet_address(self) -> str:
        return self.get('Settings', 'WALLET_ADDRESS')

    @wallet_address.setter
    def wallet_address(self, value: str):
        self.set('Settings', 'wallet_address', value)

    @property
    def support_contact(self) -> str:
        return self.get('Settings', 'SUPPORT_CONTACT')

    @support_contact.setter
    def support_contact(self, value: str):
        self.set('Settings', 'support_contact', value)
