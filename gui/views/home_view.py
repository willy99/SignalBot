from nicegui import ui

from dics.security_config import PERM_READ, PERM_EDIT, MODULE_PERSON, MODULE_SEARCH, MODULE_DOC_NOTIF, MODULE_DOC_SUPPORT, MODULE_DOC_DBR, MODULE_TASK, MODULE_REPORT_UNITS, \
    MODULE_REPORT_GENERAL, MODULE_ADMIN
from gui.auth_routes import logout
from gui.controllers.report_controller import ReportController
from gui.services.auth_manager import AuthManager

def create_nav_card(title: str, description: str, icon_name: str, route: str, color: str = 'blue'):
    """Компактна вертикальна картка з описом"""
    with ui.card().classes(
            f'cursor-pointer hover:shadow-md transition-shadow duration-300 border-t-4 border-{color}-500 w-full p-4 flex flex-col items-center text-center gap-1 bg-white/95 backdrop-blur-sm') \
            .on('click', lambda: ui.navigate.to(route)):
        ui.icon(icon_name, size='2.5rem', color=color).classes('mb-1')
        ui.label(title).classes('text-base font-bold text-gray-800 leading-tight')
        ui.label(description).classes('text-xs text-gray-500 leading-snug')


def render_home_page(auth_manager:AuthManager, report_ctrl: ReportController):
    can_search = auth_manager.has_access(MODULE_SEARCH, PERM_READ)
    if not can_search:
        logout(auth_manager)

    stats = report_ctrl.get_latest_dashboard_stats(auth_manager.get_current_context())
    bg_style = 'background-image: url("/static/images/bg_home.jpg"); background-size: cover; background-position: center; background-attachment: fixed;'

    with ui.element('div').classes('w-full min-h-screen relative').style(bg_style):
        ui.element('div').classes('absolute inset-0 bg-white/60 z-0')

        with ui.column().classes('w-full items-center px-4 py-8 min-h-screen relative z-10'):

            # --- КРОК 2: ВІДОБРАЖАЄМО ТАБЛИЦЮ СТАНУ (як у Daily Report) ---
            if stats:
                with ui.card().classes('w-full max-w-7xl bg-yellow-50 border-b mb-6 p-0 overflow-hidden'):
                    with ui.row().classes('w-full p-3 items-center justify-between bg-yellow-100'):
                        ui.label('⭐️ Загальний стан Військової частини (на основі останнього звіту)').classes('font-bold text-yellow-900 text-sm uppercase tracking-wide')
                        ui.label(f"Оновлено: {stats['updated_at']}").classes('text-[10px] text-yellow-700')

                    # Використовуємо ту саму логіку колонок, що і в daily_report
                    with ui.row().classes('w-full p-4 justify-around gap-4'):
                        def stat_item(label, value, color='gray-800'):
                            with ui.column().classes('items-center'):
                                ui.label(str(value)).classes(f'text-3xl font-black text-{color}')
                                ui.label(label).classes('text-[10px] uppercase text-gray-500 font-bold')

                        stat_item('Здійснили СЗЧ', stats['total_awol'])
                        stat_item('В розшуку', stats['in_search'], 'red-600')
                        stat_item('Повернулися', stats['returned'], 'green-600')
                        stat_item('В БРЕЗ', stats['res_returned'], 'green-600')
                        stat_item('В розпорядженні', stats['in_disposal'])

             # --- 2. СІТКА КАРТОК (Всі модулі) ---
            grid_classes = 'w-full max-w-7xl gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6'

            with ui.grid().classes(grid_classes):

                # ПОШУК
                if auth_manager.has_access(MODULE_PERSON, PERM_READ):
                    create_nav_card('Пошук О/С', 'База військовослужбовців', 'search', '/search', 'blue')
                if auth_manager.has_access(MODULE_SEARCH, PERM_READ):
                    create_nav_card('Батч Пошук', 'Пошук списком прізвищ', 'manage_search', '/batch_search', 'blue')
                    create_nav_card('Пошук файлів', 'Пошук у мережевих папках', 'find_in_page', '/doc_files', 'blue')

                # ПЛАНИ
                if auth_manager.has_access(MODULE_TASK, PERM_READ):
                    create_nav_card('Мої задачі', 'Поточні доручення', 'person_pin', '/tasks/today', 'yellow')
                    create_nav_card('Inbox/Outbox', 'Сходити на пошту', 'email', '/inbox', 'yellow')
                    create_nav_card('Календар', 'Графік дедлайнів', 'calendar_month', '/calendar', 'yellow')

                # ДОКУМЕНТИ
                if auth_manager.has_access(MODULE_DOC_NOTIF, PERM_READ):
                    create_nav_card('Повідомлення', 'Генерація сповіщень', 'description', '/doc_notif', 'green')
                if auth_manager.has_access(MODULE_DOC_SUPPORT, PERM_READ):
                    create_nav_card('Супровідні', 'Пакети документів', 'drive_file_move', '/doc_support', 'green')
                if auth_manager.has_access(MODULE_DOC_DBR, PERM_READ):
                    create_nav_card('На ДБР', 'Трекінг справ у ДБР', 'gavel', '/doc_dbr', 'green')

                # ЗВІТИ ТА АНАЛІТИКА
                if auth_manager.has_access(MODULE_REPORT_GENERAL, PERM_READ):
                    create_nav_card('Щоденний звіт', 'Статистика за добу', 'event_available', '/report_daily', 'purple')
                    create_nav_card('Звіт по підрозділам', 'Статистика за окремий рік по підрозділам', 'bar_chart', '/report_units', 'purple')
                    create_nav_card('Звіт по рокам', 'Загальна по рокам', 'event_note', '/report_yearly', 'purple')

                    create_nav_card('Загальний стан', 'Загальний стан', 'fact_check', '/report_general_state', 'purple')
                    create_nav_card('Теплова карта', 'Теплова карта СЗЧ', 'gradient', '/report_heatmap', 'purple')
                    create_nav_card('Динаміка', 'Помісячна дінамика СЗЧ', 'ssid_chart', '/report_monthly', 'purple')

                # ПОРЯДОК / БД
                if auth_manager.has_access(MODULE_REPORT_GENERAL, PERM_READ):
                    create_nav_card('Очікують ЄРДР', 'Контроль внесених справ', 'pending_actions', '/report_waiting_erdr', 'purple')
                    create_nav_card('Виправлення помилок', 'Де непорядок в базі', 'error', '/error_audit', 'purple')
                    if auth_manager.has_access(MODULE_REPORT_GENERAL, PERM_EDIT):
                        create_nav_card('Порівняння Excel', 'Звірка даних з зовнішнім Excel', 'difference', '/report_compare', 'indigo')

                # --- СИСТЕМА (Ось тут твої логи!) ---
                if auth_manager.has_access(MODULE_ADMIN, PERM_READ):
                    create_nav_card('Системні логи', 'Живий моніторинг помилок', 'terminal', '/logs', 'slate')
                    create_nav_card('Користувачі', 'Кішкомоти і бджілки системи', 'manage_accounts', '/admin/users', 'slate')
                    create_nav_card('Права доступу', 'Доступи та ролі', 'vpn_key', '/admin/permissions', 'slate')
                    create_nav_card('Індексація', 'Статус сховища', 'cached', '/admin/file_index', 'slate')
                    create_nav_card('Налаштування', 'Конфігурація системи', 'settings', '/admin/settings', 'slate')

            ui.element('div').classes('flex-grow')

            with ui.row().classes('w-full justify-center items-center py-6 border-t border-gray-200 mt-8'):
                with ui.row().classes('bg-white/80 px-6 py-2 rounded-full items-center gap-2 shadow-sm'):
                    ui.icon('pets', size='2.5rem', color='slate').classes('mb-1')
                    ui.html('''
                        <div class="text-gray-400 text-sm">
                            2026 (С) <a href="mailto:willy2005@gmail.com" 
                                        class="text-blue-400 hover:text-blue-600 transition-colors duration-200 font-medium"
                                        style="text-decoration: none;">
                                        Pashkinson
                                     </a>
                        </div>
                    ''')