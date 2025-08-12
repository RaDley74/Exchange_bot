# SafePay Bot | Currency Exchange Telegram Bot

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

A feature-rich Telegram bot designed to automate the currency exchange process (e.g., USDT to fiat). This project features a comprehensive admin panel, a referral system, user profile management, and a sophisticated request-handling workflow.

This is not just a simple bot, but a robust and reliable software system, engineered with modern development best practices in mind.

---

### Demo

![Bot Demo GIF](https://i.imgur.com/amg3683.gif)

---

## 🚀 Features

### 💱 Core Exchange Workflow
*   A multi-step, guided conversation to create a new exchange request.
*   Automatic calculation of the final amount based on the current exchange rate.
*   Option to use previously saved payment details or enter new ones.
*   A special workflow for users needing TRX for gas fees: the bot deducts a fixed amount from the exchange total and notifies the administrator.
*   Automatically saves user payment details to their profile after the first successful exchange.

### ⚙️ Admin Panel
*   **Secure Access:** Protected by a password and an admin ID whitelist.
*   **Bot Management:** Globally enable or disable the bot for maintenance.
*   **Real-time Configuration:** Update the exchange rate, wallet address, or support contact without restarting the bot.
*   **Request Search:** Find active requests by user ID or Telegram username.
*   **Manual Request Management:** Manually advance a request through its workflow (e.g., confirm payment received, mark as completed).
*   **Request Restoration:** A critical feature to resend all status messages to the user and admins if something goes wrong.
*   **Request Cancellation:** Decline a request with an optional reason sent to the user.

### 🏆 Referral System
*   Generates a unique referral link for each user.
*   Automatically credits a bonus to the referrer's balance after their referral completes their first successful exchange.
*   A paginated view of all referred users.

### 👤 User Cabinet
*   View saved payment details and current referral balance.
*   A dedicated conversation flow to edit and update all saved profile information.

---

## 🛠️ Architecture & Technical Highlights

This project was built with a strong emphasis on reliability, scalability, and code quality.

*   **Modular Architecture:** The codebase is logically separated into independent components (`handlers`, `managers`), making it easy to understand, maintain, and extend.
*   **Object-Oriented Design:** All functionality is encapsulated within classes, ensuring low coupling and high code reusability.
*   **Robust Database Management:** The `DatabaseManager` features **automatic schema migration**. When new fields are added to the code, the corresponding database columns are created automatically on startup, preventing errors during updates.
*   **Advanced State Management:** Leverages the `ConversationHandler` from `python-telegram-bot` to create complex, multi-step dialogues for both users and administrators.
*   **Clean Configuration Management:** The `ConfigManager` allows for easy management of all bot settings via a `settings.ini` file and supports asynchronous saving of changes made from the admin panel.
*   **Fully Asynchronous:** The project is built on `async`/`await`, ensuring high performance and a non-blocking, responsive bot.

---

## 💻 Tech Stack

*   **Language:** Python 3.10+
*   **Telegram Framework:** `python-telegram-bot`
*   **Database:** SQLite
*   **Logging:** `logging`

---

## 🔧 Getting Started

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your_username/your_repository_name.git
    cd your_repository_name
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # For Windows:
    venv\Scripts\activate
    # For macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies from `requirements.txt`:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure your bot:**
    Create a `settings.ini` file in the root directory by copying the contents of a template or creating it from scratch.

    **settings.ini**
    ```ini
    [User]
    TOKEN = your_token_from_BotFather
    ADMIN_CHAT_ID = your_telegram_id,another_admin_id

    [Settings]
    EXCHANGE_RATE = 41.5
    ADMIN_PASSWORD = your_secret_password
    WALLET_ADDRESS = your_usdt_wallet_address
    SUPPORT_CONTACT = @your_support_username
    BOT_ENABLED = True
    ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

---

