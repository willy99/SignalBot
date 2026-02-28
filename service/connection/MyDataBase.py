import sqlite3
from typing import Final
from contextlib import closing
import config

DB_TABLE_SUPPORT_DOC: Final[str] = 'support_docs'

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
                            CREATE TABLE IF NOT EXISTS ''' + DB_TABLE_SUPPORT_DOC  + ''' (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                created_by INTEGER NOT NULL,
                                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                status TEXT DEFAULT 'DRAFT',
                                city TEXT,
                                support_number TEXT,
                                payload TEXT
                            );
                        ''')


            cursor.execute('''
                    CREATE TABLE task (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Використовуйте SERIAL, якщо у вас PostgreSQL
                        created_by INTEGER NOT NULL,           -- Хто поставив задачу
                        assignee INTEGER,                      -- Кому призначено (може бути NULL, якщо задача ще "нічия")
                        task_status VARCHAR(50) DEFAULT 'NEW', -- Наприклад: NEW, IN_PROGRESS, COMPLETED, CANCELED
                        task_type VARCHAR(50) DEFAULT '',      -- далі буде
                        task_subject VARCHAR(255) NOT NULL,    -- Короткий заголовок задачі
                        task_details TEXT,                     -- Довгий опис (LONGTEXT у MySQL або просто TEXT у SQLite/Postgres)
                        task_deadline DATETIME,                -- Дедлайн виконання
                        
                        -- Системні поля для аудиту
                        created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                        -- Зв'язки з таблицею користувачів (припускаю, що вона називається users)
                        FOREIGN KEY (created_by) REFERENCES users(id),
                        FOREIGN KEY (assignee) REFERENCES users(id)
                    );            
            ''')
            conn.commit()

    def connect(self):
        """Відкриває з'єднання, якщо воно закрите."""
        if self.connection is None:
            # timeout=10 змушує SQLite почекати 10 секунд, якщо база зайнята, замість помилки
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False, timeout=10)

            # Вмикаємо режим WAL (дозволяє паралельне читання та запис)
            self.connection.execute('PRAGMA journal_mode=WAL;')
        return self.connection

    def disconnect(self):
        """Закриває з'єднання."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __execute_fetch__(self, query, params=None):
        conn = self.connect()
        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"❌ Помилка читання БД: {e}")
            return None

    def __execute_fetchall__(self, query, params=None):
        conn = self.connect()
        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"❌ Помилка читання БД (fetchall): {e}")
            return []

    def __execute_insert__(self, query, params=None):
        conn = self.connect()
        try:
            with closing(conn.cursor()) as cursor:
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
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        # __execute_insert__ повертає lastrowid, що нам і треба
        return self.__execute_insert__(query, tuple(data.values()))

    def update_record(self, table: str, record_id: int, data: dict):
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE id = ?"

        values = tuple(data.values()) + (record_id,)
        self.__execute_insert__(query, values)
        return record_id

    def delete_record(self, table: str, record_id: int):
        query = f"DELETE FROM {table} WHERE id = ?"
        self.__execute_insert__(query, (record_id,))
        return True