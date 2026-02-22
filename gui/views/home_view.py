from nicegui import ui

def create_nav_card(title: str, description: str, icon_name: str, route: str, color: str = 'blue'):
    """Функція для створення красивої клікабельної картки"""
    # cursor-pointer - робить курсор у вигляді руки при наведенні
    # hover:shadow-md - додає тінь при наведенні
    with ui.card().classes(
            f'cursor-pointer hover:shadow-md transition-shadow duration-300 border-t-4 border-{color}-500 w-full') \
            .on('click', lambda: ui.navigate.to(route)):
        with ui.row().classes('items-center no-wrap'):
            ui.icon(icon_name, size='3rem', color=color).classes('mr-4')
            with ui.column().classes('gap-0'):
                ui.label(title).classes('text-xl font-bold text-gray-800')
                ui.label(description).classes('text-sm text-gray-500')


def render_home_page():
    with ui.column().classes('w-full items-center px-4 py-8 bg-gray-50 min-h-screen'):
        # --- Секція: ПОШУК ТА ДАНІ ---
        ui.label('Пошук та База даних').classes('text-xl font-bold w-full max-w-5xl mt-4 text-gray-600 border-b pb-2')
        with ui.grid().classes('w-full max-w-5xl gap-6 mt-4 grid-cols-1 md:grid-cols-2'):
            create_nav_card('Пошук О/С', 'Глобальний пошук по базі військовослужбовців', 'search', '/search', 'blue')
            create_nav_card('Дані ЄРДР', 'Введення та пошук даних щодо СЗЧ/ЄРДР', 'gavel', '/erdr', 'orange')

        # --- Секція: ДОКУМЕНТООБІГ ---
        ui.label('Документообіг').classes('text-xl font-bold w-full max-w-5xl mt-8 text-gray-600 border-b pb-2')
        with ui.grid().classes('w-full max-w-5xl gap-6 mt-4 grid-cols-1 md:grid-cols-2'):
            create_nav_card('Супровідні листи', 'Масова генерація пакетів супровідних документів', 'mark_email_unread',
                            '/support_doc', 'green')
            create_nav_card('Довідки', 'Формування довідок та витягів (В розробці)', 'description', '/notif_doc',
                            'green')

        # --- Секція: АНАЛІТИКА ---
        ui.label('Аналітика та Звіти').classes('text-xl font-bold w-full max-w-5xl mt-8 text-gray-600 border-b pb-2')
        with ui.grid().classes('w-full max-w-5xl gap-6 mt-4 grid-cols-1 md:grid-cols-2'):
            create_nav_card('Звіт по підрозділам', 'Статистика СЗЧ по підрозділах (Додаток 2)', 'bar_chart', '/report',
                            'purple')

        # --- Секція: СИСТЕМА ---
        ui.label('Система').classes('text-xl font-bold w-full max-w-5xl mt-8 text-gray-600 border-b pb-2')
        with ui.grid().classes('w-full max-w-5xl gap-6 mt-4 grid-cols-1 md:grid-cols-2'):
            create_nav_card('Налаштування', 'Параметри проекту та системні довідники', 'settings', '/settings', 'slate')
            create_nav_card('Системні логи', 'Живий моніторинг роботи бота та парсерів', 'terminal', '/logs', 'slate')