from typing import Optional
from domain.user import User
from werkzeug.security import generate_password_hash
from gui.services.request_context import RequestContext
from dics.security_config import PERM_READ
from service.processing.MyWorkFlow import MyWorkFlow
from service.users.AuthService import AuthService
import time
from datetime import datetime
import config
from nicegui import app, run

class AuthManager:
    def __init__(self, workflow:MyWorkFlow):
        self.db = workflow.db
        self.auth_service = AuthService(self.db)
        self.auth_service.init_default_admin()
        self.logger = workflow.log_manager.get_logger()

    def create_user(self, username: str, password: str, role: str, full_name: str):
        """Delegate entirely to AuthService — no duplicate hashing or SQL here."""
        return self.auth_service.create_user(username, password, role, full_name)

    def get_user(self, username: str) -> User:
        return self.auth_service.get_user_by_username(username)

    def get_all_users(self) -> list:
        return self.auth_service.get_all_users()

    def update_user(self, user_id: int, role: str, full_name: str, is_active: bool):
        self.auth_service.update_user(user_id=user_id, role=role, full_name=full_name, is_active=is_active)

    def update_password(self, user_id: int, new_password: str):
        self.auth_service.update_password(user_id=user_id, new_password=new_password)

    def clear_force_password_change(self, user_id: int):
        """Знімає прапор примусової зміни пароля після успішної зміни."""
        self.auth_service.clear_force_password_change(user_id)

    def set_permissions(self, role: str, module_name: str, can_read: int, can_write: int, can_delete: int):
        self.auth_service.set_permissions(role=role, module_name=module_name, can_read=can_read, can_write=can_write, can_delete=can_delete)

    def get_user_permissions(self, role: str) -> dict:
        return self.auth_service.get_user_permissions(role)


    async def authenticate(self, username: str, password: str) -> Optional[dict]:
        user: User = self.auth_service.authenticate(username, password)
        if not user:
            return None

        # Початкові дані сесії (поки без 'authenticated': True)
        session_data = {
            'user_id': user.id,
            'user_info': {
                'username': user.username,
                'role': user.role,
                'full_name': user.full_name,
                'id': user.id,
                'session_token': user.session_token
            },
            'last_activity': time.time()
        }

        if user.use_2fa:
            contact_info = user.phone or user.email
            contact_type = 'Signal' if user.phone else 'Email'
            if not contact_info:
                # Якщо 2FA увімкнено, а контактів нема — це помилка конфігурації
                raise ValueError("2FA увімкнено, але не знайдено підтвердженого контакту (Signal/Email)")
            app.storage.user.update(session_data)
            app.storage.user['authenticated'] = False
            return {
                "status": "2fa_required",
                "user": user,
                "send_to": contact_info,
                "send_type": contact_type
            }

        # Примусова зміна пароля (наприклад, після першого запуску)
        if user.force_password_change:
            app.storage.user.update(session_data)
            app.storage.user['authenticated'] = False
            return {"status": "force_password_change", "user": user}

        # 2FA ВИМКНЕНА і пароль не потребує заміни — пускаємо відразу
        session_data['authenticated'] = True
        app.storage.user.update(session_data)
        return {"status": "success", "user": user}

    def check_session(self, ctx: RequestContext) -> bool:
        """Перевірка, чи не застаріла сесія."""
        if not app.storage.user.get('authenticated'):
            return False
        storage_time = app.storage.user.get('last_activity', 0)
        ctx_time = ctx.last_activity if ctx else 0

        last_activity = max(storage_time, ctx_time)
        user_info = app.storage.user.get('user_info', {})
        client_token = user_info.get('session_token')

        # time_str = datetime.fromtimestamp(last_activity).strftime('%H:%M:%S')
        # print(f'>>> check sessions (formatted): {time_str}')
        # print(f'>>> diff: {str(time.time() - last_activity)})')

        if time.time() - last_activity > config.SECURITY_SESSION_TIMEOUT:
            self.logout()
            return False

        new_now = time.time()
        app.storage.user['last_activity'] = new_now
        if ctx:
            ctx.last_activity = new_now

        user = self.auth_service.get_user_by_username(user_info.get('username'))

        if not user or user.session_token != client_token:
            self.logger.warning(f"ОЙ! Токени не збігаються для користувача: {user.username}!")
            self.logout()
            return False

        if not user or not user.is_active:
            self.logout()
            return False
        return True

    async def execute(self, func, ctx: RequestContext, *args, **kwargs):
        """
        Централізований запуск важких функцій у фоновому потоці
        з автоматичним менеджментом сесії.
        """
        if not self.check_session(ctx):
            return None  # Або raise PermissionError

        try:
            result = await run.io_bound(func, ctx, *args, **kwargs)

            app.storage.user['last_activity'] = time.time()
            if ctx:
                ctx.last_activity = app.storage.user['last_activity']

            return result

        except Exception as e:
            # Тут можна централізовано логувати помилки всіх звітів
            print(f"❌ Помилка при виконанні {func.__name__}: {e}")
            raise e

    def logout(self):
        """
        Інвалідує session_token у БД і очищує локальну сесію.
        Перехоплений токен стає недійсним одразу після logout,
        а не лише після закінчення таймауту.
        """

        user_info = app.storage.user.get('user_info', {})
        user_id = user_info.get('id')
        self.logger.debug('>>> Logout ' + user_info.get('username'))
        if user_id:
            try:
                self.auth_service.invalidate_session_token(user_id)
            except Exception as e:
                self.logger.warning(f"Не вдалося інвалідувати токен для user_id={user_id}: {e}")
        app.storage.user.clear()


    def has_access(self, module_name: str, action: str = PERM_READ) -> bool:
        from nicegui import app

        user_info = app.storage.user.get('user_info', None)
        if not user_info:
            return False

        perms = self.get_user_permissions(user_info.get('role'))
        module_perms = perms.get(module_name, {})

        return bool(module_perms.get(action, False))



    def get_current_context(self) -> RequestContext:
        user_info = app.storage.user.get('user_info', {})
        ctx = RequestContext(
            user_name=user_info.get('full_name') or user_info.get('username') or 'Гість',
            user_role=user_info.get('role'),
            user_id=user_info.get('id'),
            user_login=user_info.get('username'),
            last_activity=app.storage.user.get('last_activity', time.time()),
            session_token=user_info.get('session_token')
        )
        return ctx
