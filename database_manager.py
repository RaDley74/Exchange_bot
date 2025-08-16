# database_manager.py

import sqlite3
import logging
import json

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages all database operations for the bot.
    Uses SQLite to store and retrieve exchange requests and user profiles.
    This version includes an automatic schema verification to add missing columns.
    """

    TABLE_SCHEMAS = {
        'exchange_requests': {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'user_id': 'INTEGER NOT NULL',
            'username': 'TEXT',
            'status': 'TEXT NOT NULL',
            'currency': 'TEXT',
            'amount_currency': 'REAL',
            'amount_uah': 'REAL',
            'exchange_rate': 'REAL',
            'bank_name': 'TEXT',
            'card_info': 'TEXT',
            'card_number': 'TEXT',
            'fio': 'TEXT',
            'inn': 'TEXT',
            'trx_address': 'TEXT',
            'needs_trx': 'BOOLEAN DEFAULT 0',
            'transaction_hash': 'TEXT',
            'admin_message_ids': 'TEXT',
            'user_message_id': 'INTEGER',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'referral_payout_amount': 'REAL DEFAULT 0.0'
        },
        'user_profiles': {
            'user_id': 'INTEGER PRIMARY KEY',
            'username': 'TEXT',
            'bank_name': 'TEXT',
            'card_info': 'TEXT',
            'card_number': 'TEXT',
            'fio': 'TEXT',
            'inn': 'TEXT',
            'referral_balance': 'REAL DEFAULT 0.0',
            'vip_status': 'TEXT DEFAULT NULL',
            'updated_at': 'TIMESTAMP'
        },
        'referrals': {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'referrer_id': 'INTEGER NOT NULL',
            'referred_id': 'INTEGER NOT NULL UNIQUE',
            'referred_username': 'TEXT',
            'is_credited': 'BOOLEAN DEFAULT 0',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
    }

    def __init__(self, db_path=r'database/SafePay_bot.db'):
        """
        Initializes the database manager.
        :param db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._conn = None

    def connect(self):
        """Establishes a connection to the database."""
        try:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            logger.info("[System] - Successfully connected to the database.")
        except sqlite3.Error as e:
            logger.error(f"[System] - Database connection error: {e}")
            raise

    def close(self):
        """Closes the database connection."""
        if self._conn:
            self._conn.close()
            logger.info("[System] - Database connection closed.")

    def _verify_and_add_columns(self):
        """
        Verifies each table in the schema, finds missing columns, and adds them.
        This replaces older, table-specific _add_missing_columns functions.
        """
        try:
            cursor = self._conn.cursor()
            for table_name, schema_columns in self.TABLE_SCHEMAS.items():
                cursor.execute(f"PRAGMA table_info({table_name});")
                existing_columns = {row['name'] for row in cursor.fetchall()}

                for column_name, column_type in schema_columns.items():
                    if column_name not in existing_columns:
                        try:
                            cursor.execute(
                                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};")
                            logger.info(
                                f"[System] - Schema migration: Successfully added column '{column_name}' to table '{table_name}'.")
                        except sqlite3.OperationalError as e:
                            logger.error(
                                f"[System] - Could not add column '{column_name}' to '{table_name}'. It might have constraints not supported by ALTER TABLE (e.g., PRIMARY KEY). Error: {e}")

            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"[System] - An error occurred during schema verification: {e}")
            self._conn.rollback()

    def setup_database(self):
        """
        Creates necessary tables if they don't exist, then verifies
        and adds any missing columns according to TABLE_SCHEMAS.
        """
        if not self._conn:
            self.connect()

        try:
            cursor = self._conn.cursor()
            for table_name, schema_columns in self.TABLE_SCHEMAS.items():
                columns_defs = [f"'{name}' {typedef}" for name, typedef in schema_columns.items()]
                create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns_defs)});"
                cursor.execute(create_table_query)

            self._conn.commit()
            logger.info("[System] - Initial table creation check complete.")

            self._verify_and_add_columns()

            logger.info(
                "[System] - Database setup and schema verification complete. All tables are up-to-date.")

        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to setup database schema: {e}")
            self._conn.rollback()

    def create_exchange_request(self, user, user_data):
        """
        Creates a new exchange request and automatically saves/updates the user's profile.
        """
        query = """
        INSERT INTO exchange_requests 
        (user_id, username, status, currency, amount_currency, amount_uah, exchange_rate, bank_name, card_info, card_number, fio, inn, needs_trx, trx_address, referral_payout_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            user.id, user.username, 'awaiting payment', user_data.get(
                'currency'), user_data.get('amount'),
            user_data.get('sum_uah'), user_data.get('exchange_rate'), user_data.get('bank_name'),
            user_data.get('card_info'), user_data.get('card_number'), user_data.get('fio'),
            user_data.get('inn'), 'trx_address' in user_data, user_data.get('trx_address'),
            user_data.get('total_referral_debit', 0.0)
        )
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            request_id = cursor.lastrowid
            logger.info(
                f"[Uid] ({user.id}, {user.username}) - Created new exchange request with ID: {request_id}")

            if user_data.get('total_referral_debit', 0.0) > 0:
                self.update_referral_balance(user.id, -user_data['total_referral_debit'])

            profile_data = {
                'username': user.username,
                'bank_name': user_data.get('bank_name'),
                'card_info': user_data.get('card_info'),
                'card_number': user_data.get('card_number'),
                'fio': user_data.get('fio'),
                'inn': user_data.get('inn')
            }
            self.create_or_update_user_profile(user.id, profile_data)

            self._conn.commit()
            return request_id
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to create exchange request for user {user.id}: {e}")
            self._conn.rollback()
            return None

    def get_user_profile(self, user_id):
        """
        Retrieves a user's saved profile by their ID and returns it as a dictionary.
        """
        query = "SELECT * FROM user_profiles WHERE user_id = ?"
        cursor = self._conn.cursor()
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_profile_by_id_or_login(self, user_id_or_login: str):
        """
        Retrieves a user profile by their numeric ID or username string.
        """
        cursor = self._conn.cursor()
        if user_id_or_login.isdigit():
            query = "SELECT * FROM user_profiles WHERE user_id = ?"
            params = (int(user_id_or_login),)
        else:
            query = "SELECT * FROM user_profiles WHERE username = ?"
            params = (user_id_or_login.lstrip('@'),)

        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_or_update_user_profile(self, user_id, profile_data: dict):
        """
        Creates a new user profile or updates an existing one with new data.
        """
        # update_data = {k: v for k, v in profile_data.items() if v is not None}
        update_data = profile_data
        if not update_data:
            return

        operation = ""
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT 1 FROM user_profiles WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone()

            if exists:
                operation = "update"
                set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
                query = f"UPDATE user_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
                params = list(update_data.values()) + [user_id]
            else:
                operation = "insert"
                update_data['user_id'] = user_id
                if 'referral_balance' not in update_data:
                    update_data['referral_balance'] = 0.0
                columns = ", ".join(update_data.keys())
                placeholders = ", ".join(["?"] * len(update_data))
                query = f"INSERT INTO user_profiles ({columns}, updated_at) VALUES ({placeholders}, CURRENT_TIMESTAMP)"
                params = list(update_data.values())

            cursor.execute(query, tuple(params))
            self._conn.commit()
            logger.info(
                f"[System] - Successfully {operation}d profile for user {user_id} with data: {list(update_data.keys())}.")
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to {operation} profile for user {user_id}: {e}")
            self._conn.rollback()

    def get_request_by_id(self, request_id):
        """
        Retrieves a single exchange request by its primary key ID.
        """
        query = "SELECT * FROM exchange_requests WHERE id = ?"
        cursor = self._conn.cursor()
        cursor.execute(query, (request_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_request_by_user_id(self, user_id):
        """
        Retrieves an active exchange request for a given user ID.
        """
        query = '''
        SELECT * FROM exchange_requests 
        WHERE user_id = ? 
        AND status NOT IN ('declined', 'completed', 'funds sent', 'new')
        '''
        cursor = self._conn.cursor()
        cursor.execute(query, (user_id,))
        return cursor.fetchone()

    def get_request_by_user_id_or_login(self, user_id_or_login):
        """
        Retrieves all active requests for a user by their ID or username.
        """
        if user_id_or_login.isdigit():
            query = '''
            SELECT * FROM exchange_requests 
            WHERE user_id = ? 
            AND status NOT IN ('declined', 'completed', 'funds sent', 'new')
            '''
            params = (int(user_id_or_login),)
        else:
            user_name = user_id_or_login.replace("@", "").strip()
            query = '''
            SELECT * FROM exchange_requests 
            WHERE username = ? 
            AND status NOT IN ('declined', 'completed', 'funds sent', 'new')
            '''
            params = (user_name,)

        cursor = self._conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def update_request_status(self, request_id, status):
        """Updates the status of a request."""
        query = "UPDATE exchange_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (status, request_id))
            self._conn.commit()
            logger.info(f"[System] - Updated status for request {request_id} to '{status}'.")
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to update status for request {request_id}: {e}")
            self._conn.rollback()

    def update_request_data(self, request_id, data: dict):
        """
        Updates multiple fields of a request.
        """
        if 'id' in data:
            del data['id']
        if not data:
            return

        fields = ", ".join([f"{key} = ?" for key in data.keys()])
        values = list(data.values())
        query = f"UPDATE exchange_requests SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        values.append(request_id)

        try:
            cursor = self._conn.cursor()
            cursor.execute(query, tuple(values))
            self._conn.commit()
            logger.info(
                f"[System] - Updated data for request {request_id}. Fields: {list(data.keys())}")
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to update data for request {request_id}: {e}")
            self._conn.rollback()

    def create_referral(self, referrer_id: int, referred_id: int, referred_username: str):
        """Creates a new referral record."""
        query = "INSERT INTO referrals (referrer_id, referred_id, referred_username) VALUES (?, ?, ?)"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (referrer_id, referred_id, referred_username))
            self._conn.commit()
        except sqlite3.IntegrityError:
            logger.warning(
                f"Attempt to create a duplicate referral record for referred_id: {referred_id}")
        except sqlite3.Error as e:
            logger.error(
                f"Failed to create referral record for {referrer_id} -> {referred_id}: {e}")
            self._conn.rollback()

    def get_referral_by_referred_id(self, referred_id: int):
        """Gets a referral record by the referred user's ID."""
        query = "SELECT * FROM referrals WHERE referred_id = ?"
        cursor = self._conn.cursor()
        cursor.execute(query, (referred_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_referrals_by_referrer_id(self, referrer_id: int, page: int = 1, page_size: int = 10) -> tuple[list, int]:
        """
        Gets a paginated list of referrals for a given user.
        Returns a tuple: (list of referrals on the current page, total number of pages).
        """
        cursor = self._conn.cursor()
        offset = (page - 1) * page_size

        list_query = "SELECT * FROM referrals WHERE referrer_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
        cursor.execute(list_query, (referrer_id, page_size, offset))
        referrals_on_page = [dict(row) for row in cursor.fetchall()]

        count_query = "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?"
        cursor.execute(count_query, (referrer_id,))
        total_count = cursor.fetchone()[0]

        if total_count == 0:
            total_pages = 1
        else:
            total_pages = (total_count + page_size - 1) // page_size

        return referrals_on_page, total_pages

    def get_referral_count_by_referrer_id(self, referrer_id: int) -> int:
        """Counts the total number of referrals for a given referrer."""
        query = "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?"
        cursor = self._conn.cursor()
        cursor.execute(query, (referrer_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def update_referral_balance(self, user_id: int, amount_to_add: float):
        """Updates a user's referral balance."""
        query = "UPDATE user_profiles SET referral_balance = referral_balance + ? WHERE user_id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (amount_to_add, user_id))
            self._conn.commit()
            logger.info(f"Updated referral balance for user {user_id} by {amount_to_add}")
        except sqlite3.Error as e:
            logger.error(f"Failed to update referral balance for user {user_id}: {e}")
            self._conn.rollback()

    def update_referral_as_credited(self, referred_id: int):
        """Marks a referral as credited."""
        query = "UPDATE referrals SET is_credited = 1 WHERE referred_id = ?"
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, (referred_id,))
            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to mark referral {referred_id} as credited: {e}")
            self._conn.rollback()

    def get_user_completed_request_count(self, user_id: int) -> int:
        """Counts the number of completed requests for a user."""
        query = "SELECT COUNT(*) FROM exchange_requests WHERE user_id = ? AND status = 'completed'"
        cursor = self._conn.cursor()
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
