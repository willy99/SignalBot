from datetime import datetime, timedelta
from typing import Optional
from domain.user import User
from service.connection.EmailClient import EmailClient
from service.connection.MyDataBase import MyDataBase
from service.connection.SignalClient import SignalClient
from service.constants import DB_TABLE_USER
from service.users.AuthService import AuthService
from werkzeug.security import generate_password_hash
import config
from utils.utils import normalize_phone


class UserService:
    def __init__(self, db:MyDataBase, signal_client: SignalClient, email_client: EmailClient):
        self.db = db
        self.signal_client = signal_client
        self.email_client = email_client
        self.auth_service = AuthService(self.db)
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

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.auth_service.get_user_by_id(user_id)

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
        for row in rows:
            stored_digits = normalize_phone(str(row['phone']))
            if stored_digits[-9:] == suffix:
                return self.auth_service._map_to_user(row)

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