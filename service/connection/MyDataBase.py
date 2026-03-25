import sqlite3
from contextlib import closing
import config
import os

class MyDataBase:
    def __init__(self, db_name=config.DB_NAME):
        self.db_name = db_name
        self.__init_db__()
        self.connection = None

    def _execute_sql_file(self, conn, filepath: str):
        if not os.path.exists(filepath):
            print(f"⚠️ Попередження: Файл {filepath} не знайдено.")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        try:
            conn.executescript(sql_script)
            conn.commit()
            print(f"✅ Скрипт {filepath} успішно виконано.")
        except sqlite3.Error as e:
            print(f"❌ Помилка виконання {filepath}: {e}")

    def __init_db__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        scheme_path = os.path.join(current_dir, 'schema.sql')
        update_path = os.path.join(current_dir, 'update.sql')
        with sqlite3.connect(self.db_name) as conn:
            # Виконуємо файли
            self._execute_sql_file(conn, scheme_path)
            self._execute_sql_file(conn, update_path)

    def connect(self):
        """Відкриває з'єднання, якщо воно закрите."""
        if self.connection is None:
            # timeout=10 змушує SQLite почекати 10 секунд, якщо база зайнята, замість помилки
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False, timeout=10)
            self.connection.row_factory = sqlite3.Row

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

    def insert_record(self, table: str, data: dict) -> int:
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        # __execute_insert__ повертає lastrowid, що нам і треба
        return self.__execute_insert__(query, tuple(data.values()))

    def insert_records_batch(self, table: str, data_list: list) -> bool:
        """Масовий запис списку словників (для оптимізації)."""
        if not data_list:
            return True

        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['?'] * len(data_list[0]))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        conn = self.connect()
        try:
            with closing(conn.cursor()) as cursor:
                # Перетворюємо список словників у список кортежів значень
                values = [tuple(data.values()) for data in data_list]
                cursor.executemany(query, values)
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"❌ Помилка масового запису в БД: {e}")
            conn.rollback()
            return False

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

    def delete_children(self, table: str, field: str, value):
        """Універсальне видалення записів за вказаним полем (наприклад, task_id)."""
        query = f"DELETE FROM {table} WHERE {field} = ?"
        self.__execute_insert__(query, (value,))
        return True

    def __execute_sql__(self, sql):
        conn = self.connect()
        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(sql, ())
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"❌ Помилка в БД: {e}")
            conn.rollback()
            return None


