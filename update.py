from func import connect_db

# Adapting table update v2.0 (settings added)
def add_settings_column():
    conn = connect_db()
    c = conn.cursor()
    # Проверяем, есть ли столбец 'settings' в таблице
    c.execute("PRAGMA table_info(user_data)")
    columns = [column[1] for column in c.fetchall()]
    if 'settings' not in columns:
        c.execute("ALTER TABLE user_data ADD COLUMN settings TEXT")
        conn.commit()
    conn.close()

