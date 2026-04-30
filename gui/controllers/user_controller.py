from typing import Optional

from domain.user import User
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from datetime import datetime, timedelta
import string
import secrets
import config
from service.processing.MyWorkFlow import MyWorkFlow
from werkzeug.security import check_password_hash

from service.users.AuthService import AuthService
from service.users.UserService import UserService

class UserController:
    def __init__(self, workflow: MyWorkFlow, auth_manager: AuthManager):
        self.db = workflow.db
        self.log_manager = workflow.log_manager
        self.logger = self.log_manager.get_logger()
        self.user_service = UserService(self.db, workflow.signalClient, workflow.emailClient)
        self.auth_service = AuthService(self.db, self.user_service)

    def request_verification(self, ctx: RequestContext, contact_info: str, contact_type: str):
        """Етап 1: Працює в окремому потоці (через io_bound)"""
        self.logger.debug('>>> Запрос на верифікацію: ' + str(contact_info) + ' / ' + str(contact_type))

        pending = self.user_service.get_pending_info(ctx.user_id)
        now = datetime.now()

        # Анти-спам: якщо є активний (невичерпаний) код, відправлений менш ніж 60 сек тому — блокуємо
        if pending and pending.get('code_hash') and pending.get('expiry'):
            expiry = pending['expiry']
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry)
            if expiry > now:
                creation_time = expiry - timedelta(minutes=10)
                if (now - creation_time).total_seconds() < 60:
                    raise ValueError("Зачекайте хвилину перед наступною спробою")

        # Завжди генеруємо НОВИЙ код (оригінал не зберігається — тільки хеш,
        # тому повторне використання старого коду неможливе)
        code = ''.join(secrets.choice(string.digits) for _ in range(6))
        expiry = now + timedelta(minutes=10)
        self.user_service.update_user_pending_contact(ctx.user_id, contact_info, contact_type, code, expiry)
        try:
            if contact_type.lower() == 'email':
                self.user_service.send_code(contact_info, code)
            else:
                # Шлемо в Signal/Telegram через твій месенджер
                self.user_service.send_message(contact_info, f"Ваш код підтвердження: {code}")
            return True
        except Exception as e:
            self.logger.error(f"Помилка при відправці повідомлення: {e}")
            raise ValueError("Помилка при відправці повідомлення")

    def confirm_verification(self, ctx: RequestContext, entered_code: str):
        # 1. Перевіряємо, чи юзер вже не заблокований (на всяк випадок)
        user = self.user_service.get_user_by_id(ctx.user_id)
        if user.lockout_until and datetime.now() < datetime.fromisoformat(user.lockout_until):
            self.logger.error(f"Акаунт тимчасово заблоковано до {user.lockout_until}")
            raise ValueError(f"Акаунт тимчасово заблоковано до {user.lockout_until}")

        pending = self.user_service.get_pending_info(ctx.user_id)

        if not pending or not pending.get('code_hash'):
            raise ValueError("Дані для підтвердження не знайдені")

        # 2. ПЕРЕВІРКА ЧАСУ
        if datetime.now() > pending['expiry']:
            raise ValueError("Термін дії коду вичерпано")
        # 3. ПЕРЕВІРКА КОДУ через хеш (constant-time порівняння)
        if not check_password_hash(pending['code_hash'], entered_code):
            # Реєструємо провал
            attempts, lockout = self.auth_service.register_failed_attempt(ctx.user_id)

            if lockout:
                raise ValueError(f"Забагато спроб! Доступ заблоковано на {config.SECURITY_LOCKOUT_DURATION_MINS} хв.")

            left = config.SECURITY_MAX_ATTEMPTS - attempts
            raise ValueError(f"Невірний код! Залишилося спроб: {left}")


        # 4. УСПІХ — Код вірний
        if pending['type'].lower() == 'email':
            self.user_service.update_user_email(ctx.user_id, pending['contact'])
        else:
            self.user_service.update_user_phone(ctx.user_id, pending['contact'])

        # Скидаємо всі "гріхи" та очищуємо тимчасові дані
        self.auth_service.reset_failed_attempts(ctx.user_id)
        self.user_service.clear_pending(ctx.user_id)

        return True


    def get_user_profile(self, ctx: RequestContext) -> Optional[User]:
        """Отримує профіль для поточного контексту."""
        return self.user_service.get_user_by_id(ctx.user_id)

    def update_profile(self, ctx: RequestContext, full_name: str, use_2fa: bool):
        """Метод, який викликається кнопкою 'Зберегти'."""
        # Можна додати додаткову валідацію тут
        if len(full_name) > 100:
            raise ValueError("ПІБ занадто довге. До 100 символів, без фанатизму!")

        # Якщо користувач намагається ввімкнути 2FA, перевіряємо ще раз, чи є куди слати код
        if use_2fa:
            user = self.user_service.get_user_by_id(ctx.user_id)
            if not (user.email or user.phone):
                raise ValueError("Неможливо ввімкнути 2FA без підтвердженого контакту")

        return self.user_service.update_user_profile(ctx.user_id, full_name, use_2fa)