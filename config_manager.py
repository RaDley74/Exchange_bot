import configparser
import logging
import asyncio
import os
from functools import partial

# --- Настройка логирования ---
logger = logging.getLogger(__name__)

# Глобальный объект конфигурации, который будет использоваться во всем приложении
config = configparser.ConfigParser()
CONFIG_FILE_PATH = 'settings.ini'

def load_config():
    """
    Синхронно загружает конфигурацию из файла settings.ini при запуске.
    Если файл не существует, создает его с настройками по умолчанию.
    """
    if not os.path.exists(CONFIG_FILE_PATH):
        logger.warning(f"Файл конфигурации '{CONFIG_FILE_PATH}' не найден. Создание нового файла.")
        config['User'] = {
            'TOKEN': 'your_token_here',
            'ADMIN_CHAT_ID': 'your_admin_chat_id_here',
        }
        config['Settings'] = {
            'EXCHANGE_RATE': '41.2',
            'ADMIN_PASSWORD': 'your_admin_password_here',
            'WALLET_ADDRESS': 'your_wallet_address_here',
            'SUPPORT_CONTACT': 'your_support_contact_here'
        }
        try:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as config_file:
                config.write(config_file)
            logger.info(f"Файл конфигурации '{CONFIG_FILE_PATH}' создан. Пожалуйста, отредактируйте его и перезапустите бота.")
            print(f"Файл конфигурации '{CONFIG_FILE_PATH}' создан. Пожалуйста, укажите ваш токен и ID администратора, затем перезапустите скрипт.")
            input("Нажмите Enter для выхода...")
            exit(0)
        except IOError as e:
            logger.error(f"Не удалось создать файл конфигурации: {e}")
            exit(1)
    else:
        config.read(CONFIG_FILE_PATH, encoding='utf-8')
        logger.info(f"Файл конфигурации '{CONFIG_FILE_PATH}' успешно загружен.")

def _save_config_sync():
    """Синхронная функция для записи конфигурации в файл."""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as config_file:
            config.write(config_file)
        logger.info("Конфигурация успешно сохранена в файл.")
    except IOError as e:
        logger.error(f"Ошибка при сохранении конфигурации в файл: {e}")

async def save_config():
    """
    Асинхронно сохраняет текущую конфигурацию в файл, не блокируя event loop.
    """
    loop = asyncio.get_running_loop()
    # Запускаем блокирующую операцию записи в отдельном потоке
    await loop.run_in_executor(None, _save_config_sync)

def get_admin_ids():
    """Читает и возвращает список ID администраторов из загруженной конфигурации."""
    admin_ids_str = config['User'].get('admin_chat_id', '')
    if not admin_ids_str:
        return []
    try:
        return [int(admin_id.strip()) for admin_id in admin_ids_str.split(',')]
    except ValueError:
        logger.error("Ошибка в формате ADMIN_CHAT_ID. Убедитесь, что это список чисел, разделенных запятыми.")
        return []