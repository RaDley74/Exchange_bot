# database_manager.py

import sqlite3
import logging
import json

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages all database operations for the bot.
    Uses SQLite to store and retrieve exchange requests.
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
            # Use Row factory to access columns by name
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
                logger.info("[System] - Successfully added 'card_number' column to 'exchange_requests' table.")

            # --- START OF CHANGE ---
            if 'exchange_rate' not in columns:
                cursor.execute("ALTER TABLE exchange_requests ADD COLUMN exchange_rate REAL;")
                logger.info("[System] - Successfully added 'exchange_rate' column to 'exchange_requests' table.")
            # --- END OF CHANGE ---

            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to add missing columns: {e}")
            self._conn.rollback()

    def setup_database(self):
        """
        Creates the necessary tables if they don't exist.
        Should be called once at bot startup.
        """
        if not self._conn:
            self.connect()

        # The 'status' column is crucial for tracking the request's progress.
        # 'admin_message_ids' will store a JSON string of a dictionary.
        # --- START OF CHANGE ---
        create_table_query = """
        CREATE TABLE IF NOT EXISTS exchange_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            status TEXT NOT NULL,
            currency TEXT,
            amount_currency REAL,
            amount_uah REAL,
            exchange_rate REAL,
            bank_name TEXT,
            card_info TEXT,
            card_number TEXT,
            fio TEXT,
            inn TEXT,
            trx_address TEXT,
            needs_trx BOOLEAN DEFAULT 0,
            transaction_hash TEXT,
            admin_message_ids TEXT,
            user_message_id INTEGER, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        # --- END OF CHANGE ---
        try:
            cursor = self._conn.cursor()
            cursor.execute(create_table_query)
            self._conn.commit()
            logger.info("[System] - Database setup complete. Table 'exchange_requests' is ready.")
            # Add missing columns for older versions
            self._add_missing_columns()
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to create table: {e}")
            self._conn.rollback()

    def create_exchange_request(self, user, user_data):
        """
        Creates a new exchange request in the database.
        :param user: The Telegram user object.
        :param user_data: A dictionary with all the request details.
        :return: The ID of the newly created request.
        """
        # --- START OF CHANGE ---
        query = """
        INSERT INTO exchange_requests 
        (user_id, username, status, currency, amount_currency, amount_uah, exchange_rate, bank_name, card_info, card_number, fio, inn, needs_trx, trx_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            user.id,
            user.username,
            'new',  # Initial status
            user_data.get('currency'),
            user_data.get('amount'),
            user_data.get('sum_uah'),
            user_data.get('exchange_rate'), # Save the rate used for this transaction
            user_data.get('bank_name'),
            user_data.get('card_info'),
            user_data.get('card_number'),
            user_data.get('fio'),
            user_data.get('inn'),
            'trx_address' in user_data,
            user_data.get('trx_address')
        )
        # --- END OF CHANGE ---
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            self._conn.commit()
            request_id = cursor.lastrowid
            logger.info(f"[Uid] ({user.id}, {user.username}) - Created a new exchange request with ID: {request_id}")
            return request_id
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to create exchange request for user {user.id}: {e}")
            self._conn.rollback()
            return None

    def get_request_by_id(self, request_id):
        """
        Retrieves a single exchange request by its primary key ID.
        :param request_id: The ID of the request.
        :return: A dictionary-like Row object or None if not found.
        """
        query = "SELECT * FROM exchange_requests WHERE id = ?"
        cursor = self._conn.cursor()
        cursor.execute(query, (request_id,))
        return cursor.fetchone()

    def get_request_by_user_id(self, user_id):

        query = '''
        SELECT * FROM exchange_requests 
        WHERE user_id = ? 
        AND status NOT IN ('declined', 'completed', 'funds sent', 'new')
        '''
        cursor = self._conn.cursor()
        cursor.execute(query, (user_id,))

        return cursor.fetchone()

    def get_request_by_user_id_or_login(self, user_id_or_login):
        if user_id_or_login.isdigit():
            query = '''
            SELECT * FROM exchange_requests 
            WHERE user_id = ? 
            AND status NOT IN ('declined', 'completed', 'funds sent', 'new')
            '''
            cursor = self._conn.cursor()
            cursor.execute(query, (user_id_or_login,))
        else:
            user_name = user_id_or_login.replace("@", "").strip()
            query = '''
            SELECT * FROM exchange_requests 
            WHERE username = ? 
            AND status NOT IN ('declined', 'completed', 'funds sent', 'new')
            '''
            cursor = self._conn.cursor()
            cursor.execute(query, (user_name,))
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
        :param request_id: The ID of the request to update.
        :param data: A dictionary where keys are column names and values are the new values.
        """
        if 'id' in data:
            del data['id']

        fields = ", ".join([f"{key} = ?" for key in data.keys()])
        values = list(data.values())
        query = f"UPDATE exchange_requests SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        values.append(request_id)

        try:
            cursor = self._conn.cursor()
            cursor.execute(query, tuple(values))
            self._conn.commit()
            logger.info(f"[System] - Updated data for request {request_id}. Fields: {list(data.keys())}")
        except sqlite3.Error as e:
            logger.error(f"[System] - Failed to update data for request {request_id}: {e}")
            self._conn.rollback()