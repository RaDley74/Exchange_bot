# SafePay Telegram Exchange Bot

A robust Telegram bot designed to facilitate cryptocurrency exchanges (USDT to UAH) through a secure, multi-step process involving user and administrator confirmations. The bot is built with a clear separation of concerns, featuring a comprehensive admin panel for real-time management and a persistent configuration system.

## Features

-   **User-Friendly Exchange Flow**: An intuitive, conversational interface guides the user through the exchange process.
-   **Admin-Verified Transactions**: Every exchange is a multi-step process requiring administrator approval at critical stages, ensuring security and control.
-   **TRX Fee Assistance**: An optional feature allows users to request a small amount of TRX (deducted from the total) to cover network transaction fees.
-   **Secure Admin Panel**: A password-protected dashboard for administrators, accessible via a specific command (`/a`).
-   **Dynamic Configuration**: Bot settings like exchange rates, wallet addresses, and admin passwords can be changed on-the-fly from the admin panel without restarting the bot.
-   **External Configuration File**: All critical settings are stored in a `settings.ini` file, keeping them separate from the source code. The bot automatically generates this file on the first run.
-   **Multi-Admin Support**: The bot can notify and be managed by multiple administrators simultaneously.
-   **Persistent User Sessions**: The bot tracks the state of each exchange, so if a user or admin action is pending, the context is not lost.
-   **Detailed Logging**: Comprehensive logging to a `bot.log` file helps with monitoring and debugging.

## How It Works

The exchange process is designed to be secure and transparent for both the user and the administrator.

1.  **Initiation**: The user starts an exchange, specifies the amount of USDT, and provides their bank details (Bank Name, Card/IBAN, Full Name, INN).
2.  **Admin Notification**: All administrators receive a notification with the full details of the new exchange request.
3.  **TRX for Commission (Optional)**: If the user needs TRX for the transfer fee, they can request it. An admin must first confirm sending the TRX before the process continues.
4.  **User Sends Crypto**: The user is prompted to send their USDT to the bot's wallet address and then submit the transaction hash.
5.  **Admin Receives Crypto**: The admin is notified with the transaction hash and must confirm that the funds have been received.
6.  **Admin Sends Fiat**: After confirming receipt of the crypto, the admin sends the equivalent UAH to the user's bank account and marks the transfer as complete in the bot.
7.  **User Confirmation**: The user receives a final message and confirms that they have received the UAH, which closes the transaction.
8.  **Decline Option**: Admins can decline a request at any stage, which notifies the user and cancels the transaction.

## Installation & Setup

### Prerequisites

-   Python 3.8+
-   pip package installer

### 1. Clone the Repository

```bash
git clone https://github.com/RaDley74/Exchange_bot
```

### 2. Install Dependencies

Create a `requirements.txt` file with the following content:

```
python-telegram-bot
```

Then run the installation command:

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

The first time you run the bot, it will detect that `settings.ini` is missing and create it for you.

```bash
python main.py
```

You will see a message in your console prompting you to edit the file. Open `settings.ini` and fill in your details.

**`settings.ini` structure:**

```ini
[User]
TOKEN = your_token_here
ADMIN_CHAT_ID = your_admin_chat_id_here

[Settings]
EXCHANGE_RATE = 41.2
ADMIN_PASSWORD = your_admin_password_here
WALLET_ADDRESS = your_wallet_address_here
SUPPORT_CONTACT = @your_support_username
```

**How to get your details:**
*   `TOKEN`: Get this from the [@BotFather](https://t.me/BotFather) on Telegram when you create a new bot.
*   `ADMIN_CHAT_ID`: This is your personal Telegram user ID. You can get it by messaging the [@userinfobot](https://t.me/userinfobot). If you want to have multiple admins, separate their IDs with a comma (e.g., `12345,67890`).
*   `ADMIN_PASSWORD`: A secure password that you will use to access the admin panel.
*   `WALLET_ADDRESS`: The address of the USDT wallet where users will send their funds.
*   `SUPPORT_CONTACT`: A username or link for users who need help.

### 4. Run the Bot

Once you have saved your settings in `settings.ini`, run the bot again.

```bash
python main.py
```

The bot is now active and polling for updates.

## Usage Guide

### For Users

-   **/start**: Initiates a conversation with the bot and displays the main menu.
-   **Обменять (Exchange)**: Starts the currency exchange wizard.
-   **Курс (Rate)**: Shows the current USDT to UAH exchange rate.
-   **Помощь (Help)**: Displays the support contact.

### For Administrators

-   **/a**: Starts the conversation to access the admin panel. You will be prompted for your password.
-   **/ac**: Closes the admin panel conversation (though it's not strictly necessary as conversations time out).
-   **Interacting with Requests**: When a new exchange request comes in, you will receive a message with inline buttons. Use these buttons to advance the transaction through its various stages (`✅ TRX переведено`, `✅ Средства от клиента получены`, `✅ Перевод клиенту сделан`, `❌ Отказать`).

## File Structure

```
.
├── admin_panel.py      # Logic for the admin panel and settings management.
├── config_manager.py   # Handles loading and saving the settings.ini file.
├── main.py             # Main bot application, user conversation handlers.
├── requirements.txt    # List of Python dependencies.
├── settings.ini        # Configuration file (auto-generated on first run).
└── bot.log             # Log file for debugging and activity tracking.
```
