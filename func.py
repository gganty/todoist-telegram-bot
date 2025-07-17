import sqlite3
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes, ConversationHandler
)
import aiohttp
from datetime import datetime

# DB connection
def connect_db():
    return sqlite3.connect('user_data.db', check_same_thread=False)

ASK_API_KEY, ASK_TASK, ASK_DESCRIPTION, ASK_PROJECT, ASK_PRIORITY, ASK_DEADLINE = range(6)


"""
USER DATA MANAGEMENT
"""

# Get user data
def get_user_data(user_id: int) -> dict:
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM user_data WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        settings_str = row[7] if len(row) > 7 and row[7] else '{}'
        settings = json.loads(settings_str) if settings_str else {}
        # Преобразуем значения настроек в целые числа
        settings = {k: int(v) for k, v in settings.items()}
        return {
            "user_id": row[0],
            "api_key": row[1],
            "task": row[2],
            "description": row[3],
            "project_id": row[4],
            "priority": row[5],
            "deadline": row[6],
            "settings": settings
        }
    return {"settings": {}}


# Saving user data
def save_user_data(user_id: int, data) -> None:
    conn = connect_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO user_data (user_id, api_key, task, description, project_id,
                               priority, deadline, settings)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            api_key=excluded.api_key,
            task=excluded.task,
            description=excluded.description,
            project_id=excluded.project_id,
            priority=excluded.priority,
            deadline=excluded.deadline,
            settings=excluded.settings
    ''', (
        user_id,
        data.get("api_key"),
        data.get("task"),
        data.get("description"),
        data.get("project_id"),
        data.get("priority"),
        data.get("deadline"),
        json.dumps(data.get("settings", {}))
    ))
    conn.commit()
    conn.close()


# API key saver
async def save_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    api_key = update.message.text

    if len(api_key) == 40:
        user_data = get_user_data(user_id)
        user_data["api_key"] = api_key
        save_user_data(user_id, user_data)
        await update.message.reply_text("Ключ сохранён, теперь пришлите текст задачи, которую хотите добавить.")
        return ASK_TASK
    else:
        await update.message.reply_text("Ошибка формата ключа API. Пожалуйста, отправьте корректный ключ.")
        return ASK_API_KEY


# /settings handler
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    blocks = ['description', 'project', 'priority', 'deadline']
    block_names = {
        'description': 'Описание',
        'project': 'Проект',
        'priority': 'Приоритет',
        'deadline': 'Дедлайн'
    }

    settings = user_data.get('settings', {})
    settings = {k: int(v) for k, v in settings.items()}
    for block in blocks:
        if block not in settings:
            settings[block] = 1  # Turned on by default

    keyboard = []
    for block in blocks:
        state = settings.get(block, 1)
        emoji = '✅' if state else '❌'
        button_text = f"{block_names[block]} {emoji}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=block)])

    keyboard.append([InlineKeyboardButton("Готово", callback_data='done')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Настройки блоков:", reply_markup=reply_markup)


# Processing clicks in settings section
async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    settings = user_data.get('settings', {})
    settings = {k: int(v) for k, v in settings.items()}

    blocks = ['description', 'project', 'priority', 'deadline']
    block_names = {
        'description': 'Описание',
        'project': 'Проект',
        'priority': 'Приоритет',
        'deadline': 'Дедлайн'
    }

    await query.answer()

    if query.data == 'done':
        await query.edit_message_text("Настройки сохранены.")
        return
    else:
        block = query.data
        current_state = settings.get(block, 1)
        settings[block] = 0 if current_state else 1
        user_data['settings'] = settings
        save_user_data(user_id, user_data)  # Saving settings after every change

        keyboard = []
        for b in blocks:
            state = settings.get(b, 1)
            emoji = '✅' if state else '❌'
            button_text = f"{block_names[b]} {emoji}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=b)])

        keyboard.append([InlineKeyboardButton("Готово", callback_data='done')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)


# Changing API key
async def change_api(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    user_data["api_key"] = None
    save_user_data(user_id, user_data)
    await update.message.reply_text("Пришлите Ваш новый ключ API для Todoist в чат.")
    return ASK_API_KEY



"""
CHAT MANAGEMENT
"""

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if user_data and "api_key" in user_data and user_data["api_key"]:
        await update.message.reply_text("Добро пожаловать обратно!\n\nВы можете продолжить добавление задач.")
        return ASK_TASK
    else:
        await update.message.reply_text("Пришлите Ваш ключ API для Todoist в чат.")
        return ASK_API_KEY


# Title handler
async def handle_task_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if not user_data.get("api_key"):
        await update.message.reply_text("Пожалуйста, используйте команду /start, чтобы ввести ключ API.")
        return ASK_API_KEY

    if update.message.text and not update.message.photo:
        user_data["task"] = update.message.text
        save_user_data(user_id, user_data)
        settings = user_data.get('settings', {})
        if settings.get('description', 1):
            await update.message.reply_text("Напишите описание задачи. Если хотите оставить его пустым - напишите None")
            return ASK_DESCRIPTION
        elif settings.get('project', 1):
            return await ask_project(update, context, user_data)
        elif settings.get('priority', 1):
            return await ask_priority(update, context, user_data)
        elif settings.get('deadline', 1):
            await update.message.reply_text(
                "Напишите дедлайн для этой задачи в чат. Если дедлайн не требуется - отправьте точку.\n\n"
                "Дедлайн должен вводиться в формате ДД/ММ/ГГГГ ЧЧ:ММ или ДД/ММ/ГГГГ"
            )
            return ASK_DEADLINE
        else:
            return await add_task(update, context)
    else:
        await update.message.reply_text("Пожалуйста, отправьте текст задачи без изображения.")
        return ASK_TASK


# Project choice asker
async def ask_project(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data) -> int:
    api_key = user_data["api_key"]
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.todoist.com/rest/v2/projects",
            headers={"Authorization": f"Bearer {api_key}"}
        ) as response:
            if response.status != 200:
                await update.message.reply_text("Ошибка при получении списка проектов. Попробуйте снова позже.")
                return ASK_TASK
            projects = await response.json()
    keyboard = []
    for project in projects:
        keyboard.append([InlineKeyboardButton(project['name'], callback_data=project['id'])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите проект:", reply_markup=reply_markup)
    return ASK_PROJECT


# Project choice handler
async def handle_project_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.callback_query.from_user.id
    user_data = get_user_data(user_id)
    query = update.callback_query
    await query.answer()
    project_id = query.data
    if not user_data.get("api_key"):
        await query.edit_message_text("Пожалуйста, используйте команду /start, чтобы ввести ключ API.")
        return ASK_API_KEY

    user_data["project_id"] = project_id
    save_user_data(user_id, user_data)
    settings = user_data.get('settings', {})
    if settings.get('priority', 1):
        return await ask_priority(update, context, user_data)
    elif settings.get('deadline', 1):
        await query.edit_message_text(
            "Напишите дедлайн для этой задачи в чат. Если дедлайн не требуется - отправьте точку.\n\n"
            "Дедлайн должен вводиться в формате ДД/ММ/ГГГГ ЧЧ:ММ или ДД/ММ/ГГГГ"
        )
        return ASK_DEADLINE
    else:
        await add_task(update, context, query=True)
        return ASK_TASK


# Priority asker
async def ask_priority(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data) -> int:
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="4"),
            InlineKeyboardButton("2", callback_data="3"),
            InlineKeyboardButton("3", callback_data="2")
        ],
        [InlineKeyboardButton("Без приоритета", callback_data="1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("Выберите приоритет задачи:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("Выберите приоритет задачи:", reply_markup=reply_markup)
    return ASK_PRIORITY



# Priority handler
async def handle_priority_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.callback_query.from_user.id
    user_data = get_user_data(user_id)
    query = update.callback_query
    await query.answer()
    if not user_data.get("api_key"):
        await query.edit_message_text("Пожалуйста, используйте команду /start, чтобы ввести ключ API.")
        return ASK_API_KEY

    priority = query.data
    user_data["priority"] = int(priority)
    save_user_data(user_id, user_data)
    settings = user_data.get('settings', {})
    if settings.get('deadline', 1):
        await query.edit_message_text(
            "Напишите дедлайн для этой задачи в чат. Если дедлайн не требуется - отправьте точку.\n\n"
            "Дедлайн должен вводиться в формате ДД/ММ/ГГГГ ЧЧ:ММ или ДД/ММ/ГГГГ"
        )
        return ASK_DEADLINE
    else:
        await add_task(update, context, query=True)
        return ASK_TASK


# Deadline handler
async def handle_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if not user_data.get("api_key"):
        await update.message.reply_text("Пожалуйста, используйте команду /start, чтобы ввести ключ API.")
        return ASK_API_KEY

    deadline = update.message.text
    if deadline == ".":
        user_data["deadline"] = None
        await update.message.reply_text("Установка дедлайна пропущена.")
    else:
        try:
            if ":" in deadline:
                datetime.strptime(deadline, "%d/%m/%Y %H:%M")
            else:
                datetime.strptime(deadline, "%d/%m/%Y")
            user_data["deadline"] = deadline
            await update.message.reply_text("Дедлайн установлен.")
        except ValueError:
            await update.message.reply_text("Неправильный формат даты. Попробуйте снова.")
            return ASK_DEADLINE

    save_user_data(user_id, user_data)
    await add_task(update, context)
    return ASK_TASK


# Description handler
async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if not user_data.get("api_key"):
        await update.message.reply_text("Пожалуйста, используйте команду /start, чтобы ввести ключ API.")
        return ASK_API_KEY

    description = update.message.text
    if description.lower() == "none":
        description = ""
    user_data["description"] = description
    save_user_data(user_id, user_data)
    settings = user_data.get('settings', {})
    if settings.get('project', 1):
        return await ask_project(update, context, user_data)
    elif settings.get('priority', 1):
        return await ask_priority(update, context, user_data)
    elif settings.get('deadline', 1):
        await update.message.reply_text(
            "Напишите дедлайн для этой задачи в чат. Если дедлайн не требуется - отправьте точку.\n\n"
            "Дедлайн должен вводиться в формате ДД/ММ/ГГГГ ЧЧ:ММ или ДД/ММ/ГГГГ"
        )
        return ASK_DEADLINE
    else:
        return await add_task(update, context)


"""
ADD TASK
"""


# Adding a task to Todoist
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE, query=False) -> int:
    user_id = update.callback_query.from_user.id if query else update.effective_user.id
    user_data = get_user_data(user_id)

    api_key = user_data["api_key"]
    task_data = {
        "content": user_data["task"]
    }
    if user_data.get('description'):
        task_data["description"] = user_data["description"]
    if user_data.get('project_id'):
        task_data["project_id"] = user_data["project_id"]
    if user_data.get('priority'):
        task_data["priority"] = user_data["priority"]
    if user_data.get('deadline'):
        task_data["due_string"] = user_data["deadline"]

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.todoist.com/rest/v2/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {api_key}"}
        ) as response:
            if response.status in (200, 204):
                message = "Задача успешно добавлена!\nТеперь Вы можете добавить следующую задачу."
                user_data["task"] = None
                user_data["description"] = None
                user_data["project_id"] = None
                user_data["priority"] = None
                user_data["deadline"] = None
                save_user_data(user_id, user_data)
            else:
                message = "Ошибка при добавлении задачи. Попробуйте снова."

    if query:
        await update.callback_query.edit_message_text(message)
    else:
        await update.message.reply_text(message)

    return ASK_TASK
