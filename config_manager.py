# config_manager.py

import configparser
import logging
import asyncio
import os

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    A class for managing the bot's configuration from the settings.ini file.
    It encapsulates reading, writing, and accessing settings.
    """

    def __init__(self, file_path='settings.ini'):
        self.file_path = file_path
        self._config = configparser.ConfigParser()
        # Private _loop variable for asynchronous saving
        self._loop = None

    def load(self):
        """
        Synchronously loads the configuration. If the file is not found,
        it creates a new one with default values.
        """
        if not os.path.exists(self.file_path):
            logger.warning(
                f"[System] - Configuration file '{self.file_path}' not found. Creating a new file.")
            self._create_default_config()
            try:
                with open(self.file_path, 'w', encoding='utf-8') as config_file:
                    self._config.write(config_file)
                logger.info(
                    f"[System] - Configuration file '{self.file_path}' has been created. Please edit it and restart the bot.")
                print(
                    f"Configuration file '{self.file_path}' has been created. Specify the token and ID, then restart the script.")
                input("Press Enter to exit...")
                exit(0)
            except IOError as e:
                logger.error(f"[System] - Failed to create configuration file: {e}")
                exit(1)
        else:
            self._config.read(self.file_path, encoding='utf-8')
            logger.info(f"[System] - Configuration file '{self.file_path}' loaded successfully.")

    def _create_default_config(self):
        """Creates the default configuration structure."""
        self._config['User'] = {
            'TOKEN': 'your_token_here',
            'ADMIN_CHAT_ID': 'your_admin_chat_id_here',
        }
        self._config['Settings'] = {
            'EXCHANGE_RATE': 'your_exchange_rate_here',
            'ADMIN_PASSWORD': 'your_admin_password_here',
            'WALLET_ADDRESS': 'your_wallet_address_here',
            'SUPPORT_CONTACT': 'your_support_contact_here',
            'TRX_COST_USDT': '15.0',
            'BOT_ENABLED': 'True'
        }

    def _save_sync(self):
        """Synchronous function to write the configuration to a file."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as config_file:
                self._config.write(config_file)
            logger.info("[System] - Configuration saved successfully.")
        except IOError as e:
            logger.error(f"[System] - Error saving configuration: {e}")

    async def save(self):
        """
        Asynchronously saves the current configuration without blocking the event loop.
        """
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        await self._loop.run_in_executor(None, self._save_sync)

    def get(self, section, option, fallback=None):
        """Universal method for getting a value from the configuration."""
        return self._config.get(section, option, fallback=fallback)

    def set(self, section, option, value):
        """Universal method for setting a value in the configuration."""
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, option, str(value))

    # --- Properties for convenient access to settings ---
    # This allows writing bot.config.token instead of bot.config.get('User', 'TOKEN')

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
            logger.error(
                "[System] - Error in ADMIN_CHAT_ID format. Make sure it is a comma-separated list of numbers.")
            return []

    @property
    def admin_password(self) -> str:
        return self.get('Settings', 'ADMIN_PASSWORD')

    @admin_password.setter
    def admin_password(self, value: str):
        self.set('Settings', 'ADMIN_PASSWORD', value)

    @property
    def exchange_rate(self) -> float:
        return float(self.get('Settings', 'EXCHANGE_RATE', '0'))

    @exchange_rate.setter
    def exchange_rate(self, value: float):
        self.set('Settings', 'EXCHANGE_RATE', str(value))

    @property
    def wallet_address(self) -> str:
        return self.get('Settings', 'WALLET_ADDRESS')

    @wallet_address.setter
    def wallet_address(self, value: str):
        self.set('Settings', 'WALLET_ADDRESS', value)

    @property
    def support_contact(self) -> str:
        return self.get('Settings', 'SUPPORT_CONTACT')

    @support_contact.setter
    def support_contact(self, value: str):
        self.set('Settings', 'SUPPORT_CONTACT', value)

    @property
    def trx_cost_usdt(self) -> float:
        return float(self.get('Settings', 'TRX_COST_USDT', '15.0'))

    @property
    def bot_enabled(self) -> bool:
        """Returns True if the bot is enabled, False otherwise."""
        return self.get('Settings', 'BOT_ENABLED', 'True') == 'True'

    @bot_enabled.setter
    def bot_enabled(self, value: bool):
        """Sets the bot's enabled status."""
        self.set('Settings', 'BOT_ENABLED', str(value))
