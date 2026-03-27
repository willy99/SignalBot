from typing import Optional
from domain.user import User
from werkzeug.security import generate_password_hash
from nicegui import app, ui
from gui.services.request_context import RequestContext
from dics.security_config import PERM_READ
from service.users.AuthService import AuthService
import time
import config

class AuthManager:
    def __init__(self, db):
        self.db = db
        self.auth_service = AuthService(self.db)
        self.auth_service.init_default_admin()

    def create_user(self, username: str, password: str, role: str, full_name: str):
        if self.get_user(username):
            return False, "Користувач з таким логіном вже існує"

        pass_hash = generate_password_hash(password, method='pbkdf2:sha256')

        query = "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)"
        user_id = self.db.__execute_insert__(query, (username, pass_hash, role, full_name))

        if user_id:
            return True, "Користувача успішно створено"
        return False, "Помилка бази даних при створенні користувача"

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user:User = self.auth_service.authenticate(username, password)
        app.storage.user.update({
            'authenticated': True,
            'user_id': user.id,
            'user_info': {
                'username': user.username,
                'role': user.role,
                'full_name': user.full_name,
                'id': user.id
            },
            'last_activity': time.time() # Початок відліку сесії
        })

        return user

    def check_session(self) -> bool:
        """Перевірка, чи не застаріла сесія."""
        if not app.storage.user.get('authenticated'):
            return False
        last_activity = app.storage.user.get('last_activity', 0)
        print('>>> check sessions ' + str(last_activity))
        if time.time() - last_activity > config.SESSION_TIMEOUT:
            self.logout()
            return False

        # Якщо активний — оновлюємо час останньої активності
        app.storage.user['last_activity'] = time.time()
        return True

    def logout(self):
        """Очищення даних сесії."""
        app.storage.user.clear()

    def get_user_permissions(self, role: str) -> dict:
        return self.auth_service.get_user_permissions(role)

    def has_access(self, module_name: str, action: str = PERM_READ) -> bool:
        from nicegui import app

        user_info = app.storage.user.get('user_info', None)
        if not user_info:
            return False

        perms = self.get_user_permissions(user_info.get('role'))
        module_perms = perms.get(module_name, {})

        return bool(module_perms.get(action, False))

    def get_user(self, username: str) -> dict:
        return self.auth_service.get_user(username)

    def get_all_users(self) -> list:
        return self.auth_service.get_all_users()

    def update_user(self, user_id: int, role: str, full_name: str, is_active: bool):
        self.auth_service.update_user(user_id=user_id, role=role, full_name=full_name, is_active=is_active)

    def update_password(self, user_id: int, new_password: str):
        self.auth_service.update_password(user_id=user_id, new_password=new_password)

    def set_permissions(self, role: str, module_name: str, can_read: int, can_write: int, can_delete: int):
        self.auth_service.set_permissions(role=role, module_name=module_name, can_read=can_read, can_write=can_write, can_delete=can_delete)


    def get_current_context(self) -> RequestContext:
        user_info = app.storage.user.get('user_info', {})
        ctx = RequestContext(
            user_name=user_info.get('full_name') or user_info.get('username') or 'Гість',
            user_role=user_info.get('role'),
            user_id=user_info.get('id'),
            user_login=user_info.get('username')
        )
        return ctx
