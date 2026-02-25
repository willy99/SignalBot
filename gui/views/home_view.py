from nicegui import ui


# Якщо ви використовуєте menu() на головній сторінці, не забудьте його імпортувати
# from gui.components import menu

def create_nav_card(title: str, description: str, icon_name: str, route: str, color: str = 'blue'):
    """Функція для створення красивої клікабельної картки"""
    with ui.card().classes(
            f'cursor-pointer hover:shadow-md transition-shadow duration-300 border-t-4 border-{color}-500 w-full') \
            .on('click', lambda: ui.navigate.to(route)):
        with ui.row().classes('items-center no-wrap'):
            ui.icon(icon_name, size='3rem', color=color).classes('mr-4')
            with ui.column().classes('gap-0'):
                ui.label(title).classes('text-xl font-bold text-gray-800')
                ui.label(description).classes('text-sm text-gray-500')


def render_home_page(auth_manager):
    # menu(auth_manager) # Розкоментуйте, якщо головна сторінка також містить верхнє меню

    with ui.column().classes('w-full items-center px-4 py-8 bg-gray-50 min-h-screen'):

        # --- Секція: ПОШУК ТА ДАНІ ---
        can_search = auth_manager.has_access('search', 'read')
        can_person = auth_manager.has_access('person', 'read')

        if can_search or can_person:
            ui.label('Пошук та База даних').classes(
                'text-xl font-bold w-full max-w-5xl mt-4 text-gray-600 border-b pb-2')
            with ui.grid().classes('w-full max-w-5xl gap-6 mt-4 grid-cols-1 md:grid-cols-3'):
                if can_person:
                    create_nav_card('Пошук О/С', 'Глобальний пошук по базі військовослужбовців', 'search', '/search', 'blue')
                if can_search:
                    create_nav_card('Пошук Документів', 'Файловий пошук довідок по папцям в мережі', 'search', '/doc_files', 'blue')

        # --- Секція: ДОКУМЕНТООБІГ ---
        can_doc_support = auth_manager.has_access('doc_support', 'read')
        can_doc_notif = auth_manager.has_access('doc_notif', 'read')

        if can_doc_support or can_doc_notif:
            ui.label('Документообіг').classes('text-xl font-bold w-full max-w-5xl mt-8 text-gray-600 border-b pb-2')
            with ui.grid().classes('w-full max-w-5xl gap-6 mt-4 grid-cols-1 md:grid-cols-3'):
                if can_doc_support:
                    create_nav_card('Супровідні листи', 'Масова генерація пакетів супровідних документів',
                                    'mark_email_unread', '/doc_support', 'green')
                if can_doc_notif:
                    create_nav_card('Довідки', 'Формування довідок та витягів (В розробці)', 'description',
                                    '/doc_notif', 'green')
                if can_person:
                    create_nav_card('На ДБР', 'Відправка справ на ДБР і очікування  ЄРДР', 'gavel', '/erdr', 'orange')

        # --- Секція: АНАЛІТИКА ---
        can_report_units = auth_manager.has_access('report_units', 'read')
        can_report_general = auth_manager.has_access('report_general', 'read')

        if can_report_units or can_report_general:
            ui.label('Аналітика та Звіти').classes(
                'text-xl font-bold w-full max-w-5xl mt-8 text-gray-600 border-b pb-2')
            with ui.grid().classes('w-full max-w-5xl gap-6 mt-4 grid-cols-1 md:grid-cols-3'):
                if can_report_units:
                    create_nav_card('Звіт по підрозділам', 'Статистика СЗЧ по підрозділах (Додаток 2)', 'bar_chart',
                                    '/report_units', 'purple')
                if can_report_general:
                    create_nav_card('Дублікати прізвищ', 'Звіт по прізвищам, які дублюються в системі', 'bar_chart',
                                    '/report_name_dups', 'purple')

        # --- Секція: СИСТЕМА (Тільки для Адміністраторів) ---
        can_admin = auth_manager.has_access('admin_panel', 'read')

        if can_admin:
            ui.label('Система').classes('text-xl font-bold w-full max-w-5xl mt-8 text-gray-600 border-b pb-2')
            with ui.grid().classes('w-full max-w-5xl gap-6 mt-4 grid-cols-1 md:grid-cols-3'):
                # Оскільки системні речі зав'язані на адмінку, пускаємо сюди тільки якщо є доступ до admin_panel
                create_nav_card('Налаштування Користувачів', 'Користувачі та їх ролі', 'supervisor_account',
                                '/admin/users', 'slate')
                create_nav_card('Налаштування Доступу', 'Права доступу до модулів системи', 'admin_panel_settings',
                                '/admin/permissions', 'slate')
                create_nav_card('Системні логи', 'Живий моніторинг роботи системи', 'terminal', '/logs',
                                'slate')