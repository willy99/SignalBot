from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash

from dics.security_config import MODULE_ADMIN, MODULE_SEARCH, MODULE_PERSON
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

    def __init__(self, db, user_service):
        self.db = db
        self.user_service = user_service
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
            user = self.user_service.map_to_user(row)
            if user:
                # УСПІХ: Скидаємо лічильник помилок
                self.reset_failed_attempts(user_id)

                user.permissions = self.user_service.get_user_permissions(user.role)
                new_token = str(uuid.uuid4())
                update_query = f"UPDATE {DB_TABLE_USER} SET session_token = ? WHERE id = ?"
                self.db.__execute_query__(update_query, (new_token, row['id']))
                user.session_token = new_token
                return user
        else:
            self.register_failed_attempt(user_id)
            await asyncio.sleep(1)
        return None


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
        if not self.user_service.get_user_by_username('admin'):
            # Генеруємо криптографічно безпечний тимчасовий пароль
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            temp_password = ''.join(secrets.choice(alphabet) for _ in range(16))

            self.user_service.create_user('admin', temp_password, 'admin', 'Адміністратор',
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
        user:User = self.user_service.get_user_by_id(user_id)
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