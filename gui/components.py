from nicegui import app
import urllib.parse

from gui.controllers.inbox_controller import InboxController
from gui.controllers.task_controller import TaskController
from config import CHECK_INBOX_EVERY_SEC
from gui.services.auth_manager import AuthManager
from dics.security_config import MODULE_DOC_SUPPORT, MODULE_DOC_DBR, MODULE_DOC_NOTIF, MODULE_PERSON, MODULE_REPORT_UNITS, MODULE_REPORT_GENERAL, MODULE_ADMIN

if not hasattr(app, 'alarmed_tasks'):
    app.alarmed_tasks = set()

from nicegui import ui, app, run
from gui.auth_routes import logout
from datetime import datetime
from gui.services.request_context import RequestContext
import config


class AppMenu:
    def __init__(self, auth_manager: AuthManager, task_controller: TaskController, inbox_controller: InboxController):
        # Ініціалізуємо один раз при старті сервера
        self.auth_manager = auth_manager
        self.task_ctrl = task_controller
        self.inbox_ctrl = inbox_controller

    def render(self, ctx: RequestContext):
        """Цей метод викликається на кожній сторінці для малювання меню"""
        ui.add_head_html('<link rel="stylesheet" href="/static/style.css">')

        # DIRTY Status registrant
        ui.add_head_html('''
                <script>
                    window.isDirty = false; // За замовчуванням сторінка "чиста"
                    window.addEventListener('beforeunload', function (e) {
                        if (window.isDirty) {
                            e.preventDefault();
                            e.returnValue = ''; // Тригер для нативного вікна браузера
                        }
                    });
                </script>
            ''')

        # Отримуємо дані юзера
        user_info = app.storage.user.get('user_info', {})
        user_role = user_info.get('role', '')

        with ui.header().classes('bg-slate-800 items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                if config.IS_DEV:
                    title = 'DEVMODE!!!'
                    props = 'color="red" stack'
                else:
                    title = 'А0224, 🏃‍♂️ВТІКАЧІ 👨‍🚀'
                    props = 'flat'
                ui.button(title, on_click=lambda: ui.navigate.to('/')) \
                    .props(props).classes('font-bold text-xl text-white normal-case')

                # ==========================================
                # 🌟 1. ІКОНКА INBOX (Нова логіка)
                # ==========================================
                with ui.button(icon='mail', on_click=lambda: ui.navigate.to('/inbox')).props('flat round color="white"') as inbox_btn:
                    # Червоний бейдж (персональні)
                    badge_personal = ui.badge(color='red').props('floating rounded').classes('text-xs font-bold')
                    badge_personal.set_visibility(False)

                    # Сірий бейдж (спільні)
                    badge_root = ui.badge(color='grey-5').props('floating rounded').classes(
                        'text-xs font-bold text-gray-800').style('top: auto; bottom: -4px;')
                    badge_root.set_visibility(False)

                    with ui.menu().classes('w-80 max-h-96 overflow-y-auto') as inbox_menu:
                        pass

                    # Асинхронна функція оновлення Інбоксу для конкретного юзера
                    async def update_inbox():
                        try:
                            # Викликаємо контролер через self.inbox_ctrl
                            inbox_data = await run.io_bound(self.inbox_ctrl.get_user_inbox_messages, ctx)
                            # inbox_data = {'personal_files': [], 'root_files':[]}
                            p_count = len(inbox_data['personal_files'])
                            r_count = len(inbox_data['root_files'])

                            if p_count > 0:
                                badge_personal.set_text(str(p_count))
                                badge_personal.set_visibility(True)
                            else:
                                badge_personal.set_visibility(False)

                            if r_count > 0:
                                badge_root.set_text(str(r_count))
                                badge_root.set_visibility(True)
                            else:
                                badge_root.set_visibility(False)

                            inbox_btn.set_visibility(True) # p_count > 0 or r_count > 0)
                        except Exception as e:
                            print(f"Помилка оновлення Inbox для {ctx.user_login}: {e}")

                    # Таймери оновлення
                    ui.timer(config.CHECK_INBOX_EVERY_SEC, update_inbox)
                    ui.timer(0.1, update_inbox, once=True)


                # --- 2. ІКОНКА ЗАДАЧ (Персональна) ---
                with ui.button(icon='assignment', on_click=lambda: ui.navigate.to('/tasks/today')).props(
                        'flat color=white text-color=gray-7'):

                    # 1. Бейдж для НОВИХ задач (стандартний floating - правий верхній кут)
                    badge_new = ui.badge(color='red').props('floating rounded').classes('text-xs font-bold')
                    badge_new.set_visibility(False)

                    # 2. Бейдж для задач В РОБОТІ (помаранчевий)
                    # Перебиваємо стандартний 'top' і прив'язуємо до 'bottom', щоб він висів знизу праворуч
                    badge_prog = ui.badge(color='orange-8').props('floating rounded').classes('text-xs font-bold').style(
                        'top: auto; bottom: -4px;')
                    badge_prog.set_visibility(False)

                    with ui.tooltip().classes('bg-gray-800 text-white text-sm'):
                        with ui.column().classes('gap-0'):
                            lbl_new = ui.label('Нових задач: 0')
                            lbl_prog = ui.label('В роботі: 0')

                    # Функція, яка буде викликатись кожні X секунд ДЛЯ ЦЬОГО ЮЗЕРА
                    async def update_my_tasks():
                        try:
                            # Робимо запит до БД в окремому потоці, щоб не блокувати UI
                            new_count, prog_count = await run.io_bound(self.task_ctrl.get_my_task_counts, ctx)

                            if new_count > 0:
                                badge_new.set_text(str(new_count))
                                badge_new.set_visibility(True)
                            else:
                                badge_new.set_visibility(False)

                            # Оновлюємо в роботі (помаранчевий бейдж)
                            if prog_count > 0:
                                badge_prog.set_text(str(prog_count))
                                badge_prog.set_visibility(True)
                            else:
                                badge_prog.set_visibility(False)

                            # Оновлюємо тултип
                            lbl_new.set_text(f'Нових задач: {new_count}')
                            lbl_prog.set_text(f'В роботі: {prog_count}')

                            # ==========================================
                            # 2. ЛОГІКА БУДИЛЬНИКА (ALARM)
                            # ==========================================
                            alarms = await run.io_bound(self.task_ctrl.get_my_alarms, ctx)

                            for alarm in alarms:
                                task_id = alarm['id']
                                # Якщо ми ще не "дзвонили" по цій задачі після перезапуску сервера
                                if task_id not in app.alarmed_tasks:
                                    app.alarmed_tasks.add(task_id)  # Записуємо, що вже продзвеніли

                                    # Показуємо велике вікно по центру екрану
                                    ui.notify(
                                        f"⏰ Просрачено!\nЗадача: {alarm['subject']}",
                                        type='negative',
                                        position='top',
                                        timeout=0,
                                        multi_line=True,
                                        close_button='Отримати догану'
                                    )

                                    # (Опціонально) Відтворюємо звук системного будильника через JS
                                    ui.run_javascript(
                                        "new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg').play().catch(e => console.log('Автовідтворення заблоковано браузером'));")
                        except Exception as e:
                            print(f"Помилка оновлення задач для юзера {ctx.user_login}: {e}")

                    # Запускаємо таймер тільки для цієї сесії (наприклад, раз на 15 секунд)
                    ui.timer(CHECK_INBOX_EVERY_SEC, update_my_tasks)

                    # Викликаємо функцію відразу при завантаженні сторінки, щоб не чекати 15 сек
                    ui.timer(0.1, update_my_tasks, once=True)

            def make_menu_item(title: str, icon_name: str, route: str):
                """Створює пункт меню з іконкою зліва та текстом."""
                with ui.menu_item(on_click=lambda: ui.navigate.to(route)):
                    with ui.row().classes('items-center gap-3 w-full'):
                        ui.icon(icon_name, size='sm').classes('text-gray-500')
                        ui.label(title).classes('text-gray-800 font-medium')

            with ui.row():

                # 🛡 Отримуємо дані поточного користувача з сесії
                user_info = app.storage.user.get('user_info', {})
                user_role = user_info.get('role', '')
                # Якщо є ПІБ - показуємо його, інакше показуємо логін, інакше "Гість"
                user_name = user_info.get('full_name') or user_info.get('username') or 'Гість'
                can_doc_support = self.auth_manager.has_access(MODULE_DOC_SUPPORT, 'read')
                can_doc_dbr = self.auth_manager.has_access(MODULE_DOC_DBR, 'read')
                can_doc_notif = self.auth_manager.has_access(MODULE_DOC_NOTIF, 'read')
                can_search_person = self.auth_manager.has_access(MODULE_PERSON, 'read')

                # 1. Пошук
                if can_search_person:
                    # Іконка лупи зліва, стрілочка вниз справа
                    with ui.button('Пошук', icon='search').props('flat text-white icon-right="expand_more"'):
                        with ui.menu():
                            make_menu_item('Пошук подій', 'search', '/search')
                            make_menu_item('Батч пошук людей', 'manage_search', '/batch_search')
                            if can_doc_support:
                                make_menu_item('Швидкий пошук документів', 'find_in_page', '/doc_files')

                # 2. Плани (Задачі та Календар)
                with ui.button('Плани', icon='follow_the_signs').props('flat text-white icon-right="expand_more"'):
                    with ui.menu():
                        make_menu_item('Мої задачі', 'person_pin', '/tasks/today')
                        make_menu_item('Всі задачі', 'assignment', '/tasks/all')
                        make_menu_item('Календар', 'calendar_month', '/calendar')

                # 2. Документація
                if can_doc_support or can_doc_notif:
                    with ui.button('Документація', icon='folder_copy').props('flat text-white icon-right="expand_more"'):
                        with ui.menu():
                            if can_doc_notif:
                                make_menu_item('Формування Повідомлень', 'description', '/doc_notif')
                            if can_doc_support:
                                make_menu_item('Формування Супроводів', 'drive_file_move', '/doc_support')
                            if can_doc_dbr:
                                make_menu_item('Відправка На ДБР', 'gavel', '/doc_dbr')


                # 4. Звіти
                can_report_units = self.auth_manager.has_access(MODULE_REPORT_UNITS, 'read')
                can_report_general = self.auth_manager.has_access(MODULE_REPORT_GENERAL, 'read')
                if can_report_units or can_report_general:
                    with ui.button('Звіти', icon='analytics').props('flat text-white icon-right="expand_more"'):
                        with ui.menu():
                            if can_report_units:
                                make_menu_item('Звіт по підрозділам', 'bar_chart', '/report_units')
                            if can_report_general:
                                make_menu_item('Звіт по рокам', 'event_note', '/report_yearly')
                            if can_report_general:
                                make_menu_item('Дублікати прізвищ', 'people_outline', '/report_name_dups')
                            if can_report_general:
                                make_menu_item('Чекаємо на ЄРДР', 'pending_actions', '/report_waiting_erdr')
                            if can_report_general:
                                make_menu_item('Щоденний звіт', 'event_available', '/report_daily')

                # 5. Адмінка
                if self.auth_manager.has_access(MODULE_ADMIN, 'read'):
                    # Іконка щита переїхала наліво, а стрілочка вниз тепер справа
                    with ui.button('Адмінка', icon='admin_panel_settings').props(
                            'flat text-yellow-400 font-bold icon-right="expand_more"'):
                        with ui.menu():
                            make_menu_item('Права доступу', 'vpn_key', '/admin/permissions')
                            make_menu_item('Користувачі', 'manage_accounts', '/admin/users')
                            make_menu_item('Логи', 'history', '/logs')
                            make_menu_item('Конфіг Системи', 'build', '/admin/settings')

                # === ПРОФІЛЬ ТА ВИХІД ===
                ui.separator().props('vertical dark').classes('mx-2 h-8')

                user_info = app.storage.user.get('user_info', {})
                user_name = user_info.get('full_name') or user_info.get('username') or 'Гість'

                with ui.row().classes('items-center gap-2 mr-2'):
                    ui.icon('account_circle', color='gray-300', size='sm')
                    ui.label(user_name).classes('text-white font-medium')

                ui.button(icon='logout', on_click=logout).props('flat round color="red-400"').tooltip('Вийти з системи')

        inject_watermark()

def inject_watermark():
    """Створює захисний водяний знак поверх всього екрану."""
    # Отримуємо дані користувача з сесії
    user_info = app.storage.user.get('user_info', {})
    user_name = user_info.get('full_name') or user_info.get('username') or 'Невідомий користувач'

    # Генеруємо поточний час (можна додати IP, якщо є доступ до Request)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    watermark_text = f"{user_name} | {current_time}"

    # Створюємо SVG-зображення (текст під кутом)
    # rgba(150, 150, 150, 0.15) - налаштовує прозорість (0.15 - це 15%)
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='350' height='200'>
        <text x='50%' y='50%' 
              dominant-baseline='middle' text-anchor='middle' 
              transform='rotate(-30, 175, 100)' 
              fill='rgba(225, 225, 225, 0.15)' 
              font-size='16' font-family='sans-serif' font-weight='bold'>
            {watermark_text}
        </text>
    </svg>
    """

    # Кодуємо SVG для безпечної вставки у CSS
    encoded_svg = urllib.parse.quote(svg)

    # Інжектимо CSS стиль для нашого оверлею
    ui.add_head_html(f'''
        <style>
            .security-watermark {{
                position: fixed;
                top: 0;
                left: 0;
                width: 150vw;
                height: 150vh;
                pointer-events: none; /* НАЙГОЛОВНІШЕ: дозволяє клікати "крізь" текст */
                z-index: 9999;        /* Кладемо шар поверх таблиць і модальних вікон */
                background-image: url("data:image/svg+xml;utf8,{encoded_svg}");
                background-repeat: repeat; /* Замощуємо весь екран */
            }}
        </style>
    ''')

    # Додаємо сам елемент на сторінку
    ui.element('div').classes('security-watermark')