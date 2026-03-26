from nicegui import ui, app
from functools import wraps
import asyncio

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
                        # ЗБЕРІГАЄМО В СЕСІЮ
                        app.storage.user['authenticated'] = True
                        app.storage.user['user_info'] = user_data

                        ui.notify(f"Вітаємо, {user_data['full_name']}!", type='positive')
                        logger.debug('UI:' + ': LOGIN SUCCESS ' + str(user_data['full_name']))
                        ui.navigate.to('/')
                    else:
                        logger.debug('UI: ❌ : LOGIN FAILURE ' + username.value.strip())
                        ui.notify('Невірний логін або пароль', type='negative')

                # Вхід по кнопці Enter
                password.on('keydown.enter', try_login)
                ui.button('УВІЙТИ', on_click=try_login, icon='login').classes('w-full bg-blue-600 text-white shadow-md')


def require_access(auth_manager, module_name, action='read'):
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

            if not auth_manager.has_access(module_name, action):
                ui.notify('У вас немає доступу до цієї сторінки', type='negative')
                ui.navigate.to('/')
                return

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)

            return func(*args, **kwargs)

        return wrapper

    return decorator

def logout():
    """Функція для виходу з системи"""
    app.storage.user.clear()
    ui.notify('Ви вийшли з системи', type='info')
    ui.navigate.to('/login')