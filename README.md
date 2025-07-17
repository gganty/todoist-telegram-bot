# Todoist Telegram Bot

This project is a simple Telegram bot that helps you add tasks to your Todoist account. It uses the [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) library for Telegram integration and Todoist's REST API for task management.

## Features

- **Conversation based task creation.** The bot guides you through entering the task title, description, project, priority and deadline.
- **Customizable steps.** Use the `/settings` command to toggle which details you want to provide when adding tasks.
- **Multilingual interface.** The `/language` command lets you switch between English and Russian.
- **API key management.** Your Todoist API token is stored locally and can be changed with the `/change_api` command.

## Requirements

- Python 3.8+
- A Telegram bot token stored in `secret.txt` (one line with the token)
- A Todoist API key for each user

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

1. Place your Telegram bot token in a file named `secret.txt` in the project root.
2. Run the bot:

```bash
python main.py
```

3. Open a chat with your bot in Telegram and use `/start` to begin. You will be asked for your Todoist API key and then guided through task creation.

## Repository Structure

- `main.py` – entry point that starts the bot and sets up command handlers.
- `func.py` – core conversation logic and helper functions for interacting with Todoist and the SQLite database.
- `lang.py` – language dictionaries used for the English and Russian messages.
- `update.py` – helper functions for database migrations.
- `requirements.txt` – Python dependencies.

The SQLite database `user_data.db` is created automatically to store user information.

## License

This project is provided as-is without any warranty.
