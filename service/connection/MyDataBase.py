import sqlite3
from contextlib import closing
import config
import os
import regex as re
import threading

from service.constants import DB_ALLOWED_TABLES

_SAFE_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _check_table(table: str) -> None:
    """Перевіряє, що назва таблиці є в білому списку. Інакше — виняток."""
    if table not in DB_ALLOWED_TABLES:
        raise ValueError(f"Недозволена таблиця: '{table}'. Додайте її до _ALLOWED_TABLES.")


def _check_identifier(name: str) -> None:
    """Перевіряє, що ім'я колонки є безпечним SQL-ідентифікатором."""
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Небезпечне ім'я колонки або поля: '{name}'")


class MyDataBase:
    def __init__(self, db_name: str = config.DB_NAME):
        self.db_name = db_name
        self._lock = threading.Lock()  # захищає з'єднання від одночасного доступу
        self.connection: sqlite3.Connection | None = None
        self.__init_db__()

    def _execute_sql_file(self, conn: sqlite3.Connection, filepath: str) -> None:
        if not os.path.exists(filepath):
            print(f"⚠️ Попередження: файл схеми не знайдено: {filepath}")
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        try:
            conn.executescript(sql_script)
            conn.commit()
            print(f"✅ Схему застосовано: {filepath}")
        except sqlite3.Error as e:
            print(f"❌ Помилка виконання схеми {filepath}: {e}")

    def __init_db__(self) -> None:
        """Виконує schema.sql, update.sql та безпечні міграції при запуску."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        scheme_path = os.path.join(current_dir, 'schema.sql')
        update_path = os.path.join(current_dir, 'update.sql')
        with sqlite3.connect(self.db_name) as conn:
            self._execute_sql_file(conn, scheme_path)
            self._execute_sql_file(conn, update_path)


    def _connect(self) -> sqlite3.Connection:
        """
        Відкриває з'єднання, якщо воно ще закрите.
        Викликається ТІЛЬКИ всередині захищених Lock-секцій.
        """
        if self.connection is None:
            # timeout=10 — SQLite почекає 10 с, якщо база зайнята, замість негайної помилки
            self.connection = sqlite3.connect(
                self.db_name,
                check_same_thread=False,
                timeout=10
            )
            self.connection.row_factory = sqlite3.Row
            # WAL — дозволяє паралельне читання під час запису
            self.connection.execute('PRAGMA journal_mode=WAL;')
        return self.connection

    def disconnect(self) -> None:
        """Закриває з'єднання з базою."""
        with self._lock:
            if self.connection:
                self.connection.close()
                self.connection = None

    def __execute_fetch__(self, query: str, params=None):
        """Повертає один рядок або None."""
        with self._lock:
            conn = self._connect()
            try:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(query, params or ())
                    return cursor.fetchone()
            except sqlite3.Error as e:
                print(f"❌ Помилка читання БД: {e}")
                return None

    def __execute_fetchall__(self, query: str, params=None):
        """Повертає список рядків."""
        with self._lock:
            conn = self._connect()
            try:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(query, params or ())
                    return cursor.fetchall()
            except sqlite3.Error as e:
                print(f"❌ Помилка читання БД (fetchall): {e}")
                return []

    def __execute_query__(self, query: str, params=None):
        """Виконує INSERT/UPDATE/DELETE з параметризованим запитом. Повертає lastrowid."""
        with self._lock:
            conn = self._connect()
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
        """Вставляє один запис. Назва таблиці перевіряється по білому списку."""
        _check_table(table)
        for col in data.keys():
            _check_identifier(col)

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.__execute_query__(query, tuple(data.values()))

    def insert_records_batch(self, table: str, data_list: list) -> bool:
        """Масова вставка списку словників в одній транзакції."""
        if not data_list:
            return True

        _check_table(table)
        for col in data_list[0].keys():
            _check_identifier(col)

        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['?'] * len(data_list[0]))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        values = [tuple(row.values()) for row in data_list]

        with self._lock:
            conn = self._connect()
            try:
                with closing(conn.cursor()) as cursor:
                    cursor.executemany(query, values)
                    conn.commit()
                    return True
            except sqlite3.Error as e:
                print(f"❌ Помилка масового запису в БД: {e}")
                conn.rollback()
                return False

    def update_record(self, table: str, record_id: int, data: dict):
        """Оновлює запис за id. Назва таблиці та імена колонок перевіряються."""
        _check_table(table)
        for col in data.keys():
            _check_identifier(col)

        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE id = ?"
        self.__execute_query__(query, tuple(data.values()) + (record_id,))
        return record_id

    def delete_record(self, table: str, record_id: int) -> bool:
        """Видаляє один запис за id."""
        _check_table(table)
        self.__execute_query__(f"DELETE FROM {table} WHERE id = ?", (record_id,))
        return True

    def delete_children(self, table: str, field: str, value) -> bool:
        """Видаляє пов'язані записи за вказаним полем (наприклад, task_id)."""
        _check_table(table)
        _check_identifier(field)
        self.__execute_query__(f"DELETE FROM {table} WHERE {field} = ?", (value,))
        return True

    def __execute_sql__(self, sql: str):
        """
        ⚠️ УВАГА: виконує довільний SQL без параметрів.
        Використовувати ТІЛЬКИ з хардкодованими рядками (наприклад, у тестах).
        Ніколи не передавати сюди дані від користувача.
        """
        with self._lock:
            conn = self._connect()
            try:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(sql)
                    conn.commit()
                    return cursor.lastrowid
            except sqlite3.Error as e:
                print(f"❌ Помилка в БД (__execute_sql__): {e}")
                conn.rollback()
                return None

