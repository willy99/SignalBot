from datetime import datetime
from typing import Optional
from domain.user import User
from service.connection.EmailClient import EmailClient
from service.connection.MyDataBase import MyDataBase
from service.connection.SignalClient import SignalClient
from service.constants import DB_TABLE_USER
from service.users.AuthService import AuthService
from werkzeug.security import generate_password_hash


class UserService:
    def __init__(self, db:MyDataBase, signal_client: SignalClient, email_client: EmailClient):
        self.db = db
        self.signal_client = signal_client
        self.email_client = email_client
        self.auth_service = AuthService(self.db)

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
            print('>>> sending message ' + str(message) + ' to ' + phone)
            self.signal_client.send_message(phone, message)
            return True
        except Exception as e:
            print(f"❌ Помилка Signal RPC: {e}")
            raise e
