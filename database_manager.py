# database_manager.py

import sqlite3
import logging
import json

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages all database operations for the bot.
    Uses SQLite to store and retrieve exchange requests and user profiles.
    """

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

    def _add_missing_columns(self):
        """Adds missing columns to the exchange_requests table for backward compatibility."""
        try:
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA table_info(exchange_requests);")
            columns = [row['name'] for row in cursor.fetchall()]

            if 'card_number' not in columns:
                cursor.execute("ALTER TABLE exchange_requests ADD COLUMN card_number TEXT;")
                logger.info(
                    "[System] - Successfully added 'card_number' column to 'exchange_requests' table.")

            if 'exchange_rate' not in columns:
                cursor.execute("ALTER TABLE exchange_requests ADD COLUMN exchange_rate REAL;")
                logger.info(
                    "[System] - Successfully added 'exchange_rate' column to 'exchange_requests' table.")

            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to add missing columns: {e}")
            self._conn.rollback()

    def _add_missing_profile_columns(self):
        """Adds missing columns to the user_profiles table for backward compatibility."""
        try:
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA table_info(user_profiles);")
            columns = [row['name'] for row in cursor.fetchall()]

            if 'username' not in columns:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN username TEXT;")
                logger.info(
                    "[System] - Successfully added 'username' column to 'user_profiles' table.")

            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to add missing columns to user_profiles: {e}")
            self._conn.rollback()

    def setup_database(self):
        """
        Creates the necessary tables if they don't exist.
        Should be called once at bot startup.
        """
        if not self._conn:
            self.connect()

        create_exchange_table_query = """
        CREATE TABLE IF NOT EXISTS exchange_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, username TEXT, status TEXT NOT NULL,
            currency TEXT, amount_currency REAL, amount_uah REAL, exchange_rate REAL, bank_name TEXT,
            card_info TEXT, card_number TEXT, fio TEXT, inn TEXT, trx_address TEXT,
            needs_trx BOOLEAN DEFAULT 0, transaction_hash TEXT, admin_message_ids TEXT,
            user_message_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        create_profiles_table_query = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            bank_name TEXT,
            card_info TEXT,
            card_number TEXT,
            fio TEXT,
            inn TEXT,
            updated_at TIMESTAMP
        );
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(create_exchange_table_query)
            cursor.execute(create_profiles_table_query)
            self._conn.commit()
            logger.info(
                "[System] - Database setup complete. Tables 'exchange_requests' and 'user_profiles' are ready.")
            self._add_missing_columns()
            self._add_missing_profile_columns()
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to create tables: {e}")
            self._conn.rollback()

    def create_exchange_request(self, user, user_data):
        """
        Creates a new exchange request and automatically saves/updates the user's profile.
        """
        query = """
        INSERT INTO exchange_requests 
        (user_id, username, status, currency, amount_currency, amount_uah, exchange_rate, bank_name, card_info, card_number, fio, inn, needs_trx, trx_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            user.id, user.username, 'awaiting payment', user_data.get(
                'currency'), user_data.get('amount'),
            user_data.get('sum_uah'), user_data.get('exchange_rate'), user_data.get('bank_name'),
            user_data.get('card_info'), user_data.get('card_number'), user_data.get('fio'),
            user_data.get('inn'), 'trx_address' in user_data, user_data.get('trx_address')
        )
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            request_id = cursor.lastrowid
            logger.info(
                f"[Uid] ({user.id}, {user.username}) - Created new exchange request with ID: {request_id}")

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

    def create_or_update_user_profile(self, user_id, profile_data: dict):
        """
        Creates a new user profile or updates an existing one with new data.
        """
        update_data = {k: v for k, v in profile_data.items() if v is not None}
        if not update_data:
            return

        operation = ""
        try:
            cursor = self._conn.cursor()
            # Use a separate query to check existence, not relying on the public get_user_profile
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
        Returns a dict-like Row object or None.
        """
        query = "SELECT * FROM exchange_requests WHERE id = ?"
        cursor = self._conn.cursor()
        cursor.execute(query, (request_id,))
        return dict(cursor.fetchone())

    def get_request_by_user_id(self, user_id):
        """
        Retrieves an active exchange request for a given user ID.
        Returns a dict-like Row object or None.
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
        Returns a list of dict-like Row objects.
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

    # --- START OF RESTORED METHOD ---
    def update_request_data(self, request_id, data: dict):
        """
        Updates multiple fields of a request.
        :param request_id: The ID of the request to update.
        :param data: A dictionary where keys are column names and values are the new values.
        """
        if 'id' in data:
            del data['id']

        if not data:
            logger.warning(
                f"[System] - update_request_data called with no data for request {request_id}.")
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
    # --- END OF RESTORED METHOD ---
