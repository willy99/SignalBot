from nicegui import ui, app, context
from functools import wraps
import asyncio

from dics.security_config import PERM_READ
from gui.services.auth_manager import AuthManager


def create_login_page(auth_manager, log_manager):
    logger = log_manager.get_logger()
    """Створює сторінку /login"""

    @ui.page('/login')
    def login_page():
        # Якщо користувач вже авторизований, перекидаємо на головну
        if app.storage.user.get('authenticated', False):
            ui.navigate.to('/')
            return

        # Дизайн сторінки логіну
        with ui.column().classes('w-full h-screen items-center justify-center bg-slate-100'):
            with ui.card().classes('w-96 p-6 shadow-xl rounded-xl'):
                ui.label('А0224, 🏃‍♂️ВТІКАЧІ 👨‍').classes('text-2xl font-bold mb-6 text-center w-full text-slate-800')

                username = ui.input('Логін').classes('w-full mb-2').props('autofocus outlined')
                password = ui.input('Пароль').classes('w-full mb-6').props('type=password outlined')

                def try_login():
                    u = username.value.strip() if username.value else ''
                    p = password.value.strip() if password.value else ''

                    if not u or not p:
                        ui.notify('Введіть логін та пароль', type='warning')
                        return

                    # Звертаємось до нашого AuthManager
                    user_data = auth_manager.authenticate(u, p)

                    if user_data:
                        ui.notify(f"Вітаємо, {user_data.full_name}!", type='positive')
                        logger.debug('UI:' + ': LOGIN SUCCESS ' + str(user_data.full_name))
                        ui.navigate.to('/')
                    else:
                        logger.debug('UI: ❌ : LOGIN FAILURE ' + username.value.strip())
                        ui.notify('Невірний логін або пароль', type='negative')

                # Вхід по кнопці Enter
                password.on('keydown.enter', try_login)
                ui.button('УВІЙТИ', on_click=try_login, icon='login').classes('w-full bg-blue-600 text-white shadow-md')


def refresh_session_method(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Беремо менеджер безпосередньо з екземпляра контролера (self)
        manager: AuthManager = getattr(self, 'auth_manager', None)

        print('>>> manager ' + str(manager))

        if not manager:
            # Якщо забули прокинути менеджер в self, просто виконуємо
            return func(self, *args, **kwargs)

        # Перевірка через ваш існуючий метод
        if not manager.check_session():
            # check_session вже має доступ до app.storage.user
            # і оновить час, якщо все ок
            return None

        return func(self, *args, **kwargs)

    return wrapper

def refresh_session(auth_manager: AuthManager):
    """
    Декоратор для методів контролера.
    Явно використовує auth_manager для перевірки та оновлення сесії.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Перевірка авторизації через системний storage
            if not app.storage.user.get('authenticated', False):
                ui.notify('Сесія недійсна. Увійдіть знову', type='warning')
                ui.navigate.to('/login')
                return

            # 2. Оновлення сесії через переданий менеджер
            # check_session() оновить time.time() всередині storage.user
            if not auth_manager.check_session():
                ui.notify('Сесію завершено через неактивність', type='warning')
                ui.navigate.to('/login')
                return

            # 3. Виконання самого методу
            if asyncio.iscoroutinefunction(func):
                return func(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator

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
                if not auth_manager.check_session():
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