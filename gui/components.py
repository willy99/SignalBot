from nicegui import ui, app, run
from gui.auth_routes import logout
from datetime import datetime
import urllib.parse
from gui.services.request_context import RequestContext
from config import CHECK_INBOX_EVERY_SEC

if not hasattr(app, 'alarmed_tasks'):
    app.alarmed_tasks = set()

def menu(auth_manager, ctx: RequestContext, task_controller):
    ui.add_head_html('<link rel="stylesheet" href="/static/style.css">')
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

            # --- 2. ІКОНКА ЗАДАЧ (Персональна) ---
            with ui.button(icon='assignment', on_click=lambda: ui.navigate.to('/tasks')).props(
                    'flat color=white text-color=gray-7'):

                # Створюємо елементи (поки порожні/сховані)
                # Додаємо props('floating') та text-xs, як у Inbox
                task_badge = ui.badge(color='red').props('floating').classes('text-xs')
                task_badge.set_visibility(False)

                with ui.tooltip().classes('bg-gray-800 text-white text-sm'):
                    with ui.column().classes('gap-0'):
                        lbl_new = ui.label('Нових задач: 0')
                        lbl_prog = ui.label('В роботі: 0')

                # Функція, яка буде викликатись кожні X секунд ДЛЯ ЦЬОГО ЮЗЕРА
                async def update_my_tasks():
                    try:
                        # Робимо запит до БД в окремому потоці, щоб не блокувати UI
                        new_c, prog_c = await run.io_bound(task_controller.get_my_task_counts, ctx)

                        if new_c > 0:
                            task_badge.set_text(str(new_c))
                            task_badge.set_visibility(True)
                        else:
                            task_badge.set_visibility(False)

                        # Оновлюємо тултип
                        lbl_new.set_text(f'Нових задач: {new_c}')
                        lbl_prog.set_text(f'В роботі: {prog_c}')

                        # ==========================================
                        # 2. ЛОГІКА БУДИЛЬНИКА (ALARM)
                        # ==========================================
                        alarms = await run.io_bound(task_controller.get_my_alarms, ctx)

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
                                    timeout=60000,
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
            can_doc_support = auth_manager.has_access('doc_support', 'read')
            can_doc_dbr = auth_manager.has_access('doc_dbr', 'read')
            can_doc_notif = auth_manager.has_access('doc_notif', 'read')
            can_search_person = auth_manager.has_access('person', 'read')

            # 1. Пошук
            if can_search_person:
                # Іконка лупи зліва, стрілочка вниз справа
                with ui.button('Пошук', icon='search').props('flat text-white icon-right="expand_more"'):
                    with ui.menu():
                        make_menu_item('Пошук подій', 'search', '/search')
                        make_menu_item('Батч пошук людей', 'manage_search', '/batch_search')
                        if can_doc_support:
                            make_menu_item('Швидкий пошук документів', 'find_in_page', '/doc_files')

            # 2. Документація
            if can_doc_support or can_doc_notif:
                with ui.button('Документація', icon='folder_copy').props('flat text-white icon-right="expand_more"'):
                    with ui.menu():
                        if can_doc_dbr:
                            make_menu_item('Відправка На ДБР', 'gavel', '/doc_dbr')
                        if can_doc_notif:
                            make_menu_item('Формування Довідок', 'description', '/doc_notif')
                        if can_doc_support:
                            make_menu_item('Формування Супроводів', 'drive_file_move', '/doc_support')

            # 4. Звіти
            can_report_units = auth_manager.has_access('report_units', 'read')
            can_report_general = auth_manager.has_access('report_general', 'read')
            if can_report_units or can_report_general:
                with ui.button('Звіти', icon='analytics').props('flat text-white icon-right="expand_more"'):
                    with ui.menu():
                        if can_report_units:
                            make_menu_item('Звіт по підрозділам', 'bar_chart', '/report_units')
                        if can_report_general:
                            make_menu_item('Дублікати прізвищ', 'people_outline', '/report_name_dups')
                        if can_report_general:
                            make_menu_item('Чекаємо на ЄРДР', 'gavel', '/report_waiting_erdr')

            # 5. Адмінка
            if auth_manager.has_access('admin_panel', 'read'):
                # Іконка щита переїхала наліво, а стрілочка вниз тепер справа
                with ui.button('Адмінка', icon='admin_panel_settings').props(
                        'flat text-yellow-400 font-bold icon-right="expand_more"'):
                    with ui.menu():
                        make_menu_item('Права доступу', 'vpn_key', '/admin/permissions')
                        make_menu_item('Користувачі', 'manage_accounts', '/admin/users')
                        make_menu_item('Логи', 'history', '/logs')

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