import sqlite3

DB_NAME = "bot_data.db"

def init_db():
    """Створює таблицю для станів, якщо вона ще не існує."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            phone_number TEXT PRIMARY KEY,
            current_state TEXT DEFAULT 'START'
        )
    ''')
    conn.commit()
    conn.close()

def get_user_state(phone_number):
    """Отримує поточний стан користувача з бази."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT current_state FROM user_states WHERE phone_number = ?", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "START"

def set_user_state(phone_number, state):
    """Зберігає або оновлює стан користувача."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_states (phone_number, current_state)
        VALUES (?, ?)
        ON CONFLICT(phone_number) DO UPDATE SET current_state = excluded.current_state
    ''', (phone_number, state))
    conn.commit()
    conn.close()