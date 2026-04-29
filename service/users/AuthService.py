from typing import Optional, Tuple, Dict, List
from werkzeug.security import generate_password_hash, check_password_hash

from dics.security_config import PERM_READ, PERM_EDIT, PERM_DELETE, MODULE_ADMIN, MODULE_SEARCH, MODULE_PERSON
from domain.user import User
import uuid
import secrets
import string
from datetime import datetime, timedelta
import config
from service.constants import DB_TABLE_USER
import asyncio
import time

class AuthService:

    def __init__(self, db):
        self.db = db
        self.ip_attempts = {}

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Перевірка логіну/пароля."""
        # Використовуємо SELECT *, або чітко перелічуємо поля
        query = f"SELECT * FROM {DB_TABLE_USER} WHERE username = ? AND is_active = 1"
        row = self.db.__execute_fetch__(query, (username,))
        if not row:
            check_password_hash(generate_password_hash("dummy_password"), password)
            # Штучна затримка, щоб уповільнити brute-force (наприклад, 1 секунда)
            await asyncio.sleep(1)
            return None

        user_id = row['id']

        if row['lockout_until']:
            lockout_time = datetime.fromisoformat(row['lockout_until'])
            if datetime.now() < lockout_time:
                remaining = int((lockout_time - datetime.now()).total_seconds() / 60)
                await asyncio.sleep(0.5)
                raise PermissionError(f"Акаунт заблоковано. Спробуйте через {remaining} хв.")


        if row and check_password_hash(row['password_hash'], password):
            user = self._map_to_user(row)
            if user:
                # УСПІХ: Скидаємо лічильник помилок
                self.reset_failed_attempts(user_id)

                user.permissions = self.get_user_permissions(user.role)
                new_token = str(uuid.uuid4())
                update_query = f"UPDATE {DB_TABLE_USER} SET session_token = ? WHERE id = ?"
                self.db.__execute_query__(update_query, (new_token, row['id']))
                user.session_token = new_token
                return user
        else:
            self.register_failed_attempt(user_id)
            await asyncio.sleep(1)
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

    def get_user_by_username(self, username: str) -> Optional[User]:
        query = f"SELECT * FROM {DB_TABLE_USER} WHERE username = ?"
        row = self.db.__execute_fetch__(query, (username,))
        return self._map_to_user(row)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Отримує повні дані користувача за ID."""
        query = f"SELECT * FROM {DB_TABLE_USER} WHERE id = ?"
        row = self.db.__execute_fetch__(query, (user_id,))
        return self._map_to_user(row)


    def _map_to_user(self, row) -> Optional[User]:
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

    def get_all_users(self) -> List[Dict]:
        """
        Повертає список словників для таблиці NiceGUI.
        NiceGUI зручно працює саме зі списком dict.
        """
        query = f"SELECT id, username, role, full_name, use_2fa, is_active FROM {DB_TABLE_USER}"
        rows = self.db.__execute_fetchall__(query)
        return [
            {
                **dict(row),
                'is_active': bool(row['is_active'])
            } for row in rows
        ]

    def update_user(self, user_id: int, role: str, full_name: str, is_active: bool):
        """Оновлює профіль користувача (без пароля)."""
        query = f"UPDATE {DB_TABLE_USER} SET role = ?, full_name = ?, is_active = ? WHERE id = ?"
        self.db.__execute_query__(query, (role, full_name, int(is_active), user_id))

    def update_password(self, user_id: int, new_password: str):
        """Встановлює новий пароль для існуючого користувача."""
        pass_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        query = f"UPDATE {DB_TABLE_USER} SET password_hash = ? WHERE id = ?"
        self.db.__execute_query__(query, (pass_hash, user_id))

    def clear_force_password_change(self, user_id: int):
        return self.db.__execute_query__(f"UPDATE {DB_TABLE_USER} SET force_password_change = ? WHERE id = ?", (0, user_id))

    def invalidate_session_token(self, user_id: int) -> None:
        """
        Скидає session_token у БД при logout.
        Перехоплений токен стає недійсним негайно, не чекаючи таймауту сесії.
        """
        self.db.__execute_query__(
            f"UPDATE {DB_TABLE_USER} SET session_token = NULL WHERE id = ?",
            (user_id,)
        )

    def init_default_admin(self):
        """
        Створює адміна при першому запуску, якщо БД порожня.
        Пароль генерується криптографічно безпечним способом і виводиться ОДИН РАЗ.
        При першому вході система примусово вимагає змінити пароль.
        """
        if not self.get_user_by_username('admin'):
            # Генеруємо криптографічно безпечний тимчасовий пароль
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            temp_password = ''.join(secrets.choice(alphabet) for _ in range(16))

            self.create_user('admin', temp_password, 'admin', 'Адміністратор',
                             force_password_change=True)

            # Надаємо максимальні права на існуючі модулі
            modules = [MODULE_SEARCH, MODULE_PERSON, MODULE_ADMIN]
            for mod in modules:
                self.set_permissions('admin', mod, can_read=1, can_write=1, can_delete=1)

            print("=" * 60)
            print("✅  ПЕРШИЙ ЗАПУСК: створено адміністратора")
            print(f"    Логін:  admin")
            print(f"    Пароль: {temp_password}")
            print("⚠️   Збережіть цей пароль! Після входу система")
            print("     одразу вимагатиме його замінити на власний.")
            print("=" * 60)

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
            f"UPDATE {DB_TABLE_USER} SET failed_login_attempts = ?, lockout_until = ? WHERE id = ?",
            (new_attempts, lockout_until, user_id)
        )

        return new_attempts, lockout_until

    def reset_failed_attempts(self, user_id: int):
        query = f"UPDATE {DB_TABLE_USER} SET failed_login_attempts = 0, lockout_until = NULL WHERE id = ?"
        self.db.__execute_query__(query, (user_id,))


    def check_ip_rate_limit(self, ip_address):
        now = time.time()
        attempts = self.ip_attempts.get(ip_address, [])
        # Залишаємо спроби тільки за останні 5 хвилин
        attempts = [t for t in attempts if now - t < 300]
        self.ip_attempts[ip_address] = attempts

        if len(attempts) > 20:  # Наприклад, 20 спроб за 5 хв з одного IP
            return False

        attempts.append(now)
        return True


    def is_ip_blocked(self, ip: str, max_attempts=config.SECURITY_MAX_ATTEMPTS, window_seconds=300) -> bool:
        """Перевіряє, чи не перевищив IP ліміт спроб за вказаний час (5 хв)."""
        now = time.time()

        # Отримуємо список таймстемпів для цього IP
        attempts = self.ip_attempts.get(ip, [])

        # Очищаємо старі спроби (старші за window_seconds)
        attempts = [t for t in attempts if now - t < window_seconds]
        self.ip_attempts[ip] = attempts

        return len(attempts) >= max_attempts


    def register_ip_attempt(self, ip: str):
        """Фіксуємо нову невдалу спробу для IP."""
        now = time.time()
        if ip not in self.ip_attempts:
            self.ip_attempts[ip] = []
        self.ip_attempts[ip].append(now)