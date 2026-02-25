import sqlite3
import config


class MyDataBase:
    def __init__(self):
        self.db_name = config.DB_NAME
        self.__init_db__()
        self.connection = None

    def __init_db__(self):
        """Створює необхідні таблиці при запуску."""
        # Використовуємо context manager (with), щоб гарантовано закрити з'єднання
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_states (
                    phone_number TEXT PRIMARY KEY,
                    current_state TEXT DEFAULT 'START',
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            cursor.execute('''
                -- Таблиця користувачів
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    full_name TEXT,
                    is_active INTEGER DEFAULT 1
                );
            ''')
            cursor.execute('''
                -- Таблиця прав доступу для ролей
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role TEXT NOT NULL,
                    module_name TEXT NOT NULL,
                    can_read INTEGER DEFAULT 0,
                    can_write INTEGER DEFAULT 0,  -- Додавання / Редагування
                    can_delete INTEGER DEFAULT 0, -- Видалення
                    PRIMARY KEY (role, module_name)
                );                
            ''')
            conn.commit()

    def connect(self):
        """Відкриває з'єднання, якщо воно закрите."""
        if self.connection is None:
            # check_same_thread=False дозволяє працювати з БД з різних потоків Signal
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False)
        return self.connection

    def disconnect(self):
        """Закриває з'єднання."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __execute_fetch__(self, query, params=None):
        """Універсальний метод для отримання даних (SELECT)."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"❌ Помилка читання БД: {e}")
            return None

    def __execute_fetchall__(self, query, params=None):
        """Універсальний метод для отримання списку даних (SELECT багато рядків)."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"❌ Помилка читання БД (fetchall): {e}")
            return []

    def __execute_insert__(self, query, params=None):
        """Універсальний метод для запису даних (INSERT/UPDATE)."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"❌ Помилка запису в БД: {e}")
            conn.rollback()
            return None

    # --- Публічні методи для логіки бота ---

    def get_user_state(self, phone_number):
        """Отримує стан користувача (повертає 'START', якщо не знайдено)."""
        query = "SELECT current_state FROM user_states WHERE phone_number = ?"
        result = self.__execute_fetch__(query, (phone_number,))
        return result[0] if result else "START"

    def set_user_state(self, phone_number, state):
        """Зберігає або оновлює стан."""
        query = '''
            INSERT INTO user_states (phone_number, current_state, last_update)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone_number) DO UPDATE SET 
                current_state = excluded.current_state,
                last_update = CURRENT_TIMESTAMP
        '''
        return self.__execute_insert__(query, (phone_number, state))

    def reset_user(self, phone_number):
        """Скидає стан користувача до початкового."""
        return self.set_user_state(phone_number, "START")