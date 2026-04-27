from nicegui import app
import urllib.parse

from config import PROJECT_TITLE
from gui.controllers.inbox_controller import InboxController
from gui.controllers.person_controller import PersonController
from gui.controllers.task_controller import TaskController
from gui.services.auth_manager import AuthManager
from dics.security_config import MODULE_DOC_SUPPORT, MODULE_DOC_DBR, MODULE_DOC_NOTIF, MODULE_PERSON, MODULE_REPORT_UNITS, MODULE_REPORT_GENERAL, MODULE_ADMIN, PERM_READ, PERM_EDIT

if not hasattr(app, 'alarmed_tasks'):
    app.alarmed_tasks = set()

from nicegui import ui, app, run
from gui.auth_routes import logout
from datetime import datetime
import config


class AppMenu:
    def __init__(self, auth_manager: AuthManager, task_controller: TaskController, inbox_controller: InboxController, person_controller: PersonController):
        self.auth_manager = auth_manager
        self.task_ctrl = task_controller
        self.inbox_ctrl = inbox_controller
        self.person_ctrl = person_controller

    def render(self, auth_manager: AuthManager):
        dark = ui.dark_mode()
        ui.add_head_html('<link rel="stylesheet" href="/static/style.css">')
        ui.add_head_html(
            '<style>.animate-spin { animation: spin 1s linear infinite; } @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }</style>')

        ui.add_head_html('''
                <script>
                    window.isDirty = false;
                    window.addEventListener('beforeunload', function (e) {
                        if (window.isDirty) {
                            e.preventDefault();
                            e.returnValue = '';
                        }
                    });
                </script>
            ''')

        # Отримуємо дані юзера та дозволи
        user_info = app.storage.user.get('user_info', {})
        user_role = user_info.get('role', '')
        user_name = user_info.get('full_name') or user_info.get('username') or 'Гість'

        can_doc_support = self.auth_manager.has_access(MODULE_DOC_SUPPORT, PERM_READ)
        can_doc_dbr = self.auth_manager.has_access(MODULE_DOC_DBR, PERM_READ)
        can_doc_notif = self.auth_manager.has_access(MODULE_DOC_NOTIF, PERM_READ)
        can_search_person = self.auth_manager.has_access(MODULE_PERSON, PERM_READ)
        can_report_units = self.auth_manager.has_access(MODULE_REPORT_UNITS, PERM_READ)
        can_report_general = self.auth_manager.has_access(MODULE_REPORT_GENERAL, PERM_READ)
        can_report_general_edit = self.auth_manager.has_access(MODULE_REPORT_GENERAL, PERM_EDIT)
        can_admin = self.auth_manager.has_access(MODULE_ADMIN, PERM_READ)

        # ==========================================
        # 📱 МОБІЛЬНЕ МЕНЮ (БОКОВА ПАНЕЛЬ - DRAWER)
        # ==========================================
        # Drawer створюється до Header, але він "прикріплений" до правої частини екрану
        with ui.right_drawer(fixed=True).props('bordered').classes('bg-slate-50 p-0') as mobile_drawer:
            mobile_drawer.hide()  # За замовчуванням сховано

            # Шапка профілю в мобільному меню
            with ui.row().classes('w-full bg-slate-800 p-4 items-center gap-3 m-0'):
                ui.icon('account_circle', size='md', color='white')
                with ui.column().classes('gap-0'):
                    ui.label(user_name).classes('text-white font-bold text-sm')
                    ui.label(user_role).classes('text-slate-400 text-xs')

            # Хелпер для створення кнопок всередині "гармошки"
            def make_mobile_item(title: str, icon_name: str, route: str):
                ui.button(title, icon=icon_name, on_click=lambda: ui.navigate.to(route)) \
                    .props('flat align="left"').classes('w-full no-caps text-gray-700 ml-2 font-medium')

            def make_mobile_label(title: str):
                ui.label(title).classes('text-[10px] font-bold text-gray-400 uppercase tracking-wider ml-6 mt-2 mb-1')

            with ui.column().classes('w-full gap-0 p-2'):
                if can_search_person:
                    with ui.expansion('Пошук', icon='search').classes('w-full border-b border-gray-200').props('header-class="font-bold text-slate-800"'):
                        make_mobile_item('Пошук подій', 'search', '/search')
                        make_mobile_item('Розширений пошук', 'filter_alt', '/enhanced_search')
                        make_mobile_item('Батч пошук', 'manage_search', '/batch_search')
                        make_mobile_item('Швидкий пошук ДД', 'find_in_page', '/doc_files')
                        make_mobile_item('Швидкий пошук ЄРДР', 'policy', '/erdr_files')

                with ui.expansion('Плани', icon='follow_the_signs').classes('w-full border-b border-gray-200').props('header-class="font-bold text-slate-800"'):
                    make_mobile_item('Мої задачі', 'person_pin', '/tasks/today')
                    make_mobile_item('Всі задачі', 'assignment', '/tasks/all')
                    make_mobile_item('Календар', 'calendar_month', '/calendar')

                if can_doc_support or can_doc_notif:
                    with ui.expansion('Документація', icon='folder_copy').classes('w-full border-b border-gray-200').props('header-class="font-bold text-slate-800"'):
                        if can_doc_notif:
                            make_mobile_item('Формування Повідомлень', 'description', '/doc_notif')
                        if can_doc_support:
                            make_mobile_item('Формування Супроводів', 'drive_file_move', '/doc_support')
                        if can_doc_dbr:
                            make_mobile_item('Відправка На ДБР', 'gavel', '/doc_dbr')

                if can_report_units or can_report_general:
                    with ui.expansion('Звіти', icon='analytics').classes('w-full border-b border-gray-200').props('header-class="font-bold text-slate-800"'):
                        if can_report_general or can_report_units:
                            make_mobile_label('Загальні звіти')
                            if can_report_general:
                                make_mobile_item('Щоденний звіт', 'event_available', '/report_daily')
                            if can_report_units:
                                make_mobile_item('Звіт по підрозділам', 'bar_chart', '/report_units')
                            if can_report_general:
                                make_mobile_item('Звіт по рокам', 'event_note', '/report_yearly')
                        if can_report_general:
                            make_mobile_label('Аналітика та прогнози')
                            make_mobile_item('Загальний стан', 'fact_check', '/report_general_state')
                            make_mobile_item('Теплова карта СЗЧ', 'gradient', '/report_heatmap')
                            make_mobile_item('Помісячна дінамика', 'ssid_chart', '/report_monthly')
                        if can_report_general or can_report_general_edit:
                            make_mobile_label('Приводимо в порядок (БД)')
                            if can_report_general_edit and can_report_general:
                                make_mobile_item('Пошук помилок', 'error', '/error_audit')
                            if can_report_general:
                                make_mobile_item('Дублікати прізвищ', 'people_outline', '/report_name_dups')
                                make_mobile_item('Чекаємо на ЄРДР', 'pending_actions', '/report_waiting_erdr')
                            if can_report_general_edit:
                                make_mobile_item('ЄРДР КРАМ', 'library_books', '/report_erdr_kram')
                                make_mobile_item('Порівняння документів', 'difference', '/report_compare')

                if can_admin:
                    with ui.expansion('Адмінка', icon='admin_panel_settings').classes('w-full border-b border-gray-200').props('header-class="font-bold text-yellow-600"'):
                        make_mobile_item('Права доступу', 'vpn_key', '/admin/permissions')
                        make_mobile_item('Користувачі', 'manage_accounts', '/admin/users')
                        make_mobile_item('Логи', 'history', '/logs')
                        make_mobile_item('Конфіг Системи', 'build', '/admin/settings')
                        make_mobile_item('Індексація файлів', 'cached', '/admin/file_index')

                with ui.expansion('Налаштування', icon='settings').classes('w-full border-b border-gray-200').props('header-class="font-bold text-slate-800"'):
                    make_mobile_item('Налаштування профілю', 'manage_accounts', '/user_settings')
                    make_mobile_item('2FA', 'security', '/user_settings_2fa')
                    ui.button('Вийти з системи', icon='logout', on_click=lambda: logout(self.auth_manager)) \
                        .props('flat align="left" color="negative"').classes('w-full no-caps ml-2 mt-2 font-bold')

        # ==========================================
        # 💻 ГОЛОВНИЙ HEADER
        # ==========================================
        with ui.header().classes('bg-slate-800 items-center justify-between px-2 sm:px-4'):

            # --- ЛІВА ЧАСТИНА (Логотип + Синхронізація) ---
            with ui.row().classes('items-center gap-1 sm:gap-2 flex-nowrap'):
                if config.IS_DEV:
                    title = 'DEVMODE!'
                    props = 'color="red" stack'
                else:
                    title = '🏃‍♂️' + PROJECT_TITLE + ' 👨‍🚀'
                    props = 'flat'

                # На дуже малих екранах текст може бути трохи меншим
                ui.button(title, on_click=lambda: ui.navigate.to('/')) \
                    .props(props).classes('font-bold text-md sm:text-xl text-white normal-case shrink-0')

                with ui.button(icon='cloud_sync', on_click=lambda: handle_sync()) \
                        .props('flat round color="white"').classes('transition-transform') as sync_btn:
                    ui.tooltip('Оновити дані з Excel').classes('bg-gray-800')

                    async def handle_sync():
                        sync_btn.classes('animate-spin')
                        ui.notify('Почато синхронізацію з базою...', color='info', pos='bottom-right', icon='cloud_sync')
                        try:
                            success = await auth_manager.execute(self.person_ctrl.sync, auth_manager.get_current_context())
                            if success:
                                ui.notify('Дані успішно синхронізовано!', color='positive', pos='bottom-right', icon='done')
                            else:
                                ui.notify('Помилка при синхронізації', color='negative')
                        except Exception as e:
                            ui.notify(f'Критична помилка: {str(e)}', color='negative')
                        finally:
                            sync_btn.classes(remove='animate-spin')

            # --- ПРАВА ЧАСТИНА (Іконки сповіщень + Десктоп Меню + Гамбургер) ---
            with ui.row().classes('items-center gap-1 sm:gap-2 flex-nowrap'):

                # 1. ІКОНКА INBOX (Завжди видима)
                with ui.button(icon='mail', on_click=lambda: ui.navigate.to('/inbox')).props('flat round color="white"') as inbox_btn:
                    badge_personal = ui.badge(color='red').props('floating rounded').classes('text-[10px] font-bold')
                    badge_personal.set_visibility(False)
                    badge_root = ui.badge(color='grey-5').props('floating rounded').classes('text-[10px] font-bold text-gray-800').style('top: auto; bottom: -4px;')
                    badge_root.set_visibility(False)

                    async def update_inbox():
                        try:
                            if not app.storage.user.get('authenticated'): return
                            inbox_data = await run.io_bound(self.inbox_ctrl.get_user_inbox_messages, auth_manager.get_current_context())
                            if not inbox_data: return

                            p_count, r_count = len(inbox_data['personal_files']), len(inbox_data['root_files'])
                            badge_personal.set_text(str(p_count))
                            badge_personal.set_visibility(p_count > 0)
                            badge_root.set_text(str(r_count))
                            badge_root.set_visibility(r_count > 0)
                        except Exception as e:
                            pass

                    ui.timer(config.CHECK_INBOX_EVERY_SEC, update_inbox)
                    ui.timer(0.1, update_inbox, once=True)

                # 2. ІКОНКА ЗАДАЧ (Завжди видима)
                with ui.button(icon='assignment', on_click=lambda: ui.navigate.to('/tasks/today')).props('flat color=white'):
                    badge_new = ui.badge(color='red').props('floating rounded').classes('text-[10px] font-bold')
                    badge_new.set_visibility(False)
                    badge_prog = ui.badge(color='orange-8').props('floating rounded').classes('text-[10px] font-bold').style('top: auto; bottom: -4px;')
                    badge_prog.set_visibility(False)

                    with ui.tooltip().classes('bg-gray-800 text-white text-sm'):
                        with ui.column().classes('gap-0'):
                            lbl_new = ui.label('Нових задач: 0')
                            lbl_prog = ui.label('В роботі: 0')

                    async def update_my_tasks():
                        try:
                            if not app.storage.user.get('authenticated') or not auth_manager.get_current_context(): return
                            counts = await run.io_bound(self.task_ctrl.get_my_task_counts, auth_manager.get_current_context())
                            if not counts: return
                            new_count, prog_count = counts

                            badge_new.set_text(str(new_count))
                            badge_new.set_visibility(new_count > 0)
                            badge_prog.set_text(str(prog_count))
                            badge_prog.set_visibility(prog_count > 0)
                            lbl_new.set_text(f'Нових задач: {new_count}')
                            lbl_prog.set_text(f'В роботі: {prog_count}')

                            alarms = await run.io_bound(self.task_ctrl.get_my_alarms, auth_manager.get_current_context())
                            for alarm in alarms:
                                task_id = alarm['id']
                                if task_id not in app.alarmed_tasks:
                                    app.alarmed_tasks.add(task_id)
                                    ui.notify(f"⏰ Просрачено!\nЗадача: {alarm['subject']}", type='negative', position='top', timeout=0, multi_line=True,
                                              close_button='Отримати догану')
                                    ui.run_javascript("new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg').play().catch(e => console.log('Audio blocked'));")
                        except Exception as e:
                            pass

                    ui.timer(config.CHECK_INBOX_EVERY_SEC, update_my_tasks)
                    ui.timer(0.1, update_my_tasks, once=True)

                # ==========================================
                # 🖥 ДЕСКТОПНЕ МЕНЮ (ХОВАЄТЬСЯ НА МОБІЛЬНИХ lg:hidden -> hidden lg:flex)
                # ==========================================
                def make_menu_item(title: str, icon_name: str, route: str):
                    with ui.menu_item(on_click=lambda: ui.navigate.to(route)):
                        with ui.row().classes('items-center gap-3 w-full'):
                            ui.icon(icon_name, size='sm').classes('text-primary')
                            ui.label(title).classes('font-medium')

                def make_menu_label(title: str):
                    ui.separator().classes('my-1')
                    with ui.menu_item().props('disabled').classes('q-py-none'):
                        ui.label(title).classes('text-xs font-bold text-gray-500 uppercase tracking-wider ml-1')

                # Огортаємо всі пункти десктопного меню у hidden lg:flex (видимо тільки на екранах > 1024px)
                with ui.row().classes('hidden lg:flex items-center gap-1'):

                    if can_search_person:
                        with ui.button('Пошук', icon='search').props('flat text-white icon-right="expand_more"'):
                            with ui.menu():
                                make_menu_item('Пошук подій', 'search', '/search')
                                make_menu_item('Розширедний пошук', 'filter_alt', '/enhanced_search')
                                make_menu_item('Батч пошук', 'manage_search', '/batch_search')
                                make_menu_item('Швидкий пошук ДД', 'find_in_page', '/doc_files')
                                make_menu_item('Швидкий пошук ЄРДР', 'policy', '/erdr_files')

                    with ui.button('Плани', icon='follow_the_signs').props('flat text-white icon-right="expand_more"'):
                        with ui.menu():
                            make_menu_item('Мої задачі', 'person_pin', '/tasks/today')
                            make_menu_item('Всі задачі', 'assignment', '/tasks/all')
                            make_menu_item('Календар', 'calendar_month', '/calendar')

                    if can_doc_support or can_doc_notif:
                        with ui.button('Документація', icon='folder_copy').props('flat text-white icon-right="expand_more"'):
                            with ui.menu():
                                if can_doc_notif:
                                    make_menu_item('Формування Повідомлень', 'description', '/doc_notif')
                                if can_doc_support:
                                    make_menu_item('Формування Супроводів', 'drive_file_move', '/doc_support')
                                if can_doc_dbr:
                                    make_menu_item('Відправка На ДБР', 'gavel', '/doc_dbr')

                    if can_report_units or can_report_general:
                        with ui.button('Звіти', icon='analytics').props('flat text-white icon-right="expand_more"'):
                            with ui.menu().classes('w-72'):
                                if can_report_general or can_report_units:
                                    make_menu_label('Загальні звіти')
                                    if can_report_general:
                                        make_menu_item('Щоденний звіт', 'event_available', '/report_daily')
                                    if can_report_units:
                                        make_menu_item('Звіт по підрозділам', 'bar_chart', '/report_units')
                                    if can_report_general:
                                        make_menu_item('Звіт по рокам', 'event_note', '/report_yearly')
                                if can_report_general:
                                    make_menu_label('Аналітика та прогнози')
                                    make_menu_item('Загальний стан', 'fact_check', '/report_general_state')
                                    make_menu_item('Теплова карта СЗЧ', 'gradient', '/report_heatmap')
                                    make_menu_item('Помісячна дінамика', 'ssid_chart', '/report_monthly')
                                if can_report_general or can_report_general_edit:
                                    make_menu_label('Приводимо в порядок (БД)')
                                    if can_report_general_edit and can_report_general:
                                        make_menu_item('Пошук помилок', 'error', '/error_audit')
                                    if can_report_general:
                                        make_menu_item('Дублікати прізвищ', 'people_outline', '/report_name_dups')
                                        make_menu_item('Чекаємо на ЄРДР', 'pending_actions', '/report_waiting_erdr')
                                    if can_report_general_edit:
                                        make_menu_item('ЄРДР КРАМ', 'library_books', '/report_erdr_kram')
                                        make_menu_item('Порівняння документів', 'difference', '/report_compare')

                    if can_admin:
                        with ui.button('Адмінка', icon='admin_panel_settings').props('flat text-yellow-400 font-bold icon-right="expand_more"'):
                            with ui.menu():
                                make_menu_item('Права доступу', 'vpn_key', '/admin/permissions')
                                make_menu_item('Користувачі', 'manage_accounts', '/admin/users')
                                make_menu_item('Логи', 'history', '/logs')
                                make_menu_item('Конфіг Системи', 'build', '/admin/settings')
                                make_menu_item('Індексація файлів', 'cached', '/admin/file_index')

                    ui.separator().props('vertical dark').classes('mx-2 h-8')

                    with ui.button(icon='account_circle').props('flat text-white no-caps icon-right="expand_more"').classes('mr-2') as profile_btn:
                        ui.label(user_name).classes('ml-2 font-medium')
                        with ui.menu().classes('w-64'):
                            with ui.menu_item(on_click=lambda: ui.navigate.to('/user_settings')):
                                with ui.row().classes('items-center gap-3'):
                                    ui.icon('manage_accounts', color='primary')
                                    ui.label('Налаштування профілю')
                            with ui.menu_item(on_click=lambda: ui.navigate.to('/user_settings_2fa')):
                                with ui.row().classes('items-center gap-3'):
                                    ui.icon('security', color='warning')
                                    ui.label('Двофакторна автентифікація')
                            ui.separator()
                            with ui.menu_item(on_click=lambda: logout(self.auth_manager)):
                                with ui.row().classes('items-center gap-3'):
                                    ui.icon('logout', color='negative')
                                    ui.label('Вийти з системи')

                # ==========================================
                # 🍔 КНОПКА ГАМБУРГЕР (Видима ТІЛЬКИ на мобільних lg:hidden)
                # ==========================================
                ui.button(icon='menu', on_click=mobile_drawer.toggle).props('flat round color="white"').classes('lg:hidden ml-1')

        inject_watermark()


def inject_watermark():
    user_info = app.storage.user.get('user_info', {})
    user_name = user_info.get('full_name') or user_info.get('username') or 'Невідомий користувач'
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    watermark_text = f"{user_name} | {current_time}"

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
    encoded_svg = urllib.parse.quote(svg)
    ui.add_head_html(f'''
        <style>
            .security-watermark {{
                position: fixed;
                top: 0; left: 0; width: 150vw; height: 150vh;
                pointer-events: none;
                z-index: 9999;
                background-image: url("data:image/svg+xml;utf8,{encoded_svg}");
                background-repeat: repeat;
            }}
        </style>
    ''')
    ui.element('div').classes('security-watermark')