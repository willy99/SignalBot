from typing import Optional, Tuple, Dict, List
from werkzeug.security import generate_password_hash, check_password_hash

from dics.security_config import PERM_READ, PERM_EDIT, PERM_DELETE, MODULE_ADMIN, MODULE_SEARCH, MODULE_PERSON
from domain.user import User
import uuid
from datetime import datetime, timedelta
import config

class AuthService:

    def __init__(self, db):
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Перевірка логіну/пароля."""
        # Використовуємо SELECT *, або чітко перелічуємо поля
        query = "SELECT * FROM users WHERE username = ? AND is_active = 1"
        row = self.db.__execute_fetch__(query, (username,))
        if not row:
            return None
        user_id = row['id']

        if row['lockout_until']:
            lockout_time = datetime.fromisoformat(row['lockout_until'])
            if datetime.now() < lockout_time:
                remaining = int((lockout_time - datetime.now()).total_seconds() / 60)
                raise PermissionError(f"Акаунт заблоковано. Спробуйте через {remaining} хв.")


        if row and check_password_hash(row['password_hash'], password):
            user = self._map_to_user(row)
            if user:
                # УСПІХ: Скидаємо лічильник помилок
                self.reset_failed_attempts(user_id)

                user.permissions = self.get_user_permissions(user.role)
                new_token = str(uuid.uuid4())
                update_query = "UPDATE users SET session_token = ? WHERE id = ?"
                self.db.__execute_query__(update_query, (new_token, row['id']))
                user.session_token = new_token
                return user
        else:
            self.register_failed_attempt(user_id)
        return None

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

    def create_user(self, username: str, password: str, role: str, full_name: str):

        if self.get_user_by_username(username):
            return False, "Користувач з таким логіном вже існує"

        pass_hash = generate_password_hash(password, method='pbkdf2:sha256')

        query = "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)"
        user_id = self.db.__execute_query__(query, (username, pass_hash, role, full_name))

        if user_id:
            return True, "Користувача успішно створено"
        return False, "Помилка бази даних при створенні користувача"

    def get_user_by_username(self, username: str) -> Optional[User]:
        query = "SELECT * FROM users WHERE username = ?"
        row = self.db.__execute_fetch__(query, (username,))
        return self._map_to_user(row)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Отримує повні дані користувача за ID."""
        query = "SELECT * FROM users WHERE id = ?"
        row = self.db.__execute_fetch__(query, (user_id,))
        return self._map_to_user(row)


    def _map_to_user(self, row) -> Optional[User]:
        """Єдине місце, де ми створюємо об'єкт User з даних БД."""
        if not row:
            return None

        user = User(
            id=row['id'],
            username=row['username'],
            role=row['role'],
            full_name=row['full_name'],
            is_active=bool(row['is_active']),
            session_token=row['session_token'],
            lockout_until=row['lockout_until'],
            failed_login_attempts=row['failed_login_attempts'],
            use_2fa = row['use_2fa'],
            email = row['email'],
            phone = row['phone'],
            verification_code = row['verification_code']
        )
        return user

    def get_all_users(self) -> List[Dict]:
        """
        Повертає список словників для таблиці NiceGUI.
        NiceGUI зручно працює саме зі списком dict.
        """
        query = "SELECT id, username, role, full_name, is_active FROM users"
        rows = self.db.__execute_fetchall__(query)
        return [
            {
                **dict(row),
                'is_active': bool(row['is_active'])
            } for row in rows
        ]

    def update_user(self, user_id: int, role: str, full_name: str, is_active: bool):
        """Оновлює профіль користувача (без пароля)."""
        query = "UPDATE users SET role = ?, full_name = ?, is_active = ? WHERE id = ?"
        print(str(int(is_active)))
        self.db.__execute_query__(query, (role, full_name, int(is_active), user_id))

    def update_password(self, user_id: int, new_password: str):
        """Встановлює новий пароль для існуючого користувача."""
        pass_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        self.db.__execute_query__(query, (pass_hash, user_id))



    def init_default_admin(self):
        """Створює адміна при першому запуску, якщо БД порожня."""
        if not self.get_user_by_username('admin'):
            self.create_user('admin', 'admin123', 'admin', 'Адміністратор')

            # Надаємо максимальні права на існуючі модулі
            modules = [MODULE_SEARCH, MODULE_PERSON, MODULE_ADMIN]
            for mod in modules:
                self.set_permissions('admin', mod, can_read=1, can_write=1, can_delete=1)

            print("✅ Створено дефолтного адміністратора (Логін: admin, Пароль: admin123)")

    def set_permissions(self, role: str, module_name: str, can_read: int, can_write: int, can_delete: int):

        """
        Встановлює або оновлює права доступу для конкретної ролі у модулі.
        Використовує UPSERT: якщо запис для (role, module_name) вже є, він оновиться.
        """
        query = '''
            INSERT INTO role_permissions (role, module_name, can_read, can_write, can_delete)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(role, module_name) DO UPDATE SET 
                can_read = excluded.can_read,
                can_write = excluded.can_write,
                can_delete = excluded.can_delete
        '''
        return self.db.__execute_query__(query, (role, module_name, can_read, can_write, can_delete))


    def register_failed_attempt(self, user_id: int):
        """Збільшує лічильник помилок та блокує юзера, якщо ліміт вичерпано."""
        user:User = self.get_user_by_id(user_id)
        new_attempts = (user.failed_login_attempts or 0) + 1
        lockout_until = None

        if new_attempts >= config.SECURITY_MAX_ATTEMPTS:
            lockout_until = (datetime.now() + timedelta(minutes=config.SECURITY_LOCKOUT_DURATION_MINS)).isoformat()
            print(f"SECURITY: User ID {user_id} locked out until {lockout_until}")

        self.db.__execute_query__(
            "UPDATE users SET failed_login_attempts = ?, lockout_until = ? WHERE id = ?",
            (new_attempts, lockout_until, user_id)
        )

        return new_attempts, lockout_until

    def reset_failed_attempts(self, user_id: int):
        query = "UPDATE users SET failed_login_attempts = 0, lockout_until = NULL WHERE id = ?"
        self.db.__execute_query__(query, (user_id,))