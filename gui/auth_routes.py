from nicegui import ui, app, run
from functools import wraps
import asyncio

import config
from dics.security_config import PERM_READ
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
import time


def create_login_page(auth_manager, user_ctrl, log_manager):
    logger = log_manager.get_logger()

    @ui.page('/login')
    def login_page():
        if app.storage.user.get('authenticated', False):
            ui.navigate.to('/')
            return

        # Локальний стан сторінки логіну
        state = {
            'needs_2fa': False,
            'username': '',
            'loading': False
        }

        with (ui.column().classes('w-full h-screen items-center justify-center bg-slate-100')):
            with ui.card().classes('w-96 p-6 shadow-xl rounded-xl') as card:
                ui.label('А0224, 🏃‍♂️ВТІКАЧІ 👨‍🚀').classes('text-2xl font-bold mb-6 text-center w-full text-slate-800')

                # --- БЛОК 1: ЛОГІН/ПАРОЛЬ ---
                login_container = ui.column().classes('w-full')
                with login_container:
                    username = ui.input('Логін').classes('w-full mb-2').props('outlined')
                    password = ui.input('Пароль').classes('w-full mb-6').props('type=password outlined')

                    async def try_login():
                        u, p = username.value.strip(), password.value.strip()
                        if not u or not p: return

                        try:
                            res = await auth_manager.authenticate(u, p)  # Тепер це async через execute
                            if res and res['status'] == '2fa_required':
                                state['username'] = u
                                print(str(res))
                                temp_ctx = RequestContext(
                                    user_id=res['user'].id,
                                    user_login=res['user'].username,
                                    user_role=res['user'].role,
                                    user_name=res['user'].username
                                )
                                await run.io_bound(
                                    user_ctrl.request_verification,
                                    temp_ctx,
                                    res['send_to'],
                                    res['send_type']
                                )

                                login_container.set_visibility(False)
                                otp_container.set_visibility(True)
                                ui.notify('Введіть код підтвердження', type='info')

                            elif res and res['status'] == 'success':
                                ui.navigate.to('/')
                        except Exception as e:
                            ui.notify(str(e), type='negative')

                    ui.button('УВІЙТИ', on_click=try_login).classes('w-full bg-blue-600 text-white')

                # --- БЛОК 2: ВВЕДЕННЯ OTP ---
                otp_container = ui.column().classes('w-full')
                otp_container.set_visibility(False)

                with otp_container:
                    ui.label('Введіть код із Signal/Email').classes('text-sm mb-4 text-center')
                    otp_code = ui.input('Код').classes('w-full mb-4').props('outlined mask="######"')

                    async def verify_otp():
                        try:
                            # Викликаємо confirm_verification
                            success = await run.io_bound(user_ctrl.confirm_verification,
                                                                 auth_manager.get_current_context(),
                                                                 entered_code=otp_code.value)
                            if success:
                                app.storage.user['authenticated'] = True
                                ui.notify('Доступ дозволено!', type='positive')
                                ui.navigate.to('/')
                        except Exception as e:
                            ui.notify(str(e), type='negative')

                    ui.button('ПІДТВЕРДИТИ КОД', on_click=verify_otp).classes('w-full bg-green-600 text-white')
                    ui.button('Назад', on_click=lambda: ui.navigate.to('/login')).props('flat').classes('w-full text-xs mt-2')

                # Обробка Enter для обох випадків
                password.on('keydown.enter', try_login)
                otp_code.on('keydown.enter', verify_otp)

def refresh_session_method(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Шукаємо ctx серед позиційних аргументів або в kwargs
        ctx: RequestContext = next((a for a in args if isinstance(a, RequestContext)), kwargs.get('ctx'))

        if ctx:
            print(f'>>> [THREAD CHECK] User: {ctx.user_login}, Last seen: {ctx.last_activity_str}')

            # Перевіряємо час із ctx, а не з app.storage
            if time.time() - ctx.last_activity > config.SECURITY_SESSION_TIMEOUT:
                self.logger.warning(f"Session expired in thread for {ctx.user_login}")
                return None

                # Оновлюємо час у самому об'єкті контексту (локально для потоку)
            ctx.last_activity = time.time()

        return func(self, *args, **kwargs)

    return wrapper

def require_access(auth_manager, module_name, action=PERM_READ):
    """
    Декоратор для захисту маршрутів (сторінок).
    Підтримує як звичайні (def), так і асинхронні (async def) функції.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not app.storage.user.get('authenticated', False):
                ui.notify('Будь ласка, увійдіть у систему', type='warning')
                ui.navigate.to('/login')
                return
            else:
                if not auth_manager.check_session(auth_manager.get_current_context()):
                    ui.notify('Сесію завершено через неактивність', type='warning')
                    ui.navigate.to('/login')
                    return

            if not auth_manager.has_access(module_name, action):
                print(f"DEBUG: Access denied for {module_name}:{action}")  # Подивитись в консоль
                ui.notify('У вас немає доступу до цієї сторінки', type='negative')
                ui.navigate.to('/')
                return

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)

            return func(*args, **kwargs)

        return wrapper

    return decorator

def logout(auth_manager: AuthManager):
    """Функція для виходу з системи"""
    auth_manager.logout()
    ui.notify('Ви вийшли з системи', type='info')
    ui.navigate.to('/login')