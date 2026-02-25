from nicegui import ui, app
from gui.auth_routes import logout
from datetime import datetime
import urllib.parse

def menu(auth_manager):
    ui.add_head_html('<link rel="stylesheet" href="../static/style.css">')
    user_role = app.storage.user.get('user_info', {}).get('role', '')

    with ui.header().classes('bg-slate-800 items-center justify-between'):
        with ui.row().classes('items-center gap-2'):
            ui.button('А0224, 🏃‍♂️ВТІКАЧІ 👨‍🚀', on_click=lambda: ui.navigate.to('/')) \
                .props('flat').classes('font-bold text-xl text-white normal-case')

            # 🌟 ІКОНКА INBOX
            with ui.button(icon='mail').props('flat round color="white"') \
                    .bind_visibility_from(app.inbox_state, 'count', backward=lambda x: x > 0) as inbox_btn:
                ui.badge().props('color="red" floating') \
                    .bind_text_from(app.inbox_state, 'count').classes('text-xs')
                with ui.menu().classes('w-80 max-h-96 overflow-y-auto') as inbox_menu:
                    pass

            def update_inbox_menu():
                inbox_menu.clear()
                with inbox_menu:
                    ui.label('Очікують в Inbox:').classes('font-bold text-gray-700 px-3 py-2 border-b w-full')

                    files = app.inbox_state.get('files', [])
                    if not files:
                        ui.label('Папка порожня').classes('text-gray-500 italic p-3')
                    else:
                        for f in files:
                            with ui.row().classes(
                                    'items-center gap-2 px-3 py-2 w-full hover:bg-gray-50 border-b border-gray-100 last:border-0'):
                                ui.icon('description', size='sm', color='gray-400')
                                ui.label(f).classes('text-sm text-gray-600 truncate').style('max-width: 240px;')
            inbox_btn.on('click', update_inbox_menu)

        with ui.row():

            # 🛡 Отримуємо дані поточного користувача з сесії
            user_info = app.storage.user.get('user_info', {})
            user_role = user_info.get('role', '')
            # Якщо є ПІБ - показуємо його, інакше показуємо логін, інакше "Гість"
            user_name = user_info.get('full_name') or user_info.get('username') or 'Гість'

            # 1. Пошук
            if auth_manager.has_access('person', 'read'):
                ui.button('Пошук', on_click=lambda: ui.navigate.to('/search')).props('flat text-white icon="manage_search"')

            can_doc_support = auth_manager.has_access('doc_support', 'read')
            can_doc_notif = auth_manager.has_access('doc_notif', 'read')

            if can_doc_support or can_doc_notif:
                with ui.button('Документація').props('flat text-white icon-right="expand_more"'):
                    with ui.menu():
                        if can_doc_notif:
                            ui.menu_item('Відправка На ДБР', on_click=lambda: ui.navigate.to('/erdr'))
                        if can_doc_notif:
                            ui.menu_item('Формування Довідок', on_click=lambda: ui.navigate.to('/doc_notif'))
                        if can_doc_support:
                            ui.menu_item('Формування Супроводів', on_click=lambda: ui.navigate.to('/doc_support'))
                        if can_doc_support:
                            ui.menu_item('Швидкий пошук документів', on_click=lambda: ui.navigate.to('/doc_files'))

            # 4. Звіти
            can_report_units = auth_manager.has_access('report_units', 'read')
            can_report_general = auth_manager.has_access('report_general', 'read')
            if can_report_units or can_report_general:
                with ui.button('Звіти').props('flat text-white icon-right="expand_more"'):
                    with ui.menu():
                        if can_report_units:
                            ui.menu_item('Звіт по підрозділам', on_click=lambda: ui.navigate.to('/report_units'))
                        if can_report_general:
                            ui.menu_item('Дублікати прізвищ', on_click=lambda: ui.navigate.to('/report_name_dups'))

            # 5. Адмінка
            if auth_manager.has_access('admin_panel', 'read'):
                with ui.button('Адмінка').props('flat text-yellow-400 font-bold icon-right="admin_panel_settings"'):
                    with ui.menu():
                        ui.menu_item('Права доступу', on_click=lambda: ui.navigate.to('/admin/permissions'))
                        ui.menu_item('Користувачі', on_click=lambda: ui.navigate.to('/admin/users'))
                        ui.menu_item('Логи', on_click=lambda: ui.navigate.to('/logs'))

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