
import configparser
import os

config_file_name = 'settings.ini'
if not os.path.exists(config_file_name):
    config = configparser.ConfigParser()
    config['User'] = {
        'TOKEN': 'your_token_here',
        'ADMIN_CHAT_ID': 'your_admin_chat_id_here',
    }
    config['Settings'] = {
        'EXCHANGE_RATE': 41.2,
    }

    with open(config_file_name, 'w') as config_file:
        config.write(config_file)

    print(
        f"Configuration file '{config_file_name}' created. Please edit it with your token and admin chat ID, then restart the script.")
    exit(0)


def main():
    print("Hello, World!")
    # Add your code here


if __name__ == "__main__":
    main()
