from nicegui import ui

from dics.security_config import PERM_READ, PERM_EDIT


# Якщо ви використовуєте menu() на головній сторінці, не забудьте його імпортувати
# from gui.components import menu

def create_nav_card(title: str, description: str, icon_name: str, route: str, color: str = 'blue'):
    """Компактна вертикальна картка з описом"""
    with ui.card().classes(
            f'cursor-pointer hover:shadow-md transition-shadow duration-300 border-t-4 border-{color}-500 w-full p-4 flex flex-col items-center text-center gap-1') \
            .on('click', lambda: ui.navigate.to(route)):
        ui.icon(icon_name, size='2.5rem', color=color).classes('mb-1')
        ui.label(title).classes('text-base font-bold text-gray-800 leading-tight')
        ui.label(description).classes('text-xs text-gray-500 leading-snug')


def render_home_page(auth_manager):
    # menu(auth_manager) # Розкоментуйте, якщо головна сторінка також містить верхнє меню

    with ui.column().classes('w-full items-center px-4 py-8 bg-gray-50 min-h-screen'):

        # 💡 Одна суцільна сітка без заголовків груп. По 5 карток у ряд на великих екранах (lg:grid-cols-5)
        grid_classes = 'w-full max-w-7xl gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5'

        with ui.grid().classes(grid_classes):

            # --- ПОШУК ТА ДАНІ ---
            if auth_manager.has_access('person', PERM_READ):
                create_nav_card('Пошук О/С', 'Глобальний пошук по базі військовослужбовців', 'search', '/search', 'blue')
            if auth_manager.has_access('search', PERM_READ):
                create_nav_card('Пошук Документів', 'Файловий пошук довідок по папцям в мережі', 'find_in_page', '/doc_files', 'blue')
            if auth_manager.has_access('search', PERM_READ) and auth_manager.has_access('person', PERM_READ):
                create_nav_card('Батч Пошук', 'Глобальний батч-пошук по списку прізвищ', 'manage_search', '/batch_search', 'blue')

        with ui.grid().classes(grid_classes):
            # --- ДОКУМЕНТООБІГ ---
            if auth_manager.has_access('doc_notif', PERM_READ):
                create_nav_card('Повідомлення', 'Формування повідомлень та витягів', 'description', '/doc_notif', 'green')
            if auth_manager.has_access('doc_support', PERM_READ):
                create_nav_card('Супровідні листи', 'Масова генерація пакетів супровідних документів', 'mark_email_unread', '/doc_support', 'green')
            if auth_manager.has_access('doc_dbr', PERM_READ):
                create_nav_card('На ДБР', 'Відправка справ на ДБР і очікування ЄРДР', 'gavel', '/doc_dbr', 'orange')

        with ui.grid().classes(grid_classes):
            if auth_manager.has_access('task', PERM_READ):
                create_nav_card('Задачі', 'Щоденні, щомісячні та беклог', 'checklist_rtl', '/tasks', 'yellow')
                create_nav_card('Inbox', 'Керування файлами в inbox', 'forward_to_inbox', '/inbox', 'yellow')
                create_nav_card('Календар', 'Розклад задач на місяць', 'calendar_month', '/calendar', 'yellow')

        with ui.grid().classes(grid_classes):
            # --- АНАЛІТИКА ---
            if auth_manager.has_access('report_units', PERM_READ):
                create_nav_card('Щоденний звіт', 'Детальна статистика СЗЧ та повернень за день', 'event_available', '/report_daily', 'purple')
                create_nav_card('Звіт по рокам', 'Статистика СЗЧ, загальна по роках', 'calendar_today', '/report_yearly', 'purple')
                create_nav_card('По підрозділам', 'Статистика СЗЧ по підрозділах (Додаток 2)', 'bar_chart', '/report_units', 'purple')
                create_nav_card('Чєкаємо на ЄРДР', 'Статистика по тим, хто чекає на ЄРДР', 'pending_actions', '/report_waiting_erdr', 'purple')
            if auth_manager.has_access('report_general', PERM_READ):
                create_nav_card('Загальний стан', 'Стан справ, закриті, призначені та інш. ', 'fact_check', '/report_general_state', 'purple')

        with ui.grid().classes(grid_classes):

            # --- СИСТЕМА ---
            if auth_manager.has_access('admin_panel', PERM_READ):
                create_nav_card('Користувачі', 'Користувачі та їх ролі', 'supervisor_account', '/admin/users', 'slate')
                create_nav_card('Доступи', 'Права доступу до модулів системи', 'admin_panel_settings', '/admin/permissions', 'slate')
                create_nav_card('Системні логи', 'Живий моніторинг роботи системи', 'terminal', '/logs', 'slate')
            if auth_manager.has_access('admin_panel', PERM_EDIT):
                create_nav_card('Індексація файлів', 'Просто подивись на ті графічки!', 'cached', '/admin/file_index', 'slate')
                create_nav_card('Налаштування', 'Глобальні параметри системи', 'settings', '/admin/settings', 'slate')


        ui.element('div').classes('flex-grow')

        with ui.row().classes('w-full justify-center items-center py-6 border-t border-gray-200 mt-8'):
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