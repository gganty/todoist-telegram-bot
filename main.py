import logging
from func import *
from update import add_settings_column

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Creating a database
conn = connect_db()
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS user_data (
        user_id INTEGER PRIMARY KEY,
        api_key TEXT,
        task TEXT,
        description TEXT,
        project_id TEXT,
        priority INTEGER,
        deadline TEXT,
        settings TEXT
    )
''')
conn.commit()
conn.close()


# main
if __name__ == "__main__":
    # DB table update: check if settings and language columns exist
    add_settings_column()
    key = open("secret.txt", "r").readline().rstrip()
    application = ApplicationBuilder().token(key).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_api_key)],
            ASK_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_text)],
            ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)],
            ASK_PROJECT: [CallbackQueryHandler(handle_project_selection)],
            ASK_PRIORITY: [CallbackQueryHandler(handle_priority_selection)],
            ASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deadline)],
        },
        fallbacks=[CommandHandler("change_api", change_api)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('settings', settings_command))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern='^(description|project|priority|deadline|done)$'))

    application.run_polling()
