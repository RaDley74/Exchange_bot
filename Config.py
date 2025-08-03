import configparser


class Config:
    def __init__(self):
        self.config_file = "settings.ini"
        self.config = configparser.ConfigParser()
        self._load_from_file(self.config_file)

    def get_token(self):
        return self.token

    def get_admin_chat_id(self):
        return self.admin_chat_id

    def get_admin_password(self):
        return self.admin_password

    def get_exchange_rate(self):
        return self.exchange_rate

    def get_wallet_address(self):
        return self.wallet_address

    def get_support_contact(self):
        return self.support_contact

    def set_token(self, token):
        self.config.set("User", "token", token)
        self.token = token
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def set_admin_chat_id(self, admin_chat_id):
        self.config.set("User", "admin_chat_id", int(admin_chat_id))
        self.admin_chat_id = admin_chat_id
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def set_admin_password(self, admin_password):
        self.config.set("Settings", "admin_password", admin_password)
        self.admin_password = admin_password
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def set_exchange_rate(self, exchange_rate):
        self.config.set("Settings", "exchange_rate", str(exchange_rate))
        self.exchange_rate = exchange_rate
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def set_wallet_address(self, wallet_address):
        self.config.set("Settings", "wallet_address", wallet_address)
        self.wallet_address = wallet_address
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def set_support_contact(self, support_contact):
        self.config.set("Settings", "support_contact", support_contact)
        self.support_contact = support_contact
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def _load_from_file(self, config_file_name="settings.ini"):
        self.config.read(config_file_name)

        self.token = self.config.get("User", "token", fallback="")
        self.admin_chat_id = self.config.get("User", "admin_chat_id", fallback="")
        self.admin_password = self.config.get("Settings", "admin_password", fallback="")
        self.exchange_rate = self.config.get("Settings", "exchange_rate", fallback="")
        self.wallet_address = self.config.get("Settings", "wallet_address", fallback="")
        self.support_contact = self.config.get("Settings", "support_contact", fallback="")

    def read_config(self, config_file_name="settings.ini"):
        return self._load_from_file(config_file_name)
