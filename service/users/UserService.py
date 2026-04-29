from datetime import datetime, timedelta
from typing import Optional, List, Dict

from dics.security_config import PERM_READ, PERM_EDIT, PERM_DELETE
from domain.user import User
from service.connection.EmailClient import EmailClient
from service.connection.MyDataBase import MyDataBase
from service.connection.SignalClient import SignalClient
from service.constants import DB_TABLE_USER
from service.storage.LoggerManager import LoggerManager
from service.storage.StorageFactory import StorageFactory
from werkzeug.security import generate_password_hash
import config
from utils.utils import normalize_phone


class UserService:
    def __init__(self, db:MyDataBase, signal_client: SignalClient, email_client: EmailClient):
        self.db = db
        self.signal_client = signal_client
        self.email_client = email_client
        self._signal_sessions = {}

    def get_user_state(self, phone_number: str) -> str:
        """Отримує стан користувача (повертає 'START', якщо не знайдено)."""
        query = "SELECT current_state FROM user_states WHERE phone_number = ?"

        # Викликаємо метод з переданого екземпляра БД
        result = self.db.__execute_fetch__(query, (phone_number,))
        return result[0] if result else "START"

    def set_user_state(self, phone_number: str, state: str) -> int:
        """Зберігає або оновлює стан."""
        query = '''
            INSERT INTO user_states (phone_number, current_state, last_update)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone_number) DO UPDATE SET 
                current_state = excluded.current_state,
                last_update = CURRENT_TIMESTAMP
        '''
        return self.db.__execute_query__(query, (phone_number, state))

    def reset_user(self, phone_number: str) -> int:
        """Скидає стан користувача до початкового."""
        return self.set_user_state(phone_number, "START")

    def update_user_pending_contact(self, user_id, contact, contact_type, code, expiry):
        """
        Зберігає тимчасові дані для підтвердження.
        OTP-код хешується перед записом — у БД ніколи не зберігається відкритий текст.
        """
        code_hash = generate_password_hash(code, method='pbkdf2:sha256')
        query = f'''
            UPDATE {DB_TABLE_USER} SET
                pending_contact = ?,
                pending_type = ?,
                verification_code = ?,
                verification_expiry = ?
            WHERE id = ?
        '''
        return self.db.__execute_query__(query, (contact, contact_type, code_hash, expiry.isoformat(), user_id))

    def get_pending_info(self, user_id):
        """
        Отримує дані, що чекають підтвердження.
        Повертає 'code_hash' замість 'code' — порівнювати через check_password_hash.
        """
        query = f"SELECT pending_contact, pending_type, verification_code, verification_expiry FROM {DB_TABLE_USER} WHERE id = ?"
        row = self.db.__execute_fetch__(query, (user_id,))
        if row:
            return {
                'contact':   row[0],
                'type':      row[1],
                'code_hash': row[2],   # bcrypt-хеш, не відкритий код
                'expiry':    datetime.fromisoformat(row[3]) if row[3] else None
            }
        return None

    def update_user_email(self, user_id, email):
        return self.db.__execute_query__(f"UPDATE {DB_TABLE_USER} SET email = ? WHERE id = ?", (email, user_id))

    def update_user_phone(self, user_id, phone):
        return self.db.__execute_query__(f"UPDATE {DB_TABLE_USER} SET phone = ? WHERE id = ?", (phone, user_id))

    def clear_pending(self, user_id):
        return self.db.__execute_query__(
            f"UPDATE {DB_TABLE_USER} SET pending_contact=NULL, pending_type=NULL, verification_code=NULL, verification_expiry=NULL WHERE id = ?",
            (user_id,)
        )

    def update_user_profile(self, user_id: int, full_name: str, use_2fa: bool) -> bool:
        """Оновлює профіль користувача."""
        query = f'''
            UPDATE {DB_TABLE_USER} 
            SET full_name = ?, 
                use_2fa = ? 
            WHERE id = ?
        '''
        self.db.__execute_query__(query, (full_name, int(use_2fa), user_id))
        return True

    def send_code(self, email: str, code: str):
        """Проксі-метод для відправки через EmailClient"""
        return self.email_client.send_verification_code(email, code)

    def send_message(self, phone: str, message: str):
        """Відправка через твій SignalClient (JSON-RPC)."""
        try:
            self.signal_client.send_message(phone, message)
            return True
        except Exception as e:
            print(f"❌ Помилка Signal RPC: {e}")
            raise e

    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """
        Знаходить активного користувача за номером телефону Signal.
        Порівнює тільки цифрову частину номера, щоб пережити різні формати
        (+380..., 380..., 0...).

        Повертає User ТІЛЬКИ якщо:
          - телефон знайдено в полі users.phone (верифікований через 2FA)
          - користувач активний (is_active = 1)
          - use_2fa = 1 (підтверджений Signal-контакт)
        Якщо user не пройшов 2FA-верифікацію — phone порожній, доступу немає.
        """
        print('>>>> getting user by phone' + str(phone_number))
        if not phone_number:
            return None

        digits = normalize_phone(phone_number)
        if len(digits) < 9:
            return None

        # Перевіряємо по останніх 9 цифрах (локальна частина номера)
        # щоб не залежати від коду країни у форматі
        suffix = digits[-9:]

        rows = self.db.__execute_fetchall__(
            f"SELECT * FROM {DB_TABLE_USER} WHERE phone IS NOT NULL AND phone != '' AND is_active = 1 AND use_2fa = 1"
        )
        print('>>> suffix ' + str(suffix))
        for row in rows:
            stored_digits = normalize_phone(str(row['phone']))
            print('>>> checking with ' + str(stored_digits))
            if stored_digits[-9:] == suffix:
                return self.map_to_user(row)

        return None


    #### SIGNAL SESSION ###

    def verify_password(self, username: str, raw_password: str) -> bool:
        """
        Перевірка пароля.
        Використовуй ту ж логіку, що в NiceGUI (наприклад, passlib.hash.bcrypt.verify)
        """
        query = "SELECT password_hash FROM users WHERE username = ?"
        res = self.db.__execute_fetch__(query, (username,))
        if not res:
            return False

        # Приклад для bcrypt (заміни на свій метод з веб-версії)
        return generate_password_hash(raw_password) == res['password_hash']

    def update_signal_activity(self, phone_number: str):
        """Фіксуємо активність у базі даних"""
        query = "UPDATE users SET signal_last_activity = ? WHERE phone = ?"
        self.db.__execute_query__(query, (datetime.now(), phone_number))

    def is_signal_session_valid(self, phone_number: str, ttl_minutes: int) -> bool:
        """Перевіряємо валідність сесії через БД"""
        query = "SELECT signal_last_activity FROM users WHERE phone = ? AND is_active = 1"
        res = self.db.__execute_fetch__(query, (phone_number,))

        if not res or not res['signal_last_activity']:
            return False

        # Обробка формату (sqlite повертає рядок або об'єкт залежно від драйвера)
        last_act = res['signal_last_activity']
        if isinstance(last_act, str):
            last_act = datetime.fromisoformat(last_act)

        return (datetime.now() - last_act) < timedelta(minutes=ttl_minutes)

    def logout_signal(self, phone_number: str):
        """Скидаємо сесію та стан"""
        query = "UPDATE users SET signal_last_activity = NULL WHERE phone = ?"
        self.db.__execute_query__(query, (phone_number,))
        self.set_user_state(phone_number, "START")

    def get_all_users(self, hide_active=True) -> List[Dict]:
        if hide_active:
            query = f"SELECT * FROM {DB_TABLE_USER} where is_active = ?"
            rows = self.db.__execute_fetchall__(query, (int(True),))
        else:
            query = f"SELECT * FROM {DB_TABLE_USER}"
            rows = self.db.__execute_fetchall__(query)

        if not rows:
            return []

        return [
            {
                **dict(row),
                'is_active': bool(row['is_active']),
                'use_2fa': bool(row['use_2fa'])
            } for row in rows
        ]

    def init_user_folders(self):
        users = self.get_all_users()
        if not users:
            return
        # --- 1. Створення папок INBOX ---
        # Створюємо клієнт для кореневої папки inbox
        with StorageFactory.create_client(config.INBOX_LOCAL_DIR_PATH, LoggerManager()) as client:
            for user in users:
                username = user.get('username')
                if username:
                    # Створюємо директорію для конкретного юзера (відносно INBOX_LOCAL_DIR_PATH)
                    print('>>> створюємо папку ' + str(f'{config.INBOX_LOCAL_DIR_PATH}{client.get_separator()}{username}'))
                    client.make_dirs(f'{config.INBOX_LOCAL_DIR_PATH}{client.get_separator()}{username}')

        # --- 2. Створення папок OUTBOX ---
        # Створюємо клієнт для кореневої папки outbox
        with StorageFactory.create_client(config.OUTBOX_LOCAL_DIR_PATH, LoggerManager()) as client:
            for user in users:
                username = user.get('username')
                if username:
                    print('>>> створюємо папку ' + str(f'{config.OUTBOX_LOCAL_DIR_PATH}{client.get_separator()}{username}'))
                    client.make_dirs(f'{config.OUTBOX_LOCAL_DIR_PATH}{client.get_separator()}{username}')


    def update_user(self, user_id: int, **kwargs) -> bool:
        """
        Універсальний метод для оновлення будь-яких полів користувача.
        Приклад виклику:
        update_user_fields(1, role='admin', is_active=True, use_2fa=False)
        """
        if not kwargs:
            return False  # Немає полів для оновлення

        # Формуємо частину SET: "role = ?, is_active = ?, use_2fa = ?"
        set_clauses = [f"{key} = ?" for key in kwargs.keys()]
        set_string = ", ".join(set_clauses)

        # Обробляємо значення (перетворюємо Python True/False на 1/0 для надійності в SQLite)
        processed_values = [int(v) if isinstance(v, bool) else v for v in kwargs.values()]

        # Додаємо user_id в кінець для умови WHERE
        processed_values.append(user_id)

        query = f"UPDATE {DB_TABLE_USER} SET {set_string} WHERE id = ?"
        try:
            self.db.__execute_query__(query, tuple(processed_values))
            return True
        except Exception as e:
            # Тут можна додати запис у лог, якщо використовуєте self.log_manager
            print(f"❌ Помилка універсального оновлення користувача {user_id}: {e}")
            return False


    def update_password(self, user_id: int, new_password: str):
        """Встановлює новий пароль для існуючого користувача."""
        pass_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        query = f"UPDATE {DB_TABLE_USER} SET password_hash = ? WHERE id = ?"
        self.db.__execute_query__(query, (pass_hash, user_id))


    def get_user_by_username(self, username: str) -> Optional[User]:
        query = f"SELECT * FROM {DB_TABLE_USER} WHERE username = ?"
        row = self.db.__execute_fetch__(query, (username,))
        return self.map_to_user(row)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Отримує повні дані користувача за ID."""
        query = f"SELECT * FROM {DB_TABLE_USER} WHERE id = ?"
        row = self.db.__execute_fetch__(query, (user_id,))
        return self.map_to_user(row)

    def get_user_permissions(self, role: str) -> Dict[str, Dict[str, bool]]:
        """Завантажує права доступу."""
        query = "SELECT module_name, can_read, can_write, can_delete FROM role_permissions WHERE role = ?"
        rows = self.db.__execute_fetchall__(query, (role,))

        perms = {}
        for r in rows:
            perms[r['module_name']] = {
                PERM_READ: bool(r['can_read']),
                PERM_EDIT: bool(r['can_write']),
                PERM_DELETE: bool(r['can_delete'])
            }
        return perms

    def create_user(self, username: str, password: str, role: str, full_name: str,
                    force_password_change: bool = False):

        if self.get_user_by_username(username):
            return False, "Користувач з таким логіном вже існує"

        pass_hash = generate_password_hash(password, method='pbkdf2:sha256')

        query = (f"INSERT INTO {DB_TABLE_USER} (username, password_hash, role, full_name, force_password_change) "
                 "VALUES (?, ?, ?, ?, ?)")
        user_id = self.db.__execute_query__(
            query, (username, pass_hash, role, full_name, int(force_password_change))
        )

        if user_id:
            return True, "Користувача успішно створено"
        return False, "Помилка бази даних при створенні користувача"


    def map_to_user(self, row) -> Optional[User]:
        """Єдине місце, де ми створюємо об'єкт User з даних БД."""
        if not row:
            return None

        row_keys = row.keys()
        user = User(
            id=row['id'],
            username=row['username'],
            role=row['role'],
            full_name=row['full_name'],
            is_active=bool(row['is_active']),
            session_token=row['session_token'],
            lockout_until=row['lockout_until'],
            failed_login_attempts=row['failed_login_attempts'],
            use_2fa=row['use_2fa'],
            email=row['email'],
            phone=row['phone'],
            verification_code=row['verification_code'],
            # Безпечний fallback на випадок, якщо міграція ще не відбулась
            force_password_change=bool(row['force_password_change']) if 'force_password_change' in row_keys else False,
        )
        return user
