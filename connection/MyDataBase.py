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

            cursor.execute('''
                            CREATE TABLE IF NOT EXISTS support_drafts (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                created_by INTEGER NOT NULL,
                                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                status TEXT DEFAULT 'DRAFT',
                                city TEXT,
                                support_number TEXT,
                                payload TEXT
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




    def insert_record(self, table: str, data: dict) -> int:
        """
        Універсальний метод вставки словника в таблицю.
        Приклад: db.insert_record('users', {'username': 'admin', 'role': 'admin'})
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        # __execute_insert__ повертає lastrowid, що нам і треба
        return self.__execute_insert__(query, tuple(data.values()))

    def update_record(self, table: str, record_id: int, data: dict):
        """
        Універсальний метод оновлення запису за його ID.
        """
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE id = ?"

        values = tuple(data.values()) + (record_id,)
        self.__execute_insert__(query, values)
        return record_id

    def delete_record(self, table: str, record_id: int):
        """Універсальне видалення за ID."""
        query = f"DELETE FROM {table} WHERE id = ?"
        self.__execute_insert__(query, (record_id,))
        return True